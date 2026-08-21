# DevLeague Hackathon Project

> AI-Powered Customer Retention Platform with Solana Integration

## 🚀 Quick Start

```bash
# Start both backend and frontend servers
.\scripts\start-dev.bat
```

Then open: **http://localhost:8443**

## 📁 Project Structure

```
DEVLEAGUE HACKATHON/
├── backend/              # Python FastAPI backend
│   ├── main.py          # Main API server
│   ├── solana_agent.py  # Solana blockchain integration
│   ├── uplift_engine.py # Customer retention engine
│   ├── local_vision.py  # Image processing & OCR
│   └── .env.example     # Environment variables template
│
├── frontend/            # React + Vite frontend
│   ├── src/            # Source code
│   │   ├── pages/      # Page components
│   │   ├── lib/        # Utilities (API client)
│   │   └── App.tsx     # Main app component
│   ├── public/         # Static assets
│   └── package.json    # Frontend dependencies
│
├── scripts/            # Development scripts
│   ├── start-dev.bat   # Start both servers
│   └── test-connection.py  # Test backend API
│
├── docs/              # Documentation
│   └── SETUP.md       # Detailed setup guide
│
├── .env.example       # Root environment template
└── requirements.txt   # Python dependencies
```

## 🛠️ Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **Solana** - Blockchain integration for payments
- **Gemini AI** - Image processing & OCR
- **WhatsApp API** - Messaging integration

### Frontend
- **React 19** - UI framework
- **Vite** - Build tool & dev server
- **Tailwind CSS** - Styling
- **React Router** - Navigation
- **Recharts** - Data visualization

## 📋 Features

- **Revenue Command Center** - Real-time dashboard with AI insights
- **Customer Segmentation** - Automatic classification (VIP, Persuadable, etc.)
- **AI Executive Brief** - Automated analysis and recommendations
- **Solana Payments** - Blockchain-based reward distribution
- **WhatsApp Integration** - Conversational onboarding
- **Image Processing** - Handwritten inventory recognition

## 🔧 Development

### Prerequisites
- Python 3.12+
- Node.js 18+
- npm or pnpm

### Manual Setup

**Backend:**
```bash
# Install dependencies
pip install -r requirements.txt

# Start server
cd backend
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Frontend:**
```bash
# Install dependencies
cd frontend
npm install

# Start dev server
npm run dev
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```env
# WhatsApp API
WHATSAPP_TOKEN=your_token
PHONE_NUMBER_ID=your_phone_id

# AI Configuration
GEMINI_API_KEY=your_gemini_key

# Solana Wallet
SOLANA_PRIVATE_KEY_HEX=your_key
PAYMENT_RECIPIENT_WALLET=your_wallet

# Server URLs
DASHBOARD_BASE_URL=http://localhost:8443
```

## 📡 API Endpoints

- `GET /health` - Health check
- `GET /api/dashboard` - Dashboard data
- `GET /api/customers` - Customer directory
- `POST /webhook` - WhatsApp webhook
- `GET /docs` - Interactive API documentation

## 📖 Documentation

See [docs/SETUP.md](docs/SETUP.md) for detailed setup instructions, architecture details, and troubleshooting guide.

## 🧪 Testing

```bash
# Test backend API structure
python scripts\test-connection.py
```

## 🚀 Deployment

1. Build frontend: `cd frontend && npm run build`
2. Set production environment variables
3. Deploy backend with proper CORS configuration
4. Serve frontend from `frontend/dist`

## 📝 License

DevLeague Hackathon Project

## 🤝 Contributing

This is a hackathon project. Contributions and improvements are welcome!

---

**Need Help?** Check [docs/SETUP.md](docs/SETUP.md) for troubleshooting tips.
