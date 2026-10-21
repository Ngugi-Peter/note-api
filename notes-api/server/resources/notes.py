from flask import g, make_response, request
from flask_restful import Resource
from marshmallow import ValidationError

from config import db
from models import Note
from schemas import NoteSchema
from utils import login_required

DEFAULT_PER_PAGE = 10
MAX_PER_PAGE = 100


def find_own_note(note_id):
    """Look up a note by id, but only among the current user's notes.

    Another user's note is treated exactly like a missing one (None), so the
    caller answers 404 and never reveals that the note exists.
    """
    return Note.query.filter_by(id=note_id, user_id=g.current_user.id).first()


class NoteList(Resource):
    # Every method on this resource requires a logged-in user.
    method_decorators = [login_required]

    def get(self):
        """List the current user's notes, newest first, one page at a time."""
        page = request.args.get('page', default=1, type=int)
        per_page = request.args.get('per_page', default=DEFAULT_PER_PAGE, type=int)
        if page < 1 or not 1 <= per_page <= MAX_PER_PAGE:
            return {'error': f'page must be 1 or more and per_page must be '
                             f'between 1 and {MAX_PER_PAGE}.'}, 400

        pagination = (Note.query
                      .filter_by(user_id=g.current_user.id)
                      .order_by(Note.id.desc())
                      .paginate(page=page, per_page=per_page, error_out=False))

        return {
            'items': NoteSchema(many=True).dump(pagination.items),
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev,
        }, 200

    def post(self):
        """Create a note owned by the current user. 201 on success."""
        try:
            data = NoteSchema().load(request.get_json(silent=True) or {})
        except ValidationError as err:
            return {'errors': err.messages}, 422

        try:
            # user_id always comes from the session, never from the request.
            note = Note(user_id=g.current_user.id, **data)
            db.session.add(note)
            db.session.commit()
        except ValueError as err:
            db.session.rollback()
            return {'error': str(err)}, 422

        return NoteSchema().dump(note), 201


class NoteDetail(Resource):
    method_decorators = [login_required]

    def get(self, id):
        """Return one of the current user's notes, or 404."""
        note = find_own_note(id)
        if note is None:
            return {'error': 'Note not found.'}, 404
        return NoteSchema().dump(note), 200

    def patch(self, id):
        """Update title, content and/or category of an owned note."""
        note = find_own_note(id)
        if note is None:
            return {'error': 'Note not found.'}, 404

        try:
            data = NoteSchema().load(request.get_json(silent=True) or {}, partial=True)
        except ValidationError as err:
            return {'errors': err.messages}, 422
        if not data:
            return {'error': 'Provide at least one field to update.'}, 422

        try:
            for field, value in data.items():
                setattr(note, field, value)
            db.session.commit()
        except ValueError as err:
            db.session.rollback()
            return {'error': str(err)}, 422

        return NoteSchema().dump(note), 200

    def delete(self, id):
        """Delete an owned note. 204 on success."""
        note = find_own_note(id)
        if note is None:
            return {'error': 'Note not found.'}, 404
        db.session.delete(note)
        db.session.commit()
        return make_response('', 204)
