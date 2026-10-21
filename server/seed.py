#!/usr/bin/env python3
"""Reset the database contents and create starter users and notes."""
import random

from faker import Faker

from config import app, db
from models import Note, User

fake = Faker()

DEMO_USERNAME = 'demo_user'
DEMO_PASSWORD = 'password123'
CATEGORIES = ['personal', 'work', 'ideas', 'journal']

with app.app_context():
    print('Clearing existing data...')
    # Notes first: they hold the foreign key to users.
    Note.query.delete()
    User.query.delete()
    db.session.commit()

    print('Creating users...')
    users = []
    demo = User(username=DEMO_USERNAME)
    demo.password_hash = DEMO_PASSWORD
    users.append(demo)

    used = {DEMO_USERNAME}
    while len(users) < 4:
        username = fake.user_name().lower()[:30]
        if len(username) < 3 or username in used:
            continue  # usernames must be unique
        used.add(username)
        user = User(username=username)
        user.password_hash = DEMO_PASSWORD  # known password, easy to log in
        users.append(user)
    db.session.add_all(users)
    db.session.flush()  # assigns ids

    print('Creating notes...')
    for index, user in enumerate(users):
        # The demo user gets enough notes to show pagination (10 per page).
        count = 25 if index == 0 else 6
        for _ in range(count):
            db.session.add(Note(
                user_id=user.id,
                title=fake.sentence(nb_words=4).rstrip('.'),
                content=fake.paragraph(nb_sentences=3),
                category=random.choice(CATEGORIES),
            ))

    db.session.commit()
    print(f'Done seeding {User.query.count()} users and {Note.query.count()} notes.')
    print(f'Log in with username "{DEMO_USERNAME}" and password "{DEMO_PASSWORD}".')
