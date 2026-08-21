import asyncio
import base64
import csv
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
from fastapi.responses import Response
from dotenv import load_dotenv
from pydantic import BaseModel, Field

try:
    from twilio.request_validator import RequestValidator
except ImportError:  # The app can still run in local demo mode without validation.
    RequestValidator = None

try:
    from .local_vision import local_ocr_available, parse_handwritten_inventory
    from .solana_agent import LocalSolanaAgent
    from .uplift_engine import UpliftEngine
except ImportError:  # Supports running `python backend/main.py` directly.
    from local_vision import local_ocr_available, parse_handwritten_inventory
    from solana_agent import LocalSolanaAgent
    from uplift_engine import UpliftEngine

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env", override=False)
load_dotenv(BASE_DIR.parent / ".env", override=False)

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
PROCESSED_MESSAGE_SIDS: OrderedDict[str, float] = OrderedDict()
MAX_PROCESSED_MESSAGE_SIDS = 5000
MESSAGE_SID_TTL_SECONDS = 24 * 60 * 60
MAX_INVENTORY_RECORDS = 100
TWILIO_SEND_LOCK = asyncio.Lock()
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
META_GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v23.0")
META_GRAPH_BASE_URL = "https://graph.facebook.com"


class RewardClaimRequest(BaseModel):
    token: str = Field(min_length=1, max_length=128)


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


def generate_dashboard_url(phone_number: str) -> str:
    base_url = os.getenv("DASHBOARD_BASE_URL", "http://localhost:8443")
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

@app.get("/")
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

        if status and status.get("mode") == "live" and not TWILIO_VALIDATE_SIGNATURE:
            status["mode"] = "demo"
            status["reason"] = (
                "Live Solana configuration is present, but WhatsApp payments remain "
                "blocked until TWILIO_VALIDATE_SIGNATURE=true."
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


@app.get("/api/inventory")
async def inventory_summary():
    return {
        "inventory": [dict(record) for record in INVENTORY_RECORDS],
        "total": len(INVENTORY_RECORDS),
    }


@app.get("/api/rewards/status")
async def rewards_status():
    return _solana_status()


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
    return {"status": "ok", "provider": "twilio-whatsapp"}


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
    public_url = os.getenv("TWILIO_WEBHOOK_URL") or str(request.url)
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
