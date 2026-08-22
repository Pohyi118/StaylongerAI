"""WhatsApp Business Service Provider (BSP) abstraction.

The spec's "Communication" layer uses SleekFlow or Wati to execute the
interactive WhatsApp Business flows. This module implements both, plus a Meta
WhatsApp Cloud API fallback so the existing integration keeps working.

Active provider is selected with WHATSAPP_PROVIDER (sleekflow | wati | meta).

Each provider exposes the two primitives the Value Vault rescue flow needs:
    send_text(phone, text)
    send_template(phone, template_name, language, body_text, button_label, button_url)

Wati and SleekFlow are template-first BSPs: the interactive button lives inside a
pre-approved template (name + language), and the body/URL are injected as template
parameters. Meta supports ad-hoc interactive CTA-URL buttons instead.
"""
from __future__ import annotations

import os
import re

import httpx

PROVIDER = (os.getenv("WHATSAPP_PROVIDER", "meta") or "meta").lower()

# --------------------------------------------------------------------------- #
# SleekFlow
# --------------------------------------------------------------------------- #
SLEEKFLOW_API_URL = os.getenv("SLEEKFLOW_API_URL", "https://api.sleekflow.io/v1/messages/send")
SLEEKFLOW_API_KEY = os.getenv("SLEEKFLOW_API_KEY") or os.getenv("SLEEKFLOW_TOKEN")

# --------------------------------------------------------------------------- #
# Wati
# --------------------------------------------------------------------------- #
# Wati's base URL embeds an account-specific API endpoint id, e.g. "12345678".
WATI_API_ENDPOINT = os.getenv("WATI_API_ENDPOINT")
WATI_ACCESS_TOKEN = os.getenv("WATI_ACCESS_TOKEN")
WATI_BASE_URL = (
    f"https://live-mt-server.wati.io/{WATI_API_ENDPOINT}/api/v1" if WATI_API_ENDPOINT else ""
)

# --------------------------------------------------------------------------- #
# Meta (fallback / existing integration)
# --------------------------------------------------------------------------- #
META_TOKEN = os.getenv("META_WHATSAPP_ACCESS_TOKEN") or os.getenv("WHATSAPP_TOKEN")
META_PHONE_NUMBER_ID = os.getenv("META_WHATSAPP_PHONE_NUMBER_ID") or os.getenv("PHONE_NUMBER_ID")
META_GRAPH_VERSION = os.getenv("META_GRAPH_API_VERSION", "v20.0")
META_MESSAGES_URL = (
    f"https://graph.facebook.com/{META_GRAPH_VERSION}/{META_PHONE_NUMBER_ID}/messages"
    if META_PHONE_NUMBER_ID
    else ""
)


def configured() -> bool:
    """True when the active provider has the credentials it needs."""
    if PROVIDER == "sleekflow":
        return bool(SLEEKFLOW_API_URL and SLEEKFLOW_API_KEY)
    if PROVIDER == "wati":
        return bool(WATI_BASE_URL and WATI_ACCESS_TOKEN)
    return bool(META_TOKEN and META_PHONE_NUMBER_ID)


def _digits(value) -> str:
    return re.sub(r"\D", "", str(value))


async def _post(url: str, headers: dict, payload: dict) -> dict | None:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        try:
            return response.json()
        except ValueError:
            return {"status": "sent", "statusCode": response.status_code}


async def _sleekflow_send(payload: dict) -> dict | None:
    headers = {"Authorization": f"Bearer {SLEEKFLOW_API_KEY}", "Content-Type": "application/json"}
    return await _post(SLEEKFLOW_API_URL, headers, payload)


async def _wati_send(endpoint: str, payload: dict) -> dict | None:
    headers = {"Authorization": f"Bearer {WATI_ACCESS_TOKEN}", "Content-Type": "application/json"}
    return await _post(f"{WATI_BASE_URL}/{endpoint}", headers, payload)


async def _meta_send(payload: dict) -> dict | None:
    if not META_MESSAGES_URL or not META_TOKEN:
        return None
    headers = {
        "Authorization": f"Bearer {META_TOKEN}",
        "Content-Type": "application/json",
    }
    return await _post(META_MESSAGES_URL, headers, payload)


async def send_text(to_number: str, text: str) -> dict | None:
    """Send a plain WhatsApp text message via the active provider."""
    if not configured():
        print(f"WhatsApp provider '{PROVIDER}' not configured; skipping outbound text message.")
        return None

    phone = _digits(to_number)
    if PROVIDER == "sleekflow":
        return await _sleekflow_send({
            "channel": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": text},
        })
    if PROVIDER == "wati":
        return await _wati_send("sendSessionMessage", {
            "messageText": text,
            "phoneNumber": phone,
        })
    # Meta
    return await _meta_send({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text},
    })


async def send_template(
    to_number: str,
    template_name: str,
    language: str,
    body_text: str,
    button_label: str,
    button_url: str,
) -> dict | None:
    """Send a localized interactive template with a URL button ("Claim Reward").

    Returns the BSP response, or None when the message could not be sent (the
    caller then falls back to a plain text message containing the link).
    """
    if not configured():
        print(f"WhatsApp provider '{PROVIDER}' not configured; skipping outbound template message.")
        return None

    phone = _digits(to_number)

    if PROVIDER == "sleekflow":
        return await _sleekflow_send({
            "channel": "whatsapp",
            "to": phone,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": [
                    {"type": "body", "parameters": [{"type": "text", "text": body_text}]},
                    {"type": "button", "sub_type": "url", "index": 0,
                     "parameters": [{"type": "text", "text": button_url}]},
                ],
            },
        })

    if PROVIDER == "wati":
        return await _wati_send("sendTemplateMessage", {
            "template_name": template_name,
            "broadcast_name": "value_vault_rescue",
            "parameters": [
                {"name": "body", "value": body_text},
                {"name": "button_url", "value": button_url},
            ],
        })

    # Meta: ad-hoc interactive CTA-URL button (requires a public HTTPS URL).
    if not button_url.lower().startswith("https://"):
        return None
    return await _meta_send({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": {
            "type": "cta_url",
            "header": {"type": "text", "text": "🎁 Value Vault Reward"},
            "body": {"text": body_text},
            "action": {
                "name": "cta_url",
                "parameters": {"display_text": button_label, "url": button_url},
            },
        },
    })
