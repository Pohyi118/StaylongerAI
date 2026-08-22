import asyncio
import base64
import csv
import hashlib
import hmac
import io
import json
import logging
import os
import secrets
import time
import uuid
from collections import OrderedDict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import httpx
from urllib.parse import parse_qs, urlencode, urlparse
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from dotenv import load_dotenv
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)
load_dotenv(BASE_DIR.parent / ".env", override=False)

try:
    from twilio.request_validator import RequestValidator
except ImportError:  # The app can still run in local demo mode without validation.
    RequestValidator = None

try:
    from .local_vision import local_ocr_available, parse_handwritten_inventory
    from .report_export import REPORT_PERIODS, ReportExportError, render_report_pdf
    from .solana_agent import LocalSolanaAgent
    from .uplift_engine import UpliftEngine
    from . import whatsapp_provider
except ImportError:  # Supports running `python backend/main.py` directly.
    from local_vision import local_ocr_available, parse_handwritten_inventory
    from report_export import REPORT_PERIODS, ReportExportError, render_report_pdf
    from solana_agent import LocalSolanaAgent
    from uplift_engine import UpliftEngine
    import whatsapp_provider

logger = logging.getLogger("staylonger.backend")

cors_origins = {
    "http://localhost:3000",
    "http://localhost:8443",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8443",
    "http://0.0.0.0:8443",
    "http://0.0.0.0:3000",
}
cors_origins.update(
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "").split(",")
    if origin.strip()
)


@asynccontextmanager
async def app_lifespan(_app: FastAPI):
    yield
    active_solana_agent = globals().get("solana_agent")
    if active_solana_agent is not None and hasattr(active_solana_agent, "close"):
        try:
            await active_solana_agent.close()
        except Exception:
            logger.warning("Solana client cleanup failed during shutdown.")


