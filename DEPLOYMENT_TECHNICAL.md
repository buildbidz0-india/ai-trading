# Technical Deployment Guide

This guide provides technical instructions for deploying the AI Trading Platform in a production-ready environment.

## 📋 Prerequisites
- **Operating System:** Linux (Ubuntu 22.04+ recommended) or Windows with WSL2.
- **Docker & Docker Compose:** Required for containerized deployment.
- **Python 3.12+:** For local development and automation scripts.
- **Node.js 20+:** For frontend development and build.
- **Tools:** Git, `make` (optional), `httpx` (for health checks).

## 🛠️ Environment Setup

### 1. Clone the Repository
```bash
git clone https://github.com/user/Trading_Ai.git
cd Trading_Ai
```

### 2. Configuration Management
The system uses `.env` files for configuration. Copy the example files and populate them with your credentials.

#### Backend Configuration (`backend/.env`)
```env
# Database & Redis
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/trading_platform
REDIS_URL=redis://redis:6379/0

# LLM API Keys
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key
GOOGLE_API_KEY=your_key

# Broker Credentials (Dhan/Shoonya/Zerodha)
BROKER_API_KEY=your_key
BROKER_SECRET=your_secret
```

#### Frontend Configuration (`frontend/.env.local`)
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🚀 Infrastructure Requirements

### Containerization
The easiest way to deploy the entire stack is using Docker Compose.

```bash
cd backend
docker-compose up -d --build
```
This will start:
- **FastAPI App:** Port 8000
- **PostgreSQL/TimescaleDB:** Port 5432
- **Redis:** Port 6379
- **Prometheus:** Port 9090
- **Grafana:** Port 3001 (Admin: `admin/admin`)

### CI/CD Integration
The platform includes a GitHub Actions workflow (`.github/workflows/ci.yml`) that handles:
- Linting (Ruff, ESLint).
- Type checking (MyPy, TypeScript).
- Unit and Integration tests.
- Docker build verification.

## 📈 Scaling & Monitoring

### Scaling Considerations
- **Backend:** The FastAPI app is stateless and can be scaled horizontally behind a load balancer (Nginx/Traefik).
- **Database:** TimescaleDB is used for high-volume time-series data. Ensure appropriate volume sizing for tick data storage.
- **LLM Rate-Limiting:** Use multiple API keys and adjust `rpm_limit`/`tpm_limit` in `backend/src/app/adapters/outbound/llm/__init__.py`.

### Monitoring Setup
- **Metrics:** Metrics are exposed at `/metrics` for Prometheus.
- **Dashboards:** Access Grafana at `http://localhost:3001` to view pre-configured trading and system health dashboards.
- **Logging:** Structured JSON logs are output to `stdout`, suitable for aggregation via ELK or Loki.

## 🛡️ Production Hardening
- Change default database passwords.
- Use HTTPS for all API and Frontend communication.
- Restrict access to Prometheus and Grafana ports via firewall.
- Implement specialized "Kill Switch" logic in broker adapters for emergency stops.
