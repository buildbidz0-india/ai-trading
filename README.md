# AI-Native Option Trading Platform

[![CI](https://github.com/user/Trading_Ai/actions/workflows/ci.yml/badge.svg)](https://github.com/user/Trading_Ai/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An institutional-grade, AI-powered trading platform tailored for the Indian Stock Market (NSE/BSE). Built with modern "Vibe Coding" principles, this platform combines high-frequency trading (HFT) infrastructure with cutting-edge AI orchestration.

## 🚀 Core Capabilities
- **Trio-Agent Intelligence:** Specialized AI Agents (Market Sensor, Quant, Executioner) collaborate to identify and execute high-probability trades.
- **Institutional-Grade UI:** A Microsoft-engineered frontend experience following Fluent Design principles.
- **Resilient AI Infrastructure:** Multi-provider rotational API system with autonomous failover across Anthropic, OpenAI, and Google.
- **Deterministic Guardrails:** Hard-coded safety triggers that intercept and validate every AI-generated order.
- **Real-Time Visualization:** Bloomberg-esque dashboard with live TradingView charts and option chain analysis.

## 🏗️ Technical Architecture
### Frontend (The Face)
- **Framework:** Next.js 15
- **Design:** Fluent Design (Microsoft-grade)
- **Charts:** TradingView Lightweight Charts

### Backend (The Body)
- **Framework:** FastAPI (Python)
- **Database:** PostgreSQL + TimescaleDB
- **State:** Redis (High-speed tick data)

### AI Orchestration (The Brain)
- **Providers:** Anthropic (Claude), OpenAI (GPT), Google (Gemini)
- **Logic:** Mixture of Experts (MoE) for reasoning, math, and execution.

## 🛠️ System Design Philosophy
Built for high-performance and absolute reliability, the system follows Clean Architecture principles, ensuring modularity, scalability, and ease of maintainability.

## 📖 Documentation
- [System Design & Architecture](architecture/system_design.md)
- [LLM Configuration](config/llm_config.md)
- [Technical Deployment Guide](DEPLOYMENT_TECHNICAL.md)
- [Non-Technical Deployment Guide](DEPLOYMENT_NON_TECHNICAL.md)

## ⚖️ Disclaimer
*Trading stocks and options involves significant risk. This software is for educational purposes and should be used with extreme caution in live markets.*
