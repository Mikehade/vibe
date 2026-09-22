# Vibe Backend

FastAPI backend for the Vibe Session Architect. Handles mood parsing, session plan generation via Amazon Bedrock, content discovery via TMDB, taste profile management, and the feedback learning loop.

## Setup (Local Development)

### Prerequisites

- Python 3.11+
- PostgreSQL 16 (or use Docker)
- AWS credentials with Bedrock access
- TMDB API key

### Install

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
```

### Database

With Docker Compose (from project root):

```bash
make start-db
```

Or with a local PostgreSQL:

```bash
createdb vibe
```

Run migrations:

```bash
alembic upgrade head
```

The app also auto-creates tables on startup via `db.create_all()` in the lifespan handler, so migrations are optional for initial development.

### Run

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### Test

```bash
python -m pytest tests/ -v

# With coverage
python -m pytest tests/ --cov=src --cov-report=term-missing
```

Current: **43 unit tests** covering domain logic, API schemas, tool specs, and registry routing.

## Architecture

```
src/
├── api/                         # Layer 1: HTTP interface
│   ├── health/router.py         # GET /health
│   ├── session/                 # Plan generation + management
│   │   ├── models.py            # Pydantic request/response schemas
│   │   └── router.py            # POST /plan, GET /plan/{id}, etc.
│   ├── mood/                    # Mood parsing
│   ├── profile/                 # Taste profile + onboarding
│   ├── content/                 # TMDB search + details
│   └── feedback/                # Session + pick ratings
│
├── core/                        # Layer 2: Domain (zero infra imports)
│   ├── domain/
│   │   ├── interfaces.py        # ABCs (IDeviceRepo, IContentClient, etc.)
│   │   ├── session_plan.py      # Mood, ArcRole, PlanStatus enums + entities
│   │   └── taste_profile.py     # TasteProfileEntity with boost/suppress
│   ├── constants/
│   │   ├── moods.py             # Mood → genre/energy mappings
│   │   ├── genres.py            # TMDB genre ID ↔ name maps
│   │   └── pacing.py            # Arc roles, shapes, session sizing
│   ├── engine/
│   │   ├── session_architect.py # 4-step Bedrock reasoning chain
│   │   ├── energy_trajectory.py # Fallback trajectory inference
│   │   ├── candidate_evaluator.py # Pre-filtering
│   │   └── pacing_logic.py      # Role assignment + validation
│   ├── prompts/                 # Bedrock prompt templates
│   └── tools/                   # BaseTool ABC + introspection
│       ├── base.py              # Auto toolSpec from signatures
│       ├── content_tools.py     # TMDB queries
│       ├── profile_tools.py     # Taste profile lookups
│       └── availability_tools.py # Streaming availability
│
├── infrastructure/              # Layer 3: External world
│   ├── db/
│   │   ├── base.py              # SQLAlchemy Base (UUID PK, timestamps)
│   │   ├── session.py           # Async engine + session factory
│   │   ├── mixins.py            # SoftDeleteMixin
│   │   └── models/              # ORM models (device, profile, plan, feedback)
│   ├── repository/              # Query-only repos (session injected)
│   ├── services/                # Business logic orchestration
│   ├── clients/                 # TMDB + JustWatch HTTP clients
│   ├── language_models/         # Bedrock LLM with tool-calling loop
│   └── middleware/              # Device auth + rate limiting
│
└── config/                      # Layer 4: Wiring
    ├── base.py                  # Pydantic BaseSettings
    ├── development.py           # Dev overrides
    ├── staging.py / production.py
    └── dependency_injection/
        └── container.py         # DeclarativeContainer (all DI wiring)
```

## Key Concepts

### Session Plan Generation Flow

1. **Mood parsing** — LLM converts voice/text to structured mood
2. **Energy trajectory** — LLM decides the session's energy arc (e.g., "ascending")
3. **Candidate evaluation** — LLM searches TMDB via tools, evaluates candidates
4. **Session assembly** — LLM assigns arc roles (opener/anchor/closer) and orders picks
5. **Justification** — LLM generates a natural-language reason for each pick

All streamed as NDJSON events: `trajectory` → `pick` (×N) → `summary`.

### Device-Based Auth

No user accounts. Every request must include `X-Device-ID` header (any string 4–255 chars). The middleware validates it and attaches it to `request.state.device_id`. The `get_device_id` FastAPI dependency extracts it for route handlers.

### Learning Loop

Feedback flows:
- **Session feedback** (thumbs up/down + pacing rating) → updates `pacing_preference`
- **Pick feedback** (thumbs up/down per title) → adjusts `genre_weights` by ±0.1, genres below 0.3 auto-added to `disliked_genres`

### Tool System

`BaseTool` uses Python introspection to auto-generate Bedrock `toolSpec` from method signatures. Subclasses just define `_method_name(param: type)` methods and they become callable tools. `ToolRegistry` collects all tools and routes Bedrock's `toolUse` calls.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `ENV` | `development` | Environment (development/staging/production) |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Async PostgreSQL connection |
| `TMDB_API_KEY` | (required) | TMDB v3 API key |
| `AWS_ACCESS_KEY_ID` | (required) | AWS credentials for Bedrock |
| `AWS_SECRET_ACCESS_KEY` | (required) | AWS credentials for Bedrock |
| `AWS_REGION` | `us-east-1` | AWS region |
| `BEDROCK_MODEL_ID` | `us.anthropic.claude-sonnet-4-6` | Claude model ID |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed CORS origins |
| `RATE_LIMIT_PER_MINUTE` | `30` | Per-device rate limit |
| `LOG_LEVEL` | `INFO` | Logging level |

## Testing Without AWS/TMDB

The backend starts and serves the API even without valid AWS or TMDB credentials — those services will return errors when called, but you can still test:

- Health check: `curl http://localhost:8000/api/v1/health`
- Profile endpoints (with a device header): `curl -H "X-Device-ID: test-123" http://localhost:8000/api/v1/profile`
- Onboarding: `curl -X PATCH -H "X-Device-ID: test-123" -H "Content-Type: application/json" -d '{"genre_preferences":[{"genre":"action","action":"like"}],"streaming_services":["netflix"]}' http://localhost:8000/api/v1/profile/onboarding`
- Swagger UI: http://localhost:8000/docs (add X-Device-ID in the "Authorize" button or per-request)
