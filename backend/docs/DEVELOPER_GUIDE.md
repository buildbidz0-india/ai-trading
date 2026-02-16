# Developer Guide

## Prerequisites

- **Python 3.12+**
- **PostgreSQL 16+** (or TimescaleDB)
- **Redis 7+**
- **Docker** (recommended for services)

## Quick Start

### 1. Clone & Setup
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -e ".[dev,test]"
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your API keys and database URLs
```

### 3. Start Services
```bash
docker compose up -d postgres redis
```

### 4. Run Migrations
```bash
alembic upgrade head
```

### 5. Start Server
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. Open Docs
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

---

## Architecture

```
src/app/
├── domain/           # Pure business logic (entities, value objects, services)
├── ports/            # Interface definitions (inbound + outbound)
├── application/      # Use cases (commands, queries, orchestration)
├── adapters/
│   ├── inbound/      # REST API, WebSocket handlers
│   └── outbound/     # Database, Redis, broker, LLM, market data
├── shared/           # Cross-cutting (security, middleware, observability, providers)
├── config.py         # Pydantic Settings
├── dependencies.py   # DI container (singletons + factories)
└── main.py           # FastAPI app factory
```

### Key Principles
- **Hexagonal Architecture**: Domain has zero knowledge of infrastructure
- **Domain-Driven Design**: Rich entities enforce business invariants
- **Dependency Inversion**: All adapters implement port interfaces
- **Type Safety**: Full mypy strict mode, no `Any` escape hatches in domain

---

## Broker Configuration

Set `BROKER_PROVIDER` in `.env`:

| Value | Adapter | Notes |
|-------|---------|-------|
| `paper` | `PaperBrokerAdapter` | Default — simulated fills, no real money |
| `dhan` | `DhanBrokerAdapter` | Requires `DHAN_CLIENT_ID`, `DHAN_ACCESS_TOKEN` |
| `zerodha` | `ZerodhaBrokerAdapter` | Requires `ZERODHA_API_KEY`, `ZERODHA_API_SECRET` |
| `shoonya` | `ShoonyaBrokerAdapter` | Requires `SHOONYA_USER_ID`, `SHOONYA_PASSWORD`, `SHOONYA_API_KEY` |

---

## Provider Resilience

The LLM system uses a resilient gateway with:
- **4 routing strategies**: `priority_failover`, `round_robin`, `weighted`, `least_latency`
- **Circuit breakers**: auto-open on failures, half-open probing after cooldown
- **Quota management**: sliding-window RPM/TPM tracking
- **Key rotation**: multiple API keys per provider for rate limit distribution

Configure via `.env`:
```env
LLM_ROUTING_STRATEGY=priority_failover
LLM_PROVIDER_PRIORITY=google,anthropic,openai
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
GOOGLE_RPM=60
```

---

## Testing

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/ -v

# Integration tests (requires running services)
pytest tests/integration/ -v

# With coverage
pytest --cov=app --cov-report=term-missing
```

---

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one step
alembic downgrade -1

# View current state
alembic current
```

---

## Docker Deployment

```bash
# Full stack
docker compose up -d

# Rebuild after changes
docker compose up -d --build app
```

Services in docker-compose:
- `app` — FastAPI on port 8000
- `postgres` — TimescaleDB on port 5432
- `redis` — Redis on port 6379
- `prometheus` — Metrics on port 9090
- `grafana` — Dashboards on port 3000

---

## Code Style

- **Formatter**: `ruff format .`
- **Linter**: `ruff check . --fix`
- **Type checker**: `mypy src/`
- **Pre-commit**: `pre-commit run --all-files`
