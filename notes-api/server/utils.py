"""Shared helpers for authentication."""
from functools import wraps

from flask import g, session

from config import db
from models import User


def get_current_user():
    """Return the logged-in User from the session, or None."""
    user_id = session.get('user_id')
    return db.session.get(User, user_id) if user_id else None


def login_required(func):
    """Reject the request with 401 unless a user is logged in.

    On success the user is stored on `g.current_user`, so route code can
    filter every query by the owner without reading the session itself.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        user = get_current_user()
        if user is None:
            session.pop('user_id', None)  # clear a stale id (e.g. deleted user)
            return {'error': 'Unauthorized'}, 401
        g.current_user = user
        return func(*args, **kwargs)
    return wrapper
