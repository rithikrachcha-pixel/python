# ⚽ WC2026 Fantasy Football

A World Cup 2026 fantasy football game built with Flask + SQLite + vanilla JS.
Pick a $100M squad from real World Cup 2026 players, **back a nation**, and climb
the live leaderboard. The further your backed nation progresses, the more bonus
points you earn — and their players score **1.5×**.

## Features

- **48 real teams** across 12 groups (the actual 2026 World Cup format), seeded
  from announced/likely squads.
- **$100M budget** — build 11 starters + 3 bench in your chosen formation
  (4-3-3, 4-4-2, 3-5-2, 3-4-3, 5-3-2).
- **Fantasy scoring**: goals (GK/DEF 6, MID 5, FWD 4), assists 3, clean sheets
  (GK/DEF 4, MID 1), 3 saves = 1pt, yellow −1, red −3.
- **Team Progression Bonus** (the headline feature): back one nation and earn
  Group Win +5 · R32 +8 · R16 +10 · QF +20 · SF +30 · Final +50 · Champions +100.
- **1.5× loyalty multiplier** on every player from your backed nation.
- **Live leaderboard**, fixtures/results panel, and a points breakdown that
  auto-refreshes every 30 seconds.
- World Cup 2026 (USA / Canada / Mexico) red-white-blue theme.

## Run it

```bash
cd worldcup_fantasy
pip install -r requirements.txt
python init_db.py        # create + seed fantasy.db
python app.py            # http://127.0.0.1:5000
```

Run the unit tests for the scoring engine:

```bash
python tests/test_points.py
```

## Data & live updates

Player and squad data lives in `data/players.py`, sourced from public web
research of announced 2026 World Cup squads. Final 26-man squads lock on
June 1–2, 2026, so refresh `data/players.py` and re-run `python init_db.py --reset`
to update.

Match results and tournament progression are driven through token-gated admin
endpoints (so the auto-refreshing dashboard reflects real outcomes):

```bash
# header: X-Admin-Token: <ADMIN_TOKEN env, default "dev-token">
POST /admin/update-stats     {player_id, goals, assists, clean_sheets, yellow_cards, red_cards, saves}
POST /admin/update-fixture   {fixture_id, home_score, away_score}
POST /admin/advance          {nation, round}   # round in r32|r16|qf|sf|final|winner
```

> Note: this environment's sandbox blocks outbound network from the app process,
> so live scraping runs as a build-time data refresh of `data/players.py` rather
> than a runtime fetch.

## Project layout

```
worldcup_fantasy/
├── app.py              # Flask backend: auth, squad, points, leaderboard, admin
├── init_db.py          # schema + seed (players, fixtures, demo stats)
├── data/players.py     # 48-team squads, groups, fixtures
├── templates/          # base, index, team_builder, dashboard
├── static/css/style.css
├── static/js/          # team_builder.js, dashboard.js, fixtures.js
└── tests/test_points.py
```
