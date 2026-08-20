import base64
import csv
import io
import json
import os
import uuid
import httpx
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from dotenv import load_dotenv

from local_vision import parse_handwritten_inventory
from uplift_engine import UpliftEngine
from solana_agent import LocalSolanaAgent

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
USER_STATES = {}
CUSTOMER_DATA = []

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN", "vaultagent_local_token")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
META_API_URL = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages" if PHONE_NUMBER_ID else None
HEADERS = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"} if WHATSAPP_TOKEN else {"Content-Type": "application/json"}


def generate_dashboard_url(phone_number: str) -> str:
    base_url = os.getenv("DASHBOARD_BASE_URL", "http://localhost:8443")
    session_token = uuid.uuid4().hex
    USER_STATES[phone_number] = "claiming_reward"
    return f"{base_url.rstrip('/')}/reward?user={phone_number}&token={session_token}"


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


async def process_inventory_image(image_bytes: bytes, sender: str) -> list[dict]:
    local_items = parse_handwritten_inventory(image_bytes)
    if not GEMINI_API_KEY:
        return local_items

    try:
        mime_type = "image/jpeg"
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        text_prompt = (
            "Extract the inventory from this handwritten or printed image. "
            "Return ONLY valid JSON as a list of objects with fields 'item' and 'quantity'. "
            "If you are unsure, use the best estimate and keep the values concise."
        )
        payload = {
            "contents": [{
                "parts": [
                    {"text": text_prompt},
                    {"inline_data": {"mime_type": mime_type, "data": encoded}},
                ]
            }],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            text = data["candidates"][0]["content"]["parts"][0].get("text", "")
            import json
            parsed = json.loads(text)
            if isinstance(parsed, list) and parsed and all(isinstance(item, dict) for item in parsed):
                return [{"item": str(item.get("item", "Unknown")).strip(), "quantity": str(item.get("quantity", "1")).strip()} for item in parsed]
    except Exception as exc:
        print(f"Gemini parsing failed, falling back to local OCR: {exc}")

    return local_items

@app.get("/")
async def home():
    return {"status": "ok", "service": "vault-agent-whatsapp"}

@app.get("/health")
async def healthcheck():
    return {"status": "ok", "verify_token_configured": bool(VERIFY_TOKEN), "solana_configured": bool(os.getenv("SOLANA_PRIVATE_KEY_HEX") or os.getenv("SOLANA_PRIVATE_KEY"))}

@app.get("/api/dashboard")
async def dashboard_summary():
    return build_dashboard_payload()

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
    segment = segment_raw if segment_raw in {"VIP", "Persuadable", "Sure Thing", "Inactive", "Lost Cause"} else (
        "Persuadable" if int(str(health_raw).replace('%', '')) < 60 or int(str(risk_raw).replace('%', '')) > 50 else "VIP"
    )

    try:
        health = int(str(health_raw).replace("%", ""))
    except ValueError:
        health = 50

    try:
        risk_value = int(str(risk_raw).replace("%", ""))
    except ValueError:
        risk_value = 50

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

        return {
            "status": "success",
            "filename": filename,
            "customers": CUSTOMER_DATA,
            "message": f"File {filename} uploaded successfully."
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not process uploaded file: {str(exc)}")

@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN and challenge is not None:
        return PlainTextResponse(str(challenge))

    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def handle_whatsapp_messages(request: Request):
    data = await request.json()

    try:
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0].get("value", {})
        messages = changes.get("messages") or []

        if not messages:
            return {"status": "ignored", "reason": "no message payload"}

        message = messages[0]
        sender = message.get("from")
        message_type = message.get("type")

        if not sender or not message_type:
            return {"status": "ignored", "reason": "missing sender or type"}

        current_state = USER_STATES.get(sender, "idle")

        if message_type == "text":
            body = (message.get("text", {}) or {}).get("body", "").strip()
            if body.lower() in {"claim reward", "reward", "claim"}:
                dashboard_url = generate_dashboard_url(sender)
                await send_message(sender, f"Your secure dashboard is ready: {dashboard_url}\n\nOpen it to confirm your reward and continue onboarding.")
                USER_STATES[sender] = "claiming_reward"
                return {"status": "success", "state": USER_STATES[sender]}

            if current_state == "claiming_reward":
                await send_message(sender, "Tap the claim button or send the reward claim prompt to continue.")
                return {"status": "success", "state": current_state}

            await send_message(sender, "Hi! Reply with 'claim' to open your reward flow or send a photo to complete reverse onboarding.")
            return {"status": "success", "state": "idle"}

        if message_type == "interactive":
            interactive_data = message.get("interactive", {}) or {}
            button_reply = interactive_data.get("button_reply", {}) or {}
            btn_id = button_reply.get("id")

            if btn_id == "claim_reward":
                dashboard_url = generate_dashboard_url(sender)
                USER_STATES[sender] = "claiming_reward"
                await send_message(
                    sender,
                    f"Reward ready. Open this secure dashboard link to continue: {dashboard_url}"
                )
                return {"status": "success", "state": USER_STATES[sender]}

            return {"status": "success", "state": current_state}

        if message_type == "image":
            image_id = (message.get("image", {}) or {}).get("id")
            if not image_id:
                return {"status": "ignored", "reason": "missing image id"}

            USER_STATES[sender] = "reverse_onboarding"
            img_bytes = await download_media(image_id)
            extracted_items = await process_inventory_image(img_bytes, sender)

            if not extracted_items:
                await send_message(sender, "We couldn’t read that image clearly. Please send a sharper photo of the handwritten inventory.")
                return {"status": "success", "state": USER_STATES[sender]}

            summary = "\n".join([f"• {item['item']}: {item['quantity']}" for item in extracted_items])
            claim_amount = float(os.getenv("REWARD_USDC_AMOUNT", "50"))
            recipient_wallet = os.getenv("PAYMENT_RECIPIENT_WALLET")
            payment_status = "pending"

            if recipient_wallet:
                payment_result = await solana_agent.execute_reward_micropayment(
                    recipient_address=recipient_wallet,
                    amount_usdc=claim_amount,
                    payment_reference=f"claim:{sender}",
                )
                payment_status = payment_result.get("status", "processed")

            await send_message(
                sender,
                f"Successfully parsed your inventory and updated the database:\n\n{summary}\n\nReward status: {payment_status}.\nYour RM{claim_amount:.0f} value vault reward is now active."
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

    async with httpx.AsyncClient() as client:
        res = await client.get(f"https://graph.facebook.com/v20.0/{media_id}", headers=HEADERS)
        res.raise_for_status()
        media_url = res.json()["url"]
        img_res = await client.get(media_url, headers=HEADERS)
        img_res.raise_for_status()
        return img_res.content

async def send_message(to_number: str, text: str):
    if not PHONE_NUMBER_ID or not WHATSAPP_TOKEN:
        print("WhatsApp credentials missing; skipping outbound message.")
        return

    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text}
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(META_API_URL, headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json()

