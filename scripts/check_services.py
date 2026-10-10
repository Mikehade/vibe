"""Credential and model-access checks. Run via scripts/check-aws.sh."""

import os
import sys
import time

from dotenv import load_dotenv

load_dotenv(".env")

GREEN, RED, DIM, END = "\033[32m", "\033[31m", "\033[2m", "\033[0m"
failed = False


def ok(msg):
    print(f"{GREEN}✓{END} {msg}")


def bad(msg, hint=""):
    global failed
    failed = True
    print(f"{RED}✗{END} {msg}" + (f"\n  {DIM}{hint}{END}" if hint else ""))


region = os.getenv("AWS_REGION", "us-east-1")
try:
    import boto3

    ident = boto3.client("sts", region_name=region).get_caller_identity()
    ok(f"AWS credentials: account {ident['Account']} ({ident['Arn'].split('/')[-1]})")
except Exception as e:  # noqa: BLE001
    bad(f"AWS credentials: {e}", "Set AWS_ACCESS_KEY_ID/AWS_SECRET_ACCESS_KEY in backend/.env or run `aws configure`.")

for label, model in (("Planner model", os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-6")),
                     ("Fast model", os.getenv("BEDROCK_FAST_MODEL_ID", "us.anthropic.claude-haiku-4-5-20251001-v1:0"))):
    try:
        client = boto3.client("bedrock-runtime", region_name=region)
        t = time.time()
        r = client.converse(
            modelId=model,
            messages=[{"role": "user", "content": [{"text": "Reply with the single word: ready"}]}],
            inferenceConfig={"maxTokens": 10, "temperature": 0},
        )
        text = r["output"]["message"]["content"][0]["text"].strip()
        ok(f"{label} {model}: '{text}' in {time.time() - t:.1f}s")
    except Exception as e:  # noqa: BLE001
        hint = "Enable the model in Bedrock console → Model access (region " + region + "), or change the id in backend/.env."
        if label == "Fast model":
            hint += " Optional: Vibe falls back to templates if the fast model is unavailable."
        bad(f"{label} {model}: {str(e)[:180]}", hint)

key = os.getenv("TMDB_API_KEY", "")
try:
    import httpx

    headers, params = {}, {}
    if key.startswith("eyJ"):
        headers["Authorization"] = f"Bearer {key}"
    else:
        params["api_key"] = key
    r = httpx.get("https://api.themoviedb.org/3/configuration", params=params, headers=headers, timeout=10)
    if r.status_code == 200:
        ok("TMDB key works")
    else:
        bad(f"TMDB key rejected ({r.status_code})", "Get one at https://www.themoviedb.org/settings/api")
except Exception as e:  # noqa: BLE001
    bad(f"TMDB: {e}")

sys.exit(1 if failed else 0)
