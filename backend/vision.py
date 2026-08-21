"""Vision LLM extraction for Reverse Onboarding.

Primary: Claude 3.5 Sonnet (Anthropic Messages API).
Fallback: Gemini (kept for existing deployments and offline parity).

Both turn a photo of a handwritten/printed inventory into a list of
``{"item": str, "quantity": str}`` records used to configure the SaaS database.
"""
from __future__ import annotations

import base64
import json
import os
import re

import httpx

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")
ANTHROPIC_URL = os.getenv("ANTHROPIC_API_URL", "https://api.anthropic.com/v1/messages")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

_PROMPT = (
    "Extract the inventory from this handwritten or printed image. "
    "Return ONLY valid JSON as a list of objects with fields 'item' and 'quantity'. "
    "If you are unsure, use the best estimate and keep the values concise."
)


def _detect_media_type(image_bytes: bytes) -> str:
    """Best-effort image media type detection for the Anthropic/Gemini payloads."""
    if image_bytes.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if image_bytes[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if image_bytes[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if len(image_bytes) > 12 and image_bytes[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def _sanitize(items) -> list[dict]:
    out: list[dict] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        name = str(item.get("item", "")).strip()
        quantity = str(item.get("quantity", "1")).strip()
        m = re.match(r"^(\d+(?:\.\d+)?)", quantity)
        if not name or not m:
            continue
        out.append({"item": name[:80], "quantity": m.group(1)})
    return out


async def extract_with_claude(image_bytes: bytes) -> list[dict]:
    """Route the media payload to Claude 3.5 Sonnet (vision)."""
    if not ANTHROPIC_API_KEY:
        return []

    media_type = _detect_media_type(image_bytes)
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 1024,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image",
                 "source": {"type": "base64", "media_type": media_type, "data": encoded}},
                {"type": "text", "text": _PROMPT},
            ],
        }],
    }
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(ANTHROPIC_URL, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

    text = ""
    for block in data.get("content", []):
        if block.get("type") == "text":
            text += block.get("text", "")
    return _sanitize(_parse_json_list(text))


async def extract_with_gemini(image_bytes: bytes) -> list[dict]:
    """Gemini fallback for the existing integration."""
    if not GEMINI_API_KEY:
        return []

    media_type = _detect_media_type(image_bytes)
    encoded = base64.b64encode(image_bytes).decode("utf-8")

    payload = {
        "contents": [{
            "parts": [
                {"text": _PROMPT},
                {"inline_data": {"mime_type": media_type, "data": encoded}},
            ]
        }],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
            f"?key={GEMINI_API_KEY}",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

    text = data["candidates"][0]["content"]["parts"][0].get("text", "")
    return _sanitize(_parse_json_list(text))


def _parse_json_list(text: str) -> list[dict]:
    """Parse an LLM JSON response, tolerating fenced code blocks and prose."""
    text = (text or "").strip()
    # Strip ```json ... ``` fences if present.
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        # Fall back to the first balanced JSON array/object in the text.
        start = text.find("[")
        if start == -1:
            start = text.find("{")
        if start == -1:
            return []
        try:
            parsed = json.loads(text[start:])
        except json.JSONDecodeError:
            return []

    if isinstance(parsed, list):
        return parsed
    if isinstance(parsed, dict):
        # Tolerate {"items": [...]} or {"inventory": [...]} wrappers.
        for key in ("items", "inventory", "data", "products"):
            if isinstance(parsed.get(key), list):
                return parsed[key]
        return [parsed]
    return []


async def extract_inventory(image_bytes: bytes) -> list[dict]:
    """Extract inventory items, trying Claude first then Gemini.

    Returns [] when no LLM is configured or nothing was recognized.
    """
    if ANTHROPIC_API_KEY:
        try:
            items = await extract_with_claude(image_bytes)
            if items:
                return items
        except Exception as exc:  # noqa: BLE001 - fall through to Gemini
            print(f"Claude vision failed, falling back to Gemini/local OCR: {exc}")

    if GEMINI_API_KEY:
        try:
            items = await extract_with_gemini(image_bytes)
            if items:
                return items
        except Exception as exc:  # noqa: BLE001
            print(f"Gemini vision failed: {exc}")

    return []
