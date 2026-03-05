"""
Quick diagnostic: call Make.com webhooks directly and dump full response details.
"""

import os
import sys
import time
import json
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

CLIENT_ID = "cli_001"

WEBHOOKS_TO_TEST = {
    "check_client_exists": os.getenv("WEBHOOK_CHECK_CLIENT_EXISTS"),
    "load_client_context": os.getenv("WEBHOOK_LOAD_CLIENT_CONTEXT"),
}

for name, url in WEBHOOKS_TO_TEST.items():
    if not url:
        print(f"\n[{name}] NOT CONFIGURED in .env — skipping")
        continue

    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL    : {url}")
    print(f"{'='*60}")

    payload = {"client_id": CLIENT_ID}

    t0 = time.time()
    try:
        r = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=90,
        )
        elapsed = time.time() - t0
        print(f"Status : {r.status_code}")
        print(f"Elapsed: {elapsed:.2f}s")
        print(f"Body   : {repr(r.text[:500])}")
    except Exception as e:
        elapsed = time.time() - t0
        print(f"ERROR  : {e} (after {elapsed:.2f}s)")
