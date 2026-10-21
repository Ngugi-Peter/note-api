import os

# Use a throwaway in-memory database for the tests.
os.environ['DATABASE_URI'] = 'sqlite:///:memory:'

import pytest
from sqlalchemy.exc import IntegrityError

import app as routes  # noqa: F401  (importing registers the routes)
from config import app, db
from models import Note, User


@pytest.fixture
def client():
    """A test client for user A, with fresh tables for every test."""
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


@pytest.fixture
def other_client(client):
    """A second client with its own cookies, for user B."""
    return app.test_client()


def signup(client, username='alice', password='password123'):
    return client.post('/signup', json={'username': username, 'password': password})


def make_note(client, **overrides):
    body = {'title': 'Groceries', 'content': 'Milk, eggs, bread', 'category': 'personal'}
    body.update(overrides)
    return client.post('/notes', json=body)


# ---------------- Sign up ----------------
def test_signup_creates_user_and_logs_in(client):
    res = signup(client)
    assert res.status_code == 201
    assert res.json['username'] == 'alice'
    assert 'password' not in res.json and 'password_hash' not in res.json
    assert client.get('/check_session').status_code == 200


def test_signup_duplicate_username_rejected(client):
    signup(client)
    assert signup(app.test_client()).status_code == 409


def test_signup_missing_or_short_fields_rejected(client):
    assert client.post('/signup', json={'username': 'alice'}).status_code == 422
    assert client.post('/signup', json={}).status_code == 422
    assert signup(client, password='abc').status_code == 422
    assert signup(client, username='al').status_code == 422


# ---------------- User model / passwords ----------------
def test_password_is_hashed_and_not_readable(client):
    signup(client)
    user = User.query.filter_by(username='alice').first()
    assert user._password_hash != 'password123'
    assert user._password_hash.startswith('$2')  # bcrypt
    with pytest.raises(AttributeError):
        user.password_hash
    assert user.authenticate('password123')
    assert not user.authenticate('wrong-password')


def test_username_unique_in_database(client):
    first = User(username='alice')
    first.password_hash = 'password123'
    db.session.add(first)
    db.session.commit()

    second = User(username='alice')
    second.password_hash = 'password123'
    db.session.add(second)
    with pytest.raises(IntegrityError):
        db.session.commit()
    db.session.rollback()


def test_username_validation():
    with pytest.raises(ValueError):
        User(username='   ')
    with pytest.raises(ValueError):
        User(username='ab')


# ---------------- Login / logout / check_session ----------------
def test_login_success_and_failure(client):
    signup(client)
    fresh = app.test_client()
    assert fresh.post('/login', json={'username': 'alice', 'password': 'nope'}).status_code == 401
    assert fresh.post('/login', json={'username': 'ghost', 'password': 'password123'}).status_code == 401
    assert fresh.post('/login', json={'username': 'alice'}).status_code == 422
    ok = fresh.post('/login', json={'username': 'alice', 'password': 'password123'})
    assert ok.status_code == 200 and ok.json['username'] == 'alice'


def test_check_session_logged_out_and_in(client):
    assert client.get('/check_session').status_code == 401
    signup(client)
    res = client.get('/check_session')
    assert res.status_code == 200 and res.json['username'] == 'alice'
    assert client.get('/me').status_code == 200


def test_logout_clears_session(client):
    signup(client)
    assert client.delete('/logout').status_code == 204
    assert client.get('/check_session').status_code == 401
    assert client.delete('/logout').status_code == 401


# ---------------- Protected routes ----------------
@pytest.mark.parametrize('method,url', [
    ('get', '/notes'),
    ('post', '/notes'),
    ('get', '/notes/1'),
    ('patch', '/notes/1'),
    ('delete', '/notes/1'),
])
def test_notes_routes_require_login(client, method, url):
    res = getattr(client, method)(url, json={'title': 'x', 'content': 'y'})
    assert res.status_code == 401
    assert res.json['error'] == 'Unauthorized'


# ---------------- Notes CRUD ----------------
def test_create_and_get_note(client):
    signup(client)
    res = make_note(client)
    assert res.status_code == 201
    assert res.json['title'] == 'Groceries'
    note_id = res.json['id']
    got = client.get(f'/notes/{note_id}')
    assert got.status_code == 200 and got.json['content'] == 'Milk, eggs, bread'


def test_create_note_validation(client):
    signup(client)
    assert client.post('/notes', json={'title': 'No content'}).status_code == 422
    assert make_note(client, title='').status_code == 422
    assert make_note(client, title='   ').status_code == 422
    # The owner cannot be set from the request body.
    assert make_note(client, user_id=999).status_code == 422


def test_update_note(client):
    signup(client)
    note_id = make_note(client).json['id']
    res = client.patch(f'/notes/{note_id}', json={'title': 'Shopping'})
    assert res.status_code == 200
    assert res.json['title'] == 'Shopping' and res.json['content'] == 'Milk, eggs, bread'
    assert client.patch(f'/notes/{note_id}', json={}).status_code == 422
    assert client.patch(f'/notes/{note_id}', json={'user_id': 5}).status_code == 422
    assert client.patch('/notes/9999', json={'title': 'x'}).status_code == 404


def test_delete_note(client):
    signup(client)
    note_id = make_note(client).json['id']
    assert client.delete(f'/notes/{note_id}').status_code == 204
    assert client.get(f'/notes/{note_id}').status_code == 404
    assert client.delete(f'/notes/{note_id}').status_code == 404


# ---------------- Pagination ----------------
def test_notes_are_paginated(client):
    signup(client)
    for i in range(12):
        make_note(client, title=f'Note {i}')

    first = client.get('/notes?page=1&per_page=5').json
    assert len(first['items']) == 5
    assert first['total'] == 12 and first['pages'] == 3
    assert first['has_next'] is True and first['has_prev'] is False

    last = client.get('/notes?page=3&per_page=5').json
    assert len(last['items']) == 2 and last['has_next'] is False

    assert len(client.get('/notes').json['items']) == 10  # default page size
    assert client.get('/notes?page=0').status_code == 400
    assert client.get('/notes?per_page=1000').status_code == 400


# ---------------- Users cannot touch each other's data ----------------
def test_users_cannot_access_each_others_notes(client, other_client):
    signup(client, 'alice')
    signup(other_client, 'bob')
    alice_note = make_note(client, title='Alice secret').json['id']
    bob_note = make_note(other_client, title='Bob secret').json['id']

    # Bob cannot read, edit or delete Alice's note...
    assert other_client.get(f'/notes/{alice_note}').status_code == 404
    assert other_client.patch(f'/notes/{alice_note}', json={'title': 'hacked'}).status_code == 404
    assert other_client.delete(f'/notes/{alice_note}').status_code == 404

    # ...and Alice cannot touch Bob's (the reverse direction).
    assert client.get(f'/notes/{bob_note}').status_code == 404
    assert client.patch(f'/notes/{bob_note}', json={'title': 'hacked'}).status_code == 404
    assert client.delete(f'/notes/{bob_note}').status_code == 404

    # Each user's list contains only their own notes.
    assert [n['title'] for n in client.get('/notes').json['items']] == ['Alice secret']
    assert [n['title'] for n in other_client.get('/notes').json['items']] == ['Bob secret']

    # Both notes are still intact.
    assert db.session.get(Note, alice_note).title == 'Alice secret'
    assert db.session.get(Note, bob_note).title == 'Bob secret'
