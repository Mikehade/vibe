# Deploying Vibe to AWS — step by step

This guide takes you from a fresh Mac to a live Vibe URL you can open on the Fire TV simulator, a
phone, or any browser. Follow it top to bottom. Every step tells you what you should see.

**Time:** about 45 minutes the first time (20 of those are AWS creating the database and CDN).
After that, redeploying takes about 5 minutes.
**Cost:** roughly $1–2 per day while it's running. Step 10 shows how to delete everything.

---

## What gets created

```
                        ┌───────────────────────────── AWS (us-east-1) ─────────────────────────────┐
 TV / phone / browser   │                                                                            │
 ─────── HTTPS ───────▶ │  CloudFront ──▶ S3 bucket            (the web app)                          │
                        │      │                                                                     │
                        │      └── /api/*, /mcp ──▶ App Runner (backend container from ECR)          │
                        │                              │   ├──▶ Amazon Bedrock (Claude)              │
                        │                              │   ├──▶ RDS PostgreSQL                       │
                        │                              │   └──▶ Secrets Manager (DB password, TMDB)  │
                        └────────────────────────────────────────────────────────────────────────────┘
```

Everything is defined in `deploy/aws/template.yaml` and created by one script: `deploy/aws/deploy.sh`.
You only ever get one URL, the CloudFront address. It serves the TV app, the API (`/api/...`) and the
Alexa+ MCP server (`/mcp`).

---

## Step 1 — Install the tools (once)

Open **Terminal** and run:

```bash
# Homebrew (skip if you already have it: run `brew --version` to check)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

brew install awscli node python@3.12 git
```

Then install **Docker Desktop for Mac (Apple chip)** from https://www.docker.com/products/docker-desktop/,
open it once, and wait until it says *Engine running*.

**Check:**
```bash
aws --version        # aws-cli/2.x
docker info | head -3   # no error
node --version       # v18 or newer
python3 --version    # 3.11 or newer
```

---

## Step 2 — Get the code in place

```bash
cd ~/Projects                  # or wherever you keep code
unzip ~/Downloads/vibe.zip     # creates vibe-main/
cd vibe-main
```

If you're working in your own GitHub repo instead, copy the files in and remove the old ones listed in
`CHANGED_FILES.md`. Run every command in this guide from the `vibe-main` folder.

---

## Step 3 — Give the AWS CLI your credentials

The deploy script needs an AWS user that can create resources. The simplest option for a hackathon
is an IAM user with the **AdministratorAccess** policy.

**If your keys are in `backend/.env` already** (`AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY`), the deploy
script uses them automatically and you can skip to the check.

**Otherwise**, configure the CLI:
```bash
aws configure
#   AWS Access Key ID:     <your key>
#   AWS Secret Access Key: <your secret>
#   Default region name:   us-east-1
#   Default output format: json
```

**Check:**
```bash
aws sts get-caller-identity
```
You should see your account number and user ARN. If you get an error, the keys are wrong or inactive.

> Use **us-east-1**. App Runner, Bedrock and the `us.` Claude model ids all work there.

---

## Step 4 — Turn on the Claude models in Bedrock

