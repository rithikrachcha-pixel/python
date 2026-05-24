"""Flask application for AssessSim — internship assessment game simulator."""
import json
import os
import random
import sqlite3
from functools import wraps
from flask import Flask, g, jsonify, render_template, request, session
try:
    import anthropic as _anthropic_module
except ImportError:
    _anthropic_module = None

from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__)
app.secret_key = 'assessment-sim-secret-2024'
DATABASE = os.path.join(os.path.dirname(__file__), 'assesssim.db')


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
# Bot Competition & Leaderboard
# ---------------------------------------------------------------------------

BOT_PROFILES = [
    {'name': 'Alex Chen', 'school': '1st Year MORSE @ Warwick', 'avatar': 'AC'},
    {'name': 'Priya Patel', 'school': 'Final Year Economics @ LSE', 'avatar': 'PP'},
    {'name': 'James Thompson', 'school': '2nd Year CS @ UCL', 'avatar': 'JT'},
    {'name': 'Sophie Roberts', 'school': 'Grad, Goldman Sachs FO', 'avatar': 'SR'},
    {'name': 'Mohammed Al-Rashid', 'school': 'Final Year Physics @ Oxford', 'avatar': 'MA'},
    {'name': 'Emma Watson', 'school': '1st Year Maths and Economics @ LSE', 'avatar': 'EW'},
    {'name': 'Yuki Tanaka', 'school': '2nd Year Maths @ Cambridge', 'avatar': 'YT'},
    {'name': 'Liam O\'Brien', 'school': 'Final Year Engineering @ Imperial', 'avatar': 'LO'},
    {'name': 'Yuti Kumar', 'school': '1st Year E AND M  @ Oxford', 'avatar': 'YK'},
    {'name': 'Oscar Martinez', 'school': 'Intern, McKinsey', 'avatar': 'OM'},
    {'name': 'Isabella Romano', 'school': '2nd Year Finance @ Bocconi', 'avatar': 'IR'},
    {'name': 'Kai Williams', 'school': 'Final Year Law @ Cambridge', 'avatar': 'KW'},
    {'name': 'Zara Khan', 'school': '1st Year MORSE @ Oxford', 'avatar': 'ZK'},
    {'name': 'Lucas Bergmann', 'school': 'Analyst, Deutsche Bank', 'avatar': 'LB'},
    {'name': 'Nina Novak', 'school': '2nd Year Maths+CS @ MIT exchange', 'avatar': 'NN'},
    {'name': 'David James Wu', 'school': '1st Year Economics @ LSE', 'avatar': 'DJW'},
    {'name': 'Camila Silva', 'school': 'Final Year Business @ Warwick', 'avatar': 'CS'},
    {'name': 'Marcus Johnson', 'school': '2nd Year Engineering @ UCL', 'avatar': 'MJ'},
    {'name': 'Sienna Park', 'school': 'MORSE Graduate candidate', 'avatar': 'SP'},
    {'name': 'Ethan Brown', 'school': '1st Year PPE @ LSE', 'avatar': 'EB'},
    {'name': 'Violet Chen', 'school': 'Final Year Computer Science @ Cambridge', 'avatar': 'VC'},
    {'name': 'Angad Arya', 'school': '1st Year Econ @ Cambridge', 'avatar': 'NM'},
    {'name': 'Harper Taylor', 'school': 'Intern, goldman.com', 'avatar': 'HT'},
    {'name': 'Jay Shah', 'school': '1st Year CS @ Imperial', 'avatar': 'JG'},
    {'name': 'Garv Gupta', 'school': 'First Year Econ @ UCL', 'avatar': 'GG'},
    {'name': 'Arnav Sharma', 'school': '1st Year JMC @ Oxford', 'avatar': 'AS'},
    {'name': 'Mia Anderson', 'school': '1st Year MORSE @ Warwick', 'avatar': 'MA'},
    {'name': 'Leo Rossi', 'school': 'Analyst, Goldman Sachs', 'avatar': 'LR'},
    {'name': 'Olivia Delaney', 'school': 'Final Year economics @ LSE', 'avatar': 'OD'},
    {'name': 'Aurora Davis', 'school': '2nd Year JMC @ Imperial', 'avatar': 'AD'},
]

