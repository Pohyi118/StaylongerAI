# Vault Agent: Retention Command Center

A full-stack application for AI-assisted customer retention, WhatsApp workflow automation, and value-based reward claims. The project combines a FastAPI backend with a React + Vite frontend to provide a revenue protection dashboard, customer directory, alerts, reports, and reward management experience.

## Overview

This app is designed to help teams detect at-risk customers, prioritize persuadable accounts, and drive interventions through automated messaging and claim flows. It includes:

- A retention dashboard with KPI cards, risk summaries, and account health insights
- A customer directory with segment filters such as VIP and Persuadable
- WhatsApp webhook handling for reward claims and onboarding flows
- AI-assisted inventory capture from uploaded images
- Solana-based payment flow for rewards and micropayments
- A modern frontend for managing the command center experience

## Architecture

The repository contains:

- `main.py` — FastAPI backend service and webhook handlers
- `uplift_engine.py` — customer uplift/risk classification logic
- `solana_agent.py` — Solana reward payment integration
- `local_vision.py` — local OCR / inventory parsing helper
- `frontend/` — React app for the dashboard UI

## Tech Stack

### Backend
- Python 3.10+
- FastAPI
- Uvicorn
- httpx
- python-dotenv

### Frontend
- React 19
- Vite
- TypeScript
- React Router
- Tailwind CSS
- Lucide React
- Recharts

## Project Structure

```text
.
├── .env.example
├── main.py
├── local_vision.py
├── solana_agent.py
├── uplift_engine.py
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   └── ...
└── README.md
```

## Features

### 1. Revenue Dashboard
The dashboard visualizes:
- revenue protected
- account health
- churn-risk indicators
- rescued accounts
- active alerts
- reward / intervention activity

### 2. Customer Directory
Users can:
- browse company records
- search accounts by name
- filter by segment (All, VIP, Persuadable)
- review churn risk and health score information

### 3. WhatsApp Integration
The backend supports:
- webhook verification (`GET /webhook`)
- message processing (`POST /webhook`)
- reward claim flows via WhatsApp prompts
- secure dashboard links generated for user actions

### 4. Reward Claim Flow
When a customer responds to a WhatsApp message:
- a dashboard URL is generated
- the user is guided to a claim journey
- the native payment logic can invoke Solana reward transfers

### 5. Inventory and Onboarding Automation
Users can send an image for reverse onboarding. The system attempts to extract inventory items from the image and convert them into structured inputs for downstream processing.

## Local Setup

### 1. Clone the project

```bash
git clone <your-repo-url>
cd "DEVLEAGUE HACKATHON"
```

### 2. Configure environment variables

Copy the example file and fill in your real values:

```bash
copy .env.example .env
```

Example values:

```env
WHATSAPP_TOKEN=
PHONE_NUMBER_ID=
VERIFY_TOKEN=vaultagent_local_token
GEMINI_API_KEY=
DASHBOARD_BASE_URL=http://localhost:8443

SOLANA_RPC_URL=https://api.devnet.solana.com
SOLANA_PRIVATE_KEY_HEX=
USDC_MINT=
PAYMENT_RECIPIENT_WALLET=
X402_PAYMENT_URL=
REWARD_USDC_AMOUNT=50
```

> Note: For local development, the frontend is configured to run on port `8443` and calls the backend API through the Vite proxy at `http://localhost:8000`.

### 3. Install Python dependencies

```bash
python -m venv .venv
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
# macOS/Linux
source .venv/bin/activate

pip install fastapi uvicorn httpx python-dotenv
```

### 4. Install frontend dependencies

```bash
cd frontend
npm install
```

## Run the Application

### Start the backend

From the project root:

```bash
python main.py
```

If the project is served via uvicorn directly, use:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Start the frontend

From the `frontend/` directory:

```bash
npm run dev -- --host 0.0.0.0
```

Then open:

- Frontend: http://localhost:8443
- Backend API: http://localhost:8000

## API Endpoints

### Health check

```http
GET /health
```

Returns backend health status and whether key runtime configuration is present.

### Dashboard data

```http
GET /api/dashboard
```

Returns summary metrics, alert metadata, and account segment information.

### Customer directory

```http
GET /api/customers
```

Returns a list of customer records with segment, health, and churn risk data.

### WhatsApp webhook

```http
GET /webhook
POST /webhook
```

Used for WhatsApp verification and inbound message processing.

## Frontend Behavior

The UI includes:
- dashboard navigation
- customer list filtering
- route-based page transitions
- clickable action areas that push users to the next relevant screen
- mobile-friendly card layouts

## Environment Notes

To fully enable production features, set the actual values for:

- `WHATSAPP_TOKEN`
- `PHONE_NUMBER_ID`
- `VERIFY_TOKEN`
- `GEMINI_API_KEY`
- `SOLANA_PRIVATE_KEY_HEX`
- `USDC_MINT`
- `PAYMENT_RECIPIENT_WALLET`
- `X402_PAYMENT_URL`

Without these values, the app still runs in a local demo mode with fallback/mock data.

## Troubleshooting

### Frontend not loading data
- Confirm the backend is running on port `8000`
- Check the Vite proxy in `frontend/vite.config.ts`
- Ensure `DASHBOARD_BASE_URL` matches the frontend URL, usually `http://localhost:8443`

### Webhook verification fails
- Make sure `VERIFY_TOKEN` matches the token configured in the WhatsApp webhook setup
- Check the callback URL in the WhatsApp/Meta developer portal

### Solana payments fail
- Verify your wallet key and RPC settings
- Confirm the wallet has the required funds and correct environment

## Notes

This project is structured as a prototype / hackathon-style application and uses local/mock data and demo flows where live credentials are not configured. The overall goal is to demonstrate a realistic retention and rewards system that can be expanded into production.

## License

This project is provided for local development and demo use. Add a license file if you want to publish or distribute it externally.