1. Sign in to the AWS console and switch the region (top right) to **US East (N. Virginia) us-east-1**.
2. Go to **Amazon Bedrock → Model access** (left menu; in newer consoles it's under *Bedrock configurations*).
3. Make sure these show **Access granted**. If not, select them → **Request / Enable** (Anthropic may
   ask for a short use-case form; approval is usually instant):
   - **Claude Sonnet 4.6**: the planner (`BEDROCK_MODEL_ID`)
   - **Claude Haiku 4.5**: short tasks like swap reasons (`BEDROCK_FAST_MODEL_ID`). Optional: if you skip it,
     set `BEDROCK_FAST_MODEL_ID` to the same value as `BEDROCK_MODEL_ID` in `backend/.env`.

If you already use a different Claude model, put its id in `backend/.env` instead.

---

## Step 5 — Fill in `backend/.env`

```bash
./scripts/setup.sh        # installs dependencies; creates backend/.env if it doesn't exist
open -e backend/.env      # opens it in TextEdit
```

Make sure these lines are set (keep your existing values if you already had a `.env`):

```ini
TMDB_API_KEY=xxxxxxxxxxxxxxxx                                     # required
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=us.anthropic.claude-sonnet-4-6
BEDROCK_FAST_MODEL_ID=us.anthropic.claude-haiku-4-5-20251001-v1:0
DEFAULT_REGION=NG          # default streaming country for new profiles (US, GB, NG, …)
# AWS_ACCESS_KEY_ID=...    # only if you didn't run `aws configure`
# AWS_SECRET_ACCESS_KEY=...
```

The TMDB key is stored in AWS Secrets Manager during deploy. It is never put into the web app.

---

## Step 6 — Pre-flight check (2 minutes)

```bash
./scripts/check-aws.sh
```

You want **four green ticks**:
```
✓ AWS credentials: account 123456789012 (your-user)
✓ Planner model us.anthropic.claude-sonnet-4-6: 'ready' in 1.2s
✓ Fast model us.anthropic.claude-haiku-4-5-20251001-v1:0: 'ready' in 0.6s
✓ TMDB key works
```
Fix any red cross before deploying. The hint under it says what to do; it is usually model access
(Step 4) or a typo in `.env`.

Optional but recommended: `./scripts/test.sh` should end with **✓ All checks passed**.

---

## Step 7 — Deploy

Make sure Docker Desktop is running, then:

```bash
./deploy/aws/deploy.sh
```

What happens, in order (you'll see a `→` line for each):

| Stage | What it does | First run | Later runs |
|---|---|---|---|
| ECR | Creates the image repository `vibe-api`, logs Docker in | seconds | seconds |
| Docker build | Builds the backend for linux/amd64 and pushes it | 5–10 min on an M1 (it emulates Intel; slow is normal) | 1–3 min |
| CloudFormation | Creates RDS, App Runner, S3, CloudFront, secrets, IAM roles | **15–25 min** | 3–6 min |
| Web app | Builds the TV app and uploads it to S3, clears the CDN cache | 1 min | 1 min |
| Smoke test | Calls `/api/v1/health` through CloudFront | up to 5 min | seconds |

You can watch progress in the AWS console → **CloudFormation → Stacks → vibe → Events**.
Don't close the Terminal while it runs.

**When it finishes you'll see:**
```
  Vibe is live.

  Web app (TV/browser):  https://d1abcd2efgh3ij.cloudfront.net
  MCP (Alexa+):          https://d1abcd2efgh3ij.cloudfront.net/mcp
  API docs:              https://d1abcd2efgh3ij.cloudfront.net/api/v1/docs
```
The same values are saved in `deploy/aws/outputs.env`.

---

## Step 8 — Check it works

1. **Browser:** open the Web app URL in Chrome. Use the arrow keys, Enter and Esc. Complete onboarding, pick
   a mood and a time, and watch the plan stream in with real posters.
2. **API:** open `…/api/v1/health`. It should show `{"status":"ok",…}`.
3. **MCP (Alexa+):**
   ```bash
   ./scripts/mcp-smoke.sh https://d1abcd2efgh3ij.cloudfront.net/mcp
   ```
   Expect `✓ initialize — protocol 2025-11-25`, the tool list, a planned night, and `✓ TV inbox received`.
4. **Phone (Couch Mode):** on the TV page open **Couch Mode** and scan the QR with your phone. It works over
   mobile data too, because it's a public HTTPS URL.

---

## Step 9 — Point the Fire TV app at it

```bash
./tv-app/vega/setup.sh ~/path/to/VibeTV https://d1abcd2efgh3ij.cloudfront.net
```
Then build and run in Vega Studio. Full steps are in `tv-app/vega/README.md`.
Any real Fire TV can also open the URL in the **Silk** browser.

---

## Updating after code changes

Run the same command again:
```bash
./deploy/aws/deploy.sh
```
It builds a new image, rolls App Runner over to it (no downtime), and re-uploads the web app.
The database and your data are kept.

Only changed the web app? Running the full deploy is still fine. It just takes a couple of extra minutes for the image.

---

## Step 10 — Tear it down after judging

```bash
./deploy/aws/destroy.sh
```
Type `delete` to confirm. This removes the stack (database included, so all data is lost), empties the
bucket and deletes the ECR repository. It takes about 10–15 minutes because CloudFront is slow to delete.

Keep it running until judging is finished. Judges may open your demo link.

---

## Troubleshooting

| What you see | What to do |
|---|---|
| `AWS credentials not working` | Re-run Step 3. Check `aws sts get-caller-identity`. |
| `Docker is installed but not running` | Open Docker Desktop and wait for *Engine running*. |
| Docker build seems stuck at `pip install` | It's emulating Intel on Apple silicon. The first build can take 10 minutes. |
| `No default VPC in us-east-1` | `aws ec2 create-default-vpc` then re-run. |
| `AccessDenied … iam:CreateRole` (or similar) | Your IAM user lacks permissions. Attach **AdministratorAccess** (Step 3). |
| Stack fails while creating **ApiService** | The container didn't become healthy. Open **App Runner** in the console, pick the service whose name starts with `ApiService`, then **Logs → Application logs**. Common causes: Bedrock model not enabled (Step 4), wrong model id in `.env`. Fix it and re-run `deploy.sh`. The script removes a failed first attempt automatically. |
| Stack shows `UPDATE_ROLLBACK_COMPLETE` | An update failed and was rolled back; the old version is still running. Check the Events tab for the first red line, fix it, re-run. |
| Web page loads but plans fail | Open `…/api/v1/health`. If that works, check App Runner application logs for Bedrock or TMDB errors and run `./scripts/check-aws.sh` locally. |
| No posters / "Nothing matched" | TMDB key or region. In the app go to Settings → Streaming services and add a service or choose another country. |
| Old version still showing in the browser | Hard refresh (Cmd+Shift+R). The script invalidates the CDN, which can take 1–2 minutes. |
| `Smoke test: API not answering yet` | App Runner can take a few extra minutes after the stack completes. Open the URL again in 5 minutes. |
| You want to see costs | AWS console → **Billing → Bills**. Set a budget alert: Billing → Budgets → create a $20 monthly budget. |

---

## Reference

| File | Purpose |
|---|---|
| `deploy/aws/deploy.sh` | The whole deploy: ECR, CloudFormation, web upload, smoke test |
| `deploy/aws/template.yaml` | All AWS resources (RDS, App Runner, S3, CloudFront, Secrets Manager, IAM) |
| `deploy/aws/destroy.sh` | Deletes everything |
| `deploy/aws/outputs.env` | Your URLs after a deploy (not committed to git) |

Optional environment variables for `deploy.sh`:

| Variable | Default | Use |
|---|---|---|
| `STACK` | `vibe` | Run a second copy, e.g. `STACK=vibe-test ./deploy/aws/deploy.sh` |
| `REPO` | `vibe-api` | ECR repository name |
| `AWS_REGION` | from `.env`, else `us-east-1` | Region to deploy into |
