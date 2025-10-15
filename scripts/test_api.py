#!/usr/bin/env python3
"""Test runner for the unifero-cli FastAPI server.

Sends a collection of predefined JSON payloads to POST /process and writes
the request+response details to output.txt in the project root.

Usage:
  source .venv/bin/activate
  python3 scripts/test_api.py

You can override the server URL with the SERVER_URL env var.
"""
import os
import time
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Tuple

import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Configuration
SERVER_URL = os.environ.get("SERVER_URL", "http://127.0.0.1:8000")
ENDPOINT = f"{SERVER_URL}/process"
HEALTH = f"{SERVER_URL}/health"
OUTPUT_PATH = os.path.join(os.getcwd(), "output.txt")

# Test cases covering various scenarios
TEST_CASES: List[Tuple[str, Dict[str, Any]]] = [
    ("search_minimal", {"mode": "search", "query": "Next.js routing"}),
    ("search_full", {"mode": "search", "query": "Next.js routing", "limit": 3, "snippet_len": 150, "content_len": 2000}),
    ("docs_minimal", {"mode": "docs", "url": "https://example.com/docs"}),
    ("docs_full", {"mode": "docs", "url": "https://example.com/docs", "limit": 5, "include_content": True, "content_limit": 1500}),
    ("ai_sdk_docs_test", {"mode": "docs", "url": "https://ai-sdk.dev/docs/ai-sdk-ui/chatbot", "limit": 1, "include_content": True, "content_limit": 3000}),
    ("search_missing_query", {"mode": "search"}),
    ("invalid_mode", {"mode": "bogus", "query": "x"}),
]


def run_case(name: str, payload: dict, retries: int = 2, timeout: int = 10) -> dict:
    start = time.time()
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(ENDPOINT, json=payload, timeout=timeout)
            elapsed = time.time() - start
            try:
                body = resp.json()
            except Exception:
                body = resp.text
            return {
                "name": name,
                "request": payload,
                "status_code": resp.status_code,
                "response": body,
                "elapsed": elapsed,
                "attempts": attempt,
            }
        except Exception as e:
            last_exc = e
            time.sleep(0.5 * attempt)

    elapsed = time.time() - start
    return {
        "name": name,
        "request": payload,
        "status_code": None,
        "response": str(last_exc),
        "elapsed": elapsed,
        "attempts": retries,
    }


def main():
    print(f"Running {len(TEST_CASES)} tests against {ENDPOINT}")

    # wait for health
    ready = False
    for i in range(20):
        try:
            h = requests.get(HEALTH, timeout=2)
            if h.status_code == 200:
                ready = True
                break
        except Exception:
            pass
        time.sleep(0.25)

    if not ready:
        print(f"WARNING: {HEALTH} did not respond; tests will still attempt requests and may fail.")

    now = datetime.utcnow().isoformat() + "Z"
    with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
        f.write("# Test run: " + now + "\n")

    for name, payload in TEST_CASES:
        print(f"- {name} -> sending...", end=" ")
        r = run_case(name, payload)
        print(f"done (status={r['status_code']}) in {r['elapsed']:.2f}s, attempts={r.get('attempts')}")
        # write each result immediately so partial runs are preserved
        with open(OUTPUT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(r, indent=2, ensure_ascii=False))
            f.write("\n\n")

    print(f"Appended results to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
