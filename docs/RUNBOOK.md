# Runbook — test, deploy, demo

Everything here runs from the repo root on your Mac (Apple silicon is fine). Each step says what you
should see. If something fails, check **Troubleshooting** at the bottom.

## 0. One-time tools
```bash
brew install python@3.12 node awscli git
# Docker Desktop: https://www.docker.com/products/docker-desktop/  (start it once)
softwareupdate --install-rosetta --agree-to-license   # needed later for the Vega simulator
```

## 1. Keys
`backend/.env` holds your keys. If you already have one from the old version, keep it and add the new
lines from `backend/.env.example` (`BEDROCK_FAST_MODEL_ID`, `PLAN_TIMEOUT_SECONDS`, `MAX_AGENT_TURNS`,
`DEFAULT_REGION`, `FAKE_SERVICES`). Otherwise:
```bash
cp backend/.env.example backend/.env
```
Then fill in:
- `TMDB_API_KEY` — v3 key or v4 read token
- AWS: either `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` in the file, or leave them empty and use `aws configure`
- `DEFAULT_REGION=NG` if most viewers are in Nigeria (each profile can pick its own region in onboarding)

## 2. Install and check
```bash
./scripts/setup.sh
./scripts/check-aws.sh
```
You should see four green ticks: AWS account, planner model, fast model, TMDB.
- **Planner model fails:** Bedrock console → *Model access* (us-east-1) → enable Anthropic Claude Sonnet 4.6, or set `BEDROCK_MODEL_ID` to a Claude model you have.
- **Fast model fails:** enable Claude Haiku 4.5 too, or set `BEDROCK_FAST_MODEL_ID` to the same value as `BEDROCK_MODEL_ID`. (Vibe still works without it — swap reasons fall back to templates.)

## 3. Automated tests
```bash
./scripts/test.sh
```
Runs 60+ backend tests (engine, streaming, swap, re-plan, Couch Mode, profiles, MCP handshake) with
built-in fakes, then type-checks and builds the web app. Ends with **✓ All checks passed**.

## 4. Run locally
```bash
./scripts/dev.sh --fake     # offline catalogue + generated artwork — no keys needed
./scripts/dev.sh            # real Bedrock + TMDB
```
Open http://localhost:5173 in Chrome. Use **only the arrow keys, Enter and Esc** — that's exactly what
the Fire TV remote sends.

Things to try:
1. Onboarding → pick your services → pick tastes.
2. Choose a mood → a time → watch the plan stream in (status lines, tool calls, picks landing).
3. Focus a pick → **Not this one** swaps it.
4. **Start watching** → **I've finished** → *Wind me down* re-plans the rest.
5. **Couch Mode:** on your phone (same Wi-Fi), open the LAN address `dev.sh` printed, e.g.
   `http://192.168.1.20:5173/#/join/ABCD`, or scan the QR (the QR uses the address the TV page was opened with —
   open the TV page via the LAN address too if you want to scan it). Add moods from two phones, build the night,
   vote to skip on both phones and watch the TV swap it.
6. **Settings → Link Alexa** shows the 6-digit TV code.
7. MCP (acts as Alexa): in another terminal `./scripts/mcp-smoke.sh` — keep the TV page open and watch the
   lineup appear on it.

## 5. Deploy to AWS (~20 minutes the first time)
Detailed step-by-step guide: **[DEPLOY_AWS.md](DEPLOY_AWS.md)**

```bash
./deploy/aws/deploy.sh
```
It builds the backend image for App Runner, pushes it to ECR, creates the stack (RDS PostgreSQL,
App Runner, S3 + CloudFront, Secrets Manager), uploads the web app and smoke-tests it. At the end it prints:
```
Web app (TV/browser):  https://dxxxxxxxx.cloudfront.net
MCP (Alexa+):          https://dxxxxxxxx.cloudfront.net/mcp
```
Re-run the same command after any change — it ships a new image and web build.
Check the deployed MCP: `./scripts/mcp-smoke.sh https://dxxxxxxxx.cloudfront.net/mcp`

**Cost:** roughly $1–2 a day while it's running (App Runner + a small RDS instance). After judging:
`./deploy/aws/destroy.sh`.

## 6. Fire TV — Vega Virtual Device (no hardware needed)
Follow **[tv-app/vega/README.md](../tv-app/vega/README.md)**. Short version:
1. Install the Vega SDK + Vega Studio (VS Code).
2. Vega Studio → **+** → template **hello-world** → name `VibeTV`, package `com.vibe.tv`.
3. `./tv-app/vega/setup.sh ~/path/to/VibeTV https://dxxxxxxxx.cloudfront.net`
4. In Vega Studio: build → ▶ *VirtualDevice:Tv* → ▶ *VibeTV*.

Phones in Couch Mode then join via the CloudFront URL (QR on the TV).
Any real Fire TV (Fire OS or Vega) can also open the CloudFront URL in the **Silk** browser.

## 7. Alexa+
The server speaks MCP 2025-11-25 over Streamable HTTP at `…/mcp` (no auth, single household demo).
Ways to show it, best first:
1. **Alexa+ MCP Toolkit / web simulator** (US accounts): register the MCP URL as your add-on endpoint,
   then say "link Vibe to my TV, code 123456" and "plan a chill movie night, about two hours".
2. **MCP Inspector** (works anywhere): `npx @modelcontextprotocol/inspector` → Transport *Streamable HTTP* →
   URL `https://dxxxxxxxx.cloudfront.net/mcp` → Connect → run `link_tv` with the TV's code, then
   `plan_movie_night`. Record the Inspector next to the TV simulator: the lineup builds live on the TV.
3. `./scripts/mcp-smoke.sh <url>` for a scripted run.

## 8. Demo video and submission
- Script (under 3 minutes): **[DEMO_SCRIPT.md](DEMO_SCRIPT.md)**
- Devpost text, AWS Builder and Open Source fields: **[SUBMISSION.md](SUBMISSION.md)**
- Product feedback draft: **[PRODUCT_FEEDBACK.md](PRODUCT_FEEDBACK.md)**
- Friction log (up to 10% bonus): **[FRICTION_LOG.md](FRICTION_LOG.md)** — add to it as you go.
- Repo access: make it private and add `chris-trag, knmeiss, giolaq, anishamalde, mosesroth, emersonsklar`
  as collaborators **within 7 days of the deadline** (invites expire after 7 days), or make it public (MIT licence included).

## Troubleshooting
| Symptom | Fix |
|---|---|
| Plan shows "Planning failed" or only template reasons | `./scripts/check-aws.sh`; check model access and region. The plan still completes with the deterministic planner. |
| No titles / "Nothing matched" | Region with few titles on the chosen services — add a service, or choose "show me everything" in Settings → Streaming services. |
| Posters missing | TMDB key invalid or rate-limited — `./scripts/check-aws.sh`. |
| `deploy.sh` stuck uploading the image | Ctrl+C and re-run — the image is now built inside AWS (CodeBuild). See DEPLOY_AWS.md. |
| App Runner unhealthy | AWS console → App Runner → service starting with *ApiService* → Logs. Usually a Bedrock permission/model id or DB start-up; re-run deploy. |
| Stream stops after ~60 s behind CloudFront | The API sends keep-alive lines; if you changed `PLAN_TIMEOUT_SECONDS` above 55, lower it. |
| Vega app shows a white screen | Wrong URL in `src/config.ts`; open the URL in Chrome first. |
| Phone can't join locally | Phone and Mac on the same Wi-Fi; use the LAN URL, not localhost. |
