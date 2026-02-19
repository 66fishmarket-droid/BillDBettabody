"""
Bill D'Bettabody — End-to-End Backend Test Suite
=================================================
Tests all endpoints against a live local server.

Usage:
    python test_e2e.py

Requires:
    - Flask server running on localhost:5000
    - cli_001 exists in Google Sheets (returning-client tests)
    - .env configured with valid API keys and webhooks
"""

import json
import sys
import time
import requests

BASE_URL = "http://localhost:5000"
KNOWN_CLIENT_ID = "cli_001"        # Existing client in Sheets
NEW_CLIENT_ID   = "cli_test_e2e"   # Will be created during onboarding tests

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

# ── Result tracking ───────────────────────────────────────────────────────────
results = []

def run(label, fn):
    """Run a single test, capture pass/fail/warn, print summary line."""
    print(f"\n{CYAN}>> {label}{RESET}")
    try:
        outcome = fn()
        if outcome is True:
            status = f"{GREEN}PASS{RESET}"
            results.append(("PASS", label))
        elif outcome == "SKIP":
            status = f"{YELLOW}SKIP{RESET}"
            results.append(("SKIP", label))
        else:
            status = f"{YELLOW}WARN{RESET} -- {outcome}"
            results.append(("WARN", label))
        print(f"  {status}")
    except AssertionError as e:
        print(f"  {RED}FAIL{RESET} -- {e}")
        results.append(("FAIL", label))
    except Exception as e:
        print(f"  {RED}ERROR{RESET} -- {e}")
        results.append(("ERROR", label))


def p(label, data):
    """Pretty-print a response snippet."""
    snippet = json.dumps(data, indent=2)[:600]
    print(f"  {YELLOW}{label}:{RESET}\n{snippet}")


# ── Shared state (populated as tests run) ─────────────────────────────────────
state = {}


# ============================================================
# 1. HEALTH & STATUS
# ============================================================

def test_health():
    r = requests.get(f"{BASE_URL}/health", timeout=5)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    body = r.json()
    assert body.get("status") == "ok", f"status field: {body}"
    p("Response", body)
    return True


def test_status():
    r = requests.get(f"{BASE_URL}/status", timeout=5)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}"
    body = r.json()
    p("Response", body)
    configured = body.get("webhooks_configured", 0)
    if configured == 0:
        return "0 webhooks configured — check .env"
    return True


# ============================================================
# 2. INITIALIZE — STRANGER (no client_id)
# ============================================================

def test_initialize_stranger():
    r = requests.post(f"{BASE_URL}/initialize", json={}, timeout=5)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("status") == "stranger", f"Expected stranger: {body}"
    assert body.get("session_id"), "Missing session_id"
    assert body.get("greeting"), "Missing greeting"
    p("Response", body)
    state["stranger_session_id"] = body["session_id"]
    return True


# ============================================================
# 3. INITIALIZE — RETURNING CLIENT (cli_001)
# ============================================================

def test_initialize_returning():
    r = requests.post(f"{BASE_URL}/initialize",
                      json={"client_id": KNOWN_CLIENT_ID}, timeout=15)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    p("Response", body)
    assert body.get("status") == "ready", f"Expected ready, got: {body.get('status')} — client may not exist in Sheets"
    assert body.get("session_id"), "Missing session_id"
    assert body.get("greeting"), "Missing greeting"
    state["ready_session_id"] = body["session_id"]
    return True


# ============================================================
# 4. PROFILE
# ============================================================

def test_profile_no_session():
    r = requests.get(f"{BASE_URL}/profile", timeout=5)
    assert r.status_code == 400, f"Expected 400 without session_id, got {r.status_code}"
    return True


