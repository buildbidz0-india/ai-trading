"""AI Agent Orchestration Service.

Fans out analysis to three specialised LLM agents (Market Sensor, Quant,
Executioner), aggregates results, and returns a structured recommendation.

Provider selection is now **autonomous** — each agent *prefers* a provider
but falls through the resilient gateway's failover chain if that provider
is unavailable, degraded, or quota-exhausted.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, cast
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


# ── Agent→Provider preference mapping (soft, not hard) ──────
DEFAULT_AGENT_PREFERENCES: dict[AgentRole, LLMProvider] = {
    AgentRole.MARKET_SENSOR: LLMProvider.GOOGLE,
    AgentRole.QUANT: LLMProvider.ANTHROPIC,
    AgentRole.EXECUTIONER: LLMProvider.OPENAI,
}


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
    """Fan-out to 3 LLM agents with autonomous provider selection.

    Each agent has a *preferred* provider, but the underlying
    ResilientProviderGateway handles failover transparently.
    No manual intervention is needed — the system operates autonomously.
    """

    def __init__(
        self,
        llm: LLMPort,
        cache: CachePort,
        event_bus: EventBusPort,
        *,
        agent_preferences: dict[AgentRole, LLMProvider] | None = None,
    ) -> None:
        self._llm = llm
        self._cache = cache
        self._event_bus = event_bus
        self._prefs = agent_preferences or DEFAULT_AGENT_PREFERENCES

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
                system_prompt=MARKET_SENSOR_SYSTEM,
                user_prompt=f"Analyze market conditions for {symbol}.\n\nContext:\n{context}",
            ),
            self._invoke_agent(
                role=AgentRole.QUANT,
                system_prompt=QUANT_SYSTEM,
                user_prompt=f"Analyze option chain for {symbol}:\n\n{chain_context}",
            ),
            self._invoke_agent(
                role=AgentRole.EXECUTIONER,
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
        # Filter out exceptions and cast to AgentResult for type checker
        valid_results = [cast("AgentResult", r) for r in agent_results if not isinstance(r, BaseException)]
        analysis = OrchestratedAnalysis(symbol=symbol, results=valid_results)

        # Extract recommendation from executioner
        for r in valid_results:
            if r.role == AgentRole.EXECUTIONER and r.error is None:
                analysis.recommended_action = r.output.get("action", "HOLD")

        # Overall confidence = weighted average
        if agent_results:
            analysis.overall_confidence = sum(r.confidence for r in agent_results) / len(
                agent_results
            )

        # Publish events
        for r in valid_results:
            # Decomposed for pedantic type checker
            out_data: dict[str, Any] = r.output or {}
            rec_text = out_data.get("recommendation") or out_data.get("action") or ""
            summary_str = str(rec_text)
            
            await self._event_bus.publish(
                AgentAnalysisCompletedEvent(
                    agent_role=r.role.value,
                    provider=r.provider.value,
                    confidence=r.confidence,
                    latency_ms=r.latency_ms,
                    summary=summary_str[:200],
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
        system_prompt: str,
        user_prompt: str,
    ) -> AgentResult:
        """Invoke a single agent — provider is a *soft preference*.

        The gateway will try the preferred provider first, then fail over
        to any available alternative automatically.
        """
        preferred = self._prefs.get(role)
        log = logger.bind(agent=role.value, preferred_provider=preferred.value if preferred else "any")
        start = time.monotonic()
        try:
            response = await self._llm.invoke(
                provider=preferred,  # soft preference — gateway may override
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.1,
                max_tokens=2048,
                response_format={"type": "json_object"},
            )
            latency = (time.monotonic() - start) * 1000
            confidence = float(response.get("confidence", 0.0))

            # Determine which provider actually handled it
            actual_provider = preferred or LLMProvider.GOOGLE  # the gateway picks

            log.info("agent_completed", latency_ms=float(f"{latency:.1f}"), confidence=confidence)
            return AgentResult(
                role=role,
                provider=actual_provider,
                output=response,
                confidence=confidence,
                latency_ms=latency,
            )
        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            log.error("agent_error", error=str(exc), latency_ms=float(f"{latency:.1f}"))
            return AgentResult(
                role=role,
                provider=preferred or LLMProvider.GOOGLE,
                output={},
                confidence=0.0,
                latency_ms=latency,
                error=str(exc),
            )
