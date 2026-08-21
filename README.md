# StayLongerAI

StayLongerAI is a hackathon-ready customer-retention demo built with FastAPI, React, Vite, Twilio WhatsApp, EasyOCR with a Gemini fallback, and an explicitly opt-in Solana reward integration.

The existing dashboard includes customer health, alerts, rewards, reports, customer import, secure reward-claim links, and recent structured inventory extracted from WhatsApp images.

## Project layout

```text
.
├── backend/
│   ├── main.py             # FastAPI routes and WhatsApp workflow
│   ├── local_vision.py     # EasyOCR inventory extraction
│   ├── solana_agent.py     # Demo-safe optional USDC integration
│   ├── uplift_engine.py    # Retention/uplift scoring
│   └── .env.example
├── frontend/               # React + Vite application (port 8443)
├── scripts/
│   ├── start-dev.bat       # Windows setup and launcher
│   └── test-connection.py  # Offline backend contract smoke checks
├── docs/SETUP.md
├── .env.example
└── requirements.txt
```

## Prerequisites

- Python 3.10 or newer (Python 3.12 is recommended)
- Node.js 22 and npm
- ngrok for a public Twilio webhook
- A joined Twilio WhatsApp Sandbox for live WhatsApp testing
- Internet access during the first EasyOCR model download

Twilio, Gemini, and Solana credentials are optional for local UI/API demo mode. Never place credentials in source files or commit a real `.env`.

## Quick start on Windows

Run these commands from the repository root in PowerShell.

### 1. Create the backend environment

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item backend\.env.example backend\.env
```

Edit `backend\.env` locally. For Twilio WhatsApp, set at least:

```env
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_MEDIA_HOSTS=api.twilio.com
TWILIO_VALIDATE_SIGNATURE=false
DASHBOARD_BASE_URL=http://localhost:8443
```

Blank values are intentional placeholders. Use credentials from your own Twilio account. `backend/.env` is ignored by Git.

### 2. Install the frontend

```powershell
cd frontend
npm.cmd install
cd ..
```

### 3. Start the backend

In terminal 1, from the repository root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Start the frontend

In terminal 2:

```powershell
cd frontend
npm.cmd run dev
```

Open:

- Frontend: `http://localhost:8443`
- Backend health: `http://localhost:8000/health`
- FastAPI documentation: `http://localhost:8000/docs`

### Automated Windows launcher

The launcher is working-directory independent. It creates `.venv`, installs dependencies, and opens both servers in separate terminals:

```powershell
.\scripts\start-dev.bat
```

Close both server terminals to stop the stack.

## ngrok and Twilio Sandbox

### Recommended: one tunnel for the full demo

Keep both servers running, then run:

```powershell
ngrok http 8443
```

The Vite development server proxies both `/api` and `/webhook` to FastAPI on port 8000. With an ngrok origin such as `https://example.ngrok-free.app`:

1. Set the Twilio Sandbox incoming-message webhook to `https://example.ngrok-free.app/webhook` using `POST`.
2. Set `DASHBOARD_BASE_URL=https://example.ngrok-free.app` in `backend/.env`.
3. Restart the backend after changing `.env`.
4. Open the ngrok origin to confirm the dashboard loads publicly.

This single public origin lets a phone receive and open the reward link while keeping frontend API requests and the Twilio webhook on one tunnel.

`CORS_ORIGINS` is normally blank for this same-origin proxy flow. Set it to a comma-separated list of exact frontend origins only when a browser calls FastAPI directly from another origin.

If `TWILIO_VALIDATE_SIGNATURE=true`, also set the exact externally configured callback URL:

```env
TWILIO_WEBHOOK_URL=https://example.ngrok-free.app/webhook
```

The scheme, host, path, and any query string must exactly match Twilio's webhook URL. Keep signature validation disabled only for a controlled local demo; enable it for production-facing deployments.

### Alternative: backend-only tunnel

To expose only FastAPI, run:

```powershell
ngrok http 8000
```

Point Twilio at `https://example.ngrok-free.app/webhook`. This preserves inbound WhatsApp testing, but `DASHBOARD_BASE_URL=http://localhost:8443` will not open from a separate phone. Use a reachable LAN/public frontend URL or a second frontend tunnel when the reward page must open on the phone.

Free ngrok URLs can change after restart. Whenever they change, update the Twilio webhook, `DASHBOARD_BASE_URL`, and `TWILIO_WEBHOOK_URL` when signature validation is enabled, then restart the backend.

## Inventory flow

The implemented flow is:

```text
WhatsApp image
  → Twilio POST /webhook
  → authenticated media download with redirects enabled
  → EasyOCR
  → Gemini fallback when local OCR returns no structured items
  → normalized inventory record
  → WhatsApp summary + /api/inventory + dashboard inventory panel
```

