# LLM Configuration & API Management

## Rotational API System
The platform utilizes a `ResilientProviderGateway` to manage LLM interactions, ensuring maximum uptime and cost-efficiency.

### Provider Strategy
- **Anthropic (Claude-3.5-Sonnet):** Primary for Quantitative Analysis (The Quant).
- **Google (Gemini-2.0-Flash):** Primary for Market Sentiment Analysis (Market Sensor).
- **OpenAI (GPT-4o):** Primary for Trade Execution (The Executioner).

### Failover & Resilience
- **Priority Failover:** Providers are tried in order of priority (configurable via `.env`).
- **Autonomous Failover:** The gateway automatically rotates to alternative providers upon failure, rate-limits, or timeouts.
- **Key Rotation:** Supports multiple API keys per provider to increase RPM/TPM limits.
- **Circuit Breaking:** Automatically disables degraded providers for a cooldown period.

## Configuration (Environment Variables)
Settings are managed in `backend/.env`.

```env
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_API_KEY=...

# Optional: Multi-key rotation (comma-separated)
ANTHROPIC_API_KEYS=key1,key2
OPENAI_API_KEYS=key1,key2

# Priority (comma-separated)
LLM_PRIORITY_ORDER=google,anthropic,openai
```

## Monitoring
LLM usage, latency, and success rates are tracked and exposed via the `/api/v1/health` endpoint and visualized in Grafana.
