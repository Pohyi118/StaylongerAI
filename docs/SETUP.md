# StayLongerAI local demo setup

This guide runs the existing FastAPI backend on port 8000 and the React/Vite frontend on port 8443. Vite proxies `/api` and `/webhook` to FastAPI during development.

## Services

| Service | Local URL | Purpose |
| --- | --- | --- |
| Frontend | `http://localhost:8443` | Dashboard and reward-claim page |
| Backend | `http://localhost:8000` | FastAPI service |
| API docs | `http://localhost:8000/docs` | Interactive endpoint documentation |
| Health | `http://localhost:8000/health` | Dependency/configuration readiness |

Use one backend process for the hackathon demo. Inventory, reward tokens, imported customers, and webhook de-duplication are intentionally stored in memory and reset after a restart.

## Windows automated setup

From the repository root:

```powershell
.\scripts\start-dev.bat
```

The launcher:

1. Resolves the repository root independently of the current directory.
2. Creates `.venv` if needed.
3. installs `requirements.txt` with that environment's Python.
4. Installs frontend dependencies.
5. Opens backend and frontend servers in separate terminals.

If `backend/.env` is absent, the application still starts in local demo mode and the launcher prints a reminder.

## Manual setup

### Windows PowerShell

From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item backend\.env.example backend\.env

cd frontend
npm.cmd install
cd ..
```

Start the backend in terminal 1:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Start the frontend in terminal 2:

```powershell
cd frontend
npm.cmd run dev
```

Using `npm.cmd` avoids the PowerShell execution-policy issue that can block `npm.ps1` on Windows.

### macOS or Linux

From the repository root:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp backend/.env.example backend/.env

cd frontend
npm install
cd ..
```

Start the backend in terminal 1:

```bash
.venv/bin/python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Start the frontend in terminal 2:

```bash
cd frontend
npm run dev
```

## Environment reference

Prefer `backend/.env`. The backend also accepts a root `.env` as a fallback, but one local file is easier to reason about. Existing operating-system environment variables take precedence over `.env` values.

Both example files contain placeholders only. Real `.env` files, credentials, wallet files, and private-key formats are ignored by Git.

| Variable | Default/example | Meaning |
| --- | --- | --- |
| `DASHBOARD_BASE_URL` | `http://localhost:8443` | Origin placed in WhatsApp reward links; use the public frontend origin for a phone demo |
| `REWARD_LINK_TTL_HOURS` | `24` | In-memory reward-token lifetime |
| `CORS_ORIGINS` | blank | Optional comma-separated exact browser origins for direct, non-proxied API calls |
| `TWILIO_ACCOUNT_SID` | blank | Twilio account SID; secret/account-specific |
| `TWILIO_AUTH_TOKEN` | blank | Twilio Auth Token; secret |
| `TWILIO_WHATSAPP_FROM` | Sandbox sender | Twilio WhatsApp sender, including the `whatsapp:` prefix |
| `TWILIO_MEDIA_HOSTS` | `api.twilio.com` | Comma-separated initial authenticated media-host allowlist; keep this narrow |
| `TWILIO_VALIDATE_SIGNATURE` | `false` | Validate `X-Twilio-Signature` when true |
| `TWILIO_WEBHOOK_URL` | blank | Exact public callback URL used for validation; required behind a rewriting proxy |
| `GEMINI_API_KEY` | blank | Optional secret used only when local OCR has no structured result |
| `GEMINI_MODEL` | `gemini-3.7-flash` | Gemini REST model name |
| `EASYOCR_GPU` | `false` | Enable EasyOCR GPU mode only on a configured machine |
| `EASYOCR_DOWNLOAD_ENABLED` | `true` | Allow the first-run EasyOCR model download |
| `EASYOCR_MIN_CONFIDENCE` | `0.15` | Local OCR confidence floor |
| `REWARD_DISPLAY_AMOUNT_RM` | `50` | User-facing RM value in UI and WhatsApp copy |
| `SOLANA_LIVE_MODE` | `false` | Explicit opt-in required for a live USDC transaction |
| `SOLANA_RPC_URL` | Solana devnet | RPC endpoint used by reward status/live mode |
| `SOLANA_PRIVATE_KEY_HEX` | blank | Secret 32-byte seed or 64-byte private key encoded as hex |
| `USDC_MINT` | blank | SPL USDC mint address required for live mode |
| `PAYMENT_RECIPIENT_WALLET` | blank | Recipient wallet required for live mode |
| `REWARD_USDC_AMOUNT` | `50` | On-chain USDC amount; separate from the RM display value |
| `X402_PAYMENT_URL` | blank | Optional x402-protected endpoint |

