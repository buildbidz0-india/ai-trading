# API Reference

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
All endpoints (except health and auth) require a JWT Bearer token:
```
Authorization: Bearer <token>
```

---

## Health & Monitoring

### `GET /health`
System health check with service statuses.

**Response** `200`
```json
{
  "status": "ok",
  "version": "0.1.0",
  "timestamp": "2026-02-16T12:00:00Z",
  "services": {
    "database": "ok",
    "redis": "ok",
    "broker": "ok"
  }
}
```

### `GET /metrics`
Prometheus metrics in text format.

---

## Authentication

### `POST /auth/token`
Issue JWT access + refresh tokens.

**Request**
```json
{ "username": "admin", "password": "password123" }
```

**Response** `200`
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer"
}
```

### `POST /auth/refresh`
Refresh an expired access token.

**Request**
```json
{ "refresh_token": "eyJ..." }
```

---

## Orders

### `GET /orders`
List orders. Query params: `status`, `limit`, `since`.

### `GET /orders/{order_id}`
Get a single order by ID.

### `POST /orders`
Place a new order.

**Request**
```json
{
  "symbol": "NIFTY",
  "exchange": "NFO",
  "side": "BUY",
  "order_type": "LIMIT",
  "product_type": "NRML",
  "quantity": 50,
  "lot_size": 50,
  "price": "150.00",
  "idempotency_key": "unique-key-123"
}
```

**Response** `201`
```json
{ "order_id": "abc123", "status": "PENDING_VALIDATION" }
```

### `DELETE /orders/{order_id}`
Cancel a pending/open order.

---

## Positions

### `GET /positions`
List all open positions with Greeks.

### `POST /positions/sync`
Sync positions from broker.

---

## Trades

### `GET /trades`
List trade history. Query params: `since`, `limit`.

---

## AI Analysis

### `POST /ai/analyze`
Trigger multi-agent AI analysis for a symbol.

**Request**
```json
{
  "symbol": "NIFTY",
  "context": { "market_trend": "bullish" }
}
```

**Response** `200`
```json
{
  "symbol": "NIFTY",
  "agents": [
    {
      "agent_role": "MARKET_SENSOR",
      "provider": "GOOGLE",
      "confidence": 0.85,
      "latency_ms": 1200.5,
      "summary": "Bullish momentum detected..."
    }
  ],
  "recommended_action": "BUY",
  "overall_confidence": 0.82,
  "timestamp": "2026-02-16T12:00:00Z"
}
```

---

## Provider Health (Admin)

### `GET /providers/health`
Get health snapshots for all API providers.

**Response** `200`
```json
[
  {
    "provider_id": "google",
    "status": "healthy",
    "total_requests": 150,
    "success_rate": 0.98,
    "latency_p50_ms": 450.0,
    "circuit_state": "closed",
    "quota_remaining_pct": 72.0
  }
]
```

### `POST /providers/{provider_id}/reset`
Admin reset: clears circuit breaker and quota for the provider.

---

## WebSocket Endpoints

### `WS /ws/ticks`
Real-time market data ticks.

**Subscribe**: `{ "action": "subscribe", "symbols": ["NIFTY", "BANKNIFTY"] }`
**Tick**: `{ "symbol": "NIFTY", "ltp": 24500.50, "timestamp": "..." }`

### `WS /ws/agent-log`
Live AI agent execution log stream.

**Event**: `{ "agent": "MARKET_SENSOR", "status": "running", "message": "..." }`

---

## Error Responses

All errors follow this format:
```json
{
  "detail": "Error description",
  "error_code": "DOMAIN_ERROR_CODE",
  "timestamp": "2026-02-16T12:00:00Z"
}
```

| HTTP Code | Meaning |
|-----------|---------|
| 400 | Validation / domain rule violation |
| 401 | Missing or invalid JWT |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 409 | Conflict (duplicate idempotency key) |
| 422 | Unprocessable entity |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
