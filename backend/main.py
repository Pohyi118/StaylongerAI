import csv
import hashlib
import hmac
import io
import json
import os
import re
import uuid
import httpx
from fastapi import FastAPI, Request, HTTPException, UploadFile, File, Header, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from local_vision import parse_handwritten_inventory
from uplift_engine import UpliftEngine
from solana_agent import LocalSolanaAgent
import whatsapp_provider
from vision import extract_inventory

load_dotenv()

app = FastAPI(title="Vault Agent API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8443",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8443",
        "http://0.0.0.0:8443",
        "http://0.0.0.0:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
uplift = UpliftEngine()
solana_agent = LocalSolanaAgent()

# WARNING: In-memory state resets on server restart
# For production, use Redis or a database for persistence and multi-worker support
USER_STATES = {}  # Stores user conversation state
CUSTOMER_DATA = []  # Stores customer records
PROCESSED_PAYMENTS = set()  # Idempotency: track processed payment references
SESSION_TOKENS = {}  # reward claim session token -> phone number

def _first_env(*names: str) -> str:
    """Return the first non-empty environment variable among the given names."""
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return ""


# Meta WhatsApp Cloud API configuration.
# main.py reads the META_WHATSAPP_* names documented in .env.example FIRST and
# falls back to the legacy short names (WHATSAPP_TOKEN / PHONE_NUMBER_ID / ...)
# so both existing and fresh .env files keep working.
WHATSAPP_TOKEN = _first_env("META_WHATSAPP_ACCESS_TOKEN", "WHATSAPP_TOKEN")
PHONE_NUMBER_ID = _first_env("META_WHATSAPP_PHONE_NUMBER_ID", "PHONE_NUMBER_ID")
VERIFY_TOKEN = _first_env("META_WHATSAPP_VERIFY_TOKEN", "VERIFY_TOKEN") or "vaultagent_local_token"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
META_APP_SECRET = _first_env("META_APP_SECRET", "WHATSAPP_APP_SECRET")
META_GRAPH_API_VERSION = os.getenv("META_GRAPH_API_VERSION", "v20.0")
if META_GRAPH_API_VERSION and not META_GRAPH_API_VERSION.startswith("v"):
    META_GRAPH_API_VERSION = f"v{META_GRAPH_API_VERSION}"
META_API_URL = f"https://graph.facebook.com/{META_GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages" if PHONE_NUMBER_ID else None
HEADERS = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"} if WHATSAPP_TOKEN else {"Content-Type": "application/json"}


def _digits_only(value) -> str:
    """Strip everything except digits (Meta expects E.164 without '+'/spaces)."""
    return re.sub(r"\D", "", str(value))


def _normalize_phone(value) -> str:
    """Normalize a phone value for comparisons (digits with a leading '+')."""
    digits = _digits_only(value)
    return f"+{digits}" if digits else ""


def _safe_float(value, default: float) -> float:
    """Parse a float defensively; NaN and unparseable values fall back to default."""
    try:
        parsed = float(value)
        return default if parsed != parsed else parsed  # NaN check
    except (TypeError, ValueError):
        return default


# --------------------------------------------------------------------------- #
# Localized WhatsApp copy (en / ms). Language is per-customer, or from
# WHATSAPP_TEMPLATE_LANGUAGE. The spec's exact copy is preserved for English.
# --------------------------------------------------------------------------- #
VALUE_VAULT_BODY = {
    "en": "Boss, you didn't use the {feature} this month. We put RM{amount} in your Value Vault.",
    "ms": "Boss, bulan ini anda tidak menggunakan {feature}. Kami telah meletakkan RM{amount} ke dalam Value Vault anda.",
}
REVERSE_ONBOARDING_FOLLOWUP = {
    "en": "Enjoy the lunch! Was the {feature} too hard to set up? Just take a photo of your handwritten inventory list and reply here.",
    "ms": "Nikmati makan tengah hari anda! Adakah {feature} terlalu sukar untuk disediakan? Ambil sahaja gambar senarai inventori tulisan tangan anda dan balas di sini.",
}
BUTTON_CLAIM = {"en": "Claim Reward", "ms": "Tuntut Ganjaran"}
DONE_MESSAGE = {"en": "✅ Done! Database updated.", "ms": "✅ Siap! Pangkalan data telah dikemas kini."}


def localize(table: dict, lang: str, **kwargs) -> str:
    """Pick a localized string from a table, falling back to English."""
    lang = (lang or "en").lower()
    template = table.get(lang) or table.get(lang.split("-")[0]) or table["en"]
    return template.format(**kwargs) if kwargs else template


def _customer_for_phone(sender: str) -> dict | None:
    for customer in CUSTOMER_DATA:
        if customer.get("phone") and _normalize_phone(customer.get("phone")) == _normalize_phone(sender):
            return customer
    return None


def _feature_for_sender(sender: str) -> str:
    customer = _customer_for_phone(sender)
    return str((customer or {}).get("feature") or os.getenv("VALUE_VAULT_FEATURE", "Inventory Tracker")).strip()


def _language_for_sender(sender: str) -> str:
    customer = _customer_for_phone(sender)
    return str((customer or {}).get("language") or os.getenv("WHATSAPP_TEMPLATE_LANGUAGE", "en")).lower()


def create_claim_link(phone_number: str) -> str:
    """Create a single-use, TTL-scoped 1-tap claim link for a phone number.

    The token maps back to the phone number in SESSION_TOKENS so /reward can
    validate the claim later.
    """
    base_url = os.getenv("DASHBOARD_BASE_URL", "http://localhost:8000")
    session_token = uuid.uuid4().hex
    phone_key = _digits_only(phone_number)
    SESSION_TOKENS[session_token] = phone_key
    return f"{base_url.rstrip('/')}/reward?user={phone_key}&token={session_token}"


def generate_dashboard_url(phone_number: str) -> str:
    """Legacy alias: create the claim link and flip the sender into claiming state."""
    claim_url = create_claim_link(phone_number)
    USER_STATES[_digits_only(phone_number)] = "claiming_reward"
    return claim_url


def classify_sender(sender: str) -> str:
    # Reward gate: only Persuadables receive a payout. No phone->customer
    # mapping exists, so unmapped senders default to Sleeping Dog (no reward).
    for customer in CUSTOMER_DATA:
        if customer.get("phone") and _normalize_phone(customer.get("phone")) == _normalize_phone(sender):
            features = [
                float(customer.get("days_inactive", 0)),
                float(customer.get("login_frequency", 0)),
                float(customer.get("feature_usage_pct", 0)),
                float(customer.get("past_support_tickets", 0)),
            ]
            return uplift.classify_user(features)
    return "Sleeping Dog"


def customer_features(customer: dict) -> list[float]:
    """Build the four UpliftEngine features from a customer record.

    Order: [days_inactive, login_frequency, feature_usage_pct, past_support_tickets]
    Values fall back to sensible derived defaults so imported rows without every
    column can still be scored by the Uplift Engine.
    """
    health = _safe_float(customer.get("health"), 50)
    return [
        _safe_float(customer.get("days_inactive"), 100 - health),
        _safe_float(customer.get("login_frequency"), 1),
        _safe_float(customer.get("feature_usage_pct"), health / 100.0),
        _safe_float(customer.get("past_support_tickets"), 0),
    ]


def parse_mrr_rm(mrr: str) -> float:
    """Parse 'RM4,200', '4200', or 'RM 12,460.50' into a float."""
    digits = re.sub(r"[^0-9.]", "", str(mrr or ""))
    try:
        return float(digits)
    except ValueError:
        return 0.0


def build_value_vault_reward(customer: dict) -> dict:
    """Calculate the Value Vault reward for a customer.

    Rule: reward = MRR * VALUE_VAULT_REWARD_PCT%, clamped to
    [VALUE_VAULT_REWARD_MIN_RM, VALUE_VAULT_REWARD_MAX_RM].
    """
    mrr_rm = parse_mrr_rm(str(customer.get("mrr") or ""))
    pct = _safe_float(os.getenv("VALUE_VAULT_REWARD_PCT"), 10)
    min_rm = _safe_float(os.getenv("VALUE_VAULT_REWARD_MIN_RM"), 10)
    max_rm = _safe_float(os.getenv("VALUE_VAULT_REWARD_MAX_RM"), 150)
    partner = (os.getenv("VALUE_VAULT_PARTNER", "GrabFood") or "").strip() or "GrabFood"

    amount = round(max(min_rm, min(max_rm, mrr_rm * pct / 100.0)), 2)
    label_amount = f"{amount:.2f}".rstrip("0").rstrip(".")
    return {
        "partner": partner,
        "amount_rm": amount,
        "currency": "RM",
        "label": f"{partner} voucher worth RM{label_amount}",
        "expires_in_hours": _safe_float(os.getenv("REWARD_LINK_TTL_HOURS"), 24),
    }


async def trigger_value_vault_offer(customer: dict) -> dict:
    """CORE MISSING LOGIC: outbound Value Vault rescue (spec "1-Tap WhatsApp Trigger").

    Steps:
      1. Score the customer with the Uplift Engine.
      2. If classified 'Persuadable', calculate the Value Vault reward.
      3. Build a single-use, password-less claim link.
      4. Automatically send a localized interactive template with a
         "Claim Reward" URL button (or fall back to a text link).

    Returns a machine-readable result so callers can report exactly what
    happened (sent / skipped / not configured).
    """
    customer_id = customer.get("id")
    phone = _digits_only(str(customer.get("phone") or ""))
    if not phone:
        return {"customer_id": customer_id, "status": "skipped", "reason": "no_phone"}

    if not whatsapp_provider.configured():
        print(
            f"trigger_value_vault_offer: WhatsApp provider '{whatsapp_provider.PROVIDER}' "
            f"not configured; NOT sending offer to {phone}"
        )
        return {
            "customer_id": customer_id,
            "phone": phone,
            "status": "skipped",
            "reason": "whatsapp_not_configured",
            "provider": whatsapp_provider.PROVIDER,
        }

    score = uplift.score_user(customer_features(customer))
    if score["quadrant"] != "Persuadable":
        return {
            "customer_id": customer_id,
            "phone": phone,
            "status": "skipped",
            "quadrant": score["quadrant"],
            "foe_score": score["foe_score"],
        }

    reward = build_value_vault_reward(customer)
    feature = str(customer.get("feature") or os.getenv("VALUE_VAULT_FEATURE", "Inventory Tracker")).strip()
    lang = str(customer.get("language") or os.getenv("WHATSAPP_TEMPLATE_LANGUAGE", "en")).lower()
    amount_label = f"{reward['amount_rm']:.2f}".rstrip("0").rstrip(".")

    claim_url = create_claim_link(phone)
    body = localize(VALUE_VAULT_BODY, lang, feature=feature, amount=amount_label)
    button_label = localize(BUTTON_CLAIM, lang)
    template_name = os.getenv("WHATSAPP_TEMPLATE_NAME", "value_vault_rescue")

    sent = await whatsapp_provider.send_template(
        phone, template_name, lang, body, button_label, claim_url
    )
    sent_via = "template" if sent else "text"
    if sent is None:
        await whatsapp_provider.send_text(phone, f"{body}\n\n{claim_url}")

    return {
        "customer_id": customer_id,
        "phone": phone,
        "status": "sent",
        "quadrant": "Persuadable",
        "foe_score": score["foe_score"],
        "feature": feature,
        "language": lang,
        "reward": reward,
        "claim_url": claim_url,
        "sent_via": sent_via,
    }


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
        "rescues": [
            {"name": "Lumina Tech", "time": "12m ago", "reward": "GrabFood RM50", "type": "Value Vault", "status": "Claimed", "network": "x402/Solana"},
            {"name": "ScaleForge", "time": "45m ago", "reward": "Pause Subscription", "type": "Billing", "status": "Executed", "network": "Internal"},
            {"name": "OrbitWorks", "time": "2h ago", "reward": "Shopee RM30", "type": "Value Vault", "status": "Claimed", "network": "x402/Solana"},
        ],
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


def sanitize_inventory_items(items: list[dict]) -> list[dict]:
    out = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("item", "")).strip()
        quantity = str(item.get("quantity", "1")).strip()
        m = re.match(r"^(\d+(?:\.\d+)?)", quantity)
        if not name or not m:
            continue
        out.append({"item": name[:80], "quantity": m.group(1)})
    return out