Do not put `VITE_` client variables around backend credentials. Vite exposes variables prefixed with `VITE_` to browser JavaScript.

## Twilio WhatsApp configuration

Set these account-specific values in `backend/.env`:

```env
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
TWILIO_MEDIA_HOSTS=api.twilio.com
TWILIO_VALIDATE_SIGNATURE=false
```

The Sandbox callback is a `POST` endpoint. `GET /webhook` is only a status probe; Twilio does not use a Meta-style verify token in this project.

### Recommended full-demo tunnel

With backend port 8000 and Vite port 8443 both running:

```powershell
ngrok http 8443
```

For public origin `https://example.ngrok-free.app`:

```env
DASHBOARD_BASE_URL=https://example.ngrok-free.app
```

Configure Twilio's incoming-message callback as:

```text
POST https://example.ngrok-free.app/webhook
```

Vite forwards the webhook to FastAPI and also proxies frontend `/api` calls. Restart FastAPI after changing `.env`.

For production-style signature validation:

```env
TWILIO_VALIDATE_SIGNATURE=true
TWILIO_WEBHOOK_URL=https://example.ngrok-free.app/webhook
```

`TWILIO_WEBHOOK_URL` must exactly match the URL Twilio signs. This explicit setting is important for the one-tunnel route because Vite is a reverse proxy between ngrok and FastAPI. A missing helper/Auth Token or invalid signature is rejected safely.

### Backend-only tunnel

```powershell
ngrok http 8000
```

Use its public `/webhook` URL in Twilio. The frontend remains local, so a reward link using localhost cannot open on another phone. Set `DASHBOARD_BASE_URL` to a separately reachable frontend URL when needed.

When a temporary ngrok URL changes, update all configured public URLs and restart FastAPI.

## WhatsApp flows

### Text reward flow

1. Twilio posts the message to `/webhook`.
2. MessageSid de-duplication prevents repeated processing.
3. `claim`, `claim reward`, or `reward` creates a time-limited token.
4. WhatsApp receives `{DASHBOARD_BASE_URL}/reward?token=...`.
5. The frontend posts the token to `/api/rewards/claim`.
6. Reusing the same token returns `already_claimed`.

### Image inventory flow

1. Twilio sends `MediaUrl0` and its image content type.
2. FastAPI downloads bounded media with Twilio authentication and redirects enabled.
3. EasyOCR attempts local structured extraction.
4. Gemini is called only when local OCR has no usable structured items and an API key exists.
5. Items are normalized to `{ item, quantity }` records.
6. The result appears in the WhatsApp reply, `/api/inventory`, and the dashboard's recent inventory panel.

The first EasyOCR request can be slow while model data downloads. Warm it before presenting the demo by processing a non-sensitive sample image once.

## Solana demo and live modes

The default is non-transactional:

```env
SOLANA_LIVE_MODE=false
REWARD_DISPLAY_AMOUNT_RM=50
REWARD_USDC_AMOUNT=50
```

`REWARD_DISPLAY_AMOUNT_RM` is presentation currency. `REWARD_USDC_AMOUNT` is used only by an explicitly enabled live USDC transfer. They are not assumed to be exchange-rate equivalents.

Live mode requires all of the following:

- `SOLANA_LIVE_MODE=true`
- `TWILIO_VALIDATE_SIGNATURE=true` with the exact public webhook URL
- a valid RPC URL
- a dedicated valid private key
- a valid USDC mint
- a valid recipient wallet
- the correct funded source USDC account

Incomplete or unsigned-webhook configuration returns a truthful demo status and does not submit a transaction. Each claimed reward can start at most one payment attempt, and a failed USDC transfer does not fall back to SOL.

## API response contracts

### Inventory

`GET /api/inventory`:

```json
{
  "inventory": [],
  "total": 0
}
```

Each stored record includes an ID, masked source/sender information, received time, item count, structured items, processor, and payment status.

### Reward status

`GET /api/rewards/status`:

