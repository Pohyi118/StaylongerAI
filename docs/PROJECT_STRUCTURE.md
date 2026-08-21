# Project Structure

## Overview

This document describes the organized structure of the DevLeague Hackathon project after reorganization.

## Directory Tree

```
DEVLEAGUE HACKATHON/
│
├── backend/                    # Python FastAPI Backend
│   ├── __init__.py            # Package initialization
│   ├── main.py                # FastAPI application & routes
│   ├── solana_agent.py        # Solana blockchain integration
│   ├── uplift_engine.py       # Customer retention AI engine
│   ├── local_vision.py        # OCR & image processing
│   └── .env.example           # Backend environment template
│
├── frontend/                   # React + Vite Frontend
│   ├── src/
│   │   ├── pages/             # Page components
│   │   │   ├── Dashboard.tsx  # Main dashboard
│   │   │   ├── Customers.tsx  # Customer directory
│   │   │   ├── Alerts.tsx     # Alerts page
│   │   │   ├── Rewards.tsx    # Rewards page
│   │   │   └── Reports.tsx    # Reports page
│   │   ├── lib/               # Utilities
│   │   │   └── api.ts         # API client
│   │   ├── App.tsx            # Main app & routing
│   │   ├── main.tsx           # Entry point
│   │   └── index.css          # Global styles
│   ├── public/                # Static assets
│   ├── .env                   # Frontend environment config
│   ├── package.json           # Dependencies
│   ├── vite.config.ts         # Vite configuration
│   └── tsconfig.json          # TypeScript config
│
├── scripts/                    # Development Scripts
│   ├── start-dev.bat          # Start both servers (Windows)
│   └── test-connection.py     # Test backend API
│
├── docs/                       # Documentation
│   ├── SETUP.md               # Setup & installation guide
│   ├── API.md                 # API endpoint documentation
│   └── PROJECT_STRUCTURE.md   # This file
│
├── .env.example               # Root environment template
├── .gitignore                 # Git ignore rules
├── README.md                  # Project overview
└── requirements.txt           # Python dependencies
```

## File Purposes

### Backend Files

- **main.py** - Core FastAPI application with all API routes and WhatsApp webhook handlers
- **solana_agent.py** - Handles Solana blockchain transactions for reward payments
- **uplift_engine.py** - AI-powered customer retention scoring and segmentation
- **local_vision.py** - Image processing using OCR for handwritten inventory parsing

### Frontend Files

- **App.tsx** - Main application component with routing and navigation
- **pages/** - Each page corresponds to a route in the application
- **lib/api.ts** - Centralized API client for making backend requests
- **vite.config.ts** - Vite configuration including proxy setup for API calls

### Scripts

- **start-dev.bat** - One-click script to install dependencies and start both servers
- **test-connection.py** - Validates backend API structure and endpoints

### Documentation

- **SETUP.md** - Complete setup guide with troubleshooting
- **API.md** - Detailed API endpoint documentation
- **PROJECT_STRUCTURE.md** - This organizational overview

## Configuration Files

### Environment Variables

#### Backend (.env in backend/ directory)
```env
WHATSAPP_TOKEN=your_token
PHONE_NUMBER_ID=your_phone_id
VERIFY_TOKEN=vaultagent_local_token
GEMINI_API_KEY=your_gemini_key
SOLANA_PRIVATE_KEY_HEX=your_key
PAYMENT_RECIPIENT_WALLET=your_wallet
REWARD_USDC_AMOUNT=50
DASHBOARD_BASE_URL=http://localhost:8443
```

#### Frontend (.env in frontend/ directory)
```env
VITE_API_BASE_URL=
```
(Empty because we use Vite proxy)

### Python Dependencies (requirements.txt)
- fastapi - Web framework
- uvicorn - ASGI server
- python-dotenv - Environment variables
- httpx - HTTP client
- pillow - Image processing
- pytesseract - OCR
- solana/solders - Blockchain

### Node Dependencies (frontend/package.json)
- react - UI framework
- vite - Build tool
- react-router-dom - Routing
- tailwindcss - Styling
- recharts - Charts

## How Components Connect

```
┌─────────────────┐
│   Frontend      │
│  (Port 8443)    │
│                 │
│  Pages make API │
│  calls via      │
│  /api/*         │
└────────┬────────┘
         │
         │ Vite Proxy
         │
         ▼
┌─────────────────┐
│   Backend       │
│  (Port 8000)    │
│                 │
│  FastAPI serves │
│  /api/dashboard │
│  /api/customers │
└────────┬────────┘
         │
         ├─────► Solana Agent → Blockchain
         │
         ├─────► Uplift Engine → AI Scoring
         │
         ├─────► Local Vision → OCR
         │
         └─────► WhatsApp API → Messaging
```

## Development Workflow

1. **Start**: Run `.\scripts\start-dev.bat`
2. **Backend**: Runs on http://localhost:8000
3. **Frontend**: Runs on http://localhost:8443
4. **API Calls**: Frontend → Vite Proxy → Backend
5. **Hot Reload**: Both servers support live reloading

## Best Practices

### Adding New Backend Endpoints
1. Add route function in `backend/main.py`
2. Update `docs/API.md` with documentation
3. Test with `backend/test-connection.py` if applicable

### Adding New Frontend Pages
1. Create component in `frontend/src/pages/`
2. Add route in `frontend/src/App.tsx`
3. Add navigation link if needed

### Making API Calls
Always use the centralized API client:
```typescript
import { fetchJson } from "@/lib/api";
const data = await fetchJson("/api/endpoint");
```

## Deployment Checklist

- [ ] Build frontend: `cd frontend && npm run build`
- [ ] Set production environment variables
- [ ] Update CORS origins in backend
- [ ] Configure production database (if applicable)
- [ ] Set up reverse proxy (nginx/caddy)
- [ ] Enable HTTPS
- [ ] Configure Solana mainnet keys
- [ ] Test all API endpoints

## Maintenance

### Regular Updates
- Keep dependencies updated with `pip install -U -r requirements.txt`
- Update npm packages with `npm update` in frontend/
- Review security advisories

### Monitoring
- Check backend logs for errors
- Monitor API response times
- Track Solana transaction success rates
- Monitor WhatsApp webhook deliverability

## Support

For issues or questions:
1. Check [SETUP.md](SETUP.md) for troubleshooting
2. Review [API.md](API.md) for endpoint details
3. Test backend with `python scripts/test-connection.py`
4. Check browser console for frontend errors