app = FastAPI(title="StayLongerAI API", lifespan=app_lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
uplift = UpliftEngine()
solana_agent = LocalSolanaAgent()
USER_STATES: dict[str, str] = {}
CUSTOMER_DATA: list[dict] = []
INVENTORY_RECORDS: list[dict] = []
REWARD_CLAIMS: dict[str, dict] = {}
REWARD_EVENTS: list[dict] = []
DEMO_REWARD_FUND_BALANCE = Decimal("0")
PROCESSED_MESSAGE_SIDS: OrderedDict[str, float] = OrderedDict()
MAX_PROCESSED_MESSAGE_SIDS = 5000
MESSAGE_SID_TTL_SECONDS = 24 * 60 * 60
MAX_INVENTORY_RECORDS = 100
TWILIO_SEND_LOCK = asyncio.Lock()
DEMO_FUNDING_LOCK = asyncio.Lock()
TWILIO_DAILY_LIMIT_BLOCKED_UNTIL: datetime | None = None
TWILIO_DAILY_LIMIT_CODE = 63038

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv(
    "TWILIO_WHATSAPP_FROM",
    "whatsapp:+14155238886"
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
TWILIO_VALIDATE_SIGNATURE = os.getenv(
    "TWILIO_VALIDATE_SIGNATURE", "false"
).lower() in {"1", "true", "yes"}
MAX_MEDIA_BYTES = 15 * 1024 * 1024

TWILIO_MESSAGES_URL = (
    f"https://api.twilio.com/2010-04-01/Accounts/"
    f"{TWILIO_ACCOUNT_SID}/Messages.json"
    if TWILIO_ACCOUNT_SID
    else None
)

VONAGE_API_KEY = os.getenv("VONAGE_API_KEY")
VONAGE_API_SECRET = os.getenv("VONAGE_API_SECRET")
VONAGE_WHATSAPP_FROM = os.getenv("VONAGE_WHATSAPP_FROM", "14157386102")
VONAGE_MESSAGES_URL = os.getenv(
    "VONAGE_MESSAGES_URL",
    "https://messages-sandbox.nexmo.com/v1/messages",
)

META_WHATSAPP_ACCESS_TOKEN = os.getenv("META_WHATSAPP_ACCESS_TOKEN")
META_WHATSAPP_PHONE_NUMBER_ID = os.getenv("META_WHATSAPP_PHONE_NUMBER_ID")
META_WHATSAPP_VERIFY_TOKEN = os.getenv("META_WHATSAPP_VERIFY_TOKEN")
META_APP_SECRET = os.getenv("META_APP_SECRET") or os.getenv("WHATSAPP_APP_SECRET")
META_GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v23.0")
META_GRAPH_BASE_URL = "https://graph.facebook.com"


class RewardClaimRequest(BaseModel):
    token: str = Field(min_length=1, max_length=128)


class DemoFundingRequest(BaseModel):
    """A local-only reserve top-up used while the app is in demo mode."""

    amount: Decimal = Field(gt=Decimal("0"), le=Decimal("1000000"))


def _reward_amount() -> Decimal:
    try:
        amount = Decimal(os.getenv("REWARD_USDC_AMOUNT", "50"))
        return amount if amount > 0 else Decimal("50")
    except (InvalidOperation, ValueError):
        logger.warning("Invalid REWARD_USDC_AMOUNT; using the demo default of 50.")
        return Decimal("50")


def _reward_display_amount() -> Decimal:
    try:
        amount = Decimal(os.getenv("REWARD_DISPLAY_AMOUNT_RM", "50"))
        return amount if amount > 0 else Decimal("50")
    except (InvalidOperation, ValueError):
        logger.warning("Invalid REWARD_DISPLAY_AMOUNT_RM; using the demo default of 50.")
        return Decimal("50")


def _mask_sender(sender: str) -> str:
    digits = "".join(character for character in sender if character.isdigit())
    return f"WhatsApp ••••{digits[-4:]}" if digits else "WhatsApp customer"


def _prune_reward_claims() -> None:
    now = datetime.now(timezone.utc)
    expired = [
        token
        for token, claim in REWARD_CLAIMS.items()
        if claim["expires_at"] <= now
    ]
    for token in expired:
        REWARD_CLAIMS.pop(token, None)


def _dashboard_base_url() -> str:
    """Return the configured dashboard URL, with managed-host fallbacks."""
    configured_url = os.getenv("DASHBOARD_BASE_URL", "").strip().rstrip("/")
    if configured_url:
        return configured_url

    render_url = os.getenv("RENDER_EXTERNAL_URL", "").strip().rstrip("/")
    parsed_render_url = urlparse(render_url)
    if (
        parsed_render_url.scheme == "https"
        and parsed_render_url.netloc
        and not parsed_render_url.path
    ):
        return render_url

    for variable_name in ("VERCEL_PROJECT_PRODUCTION_URL", "VERCEL_URL"):
        domain = os.getenv(variable_name, "").strip().strip("/")
        parsed = urlparse(f"https://{domain}")
        if domain and parsed.scheme == "https" and parsed.netloc == domain:
            return f"https://{domain}"

    return "http://localhost:8443"


def generate_dashboard_url(phone_number: str) -> str:
    base_url = _dashboard_base_url()
    session_token = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    try:
        ttl_hours = max(1, int(os.getenv("REWARD_LINK_TTL_HOURS", "24")))
    except ValueError:
        ttl_hours = 24

    _prune_reward_claims()
    REWARD_CLAIMS[session_token] = {
        "user": phone_number,
        "created_at": now,
        "expires_at": now + timedelta(hours=ttl_hours),
        "claimed_at": None,
        "payment_started_at": None,
        "payment_status": None,
        "amount": _reward_display_amount(),
    }
    USER_STATES[phone_number] = "claiming_reward"
    query = urlencode({"token": session_token})
    return f"{base_url.rstrip('/')}/reward?{query}"


def build_dashboard_payload() -> dict:
    return {
        "title": "Revenue Command Center",
        "status": "AI Protection Active",
        "totalRevenueProtectedLabel": "RM184,320",
        "weekGrowth": "+12% this week",
        "roi": "8.4×",
        "executiveBrief": "Churn exposure decreased 12% this week. 9 persuadable accounts were automatically rescued. A coordinated activity drop across 127 SME customers may indicate a competitor campaign.",
        "metrics": [
            {"label": "Accounts Rescued", "value": "47", "trend": "+4"},
            {"label": "MRR at Risk", "value": "RM24,500", "trend": "-12%"},
            {"label": "Agent Payments", "value": "RM450", "trend": "Solana/x402"},
            {"label": "Health Avg", "value": "72/100", "trend": "Stable"},
        ],
        "chartData": [
            {"name": "1", "revenue": 120000},
            {"name": "5", "revenue": 130000},
            {"name": "10", "revenue": 128000},
            {"name": "15", "revenue": 145000},
            {"name": "20", "revenue": 160000},
            {"name": "25", "revenue": 175000},
            {"name": "30", "revenue": 184320},
        ],
        "alert": {
            "tag": "Emergency",
            "title": "Sudden drop in user activity detected.",
            "message": "Possible competitor move targeting SME segment.",
            "activityDrop": "-37%",
            "affectedUsers": 2391,
        },
        "vipAccounts": [
            {
                "name": "Acme Corp",
                "plan": "Enterprise",
                "revenueAtRisk": "RM12,460",
                "healthScore": "31 / 100 (87% risk)",
                "status": "Human Alert",
            },
            {
                "name": "Nexus Logistics",
                "plan": "Mid-Market",
                "revenueAtRisk": "RM8,200",
                "healthScore": "42 / 100 (71% risk)",
                "status": "Human Alert",
            },
        ],
        "segments": [
            {"title": "Persuadables", "description": "High risk, can be saved", "value": 45, "action": "AI Action: Invest Rewards", "theme": "pink"},
            {"title": "Sure Things", "description": "Loyal & engaged", "value": 1204, "action": "AI Action: No Discount", "theme": "emerald"},
            {"title": "Inactive", "description": "Low activity, monitor quietly", "value": 89, "action": "AI Action: Monitor", "theme": "amber"},
            {"title": "Lost Causes", "description": "Unlikely to stay", "value": 12, "action": "AI Action: Ignore", "theme": "slate"},
        ],
        "rescues": REWARD_EVENTS[:5] + [
            {"name": "Lumina Tech", "time": "12m ago", "reward": "GrabFood RM50", "type": "Value Vault", "status": "Claimed", "network": "x402/Solana"},
            {"name": "ScaleForge", "time": "45m ago", "reward": "Pause Subscription", "type": "Billing", "status": "Executed", "network": "Internal"},
            {"name": "OrbitWorks", "time": "2h ago", "reward": "Shopee RM30", "type": "Value Vault", "status": "Claimed", "network": "x402/Solana"},
        ],
        "inventory": [dict(record) for record in INVENTORY_RECORDS[:10]],
    }


def build_customer_directory() -> list[dict]:
    return [
        {"id": 1, "name": "Acme Corp", "plan": "Enterprise", "mrr": "RM12,460", "health": 31, "risk": "87%", "segment": "VIP", "status": "Human Alert", "icon": "Crown", "color": "text-brand", "bg": "bg-brand/10", "border": "border-brand/20"},
        {"id": 2, "name": "Nexora Solutions", "plan": "Growth", "mrr": "RM4,200", "health": 42, "risk": "78%", "segment": "Persuadable", "status": "AI Target", "icon": "Target", "color": "text-pink-600", "bg": "bg-pink-100", "border": "border-pink-200"},
        {"id": 3, "name": "Kinetic Labs", "plan": "Pro", "mrr": "RM1,850", "health": 94, "risk": "4%", "segment": "Sure Thing", "status": "Healthy", "icon": "Heart", "color": "text-emerald-600", "bg": "bg-emerald-100", "border": "border-emerald-200"},
        {"id": 4, "name": "OrbitWorks", "plan": "Pro", "mrr": "RM2,100", "health": 38, "risk": "82%", "segment": "Persuadable", "status": "Action Needed", "icon": "Target", "color": "text-pink-600", "bg": "bg-pink-100", "border": "border-pink-200"},
        {"id": 5, "name": "Vertex Systems", "plan": "Starter", "mrr": "RM450", "health": 51, "risk": "45%", "segment": "Inactive", "status": "Monitor", "icon": "PauseCircle", "color": "text-amber-600", "bg": "bg-amber-100", "border": "border-amber-200"},
        {"id": 6, "name": "Maju Digital", "plan": "Starter", "mrr": "RM290", "health": 12, "risk": "95%", "segment": "Lost Cause", "status": "Ignore", "icon": "Trash2", "color": "text-slate-600", "bg": "bg-slate-200", "border": "border-slate-300"},
        {"id": 7, "name": "Nexus Logistics", "plan": "Mid-Market", "mrr": "RM8,200", "health": 42, "risk": "71%", "segment": "VIP", "status": "Human Alert", "icon": "Crown", "color": "text-brand", "bg": "bg-brand/10", "border": "border-brand/20"},
    ]


CUSTOMER_DATA = build_customer_directory()


def _normalize_inventory_items(raw_items) -> list[dict[str, str]]:
    if isinstance(raw_items, dict):
        raw_items = raw_items.get("items", [])
    if not isinstance(raw_items, list):
        return []

    normalized: list[dict[str, str]] = []
    for raw_item in raw_items[:100]:
        if not isinstance(raw_item, dict):
            continue
        item_name = str(raw_item.get("item", "")).strip()[:120]
        quantity = str(raw_item.get("quantity", "1")).strip()[:40] or "1"
        if item_name:
            normalized.append({"item": item_name, "quantity": quantity})
    return normalized


async def process_inventory_image(
    image_bytes: bytes,
    mime_type: str = "image/jpeg",
) -> dict:
    """Run local OCR first, then use Gemini only when local OCR finds no items."""
    try:
        local_items = _normalize_inventory_items(
            await asyncio.to_thread(parse_handwritten_inventory, image_bytes)
        )
    except Exception:
        local_items = []
        logger.warning("Local inventory OCR failed; attempting Gemini fallback.")

    if local_items:
        return {"items": local_items, "processor": "easyocr"}

    if not GEMINI_API_KEY:
        return {"items": [], "processor": "none"}

    safe_mime_type = mime_type if mime_type.startswith("image/") else "image/jpeg"
    try:
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        text_prompt = (
            "Extract inventory from this handwritten or printed image. "
            "Return concise item names and quantities. Do not invent items that are not visible."
        )
        item_schema = {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "item": {"type": "string"},
                    "quantity": {"type": "string"},
                },
                "required": ["item", "quantity"],
            },
        }
        payload = {
            "contents": [{
                "parts": [
                    {"text": text_prompt},
                    {
                        "inline_data": {
                            "mime_type": safe_mime_type,
                            "data": encoded,
                        }
                    },
                ]
            }],
            "generationConfig": {
                "responseFormat": {
                    "text": {
                        "mimeType": "application/json",
                        "schema": item_schema,
                    }
                }
            },
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                "https://generativelanguage.googleapis.com/"
                f"v1beta/models/{GEMINI_MODEL}:generateContent",
                headers={"x-goog-api-key": GEMINI_API_KEY},
                json=payload,
            )
            if response.is_error:
                logger.warning(
                    "Gemini inventory fallback returned HTTP %s; no API response body was logged.",
                    response.status_code,
                )
                return {"items": [], "processor": "none"}

            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0].get("text", "")
            if text.startswith("```"):
                text = text.strip("`").removeprefix("json").strip()
            gemini_items = _normalize_inventory_items(json.loads(text))
            if gemini_items:
                return {"items": gemini_items, "processor": "gemini"}
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        logger.warning("Gemini returned an invalid inventory structure; no items were stored.")
    except httpx.RequestError:
        logger.warning("Gemini inventory fallback could not reach the API.")
    except Exception:
        logger.warning("Gemini inventory fallback failed without exposing request credentials.")

    return {"items": [], "processor": "none"}