```json
{
  "mode": "demo",
  "configured": false,
  "network": "https://api.devnet.solana.com",
  "asset": "USDC",
  "defaultAmount": 50,
  "reason": "Configuration reason"
}
```

### Reward claim

`POST /api/rewards/claim`:

```json
{
  "token": "token-from-whatsapp-link"
}
```

The response contains `status`, numeric `amount`, `message`, and boolean `demo` fields.

## Verification commands

Backend, from the repository root on Windows:

```powershell
.\.venv\Scripts\python.exe -m compileall backend scripts
.\.venv\Scripts\python.exe scripts\test-connection.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Frontend:

```powershell
cd frontend
npm.cmd run typecheck
npm.cmd run build
```

The backend smoke test validates payloads, route registration, inventory response shape, reward status, one-time reward claims, and idempotent repeated claims without external network calls.

## Troubleshooting

### Twilio error 63038

`63038` is the Twilio Sandbox/trial account's rolling provider quota (currently five daily messages on the affected account). It is not a webhook or application defect. StayLongerAI logs the condition, acknowledges the webhook, and does not repeatedly retry the quota-blocked outbound send.

There is no code bypass. Wait for the rolling provider window or upgrade/request a higher Twilio limit. Continued test sends only consume time and obscure useful logs.

### Twilio returns 403 with signature validation enabled

- Confirm `TWILIO_AUTH_TOKEN` belongs to the configured Account SID.
- Confirm `TWILIO_WEBHOOK_URL` exactly equals Twilio's callback, including HTTPS, host, path, port, and query string.
- Update the value after an ngrok URL changes and restart FastAPI.
- For an isolated local demo only, set validation back to `false` while diagnosing the external callback configuration.

### Reward link opens localhost on a phone

Set `DASHBOARD_BASE_URL` to the ngrok frontend origin from `ngrok http 8443`, then restart FastAPI and request a new claim link. Previously generated links do not change.

### Inventory is not recognized

- Use a sharp, well-lit image with legible item names and quantities.
- Confirm the Twilio media content type starts with `image/`.
- Confirm `/health` reports OCR availability.
- Allow the EasyOCR model download or configure `GEMINI_API_KEY` for fallback.
- Do not log or upload sensitive customer imagery during a public demo.

### Frontend cannot reach the API

- Confirm FastAPI is listening on port 8000.
- Confirm Vite is listening on port 8443.
- Leave `VITE_API_BASE_URL` unset for the local Vite proxy.
- Use the Vite development server—not a static file server—for the documented one-tunnel `/webhook` proxy.
- For a browser calling FastAPI directly from another origin, add that exact origin to the comma-separated `CORS_ORIGINS` value and restart FastAPI.

### Solana remains in demo mode

This is expected unless every live requirement is valid and `SOLANA_LIVE_MODE=true`. Check `/api/rewards/status` for the non-secret configuration reason. Never print the private key while troubleshooting.

## Final demo checklist

- [ ] Backend dependencies are installed inside `.venv`, not the global Python environment.
- [ ] Frontend dependencies are installed and both ports 8000 and 8443 start cleanly.
- [ ] `backend/.env` contains only local credentials and is not staged by Git.
- [ ] `/health` returns `status: ok`; OCR/Gemini and reward mode match expectations.
- [ ] `SOLANA_LIVE_MODE=false` unless a deliberate, low-value live USDC test is authorized.
- [ ] `REWARD_DISPLAY_AMOUNT_RM` and `REWARD_USDC_AMOUNT` are reviewed separately.
- [ ] The recommended `ngrok http 8443` tunnel is running.
- [ ] Twilio points to the current public `/webhook` using `POST`.
- [ ] `DASHBOARD_BASE_URL` matches the public frontend origin.
- [ ] When enabled, `TWILIO_WEBHOOK_URL` exactly matches Twilio's signed callback.
- [ ] The WhatsApp demo account has joined the Sandbox.
- [ ] `claim` produces one public reward link and the claim page confirms it.
- [ ] A second use of the same reward token reports that it was already claimed.
- [ ] An inventory photo produces structured items and updates the dashboard.
- [ ] Duplicate MessageSid delivery does not duplicate processing.
- [ ] A 63038 response is reported as an external rolling quota and is not retried repeatedly.
- [ ] Backend smoke/compile checks, frontend type checks, and the production build pass.
- [ ] `git status --short` shows no `.env`, token, API key, wallet key, or unwanted build output staged.
