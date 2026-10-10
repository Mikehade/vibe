# Vibe — your evening, programmed

**Vibe is an AI movie-night planner for Fire TV.** Tell it how you feel and how much time you have, and it
builds a whole evening — an easy opener, a main event, a soft landing — from titles you can actually
watch on your services. Every step streams to the screen as it happens, so there's never a blank wait.

Built for the **Amazon Developer Hackathon — Fire TV track**, with **Alexa+ (MCP)**, **AWS Builder**
(Amazon Bedrock) and **Open Source** extras.

> Start here: **[docs/RUNBOOK.md](docs/RUNBOOK.md)** — the exact commands to test, deploy and demo.

---

## What it does

| | |
|---|---|
| **Mood → a planned night** | Six moods, a time budget, and your local clock shape an *energy arc*: which slot is the opener, the main event, the nightcap, and how long each should be. |
| **Streams its thinking** | The TV shows the agent working in real time — shortlist built, tools called ("Finding titles like Paddington"), each pick landing on the lineup the moment it's decided, while the rest are still being chosen. |
| **Only what you can watch** | Candidates come from TMDB filtered by your region and streaming services, runtime, quality and kids-safety — then the model chooses and explains. Posters, runtimes and providers are always real data. |
| **Not this one** | Swap any pick instantly for the next-best fit for that slot; Vibe remembers. |
| **Adaptive check-in** | After each title: *wind me down*, *keep going*, or *pick it up* — the rest of the night is re-planned around how you feel now. |
| **Couch Mode** | Scan a QR code; everyone adds their mood, notes (voice or text) and hard no's from their phone. Vibe blends the room. Phones can vote to skip — a majority swaps it on the TV. |
| **Alexa+ (MCP)** | "Alexa, plan a chill movie night" → the lineup builds live on the linked TV. MCP server (spec 2025-11-25, Streamable HTTP) with `plan_movie_night`, `whats_next`, `swap_pick`, `mark_watched`, `tonight_lineup`, `link_tv`. |
| **Household profiles + Kids mode** | Separate taste profiles per person; kids profiles get family ratings only. Thumbs and pacing feedback tune future nights. |
| **Built for the remote** | Every screen is D-pad navigable (spatial navigation, focus scopes, Back/Play/Menu keys), sized for 10-foot viewing from 960×540 WebViews to 4K. No emoji — a calm, cinematic UI. |

## How it works

```
 Fire TV (Vega OS)                 AWS                                        Data
┌──────────────────┐   HTTPS   ┌──────────────┐   ┌───────────────────────┐   ┌──────────┐
│ Vega WebView     │──────────▶│  CloudFront  │──▶│  App Runner           │──▶│   TMDB   │
│  shell (RN)      │  NDJSON   │  S3 (web app)│   │  FastAPI  ·  /mcp     │   └──────────┘
│ └ Vibe web app   │◀──────────│  /api, /mcp  │   │  Session Architect    │   ┌──────────┐
└──────────────────┘           └──────────────┘   │   • energy arc        │──▶│ Bedrock  │
 Phones (Couch Mode) ─────────────────┘           │   • candidate pool    │   │ (Claude) │
 Alexa+ ── MCP (Streamable HTTP) ─────┘           │   • streaming agent   │   └──────────┘
                                                  └──────────┬────────────┘
                                                        RDS PostgreSQL
```

**The planning pipeline** (`backend/src/core/engine`):
1. **Arc (instant):** mood + local time + budget → slots with roles, energy and runtime targets. Late at night the arc always winds down.
2. **Shortlist (usually prefetched):** the moment a mood is selected, TMDB `/discover` runs in parallel for films and series on your services, then enriches the top ~30 with runtime, certification and where-to-watch. Cached per request.
3. **One streamed Bedrock conversation:** Claude sees the arc and the shortlist, may call tools (search, more-like-this, details), and writes one line per pick. Each line is validated (no invented ids, fits the slot) and hydrated with real metadata before it's sent to the TV.
4. **Never stuck:** heartbeat updates every few seconds, a hard deadline, and a deterministic planner that fills any slot the model didn't.

Generation runs in the background and publishes to a live hub, so the TV, phones and Alexa can all follow the same plan.

## Try it

```bash
./scripts/setup.sh          # dependencies + .env files
./scripts/dev.sh --fake     # offline demo data, no keys → http://localhost:5173
./scripts/check-aws.sh      # verify Bedrock + TMDB access
./scripts/dev.sh            # real Bedrock + TMDB
./scripts/test.sh           # 60+ tests + production build
./deploy/aws/deploy.sh      # App Runner + RDS + CloudFront
```
Full walkthrough, Fire TV simulator setup and demo tips: **[docs/RUNBOOK.md](docs/RUNBOOK.md)**. AWS deployment, step by step: **[docs/DEPLOY_AWS.md](docs/DEPLOY_AWS.md)**.

## Repository

```
backend/            FastAPI API, planning engine, MCP server, tests
frontend/           TV web app (React + Vite + Tailwind) and phone companion
tv-app/vega/        Vega OS (Fire TV) React Native WebView shell + setup script
deploy/aws/         CloudFormation template, deploy/destroy scripts
packages/tv-dpad-focus/  open-source D-pad navigation library extracted from the app (MIT)
scripts/            setup, dev, test, credential check, MCP smoke test
docs/               runbook, submission text, demo script, product feedback, friction log
```

## Tracks and challenges
- **Fire TV** — Vega OS app (WebView shell) showing the full experience on the Vega Virtual Device.
- **Alexa+ integration** — self-hosted MCP server, spec 2025-11-25, Streamable HTTP (`backend/src/mcp_server`).
- **AWS Builder** — Amazon Bedrock (Claude, ConverseStream with tool use), App Runner, RDS, S3, CloudFront, Secrets Manager, ECR — all in `deploy/aws/template.yaml`.
- **Open Source** — `packages/tv-dpad-focus` (MIT), plus this repository under MIT.

## Credits
Movie and TV metadata and images from [TMDB](https://www.themoviedb.org). This product uses the TMDB API
but is not endorsed or certified by TMDB. Streaming availability via TMDB watch providers (JustWatch data).
Fonts: Inter and Instrument Serif (SIL Open Font License).

MIT licensed — see [LICENSE](LICENSE).
