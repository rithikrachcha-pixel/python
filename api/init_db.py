"""
Initialise and seed the World Cup 2026 Fantasy database.

Usage:
    python init_db.py          # create schema + seed players, fixtures, demo stats
    python init_db.py --reset  # delete existing DB first (SQLite only)

Set DATABASE_URL env var to use Postgres instead of SQLite.
"""
import os
import sys
import random
import sqlite3

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.players import SQUADS, FIXTURES  # noqa: E402

DB_PATH = os.path.join(os.path.dirname(__file__), "fantasy.db")
DATABASE_URL = os.environ.get('DATABASE_URL')
IS_PG = bool(DATABASE_URL)

SCHEMA_SQLITE = """
CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL, nation TEXT NOT NULL, grp TEXT,
    position TEXT NOT NULL, club TEXT, age INTEGER, price REAL,
    goals INTEGER DEFAULT 0, assists INTEGER DEFAULT 0,
    clean_sheets INTEGER DEFAULT 0, yellow_cards INTEGER DEFAULT 0,
    red_cards INTEGER DEFAULT 0, saves INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
    budget_remaining REAL DEFAULT 150.0,
    backed_nation TEXT, formation TEXT DEFAULT '4-3-3',
    squad_locked INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS user_squad (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    player_id INTEGER REFERENCES players(id),
    is_bench INTEGER DEFAULT 0,
    UNIQUE(user_id, player_id)
);
CREATE TABLE IF NOT EXISTS tournament_rounds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nation TEXT NOT NULL, round TEXT NOT NULL,
    achieved_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS fixtures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    home_team TEXT, away_team TEXT,
    match_date TEXT, stage TEXT,
    home_score INTEGER, away_score INTEGER,
    played INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS leagues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    owner_id INTEGER REFERENCES users(id),
    created_at TEXT DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS league_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    league_id INTEGER REFERENCES leagues(id),
    user_id INTEGER REFERENCES users(id),
    joined_at TEXT DEFAULT (datetime('now')),
    UNIQUE(league_id, user_id)
);
"""

SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL, nation TEXT NOT NULL, grp TEXT,
    position TEXT NOT NULL, club TEXT, age INTEGER, price REAL,
    goals INTEGER DEFAULT 0, assists INTEGER DEFAULT 0,
    clean_sheets INTEGER DEFAULT 0, yellow_cards INTEGER DEFAULT 0,
    red_cards INTEGER DEFAULT 0, saves INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
    budget_remaining REAL DEFAULT 150.0,
    backed_nation TEXT, formation TEXT DEFAULT '4-3-3',
    squad_locked INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS user_squad (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    player_id INTEGER REFERENCES players(id),
    is_bench INTEGER DEFAULT 0,
    UNIQUE(user_id, player_id)
);
CREATE TABLE IF NOT EXISTS tournament_rounds (
    id SERIAL PRIMARY KEY,
    nation TEXT NOT NULL, round TEXT NOT NULL,
    achieved_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS fixtures (
    id SERIAL PRIMARY KEY,
    home_team TEXT, away_team TEXT,
    match_date TEXT, stage TEXT,
    home_score INTEGER, away_score INTEGER,
    played INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS leagues (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    owner_id INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS league_members (
    id SERIAL PRIMARY KEY,
    league_id INTEGER REFERENCES leagues(id),
    user_id INTEGER REFERENCES users(id),
    joined_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(league_id, user_id)
);
"""


def validate_squads():
    for s in SQUADS:
        players = s["players"]
        gks = sum(1 for p in players if p["position"] == "GK")
        assert gks >= 3, f"{s['nation']} has only {gks} GK (need >=3)"
        assert 23 <= len(players) <= 26, (
            f"{s['nation']} has {len(players)} players (need 23-26)"
        )
        for p in players:
            assert p["position"] in ("GK", "DEF", "MID", "FWD"), (
                f"{s['nation']}: bad position {p['position']} for {p['name']}"
            )
    print(f"Validated {len(SQUADS)} squads, "
          f"{sum(len(s['players']) for s in SQUADS)} players.")


class PgAdapter:
    """Thin adapter to make Postgres conn look like sqlite3 for seeding."""
    def __init__(self, conn):
        self.conn = conn
        self.cur = conn.cursor()

    def execute(self, sql, params=()):
        sql = sql.replace('?', '%s')
        self.cur.execute(sql, list(params) if params else None)
        return self.cur

    def fetchall(self):
        return self.cur.fetchall()

    def fetchone(self):
        return self.cur.fetchone()

    def executescript(self, script):
        for stmt in script.split(';'):
            stmt = stmt.strip()
            if stmt:
                self.cur.execute(stmt)

    def commit(self):
        self.conn.commit()

    def close(self):
        self.cur.close()
        self.conn.close()


def seed_players(db):
    for s in SQUADS:
        for p in s["players"]:
            db.execute(
                """INSERT INTO players (name, nation, grp, position, club, age, price)
                   VALUES (?,?,?,?,?,?,?)""",
                (p["name"], s["nation"], s.get("group"), p["position"],
                 p.get("club", ""), p.get("age", 26), p.get("price", 5.0)),
            )


def seed_fixtures(db):
    for f in FIXTURES:
        db.execute(
            """INSERT INTO fixtures (home_team, away_team, match_date, stage)
               VALUES (?,?,?,?)""",
            (f["home_team"], f["away_team"], f["match_date"], f["stage"]),
        )


def seed_demo_stats(db):
    """Give plausible mid-tournament stats to the priciest players so the demo
    has a populated leaderboard and points breakdown out of the box."""
    random.seed(2026)
    nations_raw = db.execute("SELECT DISTINCT nation FROM players").fetchall()
    nations = [r[0] if isinstance(r, (list, tuple)) else r["nation"] for r in nations_raw]
    for nation in nations:
        rows = db.execute(
            "SELECT * FROM players WHERE nation=? ORDER BY price DESC LIMIT 8",
            (nation,),
        ).fetchall()
        for r in rows:
            pos = r[3] if isinstance(r, (list, tuple)) else r["position"]
            pid = r[0] if isinstance(r, (list, tuple)) else r["id"]
            goals = assists = cs = saves = yc = rc = 0
            if pos == "FWD":
                goals = random.randint(0, 4)
                assists = random.randint(0, 2)
            elif pos == "MID":
                goals = random.randint(0, 2)
                assists = random.randint(0, 3)
            elif pos == "DEF":
                goals = random.randint(0, 1)
                assists = random.randint(0, 1)
                cs = random.randint(0, 2)
            elif pos == "GK":
                cs = random.randint(0, 2)
                saves = random.randint(3, 15)
            yc = random.randint(0, 2)
            if random.random() < 0.05:
                rc = 1
            db.execute(
                """UPDATE players SET goals=?, assists=?, clean_sheets=?,
                   saves=?, yellow_cards=?, red_cards=? WHERE id=?""",
                (goals, assists, cs, saves, yc, rc, pid),
            )


def seed_demo_progression(db):
    """Mark some group-stage results so backed-team bonuses are visible."""
    fixtures = db.execute(
        "SELECT * FROM fixtures WHERE stage='group' ORDER BY id"
    ).fetchall()
    seeded = 0
    for fx in fixtures:
        if seeded >= 24:
            break
        fid = fx[0] if isinstance(fx, (list, tuple)) else fx["id"]
        home = fx[1] if isinstance(fx, (list, tuple)) else fx["home_team"]
        if fid % 2 == 0:
            db.execute(
                "UPDATE fixtures SET home_score=2, away_score=1, played=1 WHERE id=?",
                (fid,),
            )
            db.execute(
                "INSERT INTO tournament_rounds (nation, round) VALUES (?, 'win')",
                (home,),
            )
            seeded += 1


def main():
    if IS_PG:
        import psycopg2
        print("Using Postgres:", DATABASE_URL[:30] + "...")
        conn = psycopg2.connect(DATABASE_URL)
        db = PgAdapter(conn)
        db.executescript(SCHEMA_PG)
        db.commit()

        already = db.execute("SELECT COUNT(*) FROM players").fetchone()
        count = already[0] if already else 0
        if count:
            print(f"Players already seeded ({count}). Schema verified.")
            db.close()
            return

        validate_squads()
        seed_players(db)
        seed_fixtures(db)
        seed_demo_stats(db)
        seed_demo_progression(db)
        db.commit()

        p = db.execute("SELECT COUNT(*) FROM players").fetchone()[0]
        f = db.execute("SELECT COUNT(*) FROM fixtures").fetchone()[0]
        print(f"Seeded {p} players and {f} fixtures into Postgres.")
        db.close()
        return

    # SQLite path
    if "--reset" in sys.argv and os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print("Removed existing database.")

    validate_squads()
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.executescript(SCHEMA_SQLITE)

    already = db.execute("SELECT COUNT(*) c FROM players").fetchone()[0]
    if already:
        print(f"Players already seeded ({already}). Use --reset to rebuild.")
        db.close()
        return

    seed_players(db)
    seed_fixtures(db)
    seed_demo_stats(db)
    seed_demo_progression(db)
    db.commit()

    p = db.execute("SELECT COUNT(*) c FROM players").fetchone()[0]
    f = db.execute("SELECT COUNT(*) c FROM fixtures").fetchone()[0]
    print(f"Seeded {p} players and {f} fixtures into {DB_PATH}")
    db.close()


if __name__ == "__main__":
    main()
