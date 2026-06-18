# HealthGuardian AI

AI-powered multi-agent health assistant built with **Streamlit**, **CrewAI**, and **DeepSeek** (via OpenRouter).

## Features

- **User Authentication** — Sign up with health profile, secure password hashing
- **Multi-Agent Workflow** — Location Scout → Wellness Planner (CrewAI sequential process)
- **Reactive Dashboard** — Live agent status during plan generation, chat UI, activity feed
- **Medical Consultant** — RAG-powered health Q&A with medical disclaimers
- **WhatsApp Integration** — Daily plan delivery and hydration reminders (Twilio)
- **Scheduled Jobs** — APScheduler for 6 AM plans and reminder nudges
- **Gamification** — Health points for completing actions

## Quick Start

### 1. Clone and install

```bash
cd medicalassistant
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

pip install -e .
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and add your API keys:

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Recommended | Powers DeepSeek LLM via OpenRouter |
| `OPENWEATHERMAP_API_KEY` | Optional | Real weather data (mock fallback) |
| `WAQI_API_KEY` | Optional | Air quality index |
| `TWILIO_*` | Optional | WhatsApp messaging (simulated without). Install with `pip install -e ".[whatsapp]"` — on Windows, enable long paths if install fails |

### 3. Run the app

```bash
streamlit run streamlit_app.py
```

Open [http://localhost:8501](http://localhost:8501) in your browser.

## Architecture

```
streamlit_app.py          # UI entry point
healthguardian/
├── agents/crew.py        # CrewAI orchestration (Location → Planner)
├── tools/                # Weather, geolocation, WhatsApp
├── services/             # LLM, RAG, scheduler
├── database/             # SQLAlchemy models & repository
└── ui/                   # Streamlit pages & styles
```

### Agent Workflow

1. **City Scout** — Detects location (IP geolocation), fetches weather & AQI
2. **Wellness Architect** — Generates personalised daily plan adapted to conditions
3. **Medical Consultant** — On-demand chat with RAG over curated health knowledge
4. **Health Buddy** — WhatsApp reminders via APScheduler

## Usage

1. **Sign Up** — Enter health profile (allergies, conditions, medications)
2. **Dashboard** — Click "Generate Today's Plan" to run the agent crew
3. **Medical Chat** — Ask health questions in the consultant panel
4. **WhatsApp** — Send plan to your registered number (or simulated mode)

## Development Notes

- SQLite is used by default (`healthguardian.db`). Set `DATABASE_URL` for PostgreSQL.
- Without API keys, the app uses intelligent fallbacks (mock weather, rule-based plans).
- Medical disclaimer is always appended to consultant responses.
- Scheduler runs in background — morning plans at 6:00 AM, hydration at 10 AM & 2 PM.

## Compliance

This application provides **general wellness information only**. It is not HIPAA-certified and should not be used as a substitute for professional medical advice. Users must provide explicit consent during signup.

## License

MIT
