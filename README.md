# Vibe — Session Architect

AI-powered movie night planner for Amazon Fire TV. Built for the [Amazon Developer Hackathon](https://amazondevhackathon.devpost.com/) (deadline: 23 Oct 2026, $138K+ in prizes).

Vibe reads your mood, your taste profile, and your streaming subscriptions, then builds a paced session plan — a curated lineup of movies and shows with an energy arc (opener → anchor → closer) that feels like a night programmed by a friend who knows what you love.

## Architecture

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Fire TV    │────▸│   FastAPI    │────▸│   Bedrock    │
│  React App   │ API │   Backend    │     │  (Claude)    │
│  (Vite/TS)   │◂────│  PostgreSQL  │◂────│  Tool Use    │
└──────────────┘NDJSON└──────────────┘     └──────────────┘
                            │
                      ┌─────┴─────┐
                      │  TMDB API │
                      │ JustWatch │
                      └───────────┘
```

**Clean Architecture** with 4 layers: API → Core Domain → Infrastructure → Config. Dependencies point inward — the core has zero imports from infrastructure.

**Key patterns**: dependency injection (`dependency-injector`), repository pattern, NDJSON streaming, device-based auth (no user accounts), Bedrock tool-calling loop, deterministic learning loop via taste profile feedback.

## Quick Start

### Prerequisites

- Docker & Docker Compose
- A TMDB API key ([get one free](https://www.themoviedb.org/settings/api))
- AWS credentials with Bedrock access (Claude model enabled in us-east-1)

### 1. Clone and configure

```bash
cd vibe
cp .env.example .env
cp backend/.env.example backend/.env
cp frontend/.env.example frontend/.env
```

Edit `backend/.env` and fill in:

```
TMDB_API_KEY=your_tmdb_api_key_here
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6
```

### 2. Start everything

```bash
make start
```

This runs `docker-compose up -d` and starts all 4 services:

| Service    | URL                        | Description            |
|------------|----------------------------|------------------------|
| Frontend   | http://localhost:5173       | React app (Vite dev)   |
| Backend    | http://localhost:8000       | FastAPI + Swagger docs  |
| API Docs   | http://localhost:8000/docs  | Interactive Swagger UI  |
| PostgreSQL | localhost:5432              | Database                |
| Redis      | localhost:6379              | Cache (future use)      |

### 3. Test the app

1. Open **http://localhost:5173** in your browser
2. The app auto-generates a device ID (stored in localStorage) — no login needed
3. Complete the onboarding wizard (pick genres + streaming services)
4. Select your mood and time budget
5. Watch the AI build your session plan in real-time (NDJSON streaming)
6. Browse picks, rate them, and see your taste profile evolve

### 4. Run backend tests

```bash
make test
# or directly:
cd backend && python -m pytest tests/ -v
```

## Project Structure

```
vibe/
├── docker-compose.yaml          # 4 services: backend, frontend, postgres, redis
├── Makefile                     # Full command palette (make start/stop/test/...)
├── .env.example                 # Shared Docker env vars
│
├── backend/                     # Python 3.12 / FastAPI
│   ├── main.py                  # App entry point + lifespan
│   ├── requirements.txt
│   ├── Dockerfile               # Multi-stage (dev + prod)
│   ├── src/
│   │   ├── api/                 # 6 routers, 14 endpoints
│   │   ├── config/              # Settings, DI container
│   │   ├── core/                # Domain (no infra imports)
│   │   │   ├── domain/          # Entities, interfaces (ABCs)
│   │   │   ├── constants/       # Mood/genre/pacing mappings
│   │   │   ├── engine/          # SessionArchitect + helpers
│   │   │   ├── prompts/         # Bedrock prompt templates
│   │   │   └── tools/           # BaseTool + introspection
│   │   └── infrastructure/      # Repos, services, clients, middleware
│   ├── tests/                   # 43 unit tests
│   ├── alembic/                 # DB migrations
│   └── utils/                   # Logger, helpers
│
└── frontend/                    # React 18 / TypeScript / Vite
    ├── Dockerfile               # Multi-stage (dev + prod + nginx)
    ├── package.json
    └── src/
        ├── api/                 # API client + NDJSON streaming
        ├── stores/              # Zustand (session + profile)
        ├── hooks/               # D-pad navigation, stream helpers
        ├── components/          # Reusable UI (TV-first design)
        ├── pages/               # Onboarding, Session, History
        ├── types/               # TypeScript domain types
        └── styles/              # Tailwind base + TV tokens
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/session/plan` | Generate plan (NDJSON stream) |
| GET | `/api/v1/session/plan/{id}` | Get plan |
| GET | `/api/v1/session/plans` | List plans |
| PATCH | `/api/v1/session/plan/{id}/pick/{id}` | Update pick status |
| POST | `/api/v1/session/plan/{id}/feedback` | Session feedback |
| POST | `/api/v1/session/pick/{id}/feedback` | Pick feedback |
| POST | `/api/v1/mood/parse` | Parse mood from text |
| GET | `/api/v1/profile` | Get taste profile |
| PATCH | `/api/v1/profile/onboarding` | Save onboarding |
| GET | `/api/v1/profile/mood-history` | Mood history |
| GET | `/api/v1/content/search` | Search TMDB |
| GET | `/api/v1/content/{id}` | Content details |
| GET | `/api/v1/content/{id}/providers` | Streaming providers |

## Device ID (Authentication)

Vibe uses **device-based identity** — no user accounts, no passwords. Every request includes an `X-Device-ID` header:

- **Frontend**: auto-generated UUID stored in `localStorage` on first visit
- **Backend**: `DeviceAuthMiddleware` validates the header on all `/api/` routes (except `/health`)
- **Testing**: use any UUID string as the header value in curl/Postman

```bash
# Example API call
curl -H "X-Device-ID: test-device-123" http://localhost:8000/api/v1/profile
```

## Makefile Commands

```bash
make start          # Start all services
make stop           # Stop all services
make restart        # Restart all services
make logs           # Tail all logs
make test           # Run backend tests
make lint           # Lint backend code
make migrate        # Run DB migrations
make reset-db       # Reset database
make clean          # Clean build artifacts
```

## Tech Stack

**Backend**: Python 3.12, FastAPI, SQLAlchemy (async), PostgreSQL, Alembic, dependency-injector, aioboto3, httpx

**Frontend**: React 18, TypeScript, Vite, Zustand, Tailwind CSS, Framer Motion

**AI**: Amazon Bedrock (Claude via Converse API), 4-step reasoning chain with tool calling

**External APIs**: TMDB (content metadata), JustWatch via TMDB (streaming availability)

## License

Hackathon project — not yet licensed for distribution.
