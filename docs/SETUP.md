# DevLeague Hackathon - Setup Guide

## Architecture Overview

This project consists of:
- **Backend**: FastAPI server (Python) running on port 8000
- **Frontend**: React + Vite app running on port 8443
- **Connection**: Vite proxy forwards `/api/*` requests to the backend

## Quick Start

### Option 1: Automated Start (Windows)
```batch
start-dev.bat
```
This will:
1. Install Python dependencies
2. Install Node.js dependencies
3. Start both backend and frontend servers in separate windows

### Option 2: Manual Start

#### Terminal 1 - Backend
```bash
# Install dependencies
pip install -r requirements.txt

# Start the backend server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Terminal 2 - Frontend
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies (first time only)
npm install

# Start the development server
npm run dev
```

## Access Points

- **Frontend**: http://localhost:8443
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

## How It Works

### API Integration

1. **Frontend API Client** (`frontend/src/lib/api.ts`):
   - Uses `fetchJson()` function for all API calls
   - Automatically prefixes requests with `/api`

2. **Vite Proxy** (`frontend/vite.config.ts`):
   ```typescript
   proxy: {
     '/api': {
       target: 'http://localhost:8000',
       changeOrigin: true,
     },
   }
   ```
   - All `/api/*` requests from frontend are proxied to backend
   - Example: Frontend calls `/api/dashboard` → Backend receives `/api/dashboard`

3. **Backend CORS** (`main.py`):
   - Configured to accept requests from frontend origins
   - Allows all methods and headers for development

### API Endpoints

#### Available Endpoints:
- `GET /` - Basic status check
- `GET /health` - Health check with configuration status
- `GET /api/dashboard` - Dashboard summary data
- `GET /api/customers` - Customer directory data
- `GET /webhook` - WhatsApp webhook verification
- `POST /webhook` - WhatsApp message handling

### Frontend Pages

All pages automatically fetch data from the backend:

1. **Dashboard** (`/`) - Fetches from `/api/dashboard`
   - Revenue metrics
   - AI executive brief
   - VIP accounts
   - Customer segments
   - Recent rescues

2. **Customers** (`/customers`) - Fetches from `/api/customers`
   - Customer directory
   - Health scores
   - Segmentation filters

3. **Other Pages**: Placeholders for future development
   - Alerts
   - Rewards
   - Reports

## Environment Variables

### Backend (.env)
```env
# WhatsApp Configuration
WHATSAPP_TOKEN=your_token_here
PHONE_NUMBER_ID=your_phone_id_here
VERIFY_TOKEN=vaultagent_local_token

# AI Configuration
GEMINI_API_KEY=your_gemini_key_here

# Solana Configuration
SOLANA_PRIVATE_KEY_HEX=your_solana_key_here
PAYMENT_RECIPIENT_WALLET=your_wallet_address_here
REWARD_USDC_AMOUNT=50

# Dashboard Configuration
DASHBOARD_BASE_URL=http://localhost:8443
```

### Frontend (frontend/.env)
```env
# Leave empty to use Vite proxy
VITE_API_BASE_URL=
```

## Troubleshooting

### CORS Issues
If you see CORS errors:
1. Ensure backend is running on port 8000
2. Check that frontend is accessing `http://localhost:8443`
3. Verify CORS origins in `main.py` include your frontend URL

### API Not Found
If API calls return 404:
1. Check backend is running: http://localhost:8000/health
2. Verify the endpoint exists: http://localhost:8000/docs
3. Ensure Vite proxy is configured correctly

### Port Already in Use
If ports 8000 or 8443 are busy:
1. Backend: Change port in start command and update `frontend/vite.config.ts`
2. Frontend: Set `PORT` env variable or update `vite.config.ts`

### Connection Refused
1. Ensure both servers are running
2. Check firewall settings
3. Try using `127.0.0.1` instead of `localhost`

## Development Tips

1. **Hot Reload**: Both servers support hot reload
   - Backend: Saves to Python files trigger reload
   - Frontend: Saves to React files trigger instant refresh

2. **API Testing**: Use the interactive docs at http://localhost:8000/docs

3. **Network Inspector**: Check browser DevTools Network tab to see API calls

4. **Logs**: Watch both terminal windows for error messages

## Production Deployment

For production deployment:
1. Set `VITE_API_BASE_URL` to your production API URL
2. Build frontend: `cd frontend && npm run build`
3. Serve frontend from `frontend/dist`
4. Deploy backend with proper CORS origins
5. Use environment-specific configuration

## Dependencies

### Backend
- FastAPI - Web framework
- Uvicorn - ASGI server
- httpx - HTTP client
- python-dotenv - Environment variables
- Pillow & pytesseract - Image processing
- solana & solders - Solana blockchain integration

### Frontend
- React 19 - UI framework
- Vite - Build tool and dev server
- React Router - Navigation
- Tailwind CSS - Styling
- Lucide React - Icons
- Recharts - Charts

## Need Help?

- Check backend logs for API errors
- Check frontend console for client errors
- Verify `.env` files are configured correctly
- Ensure all dependencies are installed
