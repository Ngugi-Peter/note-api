from sqlalchemy import CheckConstraint
from sqlalchemy.orm import validates

from config import bcrypt, db

USERNAME_MIN, USERNAME_MAX = 3, 30
PASSWORD_MIN = 6
TITLE_MAX = 100


class User(db.Model):
    """An account holder. Owns many notes."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    # Unique so a username can identify one account (and be used to log in).
    username = db.Column(db.String(USERNAME_MAX), nullable=False, unique=True)
    # Only the bcrypt hash is stored, never the plain-text password.
    _password_hash = db.Column('password_hash', db.String, nullable=False)

    # Deleting a user also deletes their notes.
    notes = db.relationship('Note', back_populates='user',
                            cascade='all, delete-orphan')

    __table_args__ = (
        CheckConstraint(f'length(username) >= {USERNAME_MIN}',
                        name='username_min_length'),
    )

    @property
    def password_hash(self):
        """Write-only: reading a password hash is never allowed."""
        raise AttributeError('Password hashes may not be viewed.')

    @password_hash.setter
    def password_hash(self, password):
        """Hash the plain-text password with bcrypt before storing it."""
        if not isinstance(password, str) or len(password) < PASSWORD_MIN:
            raise ValueError(f'Password must be at least {PASSWORD_MIN} characters.')
        self._password_hash = bcrypt.generate_password_hash(
            password.encode('utf-8')).decode('utf-8')

    def authenticate(self, password):
        """Return True if `password` matches the stored hash."""
        return bcrypt.check_password_hash(self._password_hash,
                                          password.encode('utf-8'))

    @validates('username')
    def validate_username(self, key, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Username is required.')
        value = value.strip()
        if not USERNAME_MIN <= len(value) <= USERNAME_MAX:
            raise ValueError(
                f'Username must be {USERNAME_MIN}-{USERNAME_MAX} characters.')
        return value

    def __repr__(self):
        return f'<User {self.id} {self.username}>'


class Note(db.Model):
    """A note that belongs to exactly one user."""
    __tablename__ = 'notes'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(TITLE_MAX), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, default='general')
    created_at = db.Column(db.DateTime, nullable=False,
                           server_default=db.func.now())
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    user = db.relationship('User', back_populates='notes')

    __table_args__ = (
        CheckConstraint('length(title) > 0', name='title_not_empty'),
    )

    @validates('title')
    def validate_title(self, key, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Title is required.')
        value = value.strip()
        if len(value) > TITLE_MAX:
            raise ValueError(f'Title must be at most {TITLE_MAX} characters.')
        return value

    @validates('content')
    def validate_content(self, key, value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Content is required.')
        return value.strip()

    @validates('category')
    def validate_category(self, key, value):
        value = (value or '').strip()
        return value or 'general'

    def __repr__(self):
        return f'<Note {self.id} {self.title!r} user={self.user_id}>'