@app.get("/api/status")
async def home():
    return {"status": "ok", "service": "vault-agent-whatsapp"}


def _solana_status() -> dict:
    try:
        if hasattr(solana_agent, "get_status"):
            status = dict(solana_agent.get_status())
        elif hasattr(solana_agent, "configuration_status"):
            status = dict(solana_agent.configuration_status())
        else:
            status = {}

        active_provider = (os.getenv("WHATSAPP_PROVIDER") or "twilio").lower()
        webhook_security_enabled = (
            bool(os.getenv("WHATSAPP_WEBHOOK_SECRET"))
            if active_provider in {"sleekflow", "wati"}
            else bool(META_APP_SECRET)
            if active_provider == "meta"
            else TWILIO_VALIDATE_SIGNATURE
        )
        if status and status.get("mode") == "live" and not webhook_security_enabled:
            status["mode"] = "demo"
            status["reason"] = (
                "Live Solana configuration is present, but reward payments remain "
                f"blocked until the {active_provider} webhook is authenticated."
            )
        if status:
            return status
    except Exception:
        logger.warning("Could not read Solana configuration status; using demo mode.")

    return {
        "mode": "demo",
        "configured": False,
        "network": os.getenv("SOLANA_RPC_URL", "https://api.devnet.solana.com"),
        "asset": "USDC",
        "defaultAmount": float(_reward_amount()),
        "reason": "Blockchain configuration is incomplete.",
    }


def _available_reward_claim(sender: str) -> dict | None:
    """Return one claimed, unexpired reward that has not started payment."""
    _prune_reward_claims()
    for claim in reversed(REWARD_CLAIMS.values()):
        if (
            claim.get("user") == sender
            and claim.get("claimed_at") is not None
            and claim.get("payment_started_at") is None
        ):
            return claim
    return None


def _twilio_daily_limit_is_active() -> bool:
    return bool(
        TWILIO_DAILY_LIMIT_BLOCKED_UNTIL
        and datetime.now(timezone.utc) < TWILIO_DAILY_LIMIT_BLOCKED_UNTIL
    )


@app.get("/health")
async def healthcheck():
    solana_status = _solana_status()
    return {
        "status": "ok",
        "twilio_configured": bool(
            TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN
        ),
        "twilio_daily_limit_paused": _twilio_daily_limit_is_active(),
        "twilio_signature_validation": TWILIO_VALIDATE_SIGNATURE,
        "vonage_configured": bool(VONAGE_API_KEY and VONAGE_API_SECRET),
        "meta_whatsapp_configured": bool(
            META_WHATSAPP_ACCESS_TOKEN and META_WHATSAPP_PHONE_NUMBER_ID
        ),
        "ocr_available": local_ocr_available(),
        "gemini_configured": bool(GEMINI_API_KEY),
        "gemini_model": GEMINI_MODEL,
        "solana_configured": solana_status["configured"],
        "solana_mode": solana_status["mode"],
        "inventory_records": len(INVENTORY_RECORDS),
    }

@app.get("/api/dashboard")
async def dashboard_summary():
    return build_dashboard_payload()


@app.get("/api/reports/export.pdf")
async def export_retention_report(period: str = "Last 30 Days"):
    """Return a branded, print-ready executive retention report."""
    if period not in REPORT_PERIODS:
        raise HTTPException(status_code=400, detail="Unsupported report period.")

    try:
        pdf = await asyncio.to_thread(render_report_pdf, period)
    except ReportExportError as error:
        logger.exception("Retention report PDF export failed: %s", error)
        detail = "PDF export is temporarily unavailable. Please try again."
        if os.getenv("VERCEL_ENV") == "preview":
            detail = f"PDF export failed: {error}"
        raise HTTPException(
            status_code=503,
            detail=detail,
        )

    exported_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    period_slug = period.lower().replace(" ", "-")
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'attachment; filename="staylongerai-retention-report-{period_slug}-{exported_date}.pdf"'
            ),
            "Cache-Control": "no-store",
        },
    )


@app.get("/api/inventory")
async def inventory_summary():
    return {
        "inventory": [dict(record) for record in INVENTORY_RECORDS],
        "total": len(INVENTORY_RECORDS),
    }


@app.get("/api/rewards/status")
async def rewards_status():
    return _solana_status()


def _with_demo_funding_balance(funding: dict) -> dict:
    """Make the local funding preview actionable without creating a wallet transfer."""
    result = dict(funding)
    if str(result.get("mode", "demo")).lower() != "live":
        result.update(
            {
                "usdcBalance": float(DEMO_REWARD_FUND_BALANCE),
                "balanceAvailable": True,
                "demoFunding": True,
            }
        )
    else:
        result["demoFunding"] = False
    return result


async def _funding_status_payload() -> dict:
    """Expose public funding details while preserving the demo reserve state."""
    if hasattr(solana_agent, "get_funding_status"):
        try:
            funding = await solana_agent.get_funding_status()
            public_status = _solana_status()
            funding.update(public_status)
            return _with_demo_funding_balance(funding)
        except Exception:
            logger.warning("Could not load the Solana funding status.")

    fallback = {
        **_solana_status(),
        "walletAddress": None,
        "usdcMint": os.getenv("USDC_MINT") or None,
        "solBalance": None,
        "usdcBalance": None,
        "balanceAvailable": False,
        "explorerUrl": None,
    }
    return _with_demo_funding_balance(fallback)


@app.get("/api/rewards/funding")
async def rewards_funding_status():
    """Expose only public wallet details and live balances for operator funding."""
    return await _funding_status_payload()


@app.post("/api/rewards/funding/demo")
async def add_demo_reward_funds(funding_request: DemoFundingRequest):
    """Top up the in-memory demo reserve; this endpoint never sends a transaction."""
    if _solana_status().get("mode") == "live":
        raise HTTPException(
            status_code=409,
            detail="Demo funding is unavailable while a live reserve is connected.",
        )

    global DEMO_REWARD_FUND_BALANCE
    async with DEMO_FUNDING_LOCK:
        DEMO_REWARD_FUND_BALANCE += funding_request.amount
        funding = await _funding_status_payload()

    amount_label = format(funding_request.amount.normalize(), "f").rstrip("0").rstrip(".")
    return {
        **funding,
        "message": (
            f"{amount_label} USDC was added to the demo reward reserve. "
            "No wallet transaction was created."
        ),
    }


@app.post("/api/rewards/claim")
async def claim_reward(claim_request: RewardClaimRequest):
    token = claim_request.token.strip()
    if not token:
        raise HTTPException(status_code=400, detail="A reward token is required.")

    _prune_reward_claims()
    claim = REWARD_CLAIMS.get(token)
    if claim is None:
        raise HTTPException(
            status_code=404,
            detail="This reward link is invalid or has expired. Request a new link in WhatsApp.",
        )

    solana_status = _solana_status()
    if claim["claimed_at"] is not None:
        return {
            "status": "already_claimed",
            "amount": float(claim["amount"]),
            "message": "This reward was already confirmed. Continue onboarding in WhatsApp.",
            "demo": solana_status["mode"] != "live",
        }

    claim["claimed_at"] = datetime.now(timezone.utc)
    sender = claim["user"]
    USER_STATES[sender] = "reverse_onboarding"
    is_demo = solana_status["mode"] != "live"
    amount_label = f"RM{claim['amount']:g}"
    REWARD_EVENTS.insert(0, {
        "name": _mask_sender(sender),
        "time": "Just now",
        "reward": f"Value Vault {amount_label}",
        "type": "Value Vault",
        "status": "Demo Confirmed" if is_demo else "Claimed",
        "network": "Demo mode" if is_demo else "Solana/x402",
    })
    del REWARD_EVENTS[20:]

    return {
        "status": "claimed",
        "amount": float(claim["amount"]),
        "message": "Reward confirmed. Return to WhatsApp and send an inventory photo.",
        "demo": is_demo,
    }

