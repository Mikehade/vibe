# Devpost submission — draft text

Replace everything in `<angle brackets>`. Keep claims matched to what the video shows.

## Project name
Vibe — your evening, programmed

## Tagline
Tell your Fire TV how you feel; it plans the whole night — live, on your services, for everyone on the couch.

## Tracks and challenges
- **Primary track:** Fire TV
- **Mini challenges:** AWS Builder, Open Source
- Also includes an Alexa+ MCP server as part of the Fire TV experience (entered under Fire TV only).

## What it does
Picking something to watch takes longer than watching it. Vibe replaces the scroll with one question:
*how are you feeling?* From your mood, your time and your local clock it builds an energy arc for the
evening — an easy opener, a main event, a soft landing — and fills it with titles you can actually play on
your streaming services in your country.

- **Live, not a spinner.** The plan streams to the TV as NDJSON: shortlist built, tools the agent calls,
  each pick landing as soon as it's decided, with a reason tied to its place in the night.
- **Not this one** swaps a single pick instantly; Vibe remembers.
- **Adaptive check-in:** after each title, *wind me down / keep going / pick it up* re-plans the rest.
- **Couch Mode:** everyone scans a QR code and adds their mood, notes (voice or text) and hard no's
  from their phone; Vibe blends the room, and a majority skip vote swaps a pick on the TV.
- **Voice via Alexa+ MCP:** a self-hosted MCP server lets an assistant plan the night; the lineup builds live on the linked TV.
- **Household profiles and Kids mode**, and a feedback loop (thumbs + pacing) that tunes future plans.
- Designed for the remote: spatial D-pad navigation everywhere, 10-foot typography, no emoji.

## How we built it
- **Fire TV / Vega OS:** a React Native for Vega app hosting the web UI in `@amazon-devices/webview`,
  forwarding Back and exiting cleanly. The web app (React + Vite + Tailwind) has its own geometric
  spatial-navigation engine, focus scopes, and remote key handling (Back, Select, Play/Pause, Menu), and scales
  from 960×540 WebViews to 4K by sizing everything relative to the viewport.
- **Planning engine (FastAPI):** a deterministic energy arc appears instantly; a TMDB `/discover`
  shortlist (filtered by region, services, runtime, quality, kids-safety) is *prefetched* the moment a
  mood is chosen; then **one streamed Amazon Bedrock ConverseStream conversation** with Claude writes one
  pick per line. The model may call tools (search, more-like-this, details). Every pick is validated
  (no invented ids, fits the slot) and hydrated with real posters, runtimes and providers before it reaches the
  TV. Heartbeats, a hard deadline and a deterministic fallback mean the viewer is never left waiting.
- **Live hub:** generation runs in the background and publishes events that the TV, phones and the MCP tool
  can all follow.
- **MCP server:** MCP spec 2025-11-25 over Streamable HTTP (official Python SDK), mounted at `/mcp`,
  with `link_tv`, `plan_movie_night` (reports progress), `whats_next`, `swap_pick`, `mark_watched`, `tonight_lineup`.
- **AWS:** App Runner (API + MCP), RDS PostgreSQL, S3 + CloudFront (web app, and `/api` + `/mcp` routed to
  App Runner on one domain), Secrets Manager, ECR — one CloudFormation template and one deploy script.

## AWS Builder — services and how they're used
| Service | Use | Where |
|---|---|---|
| **Amazon Bedrock** (Claude Sonnet 4.6 via cross-region inference; Claude Haiku 4.5 for short tasks) | Streaming planner with tool use (ConverseStream), swap explanations and mood parsing (Converse) | `backend/src/infrastructure/language_models/bedrock.py`, `backend/src/core/engine/session_architect.py` |
| **AWS App Runner** | Hosts the FastAPI API and MCP server (single instance, health-checked) | `deploy/aws/template.yaml` → `ApiService` |
| **Amazon RDS for PostgreSQL** | Plans, picks, profiles, feedback | `Database`, migrations in `backend/alembic` |
| **Amazon S3 + CloudFront** | Serves the TV web app; routes `/api/*` and `/mcp*` to App Runner without buffering the NDJSON stream | `WebBucket`, `Distribution` |
| **AWS Secrets Manager** | DB password and TMDB key injected into App Runner | `DbPasswordSecret`, `TmdbSecret` |
| **Amazon ECR** | Backend container image | `deploy/aws/deploy.sh` |
| **IAM** | Least-privilege roles for App Runner (Bedrock invoke, read two secrets) | `AppRunnerInstanceRole` |

## Open Source
- **Repository:** <https://github.com/USER/vibe> (MIT)
- **Contribution:** <https://github.com/USER/tv-dpad-focus> — `tv-dpad-focus`, a dependency-free D-pad
  spatial navigation library for React TV web apps (Fire TV Vega WebView, Silk, Android TV), extracted from
  Vibe during the hackathon. (Source is in `packages/tv-dpad-focus`; push it as its own public repo.)
- **GitHub username:** <your-username>
- **What it does / why it matters:** TV web apps need arrow-key navigation, Back handling and modal focus
  traps; most libraries require registering every element in a tree. `tv-dpad-focus` is geometric — mark
  elements focusable and the nearest one in the pressed direction wins — and it handles platform quirks we hit
  on Fire TV (raw Android keyCodes colliding with letters, duplicate Back events from native shells).

## What changed during the hackathon
The project started as an early prototype (`<date>`): a web page that called Bedrock in four sequential
steps and showed results with no posters. During the submission window we rebuilt it:
- New planning engine: instant energy arc, prefetched TMDB shortlist filtered by services/region/runtime/kids,
  single streamed Bedrock conversation with tool use, validation + hydration, heartbeat + deterministic fallback
  (measure with real Bedrock before submitting and fill in: before ≈ <X> s of blank screen; now first pick at ≈ <Y> s, full plan at ≈ <Z> s).
- Fixed the missing posters (metadata was being dropped between steps; picks are now hydrated server-side).
- New 10-foot UI and spatial navigation; Vega OS WebView app.
- New features: swap, adaptive check-in re-planning, Couch Mode with phone companion and skip voting,
  household profiles, Kids mode, provider/region onboarding.
- Alexa+ MCP server and TV pairing.
- AWS deployment (App Runner, RDS, CloudFront, Secrets Manager) and 60+ automated tests.

## Feature requests
| Request | Why | Urgency |
|---|---|---|
| Vega WebView ↔ app messaging documented end to end (`postMessage`/`onMessage`, Back key delivery) | Every web app on Vega needs Back and exit behaviour; we had to guess and handle both paths | Important |
| A supported way for Vega apps to deep link into major streaming apps by title | "Plan → play" is the natural end of any recommendation experience | Important |
| Alexa+ MCP Toolkit / simulator access outside the US | Developers in Nigeria and elsewhere can build MCP servers but can't test them with Alexa+ | Critical for non-US builders |
| Voice input API for Vega WebView apps (remote mic → text) | Mood-by-voice on the TV itself without a phone | Nice-to-have |