EasyOCR initializes lazily. On its first use it may download model data and take longer than later requests. Relevant settings are:

```env
EASYOCR_GPU=false
EASYOCR_DOWNLOAD_ENABLED=true
EASYOCR_MIN_CONFIDENCE=0.15
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.7-flash
```

If EasyOCR is unavailable or cannot find items, Gemini is used when `GEMINI_API_KEY` is configured. Inventory and claim records are intentionally in memory for the hackathon demo and reset when the backend restarts.

## Reward safety

Reward display value and on-chain value are separate:

```env
# UI and WhatsApp copy only
REWARD_DISPLAY_AMOUNT_RM=50

# Live USDC transfer amount only
REWARD_USDC_AMOUNT=50
```

Solana payments default to safe simulation:

```env
SOLANA_LIVE_MODE=false
```

No blockchain transaction is submitted unless `SOLANA_LIVE_MODE=true`, Twilio webhook signature validation is enabled, and the RPC URL, valid private key, USDC mint, and recipient wallet are all configured. A claimed reward can start payment only once. Live mode sends USDC only and never falls back to sending the same numeric amount in SOL.

For a live devnet test, use a dedicated low-value wallet, verify every address, fund the correct USDC token account, and start with a small `REWARD_USDC_AMOUNT`. Never commit a private key.

## Main API contracts

- `GET /health` — service, OCR, Twilio, and reward configuration status
- `GET /api/dashboard` — dashboard payload including recent inventory
- `GET /api/inventory` — `{ inventory: [...], total: number }`
- `GET /api/customers` — customer directory
- `POST /api/customers/import` — bounded CSV, JSON, or TXT import
- `GET /api/rewards/status` — demo/live reward configuration
- `POST /api/rewards/claim` — one-time claim body `{ "token": "..." }`
- `GET /webhook` — simple Twilio endpoint status probe
- `POST /webhook` — Twilio WhatsApp inbound webhook

The `/reward?token=...` frontend page confirms the token through `/api/rewards/claim`. Tokens expire and are single-use within the current backend process.

## Checks

Run backend compile and offline contract checks from the repository root:

```powershell
.\.venv\Scripts\python.exe -m compileall backend scripts
.\.venv\Scripts\python.exe scripts\test-connection.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Run the frontend type and production-build checks:

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run build
```

The smoke checks do not call Twilio, Gemini, ngrok, or Solana.

## Twilio error 63038

Twilio error `63038` means the Sandbox/trial account has exhausted its current provider-enforced rolling message quota (five daily messages on the affected account). It is an external account limitation, not an application bug.

StayLongerAI recognizes this code, logs a clear quota message, acknowledges the incoming webhook, and does not repeatedly retry the blocked outbound message. There is no supported code bypass. Wait for the provider quota window to roll forward or upgrade/request a higher Twilio limit. Do not repeatedly resend test messages while the account is limited.

## End-to-end demo checklist

- [ ] Create `.venv` and install `requirements.txt`.
- [ ] Install frontend packages with `npm.cmd install`.
- [ ] Copy `backend/.env.example` to `backend/.env`; add only your own credentials.
- [ ] Leave `SOLANA_LIVE_MODE=false` unless intentionally testing a fully configured, signature-validated, low-value USDC transfer.
- [ ] Start FastAPI on port 8000 and confirm `/health` returns `status: ok`.
- [ ] Start Vite on port 8443 and confirm the dashboard and navigation still work.
- [ ] Run `ngrok http 8443` for the recommended single-tunnel demo.
- [ ] Put the public `/webhook` URL into the Twilio WhatsApp Sandbox as a `POST` callback.
- [ ] Set `DASHBOARD_BASE_URL` to the same public origin and restart FastAPI.
- [ ] Join the Sandbox from the demo WhatsApp account if it is not already joined.
- [ ] Send `claim`; confirm one outbound reward link is generated.
- [ ] Open the link, claim once, and confirm a second claim is reported as already claimed.
- [ ] Send an inventory image; confirm Twilio media download, OCR/Gemini parsing, and a structured WhatsApp summary.
- [ ] Refresh or wait briefly for the dashboard inventory panel to show the processed record.
- [ ] Confirm `/api/inventory` and `/api/rewards/status` return their documented contracts.
- [ ] If Twilio returns `63038`, treat it as the rolling external quota and stop outbound-message retesting.
- [ ] Run the backend smoke checks, frontend type check, and frontend build.
- [ ] Run `git status --short` in the real Git clone and verify no `.env`, auth token, API key, wallet key, or generated build output is staged.

More troubleshooting and cross-platform commands are in [docs/SETUP.md](docs/SETUP.md).