def _percentage_value(raw_value, default: int = 50) -> int:
    import re

    match = re.search(r"-?\d+(?:\.\d+)?", str(raw_value))
    if not match:
        return default
    try:
        return max(0, min(100, round(float(match.group(0)))))
    except ValueError:
        return default


def build_customer_record(row: dict, idx: int) -> dict | None:
    row = {str(key).strip().lower(): value for key, value in row.items()}
    name = (
        row.get("name") or row.get("company") or row.get("customer") or row.get("account") or row.get("customer_name")
    )
    if not name:
        return None

    plan = row.get("plan") or row.get("tier") or row.get("subscription") or "Growth"
    mrr = row.get("mrr") or row.get("monthly_revenue") or row.get("revenue") or "RM0"
    health_raw = row.get("health") or row.get("health_score") or row.get("score") or "50"
    risk_raw = row.get("risk") or row.get("churn_risk") or row.get("risk_percent") or "50%"
    segment_raw = str(
        row.get("segment") or row.get("category") or row.get("status") or "Persuadable"
    ).strip()
    status = row.get("status") or row.get("action") or "Imported"
    health = _percentage_value(health_raw)
    risk_value = _percentage_value(risk_raw)
    known_segments = {
        "vip": "VIP",
        "persuadable": "Persuadable",
        "sure thing": "Sure Thing",
        "inactive": "Inactive",
        "lost cause": "Lost Cause",
    }
    segment = known_segments.get(segment_raw.lower())
    if segment is None:
        segment = "Persuadable" if health < 60 or risk_value > 50 else "VIP"

    customer = {
        "id": idx,
        "name": str(name).strip(),
        "plan": str(plan).strip(),
        "mrr": str(mrr).strip() if str(mrr).strip() else "RM0",
        "health": health,
        "risk": f"{risk_value}%",
        "segment": segment,
        "status": str(status).strip() or "Imported",
        "icon": "Crown" if segment == "VIP" else "Target" if segment == "Persuadable" else "Heart" if segment == "Sure Thing" else "PauseCircle" if segment == "Inactive" else "Trash2",
        "color": "text-brand" if segment == "VIP" else "text-pink-600" if segment == "Persuadable" else "text-emerald-600" if segment == "Sure Thing" else "text-amber-600" if segment == "Inactive" else "text-slate-600",
        "bg": "bg-brand/10" if segment == "VIP" else "bg-pink-100" if segment == "Persuadable" else "bg-emerald-100" if segment == "Sure Thing" else "bg-amber-100" if segment == "Inactive" else "bg-slate-200",
        "border": "border-brand/20" if segment == "VIP" else "border-pink-200" if segment == "Persuadable" else "border-emerald-200" if segment == "Sure Thing" else "border-amber-200" if segment == "Inactive" else "border-slate-300",
    }
    return customer

@app.get("/api/customers")
async def customers_summary():
    return {"customers": CUSTOMER_DATA}

@app.post("/api/customers/import")
async def import_customers(file: UploadFile = File(...)):
    filename = file.filename or "customer_import"
    file_ext = os.path.splitext(filename)[1].lower()
    parsed_rows: list[dict] = []

    try:
        if file_ext not in {".csv", ".json", ".txt"}:
            raise HTTPException(
                status_code=400,
                detail="Supported customer import formats are CSV, JSON, and TXT.",
            )

        contents = await file.read(5 * 1024 * 1024 + 1)
        if len(contents) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Customer import files are limited to 5 MB.")
        if not contents:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")

        if file_ext == ".csv":
            text = contents.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            parsed_rows = [row for row in reader]
        elif file_ext == ".json":
            text = contents.decode("utf-8-sig")
            parsed_json = json.loads(text)
            parsed_rows = parsed_json if isinstance(parsed_json, list) else [parsed_json]
        else:
            text = contents.decode("utf-8-sig")
            try:
                parsed_json = json.loads(text)
                parsed_rows = parsed_json if isinstance(parsed_json, list) else [parsed_json]
            except json.JSONDecodeError:
                parsed_rows = [
                    {"name": line.strip(), "status": "Imported"}
                    for line in text.splitlines()
                    if line.strip()
                ]

        imported_customers = []
        next_id = max((customer["id"] for customer in CUSTOMER_DATA), default=0) + 1
        for row in parsed_rows:
            if not isinstance(row, dict):
                continue
            record = build_customer_record(row, next_id)
            if record is not None:
                imported_customers.append(record)
                next_id += 1

        if not imported_customers:
            raise HTTPException(
                status_code=400,
                detail="No valid customer records were found in the uploaded file.",
            )

        CUSTOMER_DATA.extend(imported_customers)

        return {
            "status": "success",
            "filename": filename,
            "customers": CUSTOMER_DATA,
            "imported": len(imported_customers),
            "message": f"File {filename} uploaded successfully.",
        }
    except HTTPException:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError, csv.Error):
        raise HTTPException(status_code=400, detail="The customer file could not be parsed.")
    finally:
        await file.close()

@app.get("/webhook")
async def webhook_status():
    provider = whatsapp_provider.PROVIDER
    if provider not in {"sleekflow", "wati"}:
        provider = "twilio"
    return {"status": "ok", "provider": f"{provider}-whatsapp"}


def _twiml_response(status_code: int = 200) -> Response:
    return Response(
        content="<Response></Response>",
        media_type="application/xml",
        status_code=status_code,
    )


def _validate_twilio_request(request: Request, form_data: dict[str, list[str]]) -> bool:
    if not TWILIO_VALIDATE_SIGNATURE:
        return True
    if RequestValidator is None or not TWILIO_AUTH_TOKEN:
        logger.error(
            "Twilio signature validation is enabled but its helper or Auth Token is unavailable."
        )
        return False

    signature = request.headers.get("X-Twilio-Signature", "")
    configured_webhook_url = os.getenv("TWILIO_WEBHOOK_URL", "").strip()
    has_public_dashboard_url = any(
        os.getenv(variable_name, "").strip()
        for variable_name in (
            "DASHBOARD_BASE_URL",
            "RENDER_EXTERNAL_URL",
            "RENDER_EXTERNAL_HOSTNAME",
            "VERCEL_PROJECT_PRODUCTION_URL",
            "VERCEL_URL",
        )
    )
    public_url = configured_webhook_url or (
        f"{_dashboard_base_url()}/webhook"
        if has_public_dashboard_url
        else str(request.url)
    )
    flat_form = {key: values[0] if values else "" for key, values in form_data.items()}
    try:
        return bool(RequestValidator(TWILIO_AUTH_TOKEN).validate(public_url, flat_form, signature))
    except Exception:
        logger.warning("Twilio signature validation failed safely.")
        return False


def _is_duplicate_message(message_sid: str) -> bool:
    if not message_sid:
        return False

    now = time.monotonic()
    while PROCESSED_MESSAGE_SIDS:
        oldest_sid, recorded_at = next(iter(PROCESSED_MESSAGE_SIDS.items()))
        if now - recorded_at <= MESSAGE_SID_TTL_SECONDS:
            break
        PROCESSED_MESSAGE_SIDS.pop(oldest_sid, None)

    if message_sid in PROCESSED_MESSAGE_SIDS:
        PROCESSED_MESSAGE_SIDS.move_to_end(message_sid)
        return True

    PROCESSED_MESSAGE_SIDS[message_sid] = now
    while len(PROCESSED_MESSAGE_SIDS) > MAX_PROCESSED_MESSAGE_SIDS:
        PROCESSED_MESSAGE_SIDS.popitem(last=False)
    return False


