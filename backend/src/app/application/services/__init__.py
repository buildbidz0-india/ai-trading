"""AI Agent Orchestration Service.

Fans out analysis to three specialised LLM agents (Market Sensor, Quant,
Executioner), aggregates results, and returns a structured recommendation.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field

import structlog

from app.domain.enums import AgentRole, LLMProvider
from app.domain.events import AgentAnalysisCompletedEvent
from app.ports.outbound import CachePort, EventBusPort, LLMPort

logger = structlog.get_logger(__name__)


# ── Agent prompts ────────────────────────────────────────────
MARKET_SENSOR_SYSTEM = """You are a Market Sensor AI agent for Indian stock markets (NSE/BSE).
Analyze the provided market context, news, and sentiment data.
Return a JSON object with keys: sentiment (bullish/bearish/neutral),
key_events (list of strings), risk_factors (list of strings),
confidence (float 0-1)."""

QUANT_SYSTEM = """You are a Quantitative Analyst AI agent for options trading.
Analyze the provided option chain data including Greeks, OI, and IV.
Validate Greeks calculations and identify opportunities.
Return a JSON object with keys: recommendation (string),
target_strikes (list of dicts with strike, type, rationale),
max_pain (float), iv_skew (string), confidence (float 0-1)."""

EXECUTIONER_SYSTEM = """You are a Trade Execution AI agent.
Based on the quant analysis and market sentiment, produce a precise trade order.
Return ONLY a valid JSON object with keys:
action (BUY/SELL), symbol (string), exchange (string),
quantity (int), order_type (MARKET/LIMIT), price (float or null),
rationale (string), confidence (float 0-1).
If no trade is recommended, return {"action": "HOLD", "rationale": "..."}."""


@dataclass
class AgentResult:
    """Result from a single agent invocation."""

    role: AgentRole
    provider: LLMProvider
    output: dict  # type: ignore[type-arg]
    confidence: float
    latency_ms: float
    error: str | None = None


@dataclass
class OrchestratedAnalysis:
    """Aggregated output from all agents."""

    symbol: str
    results: list[AgentResult] = field(default_factory=list)
    recommended_action: str | None = None
    overall_confidence: float = 0.0


class AIOrchestrationService:
    """Fan-out to 3 LLM agents, aggregate, and return recommendation."""

    def __init__(
        self,
        llm: LLMPort,
        cache: CachePort,
        event_bus: EventBusPort,
    ) -> None:
        self._llm = llm
        self._cache = cache
        self._event_bus = event_bus

    async def analyze(self, symbol: str, context: str = "") -> OrchestratedAnalysis:
        log = logger.bind(symbol=symbol)
        log.info("orchestration_started")

        # Fetch cached option chain for context
        chain_data = await self._cache.get(f"option_chain:{symbol}")
        chain_context = chain_data or "No option chain data available"

        # Fan-out to all agents concurrently
        results = await asyncio.gather(
            self._invoke_agent(
                role=AgentRole.MARKET_SENSOR,
                provider=LLMProvider.GOOGLE,
                system_prompt=MARKET_SENSOR_SYSTEM,
                user_prompt=f"Analyze market conditions for {symbol}.\n\nContext:\n{context}",
            ),
            self._invoke_agent(
                role=AgentRole.QUANT,
                provider=LLMProvider.ANTHROPIC,
                system_prompt=QUANT_SYSTEM,
                user_prompt=f"Analyze option chain for {symbol}:\n\n{chain_context}",
            ),
            self._invoke_agent(
                role=AgentRole.EXECUTIONER,
                provider=LLMProvider.OPENAI,
                system_prompt=EXECUTIONER_SYSTEM,
                user_prompt=(
                    f"Based on the analysis, determine trade for {symbol}.\n"
                    f"Context: {context}\nChain: {chain_context}"
                ),
            ),
            return_exceptions=True,
        )

        # Collect results
        agent_results: list[AgentResult] = []
        for r in results:
            if isinstance(r, AgentResult):
                agent_results.append(r)
            elif isinstance(r, Exception):
                log.error("agent_failed", error=str(r))

        # Aggregate
        analysis = OrchestratedAnalysis(symbol=symbol, results=agent_results)

        # Extract recommendation from executioner
        for r in agent_results:
            if r.role == AgentRole.EXECUTIONER and r.error is None:
                analysis.recommended_action = r.output.get("action", "HOLD")

        # Overall confidence = weighted average
        if agent_results:
            analysis.overall_confidence = sum(r.confidence for r in agent_results) / len(
                agent_results
            )

        # Publish events
        for r in agent_results:
            await self._event_bus.publish(
                AgentAnalysisCompletedEvent(
                    agent_role=r.role.value,
                    provider=r.provider.value,
                    confidence=r.confidence,
                    latency_ms=r.latency_ms,
                    summary=str(r.output.get("recommendation", r.output.get("action", "")))[:200],
                )
            )

        log.info(
            "orchestration_completed",
            n_agents=len(agent_results),
            confidence=analysis.overall_confidence,
            action=analysis.recommended_action,
        )
        return analysis

    async def _invoke_agent(
        self,
        *,
        role: AgentRole,
        provider: LLMProvider,
        system_prompt: str,
        user_prompt: str,
    ) -> AgentResult:
        log = logger.bind(agent=role.value, provider=provider.value)
        start = time.monotonic()
        try:
            response = await self._llm.invoke(
                provider=provider,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=2048,
                response_format={"type": "json_object"},
            )
            latency = (time.monotonic() - start) * 1000
            confidence = float(response.get("confidence", 0.0))
            log.info("agent_completed", latency_ms=latency, confidence=confidence)
            return AgentResult(
                role=role,
                provider=provider,
                output=response,
                confidence=confidence,
                latency_ms=latency,
            )
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            log.error("agent_error", error=str(exc), latency_ms=latency)
            return AgentResult(
                role=role,
                provider=provider,
                output={},
                confidence=0.0,
                latency_ms=latency,
                error=str(exc),
            )
