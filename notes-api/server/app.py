from config import api, app
from resources.auth import CheckSession, Login, Logout, Signup
from resources.notes import NoteDetail, NoteList

# ---- Auth (public) ----
api.add_resource(Signup, '/signup')
api.add_resource(Login, '/login')
api.add_resource(Logout, '/logout')
api.add_resource(CheckSession, '/check_session', '/me')

# ---- Notes (login required) ----
api.add_resource(NoteList, '/notes')
api.add_resource(NoteDetail, '/notes/<int:id>')


@app.errorhandler(404)
def not_found(_error):
    return {'error': 'Not found.'}, 404


if __name__ == '__main__':
    app.run(port=5555, debug=True)
