# Vibe API (backend)

FastAPI service that plans the night, streams progress as NDJSON, stores plans and taste profiles,
runs Couch Mode rooms, and serves the Alexa+ MCP server at `/mcp`.

```
src/
  api/                 HTTP routers (session, profile, content, couch, tv, feedback, mood, health)
  core/
    domain/            entities + interfaces (no infrastructure imports)
    engine/            arc.py (energy arc) · candidate_pool.py (TMDB shortlist + prefetch)
                       session_architect.py (streaming Bedrock agent) · stream_parser.py · fallback.py
    tools/             planner_tools.py — tools the model may call (search, more-like-this, details)
    prompts/           system + user prompts, line protocol
  infrastructure/
    clients/tmdb.py    cached async TMDB client
    language_models/   bedrock.py — Converse / ConverseStream with tool use, one reused client
    services/          session (background runs + LiveHub), couch, tv_link, profile, feedback, content
    fakes/             offline catalogue + model (FAKE_SERVICES=true)
  mcp_server/          MCP 2025-11-25, Streamable HTTP: link_tv, plan_movie_night, whats_next, swap_pick, …
```

## Run
From the repo root: `./scripts/dev.sh` (real services) or `./scripts/dev.sh --fake` (offline).
Tests: `./scripts/test.sh` — 60+ unit and integration tests, no keys or database needed.

## Streaming protocol
`POST /api/v1/session/plan` returns `application/x-ndjson`, one event per line:

| type | when | data |
|---|---|---|
| `plan` | immediately | `plan_id` |
| `status` | every step + heartbeat every ~3.5 s | `stage`, `message` |
| `trajectory` | instantly (deterministic), then refined by the model | arc slots, energy, targets |
| `candidates` | shortlist ready | count, poster sample |
| `tool` | model calls a tool | human-readable message |
| `pick` | each slot as soon as it's decided | fully hydrated title (poster, runtime, provider…) |
| `summary` / `done` | end | plan summary, total runtime, elapsed ms |

Generation runs in the background; `GET /api/v1/session/plan/{id}/live` replays and follows it
(used by phones and by voice-started plans).
