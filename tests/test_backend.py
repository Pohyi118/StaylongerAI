"""Focused, network-isolated regression tests for the StayLongerAI backend."""

from __future__ import annotations

import asyncio
import os
import unittest
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse
from unittest import mock

from fastapi.testclient import TestClient


# Prevent repository .env values from being loaded into module-level clients
# while the backend is imported for tests. Empty strings intentionally count as
# existing values because load_dotenv(..., override=False) preserves them.
_SAFE_IMPORT_ENV = {
    "TWILIO_ACCOUNT_SID": "",
    "TWILIO_AUTH_TOKEN": "",
    "TWILIO_WHATSAPP_FROM": "whatsapp:+10000000000",
    "TWILIO_VALIDATE_SIGNATURE": "false",
    "TWILIO_WEBHOOK_URL": "",
    "GEMINI_API_KEY": "",
    "SOLANA_PRIVATE_KEY_HEX": "",
    "SOLANA_PRIVATE_KEY": "",
    "SOLANA_LIVE_MODE": "false",
    "USDC_MINT": "",
    "PAYMENT_RECIPIENT_WALLET": "",
    "X402_PAYMENT_URL": "",
    "EASYOCR_DOWNLOAD_ENABLED": "false",
}

with mock.patch.dict(os.environ, _SAFE_IMPORT_ENV, clear=False):
    from api.index import app as vercel_app
    from backend import main as backend
    from backend import report_export
    from backend.report_export import build_report_html, render_report_pdf
    from backend.solana_agent import LocalSolanaAgent


class _DemoSolanaAgent:
    def get_status(self) -> dict:
        return {
            "mode": "demo",
            "configured": False,
            "network": "https://api.devnet.solana.com",
            "asset": "USDC",
            "defaultAmount": 50.0,
            "reason": "Test demo mode.",
        }

    async def execute_reward_micropayment(self, *args, **kwargs):
        raise AssertionError("A demo flow must not submit a blockchain transaction.")


class _FakeRequest:
    def __init__(self, body: bytes):
        self._body = body
        self.headers: dict[str, str] = {}
        self.url = "https://example.ngrok.app/webhook"

    async def body(self) -> bytes:
        return self._body


class _FakeBackgroundTasks:
    def __init__(self):
        self.calls: list[tuple] = []

    def add_task(self, function, *args, **kwargs) -> None:
        self.calls.append((function, args, kwargs))


class _AsyncClientContext:
    def __init__(self, client):
        self.client = client

    async def __aenter__(self):
        return self.client

    async def __aexit__(self, exc_type, exc, traceback):
        return False


class _TwilioDailyLimitResponse:
    status_code = 429
    headers = {"Twilio-Concurrent-Requests": "1"}

    @staticmethod
    def json() -> dict:
        return {
            "code": 63038,
            "message": "Account exceeded the daily messages limit",
            "status": 429,
        }


class _GeminiInventoryResponse:
    is_error = False
    status_code = 200

    @staticmethod
    def json() -> dict:
        return {
            "candidates": [{
                "content": {
                    "parts": [{
                        "text": '[{"item":" Rice ","quantity":" 8kg "}]'
                    }]
                }
            }]
        }


class BackendRegressionTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        # Replace every mutable process-local store so tests cannot leak state to
        # one another or to the imported application.
        self.enterContext(mock.patch.object(backend, "USER_STATES", {}))
        self.enterContext(mock.patch.object(backend, "INVENTORY_RECORDS", []))
        self.enterContext(mock.patch.object(backend, "REWARD_CLAIMS", {}))
        self.enterContext(mock.patch.object(backend, "REWARD_EVENTS", []))
        self.enterContext(
            mock.patch.object(backend, "PROCESSED_MESSAGE_SIDS", OrderedDict())
        )
        self.enterContext(
            mock.patch.object(backend, "TWILIO_DAILY_LIMIT_BLOCKED_UNTIL", None)
        )
        self.enterContext(mock.patch.object(backend, "TWILIO_ACCOUNT_SID", None))
        self.enterContext(mock.patch.object(backend, "TWILIO_AUTH_TOKEN", None))
        self.enterContext(mock.patch.object(backend, "TWILIO_MESSAGES_URL", None))
        self.enterContext(
            mock.patch.object(backend, "TWILIO_VALIDATE_SIGNATURE", False)
        )
        self.enterContext(mock.patch.object(backend, "GEMINI_API_KEY", None))
        self.enterContext(mock.patch.object(backend, "solana_agent", _DemoSolanaAgent()))
        self.enterContext(
            mock.patch.object(backend, "TWILIO_SEND_LOCK", asyncio.Lock())
        )

    async def test_report_html_embeds_the_brand_logo(self) -> None:
        report_html = build_report_html("Last 30 Days")

        self.assertIn('<img class="brand-logo"', report_html)
        self.assertIn("data:image/png;base64,", report_html)
        self.assertNotIn('class="brand-mark"', report_html)

    async def test_report_pdf_uses_serverless_renderer_without_chrome(self) -> None:
        with mock.patch.object(report_export, "_chrome_executable", return_value=None):
            pdf = render_report_pdf("Last 30 Days")

        self.assertTrue(pdf.startswith(b"%PDF-"))
        self.assertGreater(len(pdf), 1024)
        self.assertIn(b"/Image", pdf)

    async def test_report_logo_falls_back_to_deployed_dashboard_asset(self) -> None:
        canonical_logo = report_export.BRAND_LOGO_PATH.read_bytes()
        response = mock.Mock()
        response.read.return_value = canonical_logo
        response_context = mock.MagicMock()
        response_context.__enter__.return_value = response

        with (
            mock.patch.object(
                report_export,
                "BRAND_LOGO_PATH",
                Path("missing-staylonger-logo.png"),
            ),
            mock.patch.dict(
                os.environ,
                {"DASHBOARD_BASE_URL": "https://staylonger.example"},
                clear=False,
            ),
            mock.patch.object(report_export, "urlopen", return_value=response_context) as download,
        ):
            downloaded_logo = report_export._brand_logo_bytes()

        self.assertEqual(downloaded_logo, canonical_logo)
        request = download.call_args.args[0]
        self.assertEqual(request.full_url, "https://staylonger.example/staylonger-logo.png")

    async def test_vercel_entrypoint_keeps_api_and_webhook_paths_working(self) -> None:
        with TestClient(vercel_app) as client:
            dashboard_response = client.get("/api/dashboard")
            webhook_response = client.get("/api/webhook")

        self.assertEqual(dashboard_response.status_code, 200)
        self.assertEqual(
            dashboard_response.json().get("title"),
            "Revenue Command Center",
        )
        self.assertEqual(webhook_response.status_code, 200)
        self.assertEqual(webhook_response.json().get("status"), "ok")

    async def test_reward_link_uses_vercel_production_url_when_configured(self) -> None:
        environment = {
            "DASHBOARD_BASE_URL": "",
            "VERCEL_PROJECT_PRODUCTION_URL": "staylongerai.vercel.app",
        }

        with mock.patch.dict(os.environ, environment, clear=False):
            dashboard_url = backend.generate_dashboard_url("whatsapp:+60123456789")

        self.assertTrue(dashboard_url.startswith("https://staylongerai.vercel.app/reward?"))

    async def test_twilio_signature_validation_uses_the_public_vercel_webhook_url(self) -> None:
        if backend.RequestValidator is None:
            self.skipTest("Twilio signature validation dependency is unavailable.")

        auth_token = "test-auth-token"
        form_data = {
            "MessageSid": ["SM123"],
            "From": ["whatsapp:+60123456789"],
        }
        expected_url = "https://staylongerai.vercel.app/webhook"
        signature = backend.RequestValidator(auth_token).compute_signature(
            expected_url,
            {key: values[0] for key, values in form_data.items()},
        )
        request = _FakeRequest(b"")
        request.headers["X-Twilio-Signature"] = signature

        with (
            mock.patch.dict(
                os.environ,
                {
                    "DASHBOARD_BASE_URL": "",
                    "VERCEL_PROJECT_PRODUCTION_URL": "staylongerai.vercel.app",
                    "TWILIO_WEBHOOK_URL": "",
                },
                clear=False,
            ),
            mock.patch.object(backend, "TWILIO_AUTH_TOKEN", auth_token),
            mock.patch.object(backend, "TWILIO_VALIDATE_SIGNATURE", True),
        ):
            self.assertTrue(backend._validate_twilio_request(request, form_data))

    async def test_reward_token_generation_and_claim_are_idempotent(self) -> None:
        sender = "whatsapp:+60123456789"
        environment = {
            "DASHBOARD_BASE_URL": "http://localhost:8443",
            "REWARD_DISPLAY_AMOUNT_RM": "50",
            "REWARD_LINK_TTL_HOURS": "24",
        }

        with mock.patch.dict(os.environ, environment, clear=False):
            dashboard_url = backend.generate_dashboard_url(sender)

        parsed_url = urlparse(dashboard_url)
        query = parse_qs(parsed_url.query)
        token = query["token"][0]

        self.assertEqual(parsed_url.path, "/reward")
        self.assertEqual(set(query), {"token"})
        self.assertNotIn(sender, dashboard_url)
        self.assertEqual(backend.USER_STATES[sender], "claiming_reward")
        self.assertIn(token, backend.REWARD_CLAIMS)

        first = await backend.claim_reward(backend.RewardClaimRequest(token=token))
        claimed_at = backend.REWARD_CLAIMS[token]["claimed_at"]
        second = await backend.claim_reward(backend.RewardClaimRequest(token=token))

        self.assertEqual(first["status"], "claimed")
        self.assertEqual(first["amount"], 50.0)
        self.assertTrue(first["demo"])
        self.assertIsNotNone(claimed_at)
        self.assertEqual(second["status"], "already_claimed")
        self.assertEqual(backend.REWARD_CLAIMS[token]["claimed_at"], claimed_at)
        self.assertEqual(backend.USER_STATES[sender], "reverse_onboarding")
        self.assertEqual(len(backend.REWARD_EVENTS), 1)
        self.assertNotIn(sender, backend.REWARD_EVENTS[0]["name"])

    async def test_inventory_image_is_structured_persisted_and_sent(self) -> None:
        message_sid = "SM_inventory_001"
        sender = "whatsapp:+60111112222"
        image_bytes = b"mock inventory image bytes"
        form_data = {
            "MessageSid": [message_sid],
            "From": [sender],
            "Body": ["inventory photo"],
            "NumMedia": ["1"],
            "MediaUrl0": [
                "https://api.twilio.com/2010-04-01/Accounts/AC/Messages/SM/Media/ME"
            ],
            "MediaContentType0": ["image/png"],
        }
        ocr = mock.Mock(
            return_value=[
                {"item": " Rice ", "quantity": " 10kg "},
                {"item": "Soap", "quantity": 4},
            ]
        )
        download = mock.AsyncMock(return_value=image_bytes)
        send = mock.AsyncMock(return_value={"status": "sent"})
        environment = {
            "REWARD_USDC_AMOUNT": "50",
            "REWARD_DISPLAY_AMOUNT_RM": "50",
            "PAYMENT_RECIPIENT_WALLET": "",
        }

        with (
            mock.patch.dict(os.environ, environment, clear=False),
            mock.patch.object(backend, "parse_handwritten_inventory", ocr),
            mock.patch.object(backend, "download_media", download),
            mock.patch.object(backend, "send_message", send),
        ):
            await backend.process_whatsapp_message(form_data)

        download.assert_awaited_once_with(form_data["MediaUrl0"][0])
        ocr.assert_called_once_with(image_bytes)
        send.assert_awaited_once()
        self.assertEqual(len(backend.INVENTORY_RECORDS), 1)

        record = backend.INVENTORY_RECORDS[0]
        self.assertEqual(record["id"], message_sid)
        self.assertEqual(record["source"], "WhatsApp")
        self.assertEqual(record["sender"], "WhatsApp ••••2222")
        self.assertEqual(record["itemCount"], 2)
        self.assertEqual(record["processor"], "easyocr")
        self.assertEqual(record["paymentStatus"], "demo")
        self.assertEqual(
            record["items"],
            [
                {"item": "Rice", "quantity": "10kg"},
                {"item": "Soap", "quantity": "4"},
            ],
        )
        self.assertEqual(backend.USER_STATES[sender], "idle")
        self.assertEqual(backend.build_dashboard_payload()["inventory"][0], record)
        self.assertIn("Successfully parsed your inventory", send.await_args.args[1])

    async def test_gemini_is_a_structured_fallback_and_keeps_key_out_of_url(self) -> None:
        client = mock.Mock()
        client.post = mock.AsyncMock(return_value=_GeminiInventoryResponse())
        client_factory = mock.Mock(return_value=_AsyncClientContext(client))

        with (
            mock.patch.object(backend, "GEMINI_API_KEY", "test-api-key"),
            mock.patch.object(backend, "GEMINI_MODEL", "gemini-test-model"),
            mock.patch.object(backend, "parse_handwritten_inventory", return_value=[]),
            mock.patch.object(backend.httpx, "AsyncClient", client_factory),
        ):
            result = await backend.process_inventory_image(
                b"mock image bytes",
                "image/png",
            )

        self.assertEqual(result["processor"], "gemini")
        self.assertEqual(result["items"], [{"item": "Rice", "quantity": "8kg"}])
        request_url = client.post.await_args.args[0]
        request_options = client.post.await_args.kwargs
        self.assertNotIn("test-api-key", request_url)
        self.assertEqual(request_options["headers"]["x-goog-api-key"], "test-api-key")
        inline_data = request_options["json"]["contents"][0]["parts"][1]["inline_data"]
        self.assertEqual(inline_data["mime_type"], "image/png")

    async def test_live_reward_requires_claim_and_is_attempted_only_once(self) -> None:
        sender = "whatsapp:+60188887777"
        dashboard_url = backend.generate_dashboard_url(sender)
        token = parse_qs(urlparse(dashboard_url).query)["token"][0]
        await backend.claim_reward(backend.RewardClaimRequest(token=token))

        live_agent = mock.Mock()
        live_agent.get_status.return_value = {
            "mode": "live",
            "configured": True,
            "network": "https://api.devnet.solana.com",
            "asset": "USDC",
            "defaultAmount": 1.0,
            "reason": "Live test configuration.",
        }
        live_agent.execute_reward_micropayment = mock.AsyncMock(
            return_value={"status": "processed"}
        )
        inventory_result = {
            "items": [{"item": "Rice", "quantity": "1"}],
            "processor": "easyocr",
        }

        def form(message_sid: str) -> dict[str, list[str]]:
            return {
                "MessageSid": [message_sid],
                "From": [sender],
                "Body": [""],
                "NumMedia": ["1"],
                "MediaUrl0": ["https://api.twilio.com/media"],
                "MediaContentType0": ["image/jpeg"],
            }

        with (
            mock.patch.object(backend, "TWILIO_VALIDATE_SIGNATURE", True),
            mock.patch.object(backend, "solana_agent", live_agent),
            mock.patch.object(backend, "download_media", new=mock.AsyncMock(return_value=b"image")),
            mock.patch.object(
                backend,
                "process_inventory_image",
                new=mock.AsyncMock(return_value=inventory_result),
            ),
            mock.patch.object(backend, "send_message", new=mock.AsyncMock()),
            mock.patch.dict(
                os.environ,
                {"PAYMENT_RECIPIENT_WALLET": "recipient", "REWARD_USDC_AMOUNT": "1"},
                clear=False,
            ),
        ):
            await backend.process_whatsapp_message(form("SM_live_once"))
            await backend.process_whatsapp_message(form("SM_live_twice"))

        live_agent.execute_reward_micropayment.assert_awaited_once()
        self.assertEqual(backend.REWARD_CLAIMS[token]["payment_status"], "processed")
        self.assertEqual(backend.INVENTORY_RECORDS[1]["paymentStatus"], "processed")
        self.assertEqual(backend.INVENTORY_RECORDS[0]["paymentStatus"], "claim_required")

    async def test_webhook_deduplicates_message_sid_before_scheduling(self) -> None:
        body = urlencode(
            {
                "MessageSid": "SM_duplicate_001",
                "From": "whatsapp:+60199990000",
                "Body": "claim",
                "NumMedia": "0",
            }
        ).encode("utf-8")

        first_tasks = _FakeBackgroundTasks()
        first_response = await backend.handle_whatsapp_messages(
            _FakeRequest(body),
            first_tasks,
        )
        second_tasks = _FakeBackgroundTasks()
        second_response = await backend.handle_whatsapp_messages(
            _FakeRequest(body),
            second_tasks,
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(len(first_tasks.calls), 1)
        self.assertIs(first_tasks.calls[0][0], backend.process_whatsapp_message)
        self.assertEqual(len(second_tasks.calls), 0)
        self.assertEqual(list(backend.PROCESSED_MESSAGE_SIDS), ["SM_duplicate_001"])

    async def test_download_media_rejects_untrusted_url_without_http_call(self) -> None:
        client_factory = mock.Mock(
            side_effect=AssertionError("Untrusted media must not create an HTTP client.")
        )
        environment = {"TWILIO_MEDIA_HOSTS": "api.twilio.com"}

        with (
            mock.patch.dict(os.environ, environment, clear=False),
            mock.patch.object(backend, "TWILIO_ACCOUNT_SID", "AC_TEST"),
            mock.patch.object(backend, "TWILIO_AUTH_TOKEN", "test-token"),
            mock.patch.object(backend.httpx, "AsyncClient", client_factory),
        ):
            with self.assertRaisesRegex(ValueError, "untrusted Twilio media URL"):
                await backend.download_media(
                    "https://attacker.example/inventory-image.jpg"
                )

        client_factory.assert_not_called()

    async def test_solana_status_and_payment_default_to_demo(self) -> None:
        safe_solana_environment = {
            "SOLANA_PRIVATE_KEY_HEX": "",
            "SOLANA_PRIVATE_KEY": "",
            "SOLANA_LIVE_MODE": "false",
            "USDC_MINT": "",
            "PAYMENT_RECIPIENT_WALLET": "",
            "REWARD_USDC_AMOUNT": "50",
        }

        with (
            mock.patch.dict(os.environ, safe_solana_environment, clear=False),
            mock.patch(
                "backend.solana_agent.AsyncClient",
                side_effect=AssertionError("Demo mode must not create a live client."),
            ),
        ):
            agent = LocalSolanaAgent()

        with mock.patch.object(backend, "solana_agent", agent):
            status = await backend.rewards_status()
            payment = await agent.execute_reward_micropayment(
                "not-a-live-wallet",
                amount_usdc="50",
                payment_reference="test:demo",
            )

        self.assertEqual(
            set(status),
            {"mode", "configured", "network", "asset", "defaultAmount", "reason"},
        )
        self.assertEqual(status["mode"], "demo")
        self.assertFalse(status["configured"])
        self.assertEqual(status["asset"], "USDC")
        self.assertEqual(status["defaultAmount"], 50.0)
        self.assertEqual(payment["status"], "demo")
        self.assertTrue(payment["simulated"])
        self.assertIsNone(payment["signature"])
        await agent.close()

    async def test_twilio_63038_pauses_for_24h_and_suppresses_next_send(self) -> None:
        client = mock.Mock()
        client.post = mock.AsyncMock(return_value=_TwilioDailyLimitResponse())
        client_factory = mock.Mock(return_value=_AsyncClientContext(client))
        sleep = mock.AsyncMock()
        before = datetime.now(timezone.utc)

        with (
            mock.patch.object(backend, "TWILIO_ACCOUNT_SID", "AC_TEST"),
            mock.patch.object(backend, "TWILIO_AUTH_TOKEN", "test-token"),
            mock.patch.object(
                backend,
                "TWILIO_MESSAGES_URL",
                "https://api.twilio.com/test/Messages.json",
            ),
            mock.patch.object(backend.httpx, "AsyncClient", client_factory),
            mock.patch.object(backend.asyncio, "sleep", sleep),
            self.assertLogs("staylonger.backend", level="ERROR") as captured_logs,
        ):
            first = await backend.send_message("whatsapp:+60100000000", "first")
            second = await backend.send_message("whatsapp:+60100000000", "second")

        blocked_until = backend.TWILIO_DAILY_LIMIT_BLOCKED_UNTIL
        self.assertEqual(first["status"], "daily_limit_exceeded")
        self.assertEqual(first["code"], 63038)
        self.assertEqual(second["status"], "daily_limit_exceeded")
        self.assertEqual(second["code"], 63038)
        self.assertIsNotNone(blocked_until)
        remaining = blocked_until - before
        self.assertGreater(remaining, timedelta(hours=23, minutes=59))
        self.assertLessEqual(remaining, timedelta(hours=24, seconds=1))
        client.post.assert_awaited_once()
        client_factory.assert_called_once()
        sleep.assert_not_awaited()
        self.assertTrue(any("63038" in entry for entry in captured_logs.output))
        self.assertTrue(
            any("paused for 24 hours" in entry for entry in captured_logs.output)
        )


if __name__ == "__main__":
    unittest.main()