def _normalize_bsp_message(data: dict) -> dict[str, list[str]] | None:
    """Normalize Wati/SleekFlow JSON into the internal WhatsApp event shape."""
    if not isinstance(data, dict):
        return None

    provider = whatsapp_provider.PROVIDER
    if provider == "wati":
        sender = data.get("waId") or data.get("phone") or data.get("from")
        message_type = str(data.get("type") or "text").lower()
        text = data.get("text") or data.get("caption") or ""
        interactive = data.get("interactive")
        button_id = (
            interactive.get("buttonId")
            if isinstance(interactive, dict)
            else data.get("buttonId") or data.get("buttonText")
        )
        media = data.get("media") if isinstance(data.get("media"), dict) else {}
        media_url = media.get("url") or data.get("mediaUrl") or ""
        media_type = media.get("mimeType") or data.get("mimeType") or "image/jpeg"
        message_id = data.get("id") or data.get("whatsappMessageId") or uuid.uuid4().hex
    else:
        envelope = data.get("data") if isinstance(data.get("data"), dict) else data
        sender_payload = envelope.get("from")
        sender = (
            sender_payload.get("phone")
            if isinstance(sender_payload, dict)
            else sender_payload or envelope.get("phone")
        )
        message = (
            envelope.get("message")
            if isinstance(envelope.get("message"), dict)
            else envelope
        )
        message_type = str(message.get("type") or "text").lower()
        text_payload = message.get("text")
        text = (
            text_payload.get("body", "")
            if isinstance(text_payload, dict)
            else str(text_payload or "")
        )
        interactive = message.get("interactive") or {}
        button_reply = (
            interactive.get("button_reply", {})
            if isinstance(interactive, dict)
            else {}
        )
        button_id = button_reply.get("id")
        media = (
            message.get("image")
            if isinstance(message.get("image"), dict)
            else message.get("media")
            if isinstance(message.get("media"), dict)
            else {}
        )
        media_url = media.get("url") or ""
        media_type = media.get("mime_type") or media.get("mimeType") or "image/jpeg"
        message_id = message.get("id") or envelope.get("id") or uuid.uuid4().hex

    if not sender:
        return None
    if button_id == "claim_reward":
        text = "claim"
    has_media = bool(media_url) and message_type in {"image", "media"}
    return {
        "MessageSid": [str(message_id)],
        "From": [f"{provider}:{sender}"],
        "Body": [str(text or "")],
        "NumMedia": ["1" if has_media else "0"],
        "MediaUrl0": [str(media_url)],
        "MediaContentType0": [str(media_type)],
    }