def test_profile_with_session():
    sid = state.get("ready_session_id")
    if not sid:
        return "SKIP"
    r = requests.get(f"{BASE_URL}/profile", params={"session_id": sid}, timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    p("Profile snapshot", body)
    # Should have at minimum a client_id field or some profile data
    assert isinstance(body, dict), "Expected dict response"
    return True


# ============================================================
# 5. DASHBOARD
# ============================================================

def test_dashboard_no_session():
    r = requests.get(f"{BASE_URL}/dashboard", timeout=5)
    assert r.status_code == 400, f"Expected 400 without session_id, got {r.status_code}"
    return True


def test_dashboard_with_session():
    sid = state.get("ready_session_id")
    if not sid:
        return "SKIP"
    r = requests.get(f"{BASE_URL}/dashboard", params={"session_id": sid}, timeout=15)
    p("Status", {"code": r.status_code})
    assert r.status_code in (200, 503), f"Unexpected status {r.status_code}: {r.text}"
    if r.status_code == 503:
        return f"Sheets connection error: {r.json().get('details', '')[:100]}"
    body = r.json()
    p("Dashboard snapshot", body)
    return True


# ============================================================
# 6. CONTEXT INTEGRITY CHECK
# ============================================================

def test_context_integrity_check():
    sid = state.get("ready_session_id")
    if not sid:
        return "SKIP"
    r = requests.post(f"{BASE_URL}/context-integrity-check",
                      json={"session_id": sid}, timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    p("Integrity check", body)
    return True


# ============================================================
# 7. CHAT — SIMPLE GREETING (no tool calls expected)
# ============================================================

def test_chat_simple():
    sid = state.get("ready_session_id")
    if not sid:
        return "SKIP"
    r = requests.post(f"{BASE_URL}/chat",
                      json={"session_id": sid, "message": "Hey Bill, how's it going?"},
                      timeout=30)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("response"), "Empty response from Bill"
    p("Bill says", {"response": body["response"][:300]})
    return True


# ============================================================
# 8. CHAT — TRAINING QUESTION (may trigger tool call)
# ============================================================

def test_chat_training_question():
    sid = state.get("ready_session_id")
    if not sid:
        return "SKIP"
    r = requests.post(f"{BASE_URL}/chat",
                      json={"session_id": sid,
                            "message": "What does my training plan look like this week?"},
                      timeout=60)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("response"), "Empty response from Bill"
    p("Bill says", {"response": body["response"][:400]})
    return True


# ============================================================
# 9. CHAT — INJURY QUESTION (should reference context)
# ============================================================

def test_chat_injury_awareness():
    sid = state.get("ready_session_id")
    if not sid:
        return "SKIP"
    r = requests.post(f"{BASE_URL}/chat",
                      json={"session_id": sid,
                            "message": "Do I have any injuries I should be working around?"},
                      timeout=30)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("response"), "Empty response"
    p("Bill says", {"response": body["response"][:400]})
    return True


# ============================================================
# 10. REST DAY SUMMARY
# ============================================================

def test_rest_day_summary():
    sid = state.get("ready_session_id")
    if not sid:
        return "SKIP"
    r = requests.get(f"{BASE_URL}/sessions/rest-day-summary",
                     params={"session_id": sid}, timeout=30)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("summary"), "Missing summary field"
    p("Rest day message", {"summary": body["summary"]})
    return True


# ============================================================
# 11. REFRESH CONTEXT
# ============================================================

def test_refresh_context():
    sid = state.get("ready_session_id")
    if not sid:
        return "SKIP"
    r = requests.post(f"{BASE_URL}/refresh-context",
                      json={"session_id": sid}, timeout=15)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    p("Refresh result", body)
    assert body.get("status") == "refreshed", f"Unexpected status: {body}"
    return True


# ============================================================
# 12. INITIALIZE — ONBOARDING (new client)
# ============================================================

def test_initialize_onboarding():
    r = requests.post(f"{BASE_URL}/initialize",
                      json={"client_id": NEW_CLIENT_ID}, timeout=10)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    p("Response", body)
    # Could be onboarding (new) or ready (if ran before)
    assert body.get("status") in ("onboarding", "ready"), f"Unexpected status: {body}"
    state["onboarding_session_id"] = body["session_id"]
    state["onboarding_status"] = body["status"]
    return True


# ============================================================
# 13. CHAT — ONBOARDING EXCHANGE
# ============================================================

def test_chat_onboarding():
    sid = state.get("onboarding_session_id")
    if not sid or state.get("onboarding_status") != "onboarding":
        return "SKIP — client already exists, not in onboarding"
    r = requests.post(f"{BASE_URL}/chat",
                      json={"session_id": sid, "message": "Hi, my name is Test User"},
                      timeout=30)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("response"), "Empty response"
    p("Bill onboarding says", {"response": body["response"][:300]})
    return True


# ============================================================
# 14. SESSION DETAIL (fetch a real session_id from context)
# ============================================================

def test_session_detail():
    sid = state.get("ready_session_id")
    if not sid:
        return "SKIP"

    # Pull a real session_id from the loaded context
    from models import client_context as cc
    session = cc.get_session(sid)
    if not session:
        return "SKIP — no session found in state"

    context = session.get("context", {})
    sessions = context.get("sessions", {})
    active = sessions.get("active", []) if isinstance(sessions, dict) else sessions

    if not active:
        return "SKIP — no active sessions in context to test with"

    # Extract session_id from first active session (numeric key '6' or named 'session_id')
    first = active[0] if isinstance(active, list) else {}
    training_session_id = first.get("6") or first.get("session_id")
    if not training_session_id:
        return f"SKIP — could not extract session_id from: {list(first.keys())[:5]}"

    print(f"  Testing with training session_id: {training_session_id}")
    r = requests.get(f"{BASE_URL}/session/{training_session_id}",
                     params={"session_id": sid}, timeout=15)
    assert r.status_code in (200, 404), f"Unexpected status {r.status_code}: {r.text}"
    body = r.json()
    p("Session detail", body)
    return True


# ============================================================
# 15. SESSION COMPLETE — MISSING STEPS (should error gracefully)
# ============================================================

def test_session_complete_no_steps():
    sid = state.get("ready_session_id")
    if not sid:
        return "SKIP"
    r = requests.post(f"{BASE_URL}/session/fake_session_123/complete",
                      json={"session_id": sid, "steps_upsert": []},
                      timeout=10)
    # Should be a 400 (no step updates provided)
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
    p("Error response", r.json())
    return True


# ============================================================
# 16. 404 HANDLER
# ============================================================

def test_404():
    r = requests.get(f"{BASE_URL}/nonexistent-endpoint", timeout=5)
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"
    body = r.json()
    assert "available_endpoints" in body, "Missing endpoint list in 404 response"
    return True


# ============================================================
# 17. CLEANUP SESSIONS
# ============================================================

def test_cleanup():
    r = requests.post(f"{BASE_URL}/cleanup-sessions",
                      json={"max_age_hours": 48}, timeout=5)
    assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.text}"
    body = r.json()
    p("Cleanup result", body)
    return True


# ============================================================
# MAIN
# ============================================================

TESTS = [
    # Infrastructure
    ("Health check",                   test_health),
    ("Status check",                   test_status),
    # Initialize
    ("Initialize — stranger",          test_initialize_stranger),
    ("Initialize — returning client",  test_initialize_returning),
    ("Initialize — onboarding (new)",  test_initialize_onboarding),
    # Profile & Dashboard
    ("Profile — no session_id (400)",  test_profile_no_session),
    ("Profile — with session",         test_profile_with_session),
    ("Dashboard — no session_id (400)",test_dashboard_no_session),
    ("Dashboard — with session",       test_dashboard_with_session),
    # Context
    ("Context integrity check",        test_context_integrity_check),
    ("Refresh context",                test_refresh_context),
    # Chat
    ("Chat — simple greeting",         test_chat_simple),
    ("Chat — training question",       test_chat_training_question),
    ("Chat — injury awareness",        test_chat_injury_awareness),
    ("Chat — onboarding exchange",     test_chat_onboarding),
    # Session
    ("Session detail",                 test_session_detail),
    ("Session complete — no steps (400)", test_session_complete_no_steps),
    # Utilities
    ("Rest day summary",               test_rest_day_summary),
    ("404 handler",                    test_404),
    ("Cleanup sessions",               test_cleanup),
]


if __name__ == "__main__":
    print(f"\n{BOLD}{'='*60}")
    print("Bill D'Bettabody — E2E Test Suite")
    print(f"{'='*60}{RESET}")
    print(f"Server: {BASE_URL}")
    print(f"Known client: {KNOWN_CLIENT_ID}")
    print(f"Tests to run: {len(TESTS)}\n")

    for label, fn in TESTS:
        run(label, fn)

    # ── Summary ──────────────────────────────────────────────
    print(f"\n{BOLD}{'='*60}")
    print("RESULTS SUMMARY")
    print(f"{'='*60}{RESET}")

    counts = {"PASS": 0, "WARN": 0, "SKIP": 0, "FAIL": 0, "ERROR": 0}
    for status, label in results:
        counts[status] = counts.get(status, 0) + 1
        colour = {"PASS": GREEN, "WARN": YELLOW, "SKIP": YELLOW,
                  "FAIL": RED, "ERROR": RED}.get(status, RESET)
        print(f"  {colour}{status:<5}{RESET}  {label}")

    print(f"\n  {GREEN}PASS: {counts['PASS']}{RESET}  "
          f"{YELLOW}WARN: {counts['WARN']}  SKIP: {counts['SKIP']}{RESET}  "
          f"{RED}FAIL: {counts['FAIL']}  ERROR: {counts['ERROR']}{RESET}")

    print(f"\n{'='*60}\n")

    # Exit non-zero if any hard failures
    if counts["FAIL"] > 0 or counts["ERROR"] > 0:
        sys.exit(1)
