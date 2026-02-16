"""LLM provider adapter — backed by the ResilientProviderGateway.

Each provider-specific HTTP call is a pure function.  The gateway
handles rotation, failover, circuit breaking, quota, key rotation,
and health tracking autonomously.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import structlog

from app.domain.enums import LLMProvider
from app.ports.outbound import LLMPort
from app.shared.providers.gateway import ResilientProviderGateway
from app.shared.providers.types import ProviderConfig, RoutingStrategy

logger = structlog.get_logger(__name__)


def build_provider_configs(
    *,
    anthropic_api_key: str = "",
    openai_api_key: str = "",
    google_api_key: str = "",
    anthropic_api_keys: str = "",
    openai_api_keys: str = "",
    google_api_keys: str = "",
    openai_base_url: str = "https://api.openai.com/v1",
    anthropic_model: str = "claude-3-5-sonnet-20240620",
    openai_model: str = "gpt-4o",
    google_model: str = "gemini-2.0-flash",
    anthropic_rpm: int = 50,
    openai_rpm: int = 60,
    google_rpm: int = 60,
    anthropic_tpm: int = 0,
    openai_tpm: int = 0,
    google_tpm: int = 0,
    timeout_s: float = 60.0,
    cb_failure_threshold: int = 5,
    cb_cooldown_s: float = 30.0,
    priority_order: str = "google,anthropic,openai",
) -> list[ProviderConfig]:
    """Build ProviderConfig list from settings values."""

    def _parse_keys(multi: str, single: str) -> tuple[str, ...]:
        """Merge comma-separated multi-key string with single key."""
        keys: list[str] = []
        if multi:
            keys.extend(k.strip() for k in multi.split(",") if k.strip())
        if single and single not in keys:
            keys.append(single.strip())
        return tuple(keys)

    # Parse priority order
    priority_map: dict[str, int] = {}
    for idx, name in enumerate(priority_order.split(",")):
        priority_map[name.strip().lower()] = idx + 1

    configs = [
        ProviderConfig(
            provider_id="anthropic",
            api_keys=_parse_keys(anthropic_api_keys, anthropic_api_key),
            priority=priority_map.get("anthropic", 10),
            weight=3,
            rpm_limit=anthropic_rpm,
            tpm_limit=anthropic_tpm,
            timeout_s=timeout_s,
            cb_failure_threshold=cb_failure_threshold,
            cb_cooldown_s=cb_cooldown_s,
            metadata={"model": anthropic_model, "api_version": "2023-06-01"},
        ),
        ProviderConfig(
            provider_id="openai",
            api_keys=_parse_keys(openai_api_keys, openai_api_key),
            priority=priority_map.get("openai", 10),
            weight=3,
            rpm_limit=openai_rpm,
            tpm_limit=openai_tpm,
            timeout_s=timeout_s,
            cb_failure_threshold=cb_failure_threshold,
            cb_cooldown_s=cb_cooldown_s,
            metadata={"model": openai_model, "base_url": openai_base_url},
        ),
        ProviderConfig(
            provider_id="google",
            api_keys=_parse_keys(google_api_keys, google_api_key),
            priority=priority_map.get("google", 10),
            weight=3,
            rpm_limit=google_rpm,
            tpm_limit=google_tpm,
            timeout_s=timeout_s,
            cb_failure_threshold=cb_failure_threshold,
            cb_cooldown_s=cb_cooldown_s,
            metadata={"model": "gemini-2.0-flash" if google_model == "gemini-2.0-flash" else google_model},
        ),
    ]

    return configs


class ResilientLLMAdapter(LLMPort):
    """LLM adapter with autonomous failover, rotation, and health tracking.

    Replaces the old ``MultiProviderLLMAdapter``.  The caller can request
    a *preferred* provider, but the gateway will transparently fail over
    to alternatives if the preferred provider is unavailable.
    """

    def __init__(
        self,
        provider_configs: list[ProviderConfig],
        *,
        routing_strategy: RoutingStrategy = RoutingStrategy.PRIORITY_FAILOVER,
        timeout: float = 60.0,
        backoff_base: float = 0.5,
        backoff_max: float = 8.0,
    ) -> None:
        self._client = httpx.AsyncClient(timeout=timeout)
        self._gateway = ResilientProviderGateway(
            provider_configs,
            strategy=routing_strategy,
            backoff_base=backoff_base,
            backoff_max=backoff_max,
        )

    @property
    def gateway(self) -> ResilientProviderGateway:
        """Expose gateway for health inspection / admin reset."""
        return self._gateway

    async def invoke(
        self,
        *,
        provider: LLMProvider | None = None,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Invoke an LLM — provider is now a *soft preference*, not a hard requirement."""

        preferred = provider.value if provider else None

        async def _call(cfg: ProviderConfig, api_key: str) -> dict[str, Any]:
            print(f"DEBUG: _call cfg metadata={cfg.metadata}")
            if cfg.provider_id == "anthropic":
                return await self._invoke_anthropic(
                    api_key, system_prompt, user_prompt, temperature, max_tokens,
                    model=cfg.metadata.get("model", "claude-sonnet-4-20250514"),
                )
            elif cfg.provider_id == "openai":
                return await self._invoke_openai(
                    api_key, system_prompt, user_prompt, temperature, max_tokens,
                    response_format,
                    model=cfg.metadata.get("model", "gpt-4o"),
                    base_url=cfg.metadata.get("base_url", "https://api.openai.com/v1"),
                )
            elif cfg.provider_id == "google":
                return await self._invoke_google(
                    api_key, system_prompt, user_prompt, temperature, max_tokens,
                    model=cfg.metadata.get("model", "gemini-2.0-flash"),
                )
            else:
                raise ValueError(f"Unknown provider: {cfg.provider_id}")

        return await self._gateway.execute(
            _call,
            estimated_tokens=max_tokens,
            preferred_provider=preferred,
        )

    # ── Provider HTTP calls (pure, no retry logic) ───────────
    async def _invoke_anthropic(
        self,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        *,
        model: str = "claude-sonnet-4-20250514",
    ) -> dict[str, Any]:
        response = await self._client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": model,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()
        text = data.get("content", [{}])[0].get("text", "{}")
        return self._parse_json(text)

    async def _invoke_openai(
        self,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        response_format: dict[str, Any] | None = None,
        *,
        model: str = "gpt-4o",
        base_url: str = "https://api.openai.com/v1",
        base_url: str = "https://api.openai.com/v1",
    ) -> dict[str, Any]:
        print(f"DEBUG: _invoke_openai called with base_url={base_url}")
        body: dict[str, Any] = {
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if response_format:
            body["response_format"] = response_format
        response = await self._client.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        return self._parse_json(text)

    async def _invoke_google(
        self,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        *,
        model: str = "gemini-2.0-flash",
    ) -> dict[str, Any]:
        response = await self._client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}",
            headers={"Content-Type": "application/json"},
            json={
                "system_instruction": {"parts": [{"text": system_prompt}]},
                "contents": [{"parts": [{"text": user_prompt}]}],
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                    "responseMimeType": "application/json",
                },
            },
        )
        response.raise_for_status()
        data = response.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "{}")
        )
        return self._parse_json(text)

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        try:
            return json.loads(text)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            if "```json" in text:
                start = text.index("```json") + 7
                end = text.index("```", start)
                return json.loads(text[start:end].strip())  # type: ignore[no-any-return]
            if "```" in text:
                start = text.index("```") + 3
                end = text.index("```", start)
                return json.loads(text[start:end].strip())  # type: ignore[no-any-return]
            return {"raw_text": text, "confidence": 0.0}

    async def close(self) -> None:
        await self._client.aclose()


# ── Backward compatibility alias ─────────────────────────────
MultiProviderLLMAdapter = ResilientLLMAdapter