@app.post("/webhook")
async def handle_whatsapp_messages(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Twilio sends incoming WhatsApp messages as application/x-www-form-urlencoded.

    Important:
    - We acknowledge Twilio immediately with HTTP 200.
    - OCR / Gemini / Solana work runs after the response in a background task.
    - MessageSid de-duplication prevents Twilio webhook retries from processing
      the same WhatsApp message multiple times.
    """
    try:
        raw_bytes = await request.body()
        if len(raw_bytes) > 64 * 1024:
            logger.warning("Oversized Twilio webhook body ignored.")
            return _twiml_response()

        if whatsapp_provider.PROVIDER in {"sleekflow", "wati"}:
            expected_secret = os.getenv("WHATSAPP_WEBHOOK_SECRET", "")
            provided_secret = request.headers.get("X-Webhook-Secret", "")
            if expected_secret and not secrets.compare_digest(
                expected_secret,
                provided_secret,
            ):
                return Response(status_code=403)

            normalized = _normalize_bsp_message(json.loads(raw_bytes.decode("utf-8")))
            if normalized is None:
                return Response(status_code=200)
            message_sid = normalized["MessageSid"][0]
            if not _is_duplicate_message(message_sid):
                background_tasks.add_task(process_whatsapp_message, normalized)
            return Response(status_code=200)

        raw_body = raw_bytes.decode("utf-8")
        form_data = parse_qs(raw_body, keep_blank_values=True, max_num_fields=100)

        if not _validate_twilio_request(request, form_data):
            logger.warning("Rejected a webhook with an invalid Twilio signature.")
            return _twiml_response(status_code=403)

        message_sid = form_data.get("MessageSid", [""])[0]

        if _is_duplicate_message(message_sid):
            logger.info("Duplicate Twilio webhook ignored (SID suffix %s).", message_sid[-6:])
            return _twiml_response()

        background_tasks.add_task(
            process_whatsapp_message,
            form_data,
        )

        # Return immediately so Twilio does not retry while OCR is still running.
        return _twiml_response()
    except Exception:
        logger.exception("Error accepting Twilio webhook; request was acknowledged safely.")

        # Return 200 to avoid a webhook retry storm for malformed requests.
        return _twiml_response()


@app.get("/webhook/vonage")
async def vonage_webhook_status():
    return {"status": "ok", "provider": "vonage-whatsapp"}


@app.post("/webhook/vonage/status")
async def handle_vonage_message_status():
    # Delivery receipts need only a fast acknowledgement for the local demo.
    return Response(status_code=200)


@app.post("/webhook/vonage")
async def handle_vonage_whatsapp_messages(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Accept Vonage Messages API v1 JSON and reuse the existing WhatsApp flow."""
    try:
        raw_bytes = await request.body()
        if len(raw_bytes) > 64 * 1024:
            logger.warning("Oversized Vonage webhook body ignored.")
            return Response(status_code=200)

        payload = json.loads(raw_bytes or b"{}")
        if not isinstance(payload, dict):
            return Response(status_code=200)

        message_uuid = str(payload.get("message_uuid", "")).strip()
        if _is_duplicate_message(message_uuid):
            logger.info(
                "Duplicate Vonage webhook ignored (UUID suffix %s).",
                message_uuid[-6:],
            )
            return Response(status_code=200)

        sender = str(payload.get("from", "")).strip()
        message_type = str(payload.get("message_type", "text")).lower()
        text_payload = payload.get("text")
        body = (
            str(text_payload.get("content", ""))
            if isinstance(text_payload, dict)
            else str(text_payload or "")
        )
        image_payload = payload.get("image") if message_type == "image" else None
        image_payload = image_payload if isinstance(image_payload, dict) else {}
        media_url = str(image_payload.get("url", "")).strip()
        media_type = str(image_payload.get("mime_type", "image/jpeg")).strip()

        normalized = {
            "MessageSid": [message_uuid],
            "From": [f"vonage:{sender}"],
            "Body": [body],
            "NumMedia": ["1" if media_url else "0"],
            "MediaUrl0": [media_url],
            "MediaContentType0": [media_type],
        }
        background_tasks.add_task(process_whatsapp_message, normalized)
        return Response(status_code=200)
    except Exception:
        logger.exception("Error accepting Vonage webhook; request was acknowledged safely.")
        return Response(status_code=200)


@app.get("/webhook/meta")
async def verify_meta_whatsapp_webhook(request: Request):
    mode = request.query_params.get("hub.mode", "")
    supplied_token = request.query_params.get("hub.verify_token", "")
    challenge = request.query_params.get("hub.challenge", "")
    token_matches = bool(
        META_WHATSAPP_VERIFY_TOKEN
        and secrets.compare_digest(supplied_token, META_WHATSAPP_VERIFY_TOKEN)
    )
    if mode == "subscribe" and token_matches and challenge:
        return Response(content=challenge, media_type="text/plain", status_code=200)
    logger.warning("Rejected a Meta WhatsApp webhook verification attempt.")
    return Response(status_code=403)


@app.post("/webhook/meta")
async def handle_meta_whatsapp_messages(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Accept Meta Cloud API webhooks and reuse the existing WhatsApp flow."""
    try:
        raw_bytes = await request.body()
        if len(raw_bytes) > 256 * 1024:
            logger.warning("Oversized Meta WhatsApp webhook body ignored.")
            return Response(status_code=200)
        if META_APP_SECRET:
            supplied_signature = request.headers.get("X-Hub-Signature-256", "")
            expected_signature = "sha256=" + hmac.new(
                META_APP_SECRET.encode("utf-8"),
                raw_bytes,
                hashlib.sha256,
            ).hexdigest()
            if not supplied_signature or not secrets.compare_digest(
                supplied_signature,
                expected_signature,
            ):
                logger.warning("Rejected a Meta webhook with an invalid signature.")
                return Response(status_code=403)
        payload = json.loads(raw_bytes or b"{}")
        entries = payload.get("entry", []) if isinstance(payload, dict) else []
        for entry in entries if isinstance(entries, list) else []:
            changes = entry.get("changes", []) if isinstance(entry, dict) else []
            for change in changes if isinstance(changes, list) else []:
                value = change.get("value", {}) if isinstance(change, dict) else {}
                messages = value.get("messages", []) if isinstance(value, dict) else []
                for message in messages if isinstance(messages, list) else []:
                    if not isinstance(message, dict):
                        continue
                    message_id = str(message.get("id", "")).strip()
                    if _is_duplicate_message(message_id):
                        continue
                    sender = str(message.get("from", "")).strip()
                    message_type = str(message.get("type", "text")).lower()
                    text_payload = message.get("text", {})
                    body = (
                        str(text_payload.get("body", ""))
                        if isinstance(text_payload, dict)
                        else ""
                    )
                    image_payload = message.get("image", {})
                    image_payload = image_payload if isinstance(image_payload, dict) else {}
                    media_id = (
                        str(image_payload.get("id", "")).strip()
                        if message_type == "image"
                        else ""
                    )
                    normalized = {
                        "MessageSid": [message_id],
                        "From": [f"meta:{sender}"],
                        "Body": [body],
                        "NumMedia": ["1" if media_id else "0"],
                        "MediaUrl0": [media_id],
                        "MediaContentType0": [
                            str(image_payload.get("mime_type", "image/jpeg"))
                        ],
                    }
                    background_tasks.add_task(process_whatsapp_message, normalized)
        return Response(status_code=200)
    except Exception:
        logger.exception("Error accepting Meta WhatsApp webhook; acknowledged safely.")
        return Response(status_code=200)


async def process_whatsapp_message(form_data: dict):
    try:
        message_sid = form_data.get("MessageSid", [""])[0]
        sender = form_data.get("From", [""])[0]
        provider = (
            "meta"
            if sender.startswith("meta:")
            else "vonage"
            if sender.startswith("vonage:")
            else "sleekflow"
            if sender.startswith("sleekflow:")
            else "wati"
            if sender.startswith("wati:")
            else "twilio"
        )
        body = form_data.get("Body", [""])[0].strip()
        try:
            num_media = max(0, min(10, int(form_data.get("NumMedia", ["0"])[0])))
        except ValueError:
            num_media = 0

        logger.info(
            "WhatsApp webhook accepted (SID suffix %s, sender %s, media=%s, has_text=%s).",
            message_sid[-6:] if message_sid else "unknown",
            _mask_sender(sender),
            num_media,
            bool(body),
        )

        if not sender:
            logger.warning("Ignored Twilio message with no sender.")
            return

        current_state = USER_STATES.get(sender, "idle")

        # =========================
        # IMAGE / MEDIA MESSAGE
        # =========================
        # Check media before text so an image with a caption still goes
        # through the inventory-image flow.
        if num_media > 0:
            media_url = form_data.get("MediaUrl0", [""])[0]
            media_type = form_data.get("MediaContentType0", [""])[0]

            if not media_url:
                logger.warning("Ignored Twilio media message with no MediaUrl0.")
                return

            if not media_type.startswith("image/"):
                await send_message(
                    sender,
                    "Please send an image of your inventory."
                )
                return

            USER_STATES[sender] = "reverse_onboarding"

            try:
                if provider == "meta":
                    image_bytes = await download_meta_media(media_url)
                elif provider == "vonage":
                    image_bytes = await download_media(media_url, provider="vonage")
                elif provider in {"sleekflow", "wati"}:
                    image_bytes = await download_bsp_media(media_url, provider)
                else:
                    image_bytes = await download_media(media_url)
            except Exception:
                logger.warning("WhatsApp inventory media could not be downloaded safely.")
                await send_message(
                    sender,
                    "We couldn't download that image. Please send the inventory photo again.",
                )
                return

            inventory_result = await process_inventory_image(
                image_bytes,
                media_type,
            )
            extracted_items = inventory_result["items"]

            if not extracted_items:
                await send_message(
                    sender,
                    "We couldn't read that image clearly. "
                    "Please send a sharper photo of the inventory."
                )
                return

            record = {
                "id": message_sid or uuid.uuid4().hex,
                "source": "WhatsApp",
                "sender": _mask_sender(sender),
                "receivedAt": datetime.now(timezone.utc).isoformat(),
                "itemCount": len(extracted_items),
                "items": extracted_items,
                "processor": inventory_result["processor"],
                "paymentStatus": "processing",
            }
            INVENTORY_RECORDS.insert(0, record)
            del INVENTORY_RECORDS[MAX_INVENTORY_RECORDS:]

            summary = "\n".join(
                f"• {item['item']}: {item['quantity']}"
                for item in extracted_items
            )

            chain_amount = _reward_amount()
            display_amount = _reward_display_amount()
            recipient_wallet = os.getenv("PAYMENT_RECIPIENT_WALLET", "")
            payment_status = "demo"
            solana_status = _solana_status()

            if solana_status["mode"] == "live":
                reward_claim = _available_reward_claim(sender)
                if reward_claim is None:
                    payment_status = "claim_required"
                else:
                    # Mark the claim before the network call. A timeout after chain
                    # submission must not let a second image trigger a duplicate payment.
                    reward_claim["payment_started_at"] = datetime.now(timezone.utc)
                    try:
                        payment_result = (
                            await solana_agent.execute_reward_micropayment(
                                recipient_address=recipient_wallet,
                                amount_usdc=chain_amount,
                                payment_reference=f"inventory:{record['id']}",
                            )
                        )

                        payment_status = payment_result.get(
                            "status",
                            "processed",
                        )
                    except Exception:
                        logger.warning("Live Solana reward payment failed; inventory was still stored.")
                        payment_status = "payment_error"
                    reward_claim["payment_status"] = payment_status

            record["paymentStatus"] = payment_status
            payment_label = {
                "demo": "demo mode (no blockchain transfer)",
                "payment_error": "inventory saved; payment needs review",
                "processed": "processed",
                "claim_required": "claim the reward link before live settlement",
            }.get(payment_status, payment_status)

            await send_message(
                sender,
                f"Successfully parsed your inventory ✅\n\n"
                f"{summary}\n\n"
                f"Reward status: {payment_label}\n"
                f"Your RM{display_amount:g} Value Vault reward is now active."
            )

            USER_STATES[sender] = "idle"
            return

        # =========================
        # TEXT MESSAGE
        # =========================
        if body:
            if body.lower() in {"claim reward", "reward", "claim"}:
                dashboard_url = generate_dashboard_url(sender)

                await send_message(
                    sender,
                    f"Your secure dashboard is ready:\n{dashboard_url}\n\n"
                    "Open it to confirm your reward and continue onboarding."
                )

                USER_STATES[sender] = "claiming_reward"
                return

            if current_state == "claiming_reward":
                await send_message(
                    sender,
                    "Your reward is ready. Open the dashboard link sent above to continue."
                )
                return

            await send_message(
                sender,
                "Hi! 👋\n\n"
                "Reply with *claim* to open your reward flow, "
                "or send a photo of your inventory to complete reverse onboarding."
            )
            return

        logger.info("Ignored an empty Twilio message.")

    except Exception:
        logger.exception("Error processing a Twilio message in the background.")


async def download_meta_media(media_id: str) -> bytes:
    if not META_WHATSAPP_ACCESS_TOKEN:
        raise RuntimeError("Meta WhatsApp access token is missing.")
    if not media_id.isdigit():
        raise ValueError("Rejected an invalid Meta media ID.")

    headers = {"Authorization": f"Bearer {META_WHATSAPP_ACCESS_TOKEN}"}
    metadata_url = f"{META_GRAPH_BASE_URL}/{META_GRAPH_API_VERSION}/{media_id}"
    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        metadata_response = await client.get(metadata_url, headers=headers)
        metadata_response.raise_for_status()
        metadata = metadata_response.json()
        media_url = str(metadata.get("url", "")) if isinstance(metadata, dict) else ""
        parsed_url = urlparse(media_url)
        hostname = (parsed_url.hostname or "").lower()
        trusted = (
            hostname.endswith(".facebook.com")
            or hostname.endswith(".fbcdn.net")
            or hostname.endswith(".fbsbx.com")
        )
        if parsed_url.scheme != "https" or not trusted:
            raise ValueError("Rejected an untrusted Meta media URL.")

        async with client.stream("GET", media_url, headers=headers) as response:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if content_type and not (
                content_type.startswith("image/")
                or content_type.startswith("application/octet-stream")
            ):
                raise ValueError("Meta media response was not an image.")
            chunks: list[bytes] = []
            total_bytes = 0
            async for chunk in response.aiter_bytes():
                total_bytes += len(chunk)
                if total_bytes > MAX_MEDIA_BYTES:
                    raise ValueError("Meta media image exceeds the 15 MB limit.")
                chunks.append(chunk)
            image_bytes = b"".join(chunks)
            if not image_bytes:
                raise ValueError("Meta media image was empty.")
            return image_bytes


async def download_bsp_media(media_url: str, provider: str) -> bytes:
    """Download Wati/SleekFlow media from an explicit HTTPS host allowlist."""
    parsed_url = urlparse(media_url)
    hostname = (parsed_url.hostname or "").lower()
    env_name = "WATI_MEDIA_HOSTS" if provider == "wati" else "SLEEKFLOW_MEDIA_HOSTS"
    default_hosts = "wati.io" if provider == "wati" else "sleekflow.io"
    configured_hosts = {
        host.strip().lower()
        for host in os.getenv(env_name, default_hosts).split(",")
        if host.strip()
    }
    trusted = any(
        hostname == host or hostname.endswith(f".{host}")
        for host in configured_hosts
    )
    if parsed_url.scheme != "https" or not trusted:
        raise ValueError(f"Rejected an untrusted {provider} media URL.")

    headers: dict[str, str] = {}
    if provider == "wati" and os.getenv("WATI_ACCESS_TOKEN"):
        headers["Authorization"] = f"Bearer {os.getenv('WATI_ACCESS_TOKEN')}"
    if provider == "sleekflow" and (
        os.getenv("SLEEKFLOW_API_KEY") or os.getenv("SLEEKFLOW_TOKEN")
    ):
        token = os.getenv("SLEEKFLOW_API_KEY") or os.getenv("SLEEKFLOW_TOKEN")
        headers["Authorization"] = f"Bearer {token}"

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
        async with client.stream("GET", media_url, headers=headers) as response:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if content_type and not (
                content_type.startswith("image/")
                or content_type.startswith("application/octet-stream")
            ):
                raise ValueError(f"{provider} media response was not an image.")
            chunks: list[bytes] = []
            total_bytes = 0
            async for chunk in response.aiter_bytes():
                total_bytes += len(chunk)
                if total_bytes > MAX_MEDIA_BYTES:
                    raise ValueError(f"{provider} media image exceeds the 15 MB limit.")
                chunks.append(chunk)
            image_bytes = b"".join(chunks)
            if not image_bytes:
                raise ValueError(f"{provider} media image was empty.")
            return image_bytes


async def download_media(media_url: str, provider: str = "twilio") -> bytes:
    parsed_url = urlparse(media_url)
    hostname = (parsed_url.hostname or "").lower()
    auth = None
    if provider == "vonage":
        configured_hosts = {
            host.strip().lower()
            for host in os.getenv(
                "VONAGE_MEDIA_HOSTS",
                "api.nexmo.com,api-us.nexmo.com,api-eu.nexmo.com,api-ap.nexmo.com",
            ).split(",")
            if host.strip()
        }
        trusted = (
            hostname in configured_hosts
            or hostname.endswith(".nexmo.com")
            or hostname.endswith(".vonage.com")
        )
    else:
        if not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
            raise RuntimeError("Twilio credentials are missing.")
        configured_hosts = {
            host.strip().lower()
            for host in os.getenv("TWILIO_MEDIA_HOSTS", "api.twilio.com").split(",")
            if host.strip()
        }
        trusted = (
            hostname in configured_hosts
            or hostname == "twilio.com"
            or hostname.endswith(".twilio.com")
        )
        auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

    if parsed_url.scheme != "https" or not trusted:
        provider_label = "Vonage" if provider == "vonage" else "Twilio"
        raise ValueError(f"Rejected an untrusted {provider_label} media URL.")

    async with httpx.AsyncClient(
        auth=auth,
        timeout=30.0,
        follow_redirects=True,
    ) as client:
        async with client.stream("GET", media_url) as response:
            response.raise_for_status()
            content_type = response.headers.get("Content-Type", "").lower()
            if content_type and not (
                content_type.startswith("image/")
                or content_type.startswith("application/octet-stream")
            ):
                raise ValueError("Twilio media response was not an image.")

            content_length = response.headers.get("Content-Length")
            if content_length:
                try:
                    declared_size = int(content_length)
                except ValueError:
                    declared_size = 0
                if declared_size > MAX_MEDIA_BYTES:
                    raise ValueError("Twilio media image exceeds the 15 MB limit.")

            chunks: list[bytes] = []
            total_bytes = 0
            async for chunk in response.aiter_bytes():
                total_bytes += len(chunk)
                if total_bytes > MAX_MEDIA_BYTES:
                    raise ValueError("Twilio media image exceeds the 15 MB limit.")
                chunks.append(chunk)

            image_bytes = b"".join(chunks)
            if not image_bytes:
                raise ValueError("Twilio media image was empty.")
            return image_bytes


def _twilio_error_details(response: httpx.Response) -> tuple[int | None, str | None]:
    try:
        payload = response.json()
    except (ValueError, json.JSONDecodeError):
        return None, None
    if not isinstance(payload, dict):
        return None, None

    raw_code = payload.get("code")
    try:
        code = int(raw_code) if raw_code is not None else None
    except (TypeError, ValueError):
        code = None
    message = str(payload.get("message", "")).strip() or None
    return code, message


def _pause_twilio_for_daily_limit() -> datetime:
    global TWILIO_DAILY_LIMIT_BLOCKED_UNTIL

    TWILIO_DAILY_LIMIT_BLOCKED_UNTIL = datetime.now(timezone.utc) + timedelta(hours=24)
    logger.error(
        "Twilio outbound WhatsApp paused for 24 hours: error 63038 means the account "
        "exceeded its rolling daily message limit. Incoming webhooks remain healthy; "
        "this message will not be retried."
    )
    return TWILIO_DAILY_LIMIT_BLOCKED_UNTIL


async def send_meta_message(to_number: str, text: str):
    """Send a customer-service-window reply through Meta WhatsApp Cloud API."""
    if not META_WHATSAPP_ACCESS_TOKEN or not META_WHATSAPP_PHONE_NUMBER_ID:
        logger.warning("Meta WhatsApp credentials are missing; outbound reply was skipped.")
        return {"status": "not_configured"}
    recipient = "".join(character for character in to_number if character.isdigit())
    if not recipient:
        return {"status": "invalid_number"}
    url = (
        f"{META_GRAPH_BASE_URL}/{META_GRAPH_API_VERSION}/"
        f"{META_WHATSAPP_PHONE_NUMBER_ID}/messages"
    )
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient,
        "type": "text",
        "text": {"preview_url": True, "body": text},
    }
    headers = {
        "Authorization": f"Bearer {META_WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, headers=headers, json=payload)
    except httpx.RequestError:
        logger.warning("Meta WhatsApp outbound request failed at the network layer.")
        return {"status": "network_error"}
    if 200 <= response.status_code < 300:
        logger.info("Meta WhatsApp message sent (HTTP %s).", response.status_code)
        try:
            return response.json()
        except ValueError:
            return {"status": "sent", "statusCode": response.status_code}
    error_code = None
    try:
        error_payload = response.json()
        error = error_payload.get("error", {}) if isinstance(error_payload, dict) else {}
        error_code = error.get("code") if isinstance(error, dict) else None
    except ValueError:
        pass
    logger.error(
        "Meta WhatsApp send failed safely (HTTP %s, error code=%s).",
        response.status_code,
        error_code or "unknown",
    )
    return {"status": "failed", "statusCode": response.status_code, "code": error_code}


async def send_vonage_message(to_number: str, text: str):
    """Send a free-form WhatsApp reply through the Vonage Messages Sandbox."""
    if not VONAGE_API_KEY or not VONAGE_API_SECRET or not VONAGE_WHATSAPP_FROM:
        logger.warning("Vonage credentials are missing; outbound WhatsApp was skipped.")
        return {"status": "not_configured"}

    recipient = "".join(character for character in to_number if character.isdigit())
    sender = "".join(character for character in VONAGE_WHATSAPP_FROM if character.isdigit())
    if not recipient or not sender:
        logger.warning("Vonage sender or recipient number was invalid.")
        return {"status": "invalid_number"}

    payload = {
        "from": sender,
        "to": recipient,
        "channel": "whatsapp",
        "message_type": "text",
        "text": text,
    }
    try:
        async with httpx.AsyncClient(
            auth=(VONAGE_API_KEY, VONAGE_API_SECRET),
            timeout=30.0,
        ) as client:
            response = await client.post(VONAGE_MESSAGES_URL, json=payload)
    except httpx.RequestError:
        logger.warning("Vonage outbound request failed at the network layer.")
        return {"status": "network_error"}

    if 200 <= response.status_code < 300:
        logger.info("Vonage message sent (HTTP %s).", response.status_code)
        try:
            return response.json()
        except ValueError:
            return {"status": "sent", "statusCode": response.status_code}

    error_code = None
    try:
        error_payload = response.json()
        if isinstance(error_payload, dict):
            error_code = error_payload.get("title") or error_payload.get("type")
    except ValueError:
        pass
    logger.error(
        "Vonage send failed safely (HTTP %s, error=%s).",
        response.status_code,
        error_code or "unknown",
    )
    return {
        "status": "failed",
        "statusCode": response.status_code,
        "code": error_code,
    }


async def send_message(to_number: str, text: str):
    """Send one outbound WhatsApp message without allowing failures to break a webhook."""
    if to_number.startswith("sleekflow:"):
        return await whatsapp_provider.send_text(
            to_number.removeprefix("sleekflow:"),
            text,
        )
    if to_number.startswith("wati:"):
        return await whatsapp_provider.send_text(
            to_number.removeprefix("wati:"),
            text,
        )
    if whatsapp_provider.PROVIDER in {"sleekflow", "wati"}:
        return await whatsapp_provider.send_text(to_number, text)
    if to_number.startswith("meta:"):
        return await send_meta_message(to_number.removeprefix("meta:"), text)
    if to_number.startswith("vonage:"):
        return await send_vonage_message(to_number.removeprefix("vonage:"), text)

    if (
        not TWILIO_ACCOUNT_SID
        or not TWILIO_AUTH_TOKEN
        or not TWILIO_MESSAGES_URL
    ):
        logger.warning("Twilio credentials are missing; outbound WhatsApp was skipped.")
        return {"status": "not_configured"}

    if _twilio_daily_limit_is_active():
        return {
            "status": "daily_limit_exceeded",
            "code": TWILIO_DAILY_LIMIT_CODE,
            "retryAfter": TWILIO_DAILY_LIMIT_BLOCKED_UNTIL.isoformat(),
        }

    if not to_number.startswith("whatsapp:"):
        to_number = f"whatsapp:{to_number}"

    payload = {
        "From": TWILIO_WHATSAPP_FROM,
        "To": to_number,
        "Body": text,
    }
    retry_delays = [3, 6, 12, 24, 30]

    async with TWILIO_SEND_LOCK:
        if _twilio_daily_limit_is_active():
            return {
                "status": "daily_limit_exceeded",
                "code": TWILIO_DAILY_LIMIT_CODE,
                "retryAfter": TWILIO_DAILY_LIMIT_BLOCKED_UNTIL.isoformat(),
            }

        async with httpx.AsyncClient(
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            timeout=30.0,
        ) as client:
            for attempt, fallback_delay in enumerate(retry_delays, start=1):
                try:
                    response = await client.post(TWILIO_MESSAGES_URL, data=payload)
                except httpx.RequestError:
                    logger.warning("Twilio outbound request failed at the network layer.")
                    return {"status": "network_error"}

                error_code, _ = _twilio_error_details(response)
                if error_code == TWILIO_DAILY_LIMIT_CODE:
                    retry_after = _pause_twilio_for_daily_limit()
                    return {
                        "status": "daily_limit_exceeded",
                        "code": TWILIO_DAILY_LIMIT_CODE,
                        "retryAfter": retry_after.isoformat(),
                    }

                concurrent_requests = response.headers.get("Twilio-Concurrent-Requests")
                if 200 <= response.status_code < 300:
                    logger.info(
                        "Twilio message sent (HTTP %s, concurrent requests=%s).",
                        response.status_code,
                        concurrent_requests or "unknown",
                    )
                    # The WhatsApp Sandbox permits roughly one outbound message
                    # every three seconds, so serialize successful sends.
                    await asyncio.sleep(3)
                    try:
                        return response.json()
                    except ValueError:
                        return {"status": "sent", "statusCode": response.status_code}

                if response.status_code != 429:
                    logger.error(
                        "Twilio send failed safely (HTTP %s, error code=%s).",
                        response.status_code,
                        error_code or "unknown",
                    )
                    return {
                        "status": "failed",
                        "statusCode": response.status_code,
                        "code": error_code,
                    }

                if attempt == len(retry_delays):
                    break

                retry_after_header = response.headers.get("Retry-After")
                try:
                    retry_after_seconds = (
                        float(retry_after_header) if retry_after_header else 0
                    )
                except ValueError:
                    retry_after_seconds = 0
                wait_seconds = min(60, max(retry_after_seconds, fallback_delay))
                logger.warning(
                    "Twilio rate limited this send (attempt %s/%s); retrying in %.0fs.",
                    attempt,
                    len(retry_delays),
                    wait_seconds,
                )
                await asyncio.sleep(wait_seconds)

    logger.error(
        "Twilio remained rate limited after bounded retries; the inbound webhook "
        "was already acknowledged and will not be reprocessed."
    )
    return {"status": "rate_limited"}


# Render builds the Vite dashboard before starting FastAPI. Keep this catch-all
# last so API and webhook routes always take priority over the React SPA.
FRONTEND_DIST_DIR = BASE_DIR.parent / "frontend" / "dist"


@app.get("/{frontend_path:path}", include_in_schema=False)
async def serve_frontend(frontend_path: str):
    index_file = FRONTEND_DIST_DIR / "index.html"
    if not index_file.is_file():
        raise HTTPException(status_code=503, detail="Frontend build is unavailable.")

    dist_root = FRONTEND_DIST_DIR.resolve()
    requested_file = (FRONTEND_DIST_DIR / frontend_path).resolve()
    if (
        frontend_path
        and requested_file.is_relative_to(dist_root)
        and requested_file.is_file()
    ):
        return FileResponse(requested_file)

    return FileResponse(index_file)
