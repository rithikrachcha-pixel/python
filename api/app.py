import os
import sqlite3
import random
import string
import urllib.request
import urllib.error
import json
from functools import wraps

from flask import (
    Flask, g, request, session, jsonify,
    render_template, redirect, url_for, abort,
)
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "wc2026-dev-secret")

DATABASE = os.path.join(os.path.dirname(__file__), "fantasy.db")
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "dev-token")

DATABASE_URL = os.environ.get('DATABASE_URL')
IS_PG = bool(DATABASE_URL)

if IS_PG:
    import psycopg2
    import psycopg2.extras

ROUND_BONUS = {"win": 5, "r32": 8, "r16": 10, "qf": 20, "sf": 30, "final": 50, "winner": 100}
GOAL_PTS = {"GK": 6, "DEF": 6, "MID": 5, "FWD": 4}
CS_PTS = {"GK": 4, "DEF": 4, "MID": 1, "FWD": 0}
FORMATION_POSITIONS = {
    "4-3-3": {"DEF": 4, "MID": 3, "FWD": 3},
    "4-4-2": {"DEF": 4, "MID": 4, "FWD": 2},
    "3-5-2": {"DEF": 3, "MID": 5, "FWD": 2},
    "3-4-3": {"DEF": 3, "MID": 4, "FWD": 3},
    "5-3-2": {"DEF": 5, "MID": 3, "FWD": 2},
}
BUDGET = 150.0


def get_db():
    if 'db' not in g:
        if IS_PG:
            conn = psycopg2.connect(DATABASE_URL)
            g.db = conn
        else:
            g.db = sqlite3.connect(DATABASE)
            g.db.row_factory = sqlite3.Row
    return g.db


def db_exec(sql, params=()):
    db = get_db()
    if IS_PG:
        sql = sql.replace('?', '%s')
        cur = db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur.execute(sql, list(params) if params else None)
        return cur
    return db.execute(sql, params)


def db_commit():
    get_db().commit()


@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required"}), 401
            return redirect(url_for("index"))
        return f(*args, **kwargs)
    return wrapper


def calc_player_points(p, backed_nation, is_captain=False, captain_boost=1):
    if isinstance(p, sqlite3.Row):
        p = dict(p)
    pos = p["position"]
    base = (
        p["goals"] * GOAL_PTS.get(pos, 4)
        + p["assists"] * 3
        + p["clean_sheets"] * CS_PTS.get(pos, 0)
        + (p["saves"] // 3)
        - p["yellow_cards"]
        - p["red_cards"] * 3
    )
    multiplier = 1.5 if backed_nation and p["nation"] == backed_nation else 1.0
    points = round(base * multiplier, 1)
    if is_captain:
        points = round(points * captain_boost, 1)
    return {"base": base, "multiplier": multiplier, "points": points, "is_captain": is_captain, "captain_boost": captain_boost if is_captain else 1}


def progression_bonus(nation, db=None):
    if not nation:
        return 0, []
    rows = db_exec(
        "SELECT round FROM tournament_rounds WHERE nation=?", (nation,)
    ).fetchall()
    bonus = sum(ROUND_BONUS.get(r["round"], 0) for r in rows)
    return bonus, [r["round"] for r in rows]


def user_total_points(user_id, db):
    user = db_exec("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        return 0
    backed = user["backed_nation"]
    captain_id = user["captain_id"] if "captain_id" in (user.keys() if hasattr(user, 'keys') else user) else None
    active_booster = user["active_booster"] if "active_booster" in (user.keys() if hasattr(user, 'keys') else user) else None
    include_bench = active_booster == "bench_boost"
    bench_filter = "" if include_bench else " AND us.is_bench=0"
    rows = db_exec(
        f"""SELECT p.*, us.is_bench FROM players p
           JOIN user_squad us ON p.id = us.player_id
           WHERE us.user_id=?{bench_filter}""",
        (user_id,),
    ).fetchall()
    player_pts = 0.0
    for r in rows:
        d = dict(r)
        is_cap = captain_id is not None and d["id"] == captain_id
        if is_cap and active_booster == "triple_captain":
            boost = 3
        elif is_cap:
            boost = 2
        else:
            boost = 1
        player_pts += calc_player_points(d, backed or "", is_captain=is_cap, captain_boost=boost)["points"]
    bonus, _ = progression_bonus(backed, db)
    return round(player_pts + bonus, 1)


def make_league_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


# ─── Pages ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    try:
        db_exec(
            "INSERT INTO users (username, password_hash) VALUES (?,?)",
            (username, generate_password_hash(password)),
        )
        db_commit()
    except Exception:
        return jsonify({"error": "Username already taken"}), 409
    user = db_exec("SELECT id FROM users WHERE username=?", (username,)).fetchone()
    session["user_id"] = user["id"]
    session["username"] = username
    # New user: squad not locked, go to team-builder
    return jsonify({"ok": True, "redirect": "/team-builder"})


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    user = db_exec(
        "SELECT * FROM users WHERE username=?", (data.get("username", ""),)
    ).fetchone()
    if not user or not check_password_hash(user["password_hash"], data.get("password", "")):
        return jsonify({"error": "Invalid username or password"}), 401
    session["user_id"] = user["id"]
    session["username"] = user["username"]
    # Redirect based on squad status
    redirect_url = "/dashboard" if user["squad_locked"] else "/team-builder"
    return jsonify({"ok": True, "redirect": redirect_url})


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))


