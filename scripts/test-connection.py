r"""Offline smoke checks for the StayLongerAI backend contracts.

Run from any directory with:
    .venv\Scripts\python.exe scripts\test-connection.py

The checks import the FastAPI app and call local endpoint functions directly.
They do not send Twilio, Gemini, ngrok, or blockchain network requests.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from backend import main as backend_main  # noqa: E402


def test_dashboard_data() -> None:
    data = backend_main.build_dashboard_payload()
    assert isinstance(data, dict)
    assert isinstance(data.get("title"), str) and data["title"]
    assert isinstance(data.get("metrics"), list) and len(data["metrics"]) >= 4
    assert isinstance(data.get("chartData"), list) and data["chartData"]
    assert isinstance(data.get("inventory"), list)


def test_customer_data() -> None:
    customers = backend_main.build_customer_directory()
    assert isinstance(customers, list) and customers
    required_fields = {"id", "name", "health", "risk", "segment"}
    assert all(required_fields.issubset(customer) for customer in customers)


def test_registered_routes() -> None:
    registered = {
        (method, route.path)
        for route in backend_main.app.routes
        for method in (getattr(route, "methods", None) or set())
    }
    required = {
        ("GET", "/"),
        ("GET", "/health"),
        ("GET", "/api/dashboard"),
        ("GET", "/api/customers"),
        ("POST", "/api/customers/import"),
        ("GET", "/api/inventory"),
        ("GET", "/api/rewards/status"),
        ("POST", "/api/rewards/claim"),
        ("GET", "/webhook"),
        ("POST", "/webhook"),
    }
    missing = sorted(required - registered)
    assert not missing, f"Missing routes: {missing}"


async def test_inventory_contract() -> None:
    payload = await backend_main.inventory_summary()
    assert isinstance(payload, dict)
    assert isinstance(payload.get("inventory"), list)
    assert isinstance(payload.get("total"), int)
    assert payload["total"] == len(payload["inventory"])


async def test_reward_contracts() -> None:
    status = await backend_main.rewards_status()
    required_status_fields = {
        "mode",
        "configured",
        "network",
        "asset",
        "defaultAmount",
        "reason",
    }
    assert required_status_fields.issubset(status)
    assert status["mode"] in {"demo", "live"}
    assert isinstance(status["configured"], bool)
    assert isinstance(status["network"], str) and status["network"]
    assert isinstance(status["asset"], str) and status["asset"]
    assert isinstance(status["defaultAmount"], (int, float))
    assert isinstance(status["reason"], str) and status["reason"]

    sender = "whatsapp:+15550000000"
    original_events = list(backend_main.REWARD_EVENTS)
    original_state = backend_main.USER_STATES.get(sender)
    token = ""
    try:
        claim_url = backend_main.generate_dashboard_url(sender)
        token = parse_qs(urlparse(claim_url).query).get("token", [""])[0]
        assert token, "Generated reward URL did not contain a token."

        request = backend_main.RewardClaimRequest(token=token)
        first_claim = await backend_main.claim_reward(request)
        assert first_claim["status"] == "claimed"
        assert isinstance(first_claim["amount"], (int, float))
        assert first_claim["amount"] > 0
        assert isinstance(first_claim["message"], str) and first_claim["message"]
        assert isinstance(first_claim["demo"], bool)

        second_claim = await backend_main.claim_reward(request)
        assert second_claim["status"] == "already_claimed"
        assert second_claim["amount"] == first_claim["amount"]
        assert isinstance(second_claim["demo"], bool)
    finally:
        if token:
            backend_main.REWARD_CLAIMS.pop(token, None)
        if original_state is None:
            backend_main.USER_STATES.pop(sender, None)
        else:
            backend_main.USER_STATES[sender] = original_state
        backend_main.REWARD_EVENTS[:] = original_events


def run_check(label: str, check) -> bool:
    try:
        result = check()
        if asyncio.iscoroutine(result):
            asyncio.run(result)
        print(f"[PASS] {label}")
        return True
    except Exception as exc:
        print(f"[FAIL] {label}: {exc}")
        return False


def main() -> int:
    print("StayLongerAI backend smoke checks")
    checks = [
        ("dashboard payload", test_dashboard_data),
        ("customer payload", test_customer_data),
        ("registered routes", test_registered_routes),
        ("inventory API contract", test_inventory_contract),
        ("reward API contracts", test_reward_contracts),
    ]
    passed = [run_check(label, check) for label, check in checks]

    if all(passed):
        print("All smoke checks passed.")
        print("Backend: cd backend && ..\\.venv\\Scripts\\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000")
        print("Frontend: cd frontend && npm.cmd run dev")
        return 0

    print("One or more smoke checks failed.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