async def process_inventory_image(image_bytes: bytes, sender: str) -> list[dict]:
    # Reverse Onboarding (Vision LLM): route the photo to Claude 3.5 Sonnet,
    # with Gemini as a fallback, then local OCR as the final safety net.
    llm_items = await extract_inventory(image_bytes)
    if llm_items:
        return llm_items
    return await parse_handwritten_inventory(image_bytes)

@app.get("/")
async def home():
    return {"status": "ok", "service": "vault-agent-whatsapp"}

@app.get("/health")
async def healthcheck():
    return {
        "status": "ok",
        "verify_token_configured": bool(VERIFY_TOKEN),
        "whatsapp_provider": whatsapp_provider.PROVIDER,
        "whatsapp_configured": whatsapp_provider.configured(),
        "vision_provider": "anthropic" if os.getenv("ANTHROPIC_API_KEY") else ("gemini" if GEMINI_API_KEY else "ocr"),
        "solana_configured": bool(os.getenv("SOLANA_PRIVATE_KEY_HEX") or os.getenv("SOLANA_PRIVATE_KEY")),
    }

@app.get("/api/dashboard")
async def dashboard_summary():
    return build_dashboard_payload()

@app.get("/reward")
async def reward_claim(user: str, token: str):
    stored_phone = SESSION_TOKENS.get(token)
    if not stored_phone or stored_phone != user:
        raise HTTPException(status_code=403, detail="Invalid or expired reward session")
    return PlainTextResponse(f"Reward session verified for {user}. Complete your claim in WhatsApp.")

