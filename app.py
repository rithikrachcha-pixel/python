"""Flask application for AssessSim — internship assessment game simulator."""
import json
import sqlite3
from functools import wraps
from flask import Flask, g, jsonify, render_template, request, session

from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'assessment-sim-secret-2024'
DATABASE = 'assesssim.db'


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    """Return the per-request SQLite connection, creating it if needed."""
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


@app.teardown_appcontext
def close_connection(exception):  # pylint: disable=unused-argument
    """Close the database connection at the end of each request."""
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


def init_db():
    """Create database tables if they do not already exist."""
    db = get_db()
    db.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TEXT DEFAULT (datetime('now'))
    )''')
    db.execute('''CREATE TABLE IF NOT EXISTS scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        game TEXT NOT NULL,
        score REAL NOT NULL,
        details TEXT,
        played_at TEXT DEFAULT (datetime('now')),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )''')
    db.commit()


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------

def login_required(f):
    """Decorator that returns 401 JSON if the user is not logged in."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 401
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Page routes
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    """Render the home page."""
    return render_template('index.html')


@app.route('/game/bart')
def bart():
    """Render the BART balloon risk game."""
    return render_template('bart.html')


@app.route('/game/gonogo')
def gonogo():
    """Render the Go/No-Go impulse control game."""
    return render_template('gonogo.html')


@app.route('/game/digit-span')
def digit_span():
    """Render the digit span working memory game."""
    return render_template('digit_span.html')


@app.route('/game/nback')
def nback():
    """Render the N-Back fluid intelligence game."""
    return render_template('nback.html')


@app.route('/game/numerical')
def numerical():
    """Render the SHL numerical reasoning test."""
    return render_template('numerical.html')


@app.route('/game/verbal')
def verbal():
    """Render the SHL verbal reasoning test."""
    return render_template('verbal.html')


@app.route('/game/inductive')
def inductive():
    """Render the SHL inductive reasoning test."""
    return render_template('inductive.html')


@app.route('/game/sjt')
def sjt():
    """Render the Cappfinity situational judgment test."""
    return render_template('sjt.html')


@app.route('/game/attention')
def attention():
    """Render the attention and focus game."""
    return render_template('attention.html')


@app.route('/results')
def results():
    """Render the results page with score data from query params."""
    score_data = request.args.get('data', '{}')
    return render_template('results.html', score_data=score_data)


# ---------------------------------------------------------------------------
# Auth API
# ---------------------------------------------------------------------------

@app.route('/api/register', methods=['POST'])
def api_register():
    """Register a new user account."""
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not username or not email or not password:
        return jsonify({'error': 'All fields are required'}), 400
    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    db = get_db()
    try:
        db.execute(
            'INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)',
            (username, email, generate_password_hash(password))
        )
        db.commit()
    except sqlite3.IntegrityError as e:
        field = 'Email' if 'email' in str(e) else 'Username'
        return jsonify({'error': f'{field} already registered'}), 409

    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    session['user_id'] = user['id']
    session['username'] = user['username']
    payload = {'id': user['id'], 'username': user['username'], 'email': user['email']}
    return jsonify({'user': payload})


@app.route('/api/login', methods=['POST'])
def api_login():
    """Log in with username and password."""
    data = request.get_json(silent=True) or {}
    username = (data.get('username') or '').strip()
    password = data.get('password') or ''

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    db = get_db()
    user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    if not user or not check_password_hash(user['password_hash'], password):
        return jsonify({'error': 'Invalid username or password'}), 401

    session['user_id'] = user['id']
    session['username'] = user['username']
    payload = {'id': user['id'], 'username': user['username'], 'email': user['email']}
    return jsonify({'user': payload})


@app.route('/api/logout', methods=['POST'])
def api_logout():
    """Log the current user out."""
    session.clear()
    return jsonify({'success': True})


@app.route('/api/me')
def api_me():
    """Return the currently logged-in user, or 401 if not logged in."""
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    db = get_db()
    user = db.execute('SELECT id, username, email FROM users WHERE id = ?',
                      (session['user_id'],)).fetchone()
    if not user:
        session.clear()
        return jsonify({'error': 'Not logged in'}), 401
    return jsonify({'user': dict(user)})


# ---------------------------------------------------------------------------
# Score API
# ---------------------------------------------------------------------------

@app.route('/api/save-score', methods=['POST'])
@login_required
def api_save_score():
    """Save a game score for the logged-in user."""
    data = request.get_json(silent=True) or {}
    game = (data.get('game') or '').strip()
    score = data.get('score')
    details = data.get('details')

    if not game or score is None:
        return jsonify({'error': 'game and score are required'}), 400

    try:
        score = float(score)
    except (TypeError, ValueError):
        return jsonify({'error': 'score must be a number'}), 400

    db = get_db()
    db.execute(
        'INSERT INTO scores (user_id, game, score, details) VALUES (?, ?, ?, ?)',
        (session['user_id'], game, score, json.dumps(details) if details else None)
    )
    db.commit()
    return jsonify({'success': True})


@app.route('/api/scores')
@login_required
def api_scores():
    """Return all scores for the logged-in user, newest first."""
    db = get_db()
    query = (
        'SELECT game, score, details, played_at FROM scores '
        'WHERE user_id = ? ORDER BY played_at DESC'
    )
    rows = db.execute(query, (session['user_id'],)).fetchall()
    scores = []
    for row in rows:
        scores.append({
            'game': row['game'],
            'score': row['score'],
            'details': json.loads(row['details']) if row['details'] else None,
            'played_at': row['played_at']
        })
    return jsonify({'scores': scores})


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True, port=5000)