@app.route("/team-builder")
@login_required
def team_builder():
    user = db_exec("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if not user:
        session.clear()
        return redirect(url_for("index"))
    if user["squad_locked"]:
        return redirect(url_for("dashboard"))
    return render_template("team_builder.html", username=session["username"])


@app.route("/dashboard")
@login_required
def dashboard():
    user = db_exec("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if not user:
        session.clear()
        return redirect(url_for("index"))
    if not user["squad_locked"]:
        return redirect(url_for("team_builder"))
    return render_template("dashboard.html", username=session["username"])


@app.route("/leagues")
@login_required
def leagues():
    user_id = session["user_id"]
    my_leagues = db_exec(
        """SELECT l.*, u.username as owner_name,
           (SELECT COUNT(*) FROM league_members lm2 WHERE lm2.league_id=l.id) as member_count
           FROM leagues l
           JOIN league_members lm ON lm.league_id=l.id
           LEFT JOIN users u ON u.id=l.owner_id
           WHERE lm.user_id=?
           ORDER BY l.created_at DESC""",
        (user_id,),
    ).fetchall()
    return render_template("leagues.html", username=session["username"],
                           my_leagues=[dict(r) for r in my_leagues])


@app.route("/league/<code>")
@login_required
def league_detail(code):
    league = db_exec("SELECT * FROM leagues WHERE code=?", (code.upper(),)).fetchone()
    if not league:
        return redirect(url_for("leagues"))
    return render_template("league_detail.html", username=session["username"],
                           league=dict(league))


# ─── Data APIs ────────────────────────────────────────────────────────────────

@app.route("/api/players")
def api_players():
    q = "SELECT * FROM players WHERE 1=1"
    params = []
    if request.args.get("position"):
        q += " AND position=?"
        params.append(request.args["position"])
    if request.args.get("nation"):
        q += " AND nation=?"
        params.append(request.args["nation"])
    if request.args.get("max_price"):
        q += " AND price<=?"
        params.append(float(request.args["max_price"]))
    if request.args.get("search"):
        q += " AND name LIKE ?"
        params.append("%" + request.args["search"] + "%")
    rows = db_exec(q + " ORDER BY price DESC, name", params).fetchall()

    backed = None
    if "user_id" in session:
        u = db_exec("SELECT backed_nation FROM users WHERE id=?", (session["user_id"],)).fetchone()
        backed = u["backed_nation"] if u else None

    out = []
    for r in rows:
        d = dict(r)
        d["points"] = calc_player_points(d, backed or "")["points"]
        out.append(d)
    return jsonify(out)


@app.route("/api/nations")
def api_nations():
    rows = db_exec(
        "SELECT nation, grp FROM players GROUP BY nation, grp ORDER BY grp, nation"
    ).fetchall()
    return jsonify([{"nation": r["nation"], "group": r["grp"]} for r in rows])


@app.route("/api/squad", methods=["GET", "POST"])
@login_required
def api_squad():
    user = db_exec("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if not user:
        return jsonify({"error": "User not found"}), 404

    if request.method == "GET":
        rows = db_exec(
            """SELECT p.*, us.is_bench FROM players p
               JOIN user_squad us ON p.id = us.player_id
               WHERE us.user_id=?""",
            (session["user_id"],),
        ).fetchall()
        backed = user["backed_nation"]
        squad = []
        for r in rows:
            d = dict(r)
            pts = calc_player_points(d, backed or "")
            d["points"] = pts["points"]
            d["multiplier"] = pts["multiplier"]
            squad.append(d)
        user_dict = dict(user)
        return jsonify({
            "formation": user["formation"],
            "backed_nation": backed,
            "budget_remaining": user["budget_remaining"],
            "locked": bool(user["squad_locked"]),
            "players": squad,
            "captain_id": user_dict.get("captain_id"),
            "used_triple_captain": bool(user_dict.get("used_triple_captain", 0)),
            "used_bench_boost": bool(user_dict.get("used_bench_boost", 0)),
            "active_booster": user_dict.get("active_booster"),
        })

    # POST: save squad
    if user["squad_locked"]:
        return jsonify({"error": "Your squad is already locked for the tournament"}), 403

    data = request.get_json(silent=True) or {}
    starting = data.get("starting_ids", [])
    bench = data.get("bench_ids", [])
    formation = data.get("formation", "4-3-3")
    backed_nation = (data.get("backed_nation") or "").strip()

    if formation not in FORMATION_POSITIONS:
        return jsonify({"error": "Invalid formation"}), 400
    if len(starting) != 11:
        return jsonify({"error": f"Starting XI must have exactly 11 players (got {len(starting)})"}), 400
    if len(bench) != 3:
        return jsonify({"error": f"Bench must have exactly 3 players (got {len(bench)})"}), 400
    all_ids = starting + bench
    if len(set(all_ids)) != 14:
        return jsonify({"error": "Duplicate players are not allowed"}), 400

    placeholders = ",".join("?" * len(all_ids))
    pdb = {
        r["id"]: dict(r)
        for r in db_exec(
            f"SELECT * FROM players WHERE id IN ({placeholders})", all_ids
        ).fetchall()
    }
    if len(pdb) != 14:
        return jsonify({"error": "One or more player IDs are invalid"}), 400

    total_cost = round(sum(pdb[i]["price"] for i in all_ids), 1)
    if total_cost > BUDGET:
        return jsonify({"error": f"Over budget: ${total_cost:.1f}M > ${BUDGET:.0f}M"}), 400

    gk = sum(1 for i in starting if pdb[i]["position"] == "GK")
    if gk != 1:
        return jsonify({"error": "Starting XI must have exactly 1 goalkeeper"}), 400
    for pos, need in FORMATION_POSITIONS[formation].items():
        have = sum(1 for i in starting if pdb[i]["position"] == pos)
        if have != need:
            return jsonify({"error": f"{formation} needs {need} {pos}, you have {have}"}), 400

    nations = {r["nation"] for r in db_exec("SELECT DISTINCT nation FROM players").fetchall()}
    if backed_nation not in nations:
        return jsonify({"error": "Please pick a valid nation to back"}), 400

    db_exec("DELETE FROM user_squad WHERE user_id=?", (session["user_id"],))
    for pid in starting:
        db_exec(
            "INSERT INTO user_squad (user_id, player_id, is_bench) VALUES (?,?,0)",
            (session["user_id"], pid),
        )
    for pid in bench:
        db_exec(
            "INSERT INTO user_squad (user_id, player_id, is_bench) VALUES (?,?,1)",
            (session["user_id"], pid),
        )
    db_exec(
        "UPDATE users SET backed_nation=?, formation=?, squad_locked=1, budget_remaining=? WHERE id=?",
        (backed_nation, formation, round(BUDGET - total_cost, 1), session["user_id"]),
    )
    db_commit()
    return jsonify({"ok": True, "budget_remaining": round(BUDGET - total_cost, 1)})


@app.route("/api/set-captain", methods=["POST"])
@login_required
def api_set_captain():
    data = request.get_json(silent=True) or {}
    player_id = data.get("player_id")
    if not player_id:
        return jsonify({"error": "player_id required"}), 400
    # Check player is in user's starting XI
    row = db_exec(
        "SELECT id FROM user_squad WHERE user_id=? AND player_id=? AND is_bench=0",
        (session["user_id"], player_id),
    ).fetchone()
    if not row:
        return jsonify({"error": "Player is not in your starting XI"}), 400
    db_exec("UPDATE users SET captain_id=? WHERE id=?", (player_id, session["user_id"]))
    db_commit()
    return jsonify({"ok": True, "captain_id": player_id})


@app.route("/api/activate-booster", methods=["POST"])
@login_required
def api_activate_booster():
    data = request.get_json(silent=True) or {}
    booster = data.get("booster")
    if booster not in ("triple_captain", "bench_boost"):
        return jsonify({"error": "Invalid booster. Use 'triple_captain' or 'bench_boost'"}), 400
    user = db_exec("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if not user:
        return jsonify({"error": "User not found"}), 404
    user_dict = dict(user)
    if booster == "triple_captain" and user_dict.get("used_triple_captain"):
        return jsonify({"error": "Triple Captain booster already used"}), 400
    if booster == "bench_boost" and user_dict.get("used_bench_boost"):
        return jsonify({"error": "Bench Boost booster already used"}), 400
    used_col = "used_triple_captain" if booster == "triple_captain" else "used_bench_boost"
    db_exec(
        f"UPDATE users SET {used_col}=1, active_booster=? WHERE id=?",
        (booster, session["user_id"]),
    )
    db_commit()
    return jsonify({"ok": True, "active_booster": booster})


@app.route("/api/points")
@login_required
def api_points():
    user = db_exec("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()
    if not user:
        return jsonify({"error": "User not found"}), 404
    backed = user["backed_nation"]
    user_dict = dict(user)
    captain_id = user_dict.get("captain_id")
    active_booster = user_dict.get("active_booster")
    rows = db_exec(
        """SELECT p.* FROM players p
           JOIN user_squad us ON p.id = us.player_id
           WHERE us.user_id=? AND us.is_bench=0""",
        (session["user_id"],),
    ).fetchall()

    breakdown = []
    total = 0.0
    for r in rows:
        d = dict(r)
        is_cap = captain_id is not None and d["id"] == captain_id
        if is_cap and active_booster == "triple_captain":
            boost = 3
        elif is_cap:
            boost = 2
        else:
            boost = 1
        pts = calc_player_points(d, backed or "", is_captain=is_cap, captain_boost=boost)
        breakdown.append({
            "name": d["name"], "nation": d["nation"], "position": d["position"],
            "club": d["club"], "goals": d["goals"], "assists": d["assists"],
            "clean_sheets": d["clean_sheets"], "saves": d["saves"],
            "yellow_cards": d["yellow_cards"], "red_cards": d["red_cards"],
            "base_points": pts["base"], "multiplier": pts["multiplier"],
            "points": pts["points"], "is_captain": is_cap, "captain_boost": pts["captain_boost"],
        })
        total += pts["points"]

    bonus, stages = progression_bonus(backed, None)
    return jsonify({
        "total": round(total + bonus, 1),
        "player_points": round(total, 1),
        "progression_bonus": bonus,
        "backed_nation": backed,
        "progression_stages": stages,
        "breakdown": sorted(breakdown, key=lambda x: x["points"], reverse=True),
    })


@app.route("/api/leaderboard")
def api_leaderboard():
    users = db_exec(
        "SELECT id, username, backed_nation FROM users WHERE squad_locked=1"
    ).fetchall()
    results = []
    for u in users:
        rows = db_exec(
            """SELECT p.* FROM players p
               JOIN user_squad us ON p.id = us.player_id
               WHERE us.user_id=? AND us.is_bench=0""",
            (u["id"],),
        ).fetchall()
        player_pts = sum(
            calc_player_points(dict(r), u["backed_nation"] or "")["points"] for r in rows
        )
        bonus, _ = progression_bonus(u["backed_nation"], None)
        results.append({
            "username": u["username"],
            "backed_nation": u["backed_nation"],
            "player_points": round(player_pts, 1),
            "progression_bonus": bonus,
            "total": round(player_pts + bonus, 1),
        })
    results.sort(key=lambda x: x["total"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return jsonify(results[:50])


@app.route("/api/fixtures")
def api_fixtures():
    rows = db_exec("SELECT * FROM fixtures ORDER BY match_date, id").fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/tournament")
def api_tournament():
    rows = db_exec("SELECT * FROM tournament_rounds ORDER BY achieved_at, id").fetchall()
    return jsonify([dict(r) for r in rows])


# ─── League APIs ──────────────────────────────────────────────────────────────

@app.route("/api/leagues/create", methods=["POST"])
@login_required
def api_league_create():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "League name required"}), 400
    if len(name) > 50:
        return jsonify({"error": "League name too long (max 50 chars)"}), 400

    for _ in range(10):
        code = make_league_code()
        exists = db_exec("SELECT id FROM leagues WHERE code=?", (code,)).fetchone()
        if not exists:
            break

    db_exec(
        "INSERT INTO leagues (name, code, owner_id) VALUES (?,?,?)",
        (name, code, session["user_id"]),
    )
    league = db_exec("SELECT id FROM leagues WHERE code=?", (code,)).fetchone()
    db_exec(
        "INSERT INTO league_members (league_id, user_id) VALUES (?,?)",
        (league["id"], session["user_id"]),
    )
    db_commit()
    return jsonify({"ok": True, "code": code, "name": name})


@app.route("/api/leagues/join", methods=["POST"])
@login_required
def api_league_join():
    data = request.get_json(silent=True) or {}
    code = (data.get("code") or "").strip().upper()
    if not code:
        return jsonify({"error": "League code required"}), 400

    league = db_exec("SELECT * FROM leagues WHERE code=?", (code,)).fetchone()
    if not league:
        return jsonify({"error": "League not found — check the code and try again"}), 404

    already = db_exec(
        "SELECT id FROM league_members WHERE league_id=? AND user_id=?",
        (league["id"], session["user_id"]),
    ).fetchone()
    if already:
        return jsonify({"error": "You're already in this league"}), 409

    db_exec(
        "INSERT INTO league_members (league_id, user_id) VALUES (?,?)",
        (league["id"], session["user_id"]),
    )
    db_commit()
    return jsonify({"ok": True, "code": code, "name": league["name"]})


@app.route("/api/leagues/<code>")
@login_required
def api_league_detail(code):
    league = db_exec("SELECT * FROM leagues WHERE code=?", (code.upper(),)).fetchone()
    if not league:
        return jsonify({"error": "League not found"}), 404

    members = db_exec(
        """SELECT u.id, u.username, u.backed_nation FROM users u
           JOIN league_members lm ON lm.user_id=u.id
           WHERE lm.league_id=? AND u.squad_locked=1""",
        (league["id"],),
    ).fetchall()

    results = []
    for u in members:
        rows = db_exec(
            """SELECT p.* FROM players p
               JOIN user_squad us ON p.id = us.player_id
               WHERE us.user_id=? AND us.is_bench=0""",
            (u["id"],),
        ).fetchall()
        player_pts = sum(
            calc_player_points(dict(r), u["backed_nation"] or "")["points"] for r in rows
        )
        bonus, _ = progression_bonus(u["backed_nation"], None)
        results.append({
            "username": u["username"],
            "backed_nation": u["backed_nation"],
            "player_points": round(player_pts, 1),
            "progression_bonus": bonus,
            "total": round(player_pts + bonus, 1),
        })

    results.sort(key=lambda x: x["total"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1

    pending = db_exec(
        """SELECT u.username FROM users u
           JOIN league_members lm ON lm.user_id=u.id
           WHERE lm.league_id=? AND u.squad_locked=0""",
        (league["id"],),
    ).fetchall()

    return jsonify({
        "name": league["name"],
        "code": league["code"],
        "owner_id": league["owner_id"],
        "leaderboard": results,
        "pending": [r["username"] for r in pending],
        "member_count": len(results) + len(pending),
    })


@app.route("/api/leagues/my")
@login_required
def api_my_leagues():
    rows = db_exec(
        """SELECT l.name, l.code,
           (SELECT COUNT(*) FROM league_members lm2 WHERE lm2.league_id=l.id) as member_count
           FROM leagues l
           JOIN league_members lm ON lm.league_id=l.id
           WHERE lm.user_id=?
           ORDER BY l.created_at DESC""",
        (session["user_id"],),
    ).fetchall()
    return jsonify([dict(r) for r in rows])


# ─── Admin ────────────────────────────────────────────────────────────────────

def _require_admin():
    if request.headers.get("X-Admin-Token") != ADMIN_TOKEN:
        abort(403)


@app.route("/admin/update-stats", methods=["POST"])
def admin_update_stats():
    _require_admin()
    d = request.get_json(silent=True) or {}
    db_exec(
        """UPDATE players SET goals=?, assists=?, clean_sheets=?,
           yellow_cards=?, red_cards=?, saves=? WHERE id=?""",
        (d.get("goals", 0), d.get("assists", 0), d.get("clean_sheets", 0),
         d.get("yellow_cards", 0), d.get("red_cards", 0), d.get("saves", 0),
         d["player_id"]),
    )
    db_commit()
    return jsonify({"ok": True})


@app.route("/admin/update-fixture", methods=["POST"])
def admin_update_fixture():
    _require_admin()
    d = request.get_json(silent=True) or {}
    db_exec(
        "UPDATE fixtures SET home_score=?, away_score=?, played=1 WHERE id=?",
        (d["home_score"], d["away_score"], d["fixture_id"]),
    )
    fx = db_exec("SELECT * FROM fixtures WHERE id=?", (d["fixture_id"],)).fetchone()
    if fx and fx["stage"] == "group":
        hs, as_ = d["home_score"], d["away_score"]
        winner = fx["home_team"] if hs > as_ else fx["away_team"] if as_ > hs else None
        if winner:
            db_exec(
                "INSERT INTO tournament_rounds (nation, round) VALUES (?, 'win')",
                (winner,),
            )
    db_commit()
    return jsonify({"ok": True})


@app.route("/admin/advance", methods=["POST"])
def admin_advance():
    _require_admin()
    d = request.get_json(silent=True) or {}
    nation, rnd = d.get("nation"), d.get("round")
    if rnd not in ROUND_BONUS:
        return jsonify({"error": "Invalid round"}), 400
    db_exec(
        "INSERT INTO tournament_rounds (nation, round) VALUES (?,?)", (nation, rnd)
    )
    db_commit()
    return jsonify({"ok": True})


def auto_seed():
    """Seed the DB on first deploy if empty (for Postgres/Vercel)."""
    try:
        from init_db import (
            SCHEMA_SQLITE, SCHEMA_PG, seed_players, seed_fixtures,
            seed_demo_stats, seed_demo_progression, PgAdapter, validate_squads
        )
        import sqlite3 as _sq3
        if IS_PG:
            import psycopg2 as _pg
            conn = _pg.connect(DATABASE_URL)
            db = PgAdapter(conn)
            for stmt in SCHEMA_PG.split(';'):
                s = stmt.strip()
                if s:
                    try:
                        db.execute(s)
                        db.commit()
                    except Exception:
                        conn.rollback()
        else:
            conn = _sq3.connect(DATABASE)
            conn.row_factory = _sq3.Row
            db = conn
            conn.executescript(SCHEMA_SQLITE)

        # Migrations: add new columns if not exist
        for migration_sql in [
            "ALTER TABLE users ADD COLUMN captain_id INTEGER",
            "ALTER TABLE users ADD COLUMN used_triple_captain INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN used_bench_boost INTEGER DEFAULT 0",
            "ALTER TABLE users ADD COLUMN active_booster TEXT",
        ]:
            try:
                db.execute(migration_sql)
                db.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

        already = db.execute("SELECT COUNT(*) FROM players").fetchone()
        count = already[0] if isinstance(already, (list, tuple)) else already["count"]
        if count == 0:
            validate_squads()
            seed_players(db)
            seed_fixtures(db)
            seed_demo_stats(db)
            seed_demo_progression(db)
            db.commit()
            app.logger.info("DB seeded successfully.")
        conn.close()
    except Exception as e:
        app.logger.warning(f"Auto-seed skipped: {e}")


_seeded = False


@app.before_request
def seed_once():
    global _seeded
    if not _seeded:
        _seeded = True
        auto_seed()


@app.route("/admin/wipe-users")
def wipe_users():
    token = request.args.get("token", "")
    if token != ADMIN_TOKEN:
        abort(403)
    db_exec("DELETE FROM user_squad")
    db_exec("DELETE FROM league_members")
    db_exec("DELETE FROM leagues")
    db_exec("DELETE FROM users")
    get_db().commit()
    return jsonify({"ok": True, "msg": "All users wiped."})


@app.route("/admin/reseed")
def admin_reseed():
    token = request.args.get("token", "")
    if token != ADMIN_TOKEN:
        abort(403)
    try:
        from init_db import (seed_players, seed_fixtures,
                             validate_squads, PgAdapter)

        class DbExecAdapter:
            """Wrap app's db_exec so init_db seeder functions can use it."""
            def execute(self, sql, params=()):
                return db_exec(sql, params)
            def fetchall(self):
                return []
            def fetchone(self):
                return None
            def executescript(self, script):
                for stmt in script.split(';'):
                    s = stmt.strip()
                    if s:
                        db_exec(s)
            def commit(self):
                get_db().commit()
            def close(self):
                pass

        db = DbExecAdapter()
        db_exec("DELETE FROM fixtures")
        db_exec("DELETE FROM players")
        get_db().commit()
        validate_squads()
        seed_players(db)
        seed_fixtures(db)
        get_db().commit()
        p = db_exec("SELECT COUNT(*) FROM players").fetchone()
        f = db_exec("SELECT COUNT(*) FROM fixtures").fetchone()
        pc = p[0] if isinstance(p, (list, tuple)) else p["count"]
        fc = f[0] if isinstance(f, (list, tuple)) else f["count"]
        return jsonify({"ok": True, "players": pc, "fixtures": fc})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# Maps football-data.org team names → our DB names
TEAM_NAME_MAP = {
    "Korea Republic": "South Korea",
    "USA": "United States",
    "Türkiye": "Turkiye",
    "Turkey": "Turkiye",
    "IR Iran": "Iran",
    "Bosnia and Herzegovina": "Bosnia-Herzegovina",
    "DR Congo": "Congo DR",
    "Ivory Coast": "Ivory Coast",
    "Côte d'Ivoire": "Ivory Coast",
    "New Zealand": "New Zealand",
    "Saudi Arabia": "Saudi Arabia",
    "Cape Verde": "Cape Verde",
    "Czech Republic": "Czechia",
    "Czechia": "Czechia",
}

def normalize_team(name):
    return TEAM_NAME_MAP.get(name, name)


@app.route("/admin/sync-scores")
def sync_scores():
    """Fetch live/finished WC2026 results from football-data.org and update DB."""
    api_key = os.environ.get("FOOTBALL_API_KEY", "")
    if not api_key:
        return jsonify({"ok": False, "error": "FOOTBALL_API_KEY not set"}), 500

    try:
        req = urllib.request.Request(
            "https://api.football-data.org/v4/competitions/WC/matches?season=2026",
            headers={"X-Auth-Token": api_key}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return jsonify({"ok": False, "error": f"API error {e.code}"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500

    updated = 0
    for m in data.get("matches", []):
        status = m.get("status")
        if status not in ("FINISHED", "IN_PLAY", "PAUSED"):
            continue
        home = normalize_team(m["homeTeam"]["name"])
        away = normalize_team(m["awayTeam"]["name"])
        score = m.get("score", {})
        full = score.get("fullTime", {})
        hs = full.get("home")
        as_ = full.get("away")
        if hs is None or as_ is None:
            continue
        played = 1 if status == "FINISHED" else 0
        rows = db_exec(
            "SELECT id FROM fixtures WHERE home_team=? AND away_team=?",
            (home, away)
        ).fetchall()
        if not rows:
            # try swap
            rows = db_exec(
                "SELECT id FROM fixtures WHERE home_team=? AND away_team=?",
                (away, home)
            ).fetchall()
            if rows:
                hs, as_ = as_, hs
        for row in rows:
            fid = row[0] if isinstance(row, (list, tuple)) else row["id"]
            db_exec(
                "UPDATE fixtures SET home_score=?, away_score=?, played=? WHERE id=?",
                (hs, as_, played, fid)
            )
            updated += 1
    get_db().commit()
    return jsonify({"ok": True, "updated": updated})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