def generate_bot_score(difficulty_level, game_type='general'):  # pylint: disable=unused-argument
    """Generate a bot score using normal distribution based on difficulty tier.

    Args:
        difficulty_level: 'easy', 'average', 'above_average', 'cut_throat'
        game_type: type of game (for future context-specific scoring)

    Returns:
        float: score between 0-100
    """

    # Define difficulty tiers using mean and std deviation
    tiers = {
        'easy': {'mean': 45, 'std': 15},
        'average': {'mean': 65, 'std': 10},
        'above_average': {'mean': 82, 'std': 8},
        'cut_throat': {'mean': 94, 'std': 4},
    }

    tier = tiers.get(difficulty_level, tiers['average'])

    # Simple normal distribution approximation (Box-Muller)
    u1, u2 = random.random(), random.random()
    z = (-2 * (u1 ** 0.5)) * (2 * 3.14159 * u2) ** 0.5
    score = tier['mean'] + z * tier['std']

    # Clamp score to 0-100
    return max(0, min(100, score))

@app.route('/api/bot/profiles', methods=['GET'])
def get_bot_profiles():
    """Return a sample of bot profiles."""
    sample = random.sample(BOT_PROFILES, min(10, len(BOT_PROFILES)))
    return jsonify({'bots': sample})

@app.route('/api/bot/leaderboard', methods=['POST'])
def get_leaderboard():
    """Generate a competitive leaderboard based on user score and difficulty."""
    data = request.get_json()
    user_score = data.get('score', 0)
    difficulty = data.get('difficulty', 'average')
    game_type = data.get('game', 'general')
    count = data.get('count', 10)


    # Generate bot scores
    leaderboard = []

    # Add user entry
    leaderboard.append({
        'rank': 0,
        'name': 'You',
        'school': 'Your Profile',
        'score': user_score,
        'is_user': True,
        'avatar': 'YOU'
    })

    # Generate bots
    bots_to_show = random.sample(BOT_PROFILES, min(count, len(BOT_PROFILES)))
    for bot in bots_to_show:
        bot_score = generate_bot_score(difficulty, game_type)
        leaderboard.append({
            'rank': 0,
            'name': bot['name'],
            'school': bot['school'],
            'score': round(bot_score, 1),
            'is_user': False,
            'avatar': bot['avatar']
        })

    # Sort by score (descending) and assign ranks
    leaderboard.sort(key=lambda x: x['score'], reverse=True)
    for i, entry in enumerate(leaderboard):
        entry['rank'] = i + 1

    # Calculate percentile for user
    user_entry = next((e for e in leaderboard if e['is_user']), None)
    user_rank = user_entry['rank'] if user_entry else 0
    percentile = 100 * (1 - (user_rank - 1) / len(leaderboard))

    return jsonify({
        'leaderboard': leaderboard,
        'user_rank': user_rank,
        'total_candidates': len(leaderboard),
        'percentile': round(percentile, 1),
        'difficulty': difficulty
    })


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
# AI Question Generation
# ---------------------------------------------------------------------------

