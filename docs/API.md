# API Documentation

## Base URL
- Development: `http://localhost:8000`
- Frontend Proxy: `/api` (proxied to backend)

## Endpoints

### Health Check

#### GET /health
Check if the backend server is running and properly configured.

**Response:**
```json
{
  "status": "ok",
  "verify_token_configured": true,
  "solana_configured": true
}
```

---

### Dashboard API

#### GET /api/dashboard
Get dashboard summary data including revenue metrics, customer segments, and AI insights.

**Response:**
```json
{
  "title": "Revenue Command Center",
  "status": "AI Protection Active",
  "totalRevenueProtectedLabel": "RM184,320",
  "weekGrowth": "+12% this week",
  "roi": "8.4×",
  "executiveBrief": "AI analysis of customer retention...",
  "metrics": [
    {
      "label": "Accounts Rescued",
      "value": "47",
      "trend": "+4"
    }
  ],
  "chartData": [
    {
      "name": "1",
      "revenue": 120000
    }
  ],
  "alert": {
    "tag": "Emergency",
    "title": "Sudden drop in user activity detected.",
    "message": "Possible competitor move...",
    "activityDrop": "-37%",
    "affectedUsers": 2391
  },
  "vipAccounts": [...],
  "segments": [...],
  "rescues": [...]
}
```

---

### Customers API

#### GET /api/customers
Get customer directory with health scores and segmentation.

**Response:**
```json
{
  "customers": [
    {
      "id": 1,
      "name": "Acme Corp",
      "plan": "Enterprise",
      "mrr": "RM12,460",
      "health": 31,
      "risk": "87%",
      "segment": "VIP",
      "status": "Human Alert",
      "icon": "Crown",
      "color": "text-brand",
      "bg": "bg-brand/10",
      "border": "border-brand/20"
    }
  ]
}
```

---

### WhatsApp Webhook

#### GET /webhook
Verify WhatsApp webhook configuration.

**Query Parameters:**
- `hub.mode` - Should be "subscribe"
- `hub.verify_token` - Verification token
- `hub.challenge` - Challenge string to return

**Response:**
Returns the challenge string if verification succeeds.

---

#### POST /webhook
Handle incoming WhatsApp messages.

**Request Body:**
WhatsApp webhook payload (handled automatically by Meta)

**Response:**
```json
{
  "status": "success",
  "state": "idle"
}
```

**Message Types Supported:**
- **text** - Text messages (supports "claim reward" command)
- **image** - Image messages (triggers inventory OCR)
- **interactive** - Button interactions

---

## Frontend API Client

The frontend uses a simple API client located at `frontend/src/lib/api.ts`:

```typescript
import { fetchJson } from "@/lib/api";

// Usage
const data = await fetchJson<DashboardData>("/api/dashboard");
```

All `/api/*` requests are automatically proxied to the backend server via Vite's proxy configuration.

---

## Error Handling

All endpoints return appropriate HTTP status codes:
- **200** - Success
- **403** - Forbidden (webhook verification failed)
- **404** - Not Found
- **500** - Internal Server Error

Error responses include a detail message:
```json
{
  "detail": "Error description"
}
```

---

## CORS Configuration

The backend accepts requests from:
- `http://localhost:8443`
- `http://localhost:3000`
- `http://127.0.0.1:8443`
- `http://127.0.0.1:3000`
- `http://0.0.0.0:8443`
- `http://0.0.0.0:3000`

All methods and headers are allowed for development.

---

## Interactive Documentation

FastAPI provides automatic interactive API documentation:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
