# AssessSim 🎮

**Interactive practice platform for consulting, finance, and tech internship assessment games.**

Practice Pymetrics, SHL, Cappfinity, HireVue, McKinsey Solve, and Watson Glaser assessments with **AI-powered competitive leaderboards**.

## ✨ Features

- **15+ Interactive Games**: BART, Go/No-Go, Digit Span, N-Back, Numerical Reasoning, Verbal Reasoning, Inductive Reasoning, SJT, and more
- **Bot Competition Mode**: Play against AI with 4 difficulty tiers:
  - 🐢 Easy (Procrastinators)
  - 👤 Average (Solid Applicants)
  - 🎯 Above Average (Target Candidates)
  - ⚡ Cut-Throat (Quant Gods)
- **Live Leaderboards**: See your percentile rank vs simulated bot profiles
- **User Accounts**: Track scores across multiple attempts
- **Realistic Profiles**: 30+ authentic candidate profiles with university affiliations

## 🚀 Quick Start

### Requirements
- Python 3.7+
- Flask 3.1.3
- Werkzeug 3.1.8

### Installation

```bash
git clone https://github.com/yourusername/assesssim.git
cd assesssim
pip install -r requirements.txt
python app.py
```

Visit `http://localhost:5001`

## 📁 Project Structure

```
assesssim/
├── app.py                 # Flask backend + bot leaderboard API
├── templates/
│   └── index.html         # Full frontend (HTML/CSS/JavaScript)
├── requirements.txt       # Python dependencies
├── README.md             # This file
└── .gitignore            # Git ignore rules
```

## 🎮 Games Included

### Pymetrics
- **BART** - Balloon Risk Task (risk tolerance)
- **Go/No-Go** - Impulse control
- **Digit Span** - Working memory
- **N-Back** - Fluid intelligence
- **Attention** - Reaction time
- **Arctic Shores** - Emotional recognition

### SHL
- **Numerical Reasoning** - Data interpretation
- **Verbal Reasoning** - Critical reading
- **Inductive Reasoning** - Pattern recognition

### Cappfinity
- **Situational Judgment Test** - Professional judgment

### Other
- **HireVue** - Behavioral + game-based
- **McKinsey Solve** - Ecosystem building
- **Watson Glaser** - Critical thinking
- **Coding OA** - Algorithm problems

## 📊 Bot Leaderboard System

When you complete a game:

1. Select difficulty tier (Easy → Cut-Throat)
2. Play the game
3. View live leaderboard with:
   - Your rank vs 11 AI bots
   - Percentile ranking
   - Medal rankings (🥇🥈🥉)
   - Candidate profiles

### Difficulty Tiers

Each tier generates bot scores using normal distribution:

| Tier | Mean Score | Std Dev | Use Case |
|------|-----------|---------|----------|
| Easy | 45% | 15 | Practice mode |
| Average | 65% | 10 | Peer comparison |
| Above Average | 82% | 8 | Target level |
| Cut-Throat | 94% | 4 | Elite benchmarking |

## 🔑 API Endpoints

### POST /api/bot/leaderboard

Generate competitive leaderboard for any game.

**Request:**
```json
{
  "score": 75,
  "difficulty": "average",
  "game": "bart",
  "count": 12
}
```

**Response:**
```json
{
  "leaderboard": [...],
  "user_rank": 5,
  "total_candidates": 13,
  "percentile": 67,
  "difficulty": "average"
}
```

## 🔐 Authentication

- Demo mode: Login with any credentials (no email required)
- `POST /auth/login` - User authentication
- `POST /auth/signup` - Account creation
- SQLite database for user scores

## 🛠️ Development

### Run in debug mode:
```bash
export FLASK_ENV=development
python app.py
```

### Database
- SQLite (`assesssim.db`) stores user profiles and scores
- Bots are dynamically generated (not persisted)

## 📈 Roadmap

- [ ] Score normalization across game types
- [ ] Leaderboard history persistence
- [ ] Firm-specific bot profiles (Goldman Sachs, McKinsey, etc.)
- [ ] Paid "Benchmarking Module"
- [ ] Admin panel for bot profile management
- [ ] Mobile app
- [ ] Real-time multiplayer mode

## ⚖️ Legal

Not affiliated with Pymetrics, SHL, Cappfinity, HireVue, McKinsey, Watson Glaser, or any assessment provider. For educational purposes only.

## 📝 License

MIT License - see LICENSE file

## 👨‍💻 Author

Built for MORSE candidates preparing for top-tier consulting and finance internships.

---

**Questions?** Open an issue on GitHub or reach out!
