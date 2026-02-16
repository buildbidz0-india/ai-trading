# Technical Deployment Guide

This document outlines the professional deployment strategy for the AI-Native Option Trading Platform, designed for DevOps engineers and technical leads.

## 🏗️ Architecture Overview

The platform follows a decoupled client-server architecture:

1.  **Frontend**: Next.js 14 (App Router) Application.
    -   Hosted on **Vercel Edge Network**.
    -   Connects to Backend via REST/WebSocket APIs.
2.  **Backend**: FastAPI (Python 3.12+) Application.
    -   Primary Deployment: **Vercel Serverless Functions** (MVP/Low-Scale).
    -   Secondary Recommendation: **Containerized Service** (Railway/Render) for high-scale/stateful needs.
    -   Database: PostgreSQL (Cloud-hosted, e.g., Neon, Supabase, or AWS RDS).
    -   Cache: Redis (Cloud-hosted, e.g., Upstash or AWS ElastiCache).

### 🔄 Multi-Provider Rotational API System

The backend implements a resilient `ResilientLLMAdapter` that manages LLM provider quotas.

-   **Rotation Logic**: Round-robin selection with circuit-breaker pattern for failures.
-   **Configuration**:
    -   Providers are configured via Environment Variables.
    -   **Gemini API Key Rotation**: Accepts a *comma-separated list* of keys to distribute load and avoid rate limits.
    -   Format: `GOOGLE_API_KEYS="key1,key2,key3"` (Note the plural naming convention for rotation).

---

## 🚀 Deployment Guide (Vercel Primary)

### Prerequisites
-   Vercel CLI installed (`npm i -g vercel`)
-   GitHub Repository connected to Vercel.
-   Cloud PostgreSQL Database (e.g., Neon).
-   Cloud Redis (e.g., Upstash).

### 1. Backend Deployment (Vercel)

Vercel supports Python runtimes, but requires specific configuration to route API requests to FastAPI.

**A. Configuration (`backend/vercel.json`)**
Create a `vercel.json` in the `backend` directory if it doesn't exist:
```json
{
  "builds": [
    {
      "src": "src/main.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "src/main.py"
    }
  ]
}
```

**B. Deploy via CLI**
```bash
cd backend
vercel
```
*Follow the prompts to link the project.*

**C. Environment Variables**
Configure the following in Vercel Project Settings > Environment Variables:

| Variable | Description | Example |
| :--- | :--- | :--- |
| `DATABASE_URL` | PostgreSQL Connection String | `postgres://user:pass@host:5432/db` |
| `REDIS_URL` | Redis Connection String | `redis://default:pass@host:6379` |
| `GOOGLE_API_KEYS` | **Critical**: Comma-separated list for rotation | `AIzaSy...1,AIzaSy...2,AIzaSy...3` |
| `ANTHROPIC_API_KEY` | Anthropic Key | `sk-ant...` |
| `OPENAI_API_KEY` | OpenAI Key | `sk-proj...` |
| `BROKER_API_KEY` | Broker Integration Key | `...` |

### 2. Frontend Deployment (Vercel)

**A. Configuration**
Ensure `frontend/next.config.ts` (or `.js`) is configured.

**B. Deploy via CLI**
```bash
cd frontend
vercel
```

**C. Environment Variables**
| Variable | Description | Example |
| :--- | :--- | :--- |
| `NEXT_PUBLIC_API_URL` | URL of the deployed Backend | `https://your-backend-project.vercel.app` |

---

## 🛡️ Production Hardening Checklist

-   [ ] **Secrets Management**: Ensure `GOOGLE_API_KEYS` relies on Vercel's encrypted environment storage. Never commit `.env` files.
-   [ ] **CORS Configuration**: Update `backend/src/main.py` CORSMiddleware to allow *only* your frontend domain.
-   [ ] **Database SSL**: Ensure `DATABASE_URL` includes `?sslmode=require` for secure connections.
-   [ ] **Logging**: Use structured logging (JSON) in production. configuring a log drain (e.g., Datadog, Axiom) in Vercel is recommended as ephemeral logs are lost.

---

## ⚖️ Platform Comparison & Recommendation

### Vercel (Current Primary)
-   **Pros**: Excellent DX, specialized for Next.js, zero-config CI/CD, global edge network.
-   **Cons**: Python runtime has "Cold Starts", WebSocket support is limited (serverless limitations), execution timeout limits (usually 10s-60s) can affect long-running AI tasks.

### Alternatives

1.  **Railway / Render (PaaS)**
    -   **Pros**: Full container support (Docker). Ideal for FastAPI. Supports background tasks (Celery) and WebSockets natively. No timeout issues for long AI chains.
    -   **Cons**: Slightly more manual setup than Vercel for Frontend.

2.  **AWS / GCP (Hyperscale)**
    -   **Pros**: Infinite scaling, full control, VPC networking.
    -   **Cons**: High complexity, higher maintenance burden.

### 🏆 Recommendations

| Scenario | Recommended Stack | Rationale |
| :--- | :--- | :--- |
| **MVP / Prototype** | **Vercel (Frontend & Backend)** | Fastest time-to-market. Free tier is generous. API rotation works via simple Env Vars. |
| **Free-Tier Usage** | **Vercel + Neon + Upstash** | All offer generous free tiers. Vercel's Python runtime is sufficient for low-traffic endpoints. |
| **Production / High Scale** | **Vercel (Frontend) + Railway (Backend)** | **Hybrid Approach**. Keep Frontend on Vercel for edge performance. Move Backend to Railway/Render to utilize full Docker containers, enabling WebSockets, long-running AI analysis, and avoiding serverless timeouts. |

## 🔄 CI/CD Pipeline
The repository assumes a Git-based workflow:
1.  **Push to `main`**: Triggers Production deployment.
2.  **Pull Request**: Triggers Preview deployment (Vercel creates unique preview URLs).
3.  **Tests**: Github Actions (`.github/workflows/ci.yml`) run unit tests before allowing merge.