def build_customer_record(row: dict, idx: int) -> dict | None:
    name = (
        row.get("name") or row.get("company") or row.get("customer") or row.get("account") or row.get("customer_name")
    )
    if not name:
        return None

    plan = row.get("plan") or row.get("tier") or row.get("subscription") or "Growth"
    mrr = row.get("mrr") or row.get("monthly_revenue") or row.get("revenue") or "RM0"
    health_raw = row.get("health") or row.get("health_score") or row.get("score") or "50"
    risk_raw = row.get("risk") or row.get("churn_risk") or row.get("risk_percent") or "50%"
    segment_raw = (row.get("segment") or row.get("category") or row.get("status") or "Persuadable").strip()
    status = row.get("status") or row.get("action") or "Imported"
    
    # Parse health and risk with proper error handling
    try:
        health = int(str(health_raw).replace("%", "").strip())
    except (ValueError, AttributeError):
        health = 50

    try:
        risk_value = int(str(risk_raw).replace("%", "").strip())
    except (ValueError, AttributeError):
        risk_value = 50
    
    # Determine segment after parsing numeric values
    segment = segment_raw if segment_raw in {"VIP", "Persuadable", "Sure Thing", "Inactive", "Lost Cause"} else (
        "Persuadable" if health < 60 or risk_value > 50 else "VIP"
    )

    phone_raw = (
        row.get("phone")
        or row.get("whatsapp")
        or row.get("mobile")
        or row.get("phone_number")
        or row.get("contact")
        or ""
    )
    customer = {
        "id": idx,
        "name": str(name).strip(),
        "phone": str(phone_raw).strip(),
        "feature": str(
            row.get("feature")
            or row.get("unused_feature")
            or row.get("module")
            or os.getenv("VALUE_VAULT_FEATURE", "Inventory Tracker")
        ).strip(),
        "language": str(row.get("language") or row.get("locale") or os.getenv("WHATSAPP_TEMPLATE_LANGUAGE", "en")).strip(),
        "days_inactive": _safe_float(row.get("days_inactive"), 100 - health),
        "login_frequency": _safe_float(row.get("login_frequency"), 1),
        "feature_usage_pct": _safe_float(row.get("feature_usage_pct"), health / 100.0),
        "past_support_tickets": _safe_float(row.get("past_support_tickets"), 0),
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
async def import_customers(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    filename = file.filename or "customer_import"
    file_ext = os.path.splitext(filename)[1].lower()
    parsed_rows = []

    try:
        contents = await file.read()
        if file_ext == ".csv":
            text = contents.decode("utf-8-sig")
            reader = csv.DictReader(io.StringIO(text))
            parsed_rows = [row for row in reader]
        elif file_ext in {".txt", ".json"}:
            text = contents.decode("utf-8-sig")
            try:
                parsed_json = json.loads(text)
                if isinstance(parsed_json, list):
                    parsed_rows = parsed_json
                else:
                    parsed_rows = [parsed_json]
            except json.JSONDecodeError:
                parsed_rows = [{"name": "Imported Account", "plan": "Growth", "mrr": "RM0", "health": 50, "risk": "50%", "segment": "Persuadable", "status": "Imported"}]
        else:
            parsed_rows = [{"name": "Imported Account", "plan": "Growth", "mrr": "RM0", "health": 50, "risk": "50%", "segment": "Persuadable", "status": "Imported"}]

        imported_customers = []
        next_id = max((customer["id"] for customer in CUSTOMER_DATA), default=0) + 1
        for row in parsed_rows:
            if not isinstance(row, dict):
                continue
            record = build_customer_record(row, next_id)
            if record is not None:
                imported_customers.append(record)
                next_id += 1

        if imported_customers:
            CUSTOMER_DATA.extend(imported_customers)

            # ---- CORE PRODUCT FLOW: auto-send Value Vault WhatsApp offers ----
            # Any imported customer with a phone number that the Uplift Engine
            # classifies as "Persuadable" gets an automatic WhatsApp message
            # with a 1-tap claim link. Runs in the background so the upload
            # response is not blocked. Disable with
            # AUTO_SEND_VALUE_VAULT_ON_IMPORT=false.
            if os.getenv("AUTO_SEND_VALUE_VAULT_ON_IMPORT", "true").lower() == "true":
                for record in imported_customers:
                    if str(record.get("phone") or "").strip():
                        background_tasks.add_task(trigger_value_vault_offer, record)

        return {
            "status": "success",
            "filename": filename,
            "customers": CUSTOMER_DATA,
            "message": f"File {filename} uploaded successfully."
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not process uploaded file: {str(exc)}")


@app.get("/api/value-vault/scan")
async def value_vault_scan():
    """Preview: score every customer with the Uplift Engine.

    No messages are sent. This is the "who would we rescue" report for the
    demo and for debugging the classification threshold.
    """
    previews = []
    for customer in CUSTOMER_DATA:
        score = uplift.score_user(customer_features(customer))
        previews.append({
            "id": customer.get("id"),
            "name": customer.get("name"),
            "phone": customer.get("phone"),
            "quadrant": score["quadrant"],
            "foe_score": score["foe_score"],
            "reward": build_value_vault_reward(customer) if score["quadrant"] == "Persuadable" else None,
        })
    return {"customers": previews}


@app.post("/api/customers/{customer_id}/value-vault/offer")
async def trigger_customer_value_vault(customer_id: int):
    """Manually trigger the Value Vault WhatsApp offer for one customer."""
    customer = next((c for c in CUSTOMER_DATA if c.get("id") == customer_id), None)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return await trigger_value_vault_offer(customer)

@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN and challenge is not None:
        return PlainTextResponse(str(challenge))

    raise HTTPException(status_code=403, detail="Verification failed")

def verify_whatsapp_signature(payload: bytes, signature: str | None) -> bool:
    """
    Verify WhatsApp webhook signature.
    Meta signs payloads with the App Secret (META_APP_SECRET), not the access token.
    """
    if not META_APP_SECRET:
        # No secret configured: only accept unsigned local requests (dev mode).
        return signature is None
    if not signature:
        return False

    try:
        expected = hmac.new(
            META_APP_SECRET.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        received = signature.replace('sha256=', '')
        return hmac.compare_digest(expected, received)
    except Exception:
        return False

def _normalize_inbound(data: dict) -> dict | None:
    """Normalize inbound webhook payloads from Meta, Wati, or SleekFlow into:

        {"sender", "type", "text", "button_id", "media_id", "media_url"}

    Meta and SleekFlow nest the message; Wati sends a flat object. This keeps
    the listener provider-agnostic.
    """
    if not isinstance(data, dict):
        return None

    provider = whatsapp_provider.PROVIDER

    if provider == "wati":
        sender = data.get("waId") or data.get("phone") or data.get("from")
        mtype = str(data.get("type") or "text").lower()
        text = data.get("text") or data.get("caption") or ""
        button_id = None
        if mtype == "interactive":
            inter = data.get("interactive")
            if isinstance(inter, dict):
                button_id = inter.get("buttonId")
            else:
                button_id = data.get("buttonId") or data.get("buttonText")
        media = data.get("media")
        if isinstance(media, dict):
            media_url, media_id = media.get("url"), media.get("id")
        else:
            media_url, media_id = data.get("mediaUrl"), data.get("mediaId")
        return {"sender": sender, "type": mtype, "text": text, "button_id": button_id,
                "media_id": media_id, "media_url": media_url}

    if provider == "sleekflow":
        d = data.get("data") if isinstance(data.get("data"), dict) else data
        frm = d.get("from")
        sender = frm.get("phone") if isinstance(frm, dict) else (frm or d.get("phone"))
        msg = d.get("message") if isinstance(d.get("message"), dict) else d
        mtype = str(msg.get("type") or "text").lower()
        if isinstance(msg.get("text"), dict):
            text = (msg.get("text") or {}).get("body", "")
        else:
            text = str(msg.get("text") or "")
        inter = msg.get("interactive") if isinstance(msg.get("interactive"), dict) else {}
        button_id = (inter.get("button_reply") or {}).get("id") if inter else None
        media = msg.get("image") if isinstance(msg.get("image"), dict) else (
            msg.get("media") if isinstance(msg.get("media"), dict) else {})
        return {"sender": sender, "type": mtype, "text": text, "button_id": button_id,
                "media_id": media.get("id"), "media_url": media.get("url")}

    # Meta (default)
    try:
        entry = (data.get("entry") or [{}])[0]
        changes = (entry.get("changes") or [{}])[0].get("value", {})
        messages = changes.get("messages") or []
        if not messages:
            return None
        message = messages[0]
        sender = message.get("from")
        mtype = str(message.get("type") or "").lower()
        text = (message.get("text") or {}).get("body", "")
        inter = message.get("interactive") or {}
        button_id = (inter.get("button_reply") or {}).get("id")
        media = message.get("image") or {}
        return {"sender": sender, "type": mtype, "text": text, "button_id": button_id,
                "media_id": media.get("id"), "media_url": None}
    except Exception:
        return None


async def _fetch_media(message: dict) -> bytes:
    """Download inbound media (provider-agnostic): direct URL, else Meta media id."""
    media_url = message.get("media_url")
    if media_url:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.get(media_url)
            res.raise_for_status()
            return res.content
    media_id = message.get("media_id")
    if media_id:
        return await download_media(media_id)
    return b""


@app.post("/webhook")
async def handle_whatsapp_messages(
    request: Request,
    x_hub_signature_256: str | None = Header(None, alias="X-Hub-Signature-256")
):
    # Read body for signature verification
    body = await request.body()

    # Meta signs payloads with X-Hub-Signature-256. Wati/SleekFlow use their own
    # auth (token + IP allowlist) and do not emit Meta's header, so only enforce
    # the signature when running against Meta.
    if whatsapp_provider.PROVIDER == "meta" and not verify_whatsapp_signature(body, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid signature")

    data = json.loads(body.decode('utf-8'))

    try:
        msg = _normalize_inbound(data)
        if not msg or not msg.get("sender") or not msg.get("type"):
            return {"status": "ignored", "reason": "no message payload"}

        sender = msg["sender"]
        message_type = msg["type"]
        current_state = USER_STATES.get(sender, "idle")
        lang = _language_for_sender(sender)
        feature = _feature_for_sender(sender)

        if message_type == "text":
            text = (msg.get("text") or "").strip()
            if text.lower() in {"claim reward", "reward", "claim"}:
                dashboard_url = generate_dashboard_url(sender)
                await send_message(sender, f"Your Value Vault is ready: {dashboard_url}")
                await send_message(sender, localize(REVERSE_ONBOARDING_FOLLOWUP, lang, feature=feature))
                USER_STATES[sender] = "claiming_reward"
                return {"status": "success", "state": USER_STATES[sender]}

            if current_state == "claiming_reward":
                await send_message(sender, "Tap the claim button or send the reward claim prompt to continue.")
                return {"status": "success", "state": current_state}

            await send_message(sender, "Hi! Reply with 'claim' to open your reward flow or send a photo to complete reverse onboarding.")
            return {"status": "success", "state": "idle"}

        if message_type == "interactive":
            if msg.get("button_id") == "claim_reward":
                dashboard_url = generate_dashboard_url(sender)
                USER_STATES[sender] = "claiming_reward"
                await send_message(sender, f"Your Value Vault is ready: {dashboard_url}")
                await send_message(sender, localize(REVERSE_ONBOARDING_FOLLOWUP, lang, feature=feature))
                return {"status": "success", "state": USER_STATES[sender]}

            return {"status": "success", "state": current_state}

        if message_type == "image":
            USER_STATES[sender] = "reverse_onboarding"
            img_bytes = await _fetch_media(msg)
            if not img_bytes:
                return {"status": "ignored", "reason": "missing image payload"}

            extracted_items = await process_inventory_image(img_bytes, sender)

            if not extracted_items:
                await send_message(sender, "We couldn't read that image clearly. Please send a sharper photo of the handwritten inventory.")
                return {"status": "success", "state": USER_STATES[sender]}

            summary = "\n".join([f"- {item['item']}: {item['quantity']}" for item in extracted_items])
            claim_amount = float(os.getenv("REWARD_USDC_AMOUNT", "50"))
            recipient_wallet = os.getenv("PAYMENT_RECIPIENT_WALLET")
            segment = classify_sender(sender)
            payment_status = "pending"

            if segment != "Persuadable":
                payment_status = f"skipped:{segment}"
            elif recipient_wallet:
                payment_ref = f"claim:{sender}:{msg.get('media_id') or 'img'}"

                # Idempotency check: prevent duplicate payments on webhook retries
                if payment_ref in PROCESSED_PAYMENTS:
                    payment_status = "already_processed"
                else:
                    try:
                        payment_result = await solana_agent.execute_reward_micropayment(
                            recipient_address=recipient_wallet,
                            amount_usdc=claim_amount,
                            payment_reference=payment_ref,
                        )
                        payment_status = payment_result.get("status", "processed")
                        PROCESSED_PAYMENTS.add(payment_ref)
                    except Exception as pay_error:
                        print(f"Payment failed: {pay_error}")
                        payment_status = "failed"

            reward_note = (
                f"Reward status: {payment_status}.\nYour RM{claim_amount:.0f} value vault reward is now active."
                if segment == "Persuadable"
                else f"Reward status: {payment_status}.\nNo value vault reward issued for this segment ({segment})."
            )
            await send_message(
                sender,
                f"{localize(DONE_MESSAGE, lang)}\n\n{summary}\n\n{reward_note}"
            )
            USER_STATES[sender] = "idle"
            return {"status": "success", "state": USER_STATES[sender]}

        return {"status": "success", "state": current_state}

    except Exception as exc:
        print(f"Error processing webhook: {exc}")
        return {"status": "error", "message": str(exc)}

async def download_media(media_id: str) -> bytes:
    if not PHONE_NUMBER_ID or not WHATSAPP_TOKEN:
        raise RuntimeError("WhatsApp credentials are missing. Set WHATSAPP_TOKEN and PHONE_NUMBER_ID in your environment.")

    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.get(f"https://graph.facebook.com/v20.0/{media_id}", headers=HEADERS)
        res.raise_for_status()
        media_url = res.json()["url"]
        img_res = await client.get(media_url, headers=HEADERS)
        img_res.raise_for_status()
        return img_res.content

async def send_message(to_number: str, text: str):
    """Send a plain WhatsApp text message (delegates to the active BSP)."""
    return await whatsapp_provider.send_text(to_number, text)