_QUESTION_PROMPTS = {
    'numerical': (
        'Generate 6 fresh SHL-style numerical reasoning questions. '
        'Each question must use a realistic business data table (company name, financial or operational metrics). '
        'Return a JSON object: {"questions":[{...},...]} where each question has: '
        'table:{title:string, headers:[string,...], rows:[[string,...],...]}, '
        'question:string, options:[string x5], answer:integer (0-indexed correct option), explanation:string. '
        'Make questions varied — percentages, ratios, absolute changes, projections. Ensure calculations are correct.'
    ),
    'verbal': (
        'Generate 9 fresh SHL-style verbal reasoning questions across 3 distinct passages (3 questions per passage). '
        'Topics: business, economics, technology or science. '
        'Return a JSON object: {"questions":[{...},...]} where each question has: '
        'passage:string (2-3 sentences), statement:string, '
        'answer:string (exactly "True", "False", or "Cannot Say"), explanation:string. '
        'Ensure a mix of True, False and Cannot Say answers. Explanations must reference the passage text.'
    ),
    'inductive': (
        'Generate 8 fresh inductive reasoning questions using number or letter patterns (no emoji). '
        'Return a JSON object: {"questions":[{...},...]} where each question has: '
        'type:string ("sequence" or "matrix3x3"), label:string, '
        'for sequence: sequence:[string x4 with last being "?"], options:[string x4], answer:integer (0-indexed), explanation:string. '
        'for matrix3x3: grid:[[string x3] x3 with bottom-right being "?"], options:[string x4], answer:integer, explanation:string. '
        'Use clear number sequences (Fibonacci, primes, doubling, arithmetic), letter patterns, or shape counts. '
        'Make patterns unambiguous with clear explanations.'
    ),
    'sjt': (
        'Generate 5 fresh Cappfinity-style situational judgement scenarios for a finance/consulting internship. '
        'Return a JSON object: {"questions":[{...},...]} where each question has: '
        'scenario:string (realistic workplace situation, 2-3 sentences), '
        'options:[string x5] (realistic response options), '
        'best:integer (0-indexed best response), worst:integer (0-indexed worst response), '
        'explanation:string (why best is best and why worst is worst). '
        'Scenarios should cover: stakeholder management, prioritisation, ethics, communication, teamwork.'
    ),
    'watson_glaser': (
        'Generate 10 fresh Watson Glaser critical thinking questions across all 5 types (2 each): '
        'Inference, Assumptions, Deductions, Interpretation, Evaluation. '
        'Return a JSON object: {"questions":[{...},...]} where each question has: '
        'type:string (one of the 5 types), stem:string (factual premise or argument), statement:string (claim to evaluate), '
        'opts:[string,...] (for Inference: ["True","Probably True","Insufficient Data","Probably False","False"], '
        'for Assumptions/Deductions/Interpretation: ["Conclusion Follows","Does Not Follow"], '
        'for Evaluation: ["Strong","Weak"]), '
        'ans:integer (0-indexed correct answer), exp:string (explanation). '
        'Vary topics: business, science, statistics, logic. Ensure logical correctness.'
    ),
    'coding': (
        'Generate 10 fresh computer science and programming questions suitable for a software engineering internship OA. '
        'Return a JSON object: {"questions":[{...},...]} where each question has: '
        'q:string (question, may include a short code snippet), opts:[string x4], ans:integer (0-indexed correct), '
        'exp:string (brief explanation). '
        'Cover: time/space complexity, data structures, algorithms, Python/JS output tracing, OOP concepts, '
        'system design fundamentals, SQL basics. Mix difficulty levels.'
    ),
}


@app.route('/api/generate-questions/<game_type>')
def api_generate_questions(game_type):
    """Generate fresh assessment questions via the Claude API."""
    if game_type not in _QUESTION_PROMPTS:
        return jsonify({'error': 'Unknown game type'}), 400

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return jsonify({'error': 'AI question generation not configured'}), 503

    if _anthropic_module is None:
        return jsonify({'error': 'anthropic package not installed'}), 503

    try:
        client = _anthropic_module.Anthropic(api_key=api_key)
        response = client.messages.create(
            model='claude-opus-4-7',
            max_tokens=8192,
            system=(
                'You are an expert assessment question generator for graduate and internship '
                'recruitment at top finance and consulting firms. '
                'Respond ONLY with a valid JSON object — no markdown fences, no explanation, just raw JSON.'
            ),
            messages=[{'role': 'user', 'content': _QUESTION_PROMPTS[game_type]}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown code fences if Claude added them despite instructions
        if raw.startswith('```'):
            raw = raw.split('```')[1]
            if raw.startswith('json'):
                raw = raw[4:]
        data = json.loads(raw)
        questions = data.get('questions', data) if isinstance(data, dict) else data
        return jsonify({'questions': questions})
    except json.JSONDecodeError:
        return jsonify({'error': 'Model returned invalid JSON'}), 500
    except Exception as exc:  # pylint: disable=broad-except
        return jsonify({'error': str(exc)}), 500


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

with app.app_context():
    init_db()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', debug=False, port=port)
