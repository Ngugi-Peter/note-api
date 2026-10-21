# Notes API

## Description

A secure Flask REST API for a personal notes app. Users sign up and log in with **session-based authentication**, and each user can create, read, update and delete **only their own notes**. The notes list is **paginated**.

- **Auth:** sessions (signed cookie) with passwords hashed using Flask-Bcrypt
- **Resource:** `Note` (`id`, `title`, `content`, `category`, `created_at`, `user_id`) that belongs to a `User`
- **Access control:** every notes route requires login (401 otherwise), and every query is filtered by the logged-in user. Another user's note behaves like a missing one (404)
- **Stack:** Flask, Flask-RESTful, Flask-SQLAlchemy, Flask-Migrate (SQLite), Flask-Bcrypt, Marshmallow, Faker, pytest

## Project structure

```
notes-api/
├── Pipfile
├── README.md
└── server/
    ├── app.py          # registers the routes
    ├── config.py       # Flask app, database, bcrypt, migrate, api
    ├── models.py       # User and Note models with validations
    ├── schemas.py      # Marshmallow validation and serialization
    ├── utils.py        # login_required and current-user helper
    ├── resources/
    │   ├── auth.py     # signup, login, logout, check_session
    │   └── notes.py    # notes CRUD with pagination
    ├── seed.py         # starter users and notes (Faker)
    └── test_app.py     # pytest suite
```

## Installation

1. Clone the repository and move into it:

   ```bash
   git clone https://github.com/Ngugi-Peter/notes-api.git
   cd notes-api
   ```

2. Install the dependencies and open the virtual environment:

   ```bash
   pipenv install --dev
   pipenv shell
   ```

3. Create the database with Flask-Migrate (run from `server/`):

   ```bash
   cd server
   export FLASK_APP=app.py
   flask db init
   flask db migrate -m "create users and notes tables"
   flask db upgrade head
   ```

   If a `migrations/` folder already exists, skip `flask db init`.

4. Seed the database (safe to re-run; it clears existing data first):

   ```bash
   python seed.py
   ```

   This creates 4 users and their notes. Every seeded user has the password `password123`. Log in as `demo_user`, who has 25 notes so pagination is easy to see.

> **Python version note:** the lab pins older package versions (Flask 2.2.2, pytest 7.2.0, ...). They are meant for Python 3.8 to 3.11. If `pipenv install` or the tests fail on a newer Python, use a 3.10 or 3.11 interpreter (`pipenv --python 3.10 install --dev`).

## Running the app

From the `server/` directory:

```bash
flask run -p 5555
```

or

```bash
python app.py
```

The API is served at `http://localhost:5555`.

## Endpoints

Send and receive JSON. Errors are returned as `{"error": "message"}` (one problem) or `{"errors": {...}}` (field validation).

### Auth (public)

| Method | Path | Description | Success | Errors |
|---|---|---|---|---|
| POST | `/signup` | Create an account and log in. Body: `username` (3-30 chars, unique), `password` (6+ chars) | 201 + user | 422 invalid or missing fields, 409 username taken |
| POST | `/login` | Log in. Body: `username`, `password` | 200 + user | 401 wrong username or password, 422 missing fields |
| DELETE | `/logout` | End the session | 204 | 401 if not logged in |
| GET | `/check_session` (alias `/me`) | Return the logged-in user. Used to stay logged in after a page refresh | 200 + user | 401 if not logged in |

### Notes (login required)

| Method | Path | Description | Success | Errors |
|---|---|---|---|---|
| GET | `/notes?page=1&per_page=10` | List your notes, newest first, paginated | 200 | 401, 400 bad page parameters |
| POST | `/notes` | Create a note. Body: `title`, `content`, optional `category` | 201 + note | 401, 422 invalid data |
| GET | `/notes/<id>` | Show one of your notes | 200 + note | 401, 404 |
| PATCH | `/notes/<id>` | Update `title`, `content` and/or `category` | 200 + note | 401, 404, 422 |
| DELETE | `/notes/<id>` | Delete one of your notes | 204 | 401, 404 |

**Pagination response** for `GET /notes`:

```json
{
  "items": [{ "id": 25, "title": "...", "content": "...", "category": "work",
              "created_at": "2026-10-21T00:00:00", "user_id": 1 }],
  "page": 1, "per_page": 10, "total": 25, "pages": 3,
  "has_next": true, "has_prev": false
}
```

`per_page` defaults to 10 and may be at most 100. A page past the end returns an empty `items` list.

**Security notes**
- A request can never set a note's owner: `user_id` is taken from the session, and sending `user_id` in the body returns 422.
- Another user's note returns 404, the same as a note that doesn't exist.
- Password hashes are never returned by any endpoint.

## Validations

- **User:** unique username (database `UNIQUE` constraint plus validation), 3-30 characters, minimum password length, bcrypt-hashed password stored in `password_hash` and never readable
- **Note:** title required (max 100), content required, owner required (foreign key to `users`)
- **Schemas (Marshmallow):** required fields, length limits, and dump-only fields (`id`, `created_at`, `user_id`) that clients cannot set

## Testing with Postman

Postman keeps cookies per domain, so after logging in the following requests are authenticated.

1. `POST /signup` with `{"username": "alice", "password": "password123"}` returns 201.
2. `GET /check_session` returns 200 with the user.
3. `POST /notes` with `{"title": "Test", "content": "Hello"}` returns 201.
4. `GET /notes` returns your notes with pagination fields.
5. `DELETE /logout` returns 204, then `GET /notes` returns 401.
6. Sign up a second user in a new Postman tab (or after clearing cookies) and confirm `GET /notes/<alice's note id>` returns 404.

## Automated tests (optional)

```bash
cd server
pytest -v
```

The suite covers signup, login, logout, check_session, password hashing, protected routes, CRUD, pagination, and access control in both directions between two users.

## Frontend

The backend works with a session-based frontend template. If the frontend runs on a different port, proxy API requests to `http://localhost:5555` so the session cookie is sent.
