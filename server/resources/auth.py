from flask import make_response, request, session
from flask_restful import Resource
from marshmallow import ValidationError
from sqlalchemy.exc import IntegrityError

from config import db
from models import User
from schemas import LoginSchema, SignupSchema, UserSchema
from utils import get_current_user


class Signup(Resource):
    def post(self):
        """Create an account and log the new user in. 201 on success."""
        try:
            data = SignupSchema().load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return {'errors': err.messages}, 422

        if User.query.filter_by(username=data['username'].strip()).first():
            return {'error': 'Username is already taken.'}, 409

        try:
            user = User(username=data['username'])
            user.password_hash = data['password']
            db.session.add(user)
            db.session.commit()
        except ValueError as err:  # model validation
            db.session.rollback()
            return {'error': str(err)}, 422
        except IntegrityError:  # lost a race on the UNIQUE constraint
            db.session.rollback()
            return {'error': 'Username is already taken.'}, 409

        session['user_id'] = user.id
        return UserSchema().dump(user), 201


class Login(Resource):
    def post(self):
        """Log in with username and password. 200, or 401 if wrong."""
        try:
            data = LoginSchema().load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return {'errors': err.messages}, 422

        user = User.query.filter_by(username=data['username'].strip()).first()
        # Same message for unknown user and wrong password, so the API does
        # not reveal which usernames exist.
        if user is None or not user.authenticate(data['password']):
            return {'error': 'Invalid username or password.'}, 401

        session['user_id'] = user.id
        return UserSchema().dump(user), 200


class Logout(Resource):
    def delete(self):
        """End the session. 204 on success, 401 if nobody was logged in."""
        if get_current_user() is None:
            session.pop('user_id', None)
            return {'error': 'Unauthorized'}, 401
        session.pop('user_id', None)
        return make_response('', 204)


class CheckSession(Resource):
    def get(self):
        """Return the logged-in user (used by the frontend on page refresh)."""
        user = get_current_user()
        if user is None:
            return {'error': 'Unauthorized'}, 401
        return UserSchema().dump(user), 200
