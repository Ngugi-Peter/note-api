"""Marshmallow schemas: validate incoming JSON and serialize outgoing JSON."""
from marshmallow import Schema, fields, validate

from models import PASSWORD_MIN, TITLE_MAX, USERNAME_MAX, USERNAME_MIN


class UserSchema(Schema):
    """What the API returns for a user. The password hash is never included."""
    id = fields.Int(dump_only=True)
    username = fields.Str()


class SignupSchema(Schema):
    username = fields.Str(required=True,
                          validate=validate.Length(min=USERNAME_MIN, max=USERNAME_MAX))
    password = fields.Str(required=True,
                          validate=validate.Length(min=PASSWORD_MIN, max=128))


class LoginSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)


class NoteSchema(Schema):
    """Input and output for notes.

    `id`, `created_at` and `user_id` are dump_only: a client that sends them
    gets a validation error, so a note's owner can never be set from a request.
    """
    id = fields.Int(dump_only=True)
    title = fields.Str(required=True, validate=validate.Length(min=1, max=TITLE_MAX))
    content = fields.Str(required=True, validate=validate.Length(min=1))
    category = fields.Str(load_default='general', validate=validate.Length(max=50))
    created_at = fields.DateTime(dump_only=True)
    user_id = fields.Int(dump_only=True)
