"""LLM provider adapters with retry, circuit-breaker, and structured output.

Each adapter wraps a specific LLM API (Anthropic, OpenAI, Google) and
returns parsed JSON responses.  A router dispatches to the correct adapter
based on the ``LLMProvider`` enum.
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import structlog
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.domain.enums import LLMProvider
from app.ports.outbound import LLMPort

logger = structlog.get_logger(__name__)

_RETRY_DECORATOR = retry(
    retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)


class MultiProviderLLMAdapter(LLMPort):
    """Routes LLM calls to the appropriate provider adapter."""

    def __init__(
        self,
        *,
        anthropic_api_key: str = "",
        openai_api_key: str = "",
        google_api_key: str = "",
        timeout: float = 60.0,
    ) -> None:
        self._keys = {
            LLMProvider.ANTHROPIC: anthropic_api_key,
            LLMProvider.OPENAI: openai_api_key,
            LLMProvider.GOOGLE: google_api_key,
        }
        self._timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def invoke(
        self,
        *,
        provider: LLMProvider,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.0,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        api_key = self._keys.get(provider, "")
        if not api_key:
            logger.warning("llm_no_api_key", provider=provider.value)
            return {"error": f"No API key for {provider.value}", "confidence": 0.0}

        if provider == LLMProvider.ANTHROPIC:
            return await self._invoke_anthropic(
                api_key, system_prompt, user_prompt, temperature, max_tokens
            )
        elif provider == LLMProvider.OPENAI:
            return await self._invoke_openai(
                api_key, system_prompt, user_prompt, temperature, max_tokens,
                response_format,
            )
        elif provider == LLMProvider.GOOGLE:
            return await self._invoke_google(
                api_key, system_prompt, user_prompt, temperature, max_tokens
            )
        else:
            return {"error": f"Unknown provider: {provider}", "confidence": 0.0}

    @_RETRY_DECORATOR
    async def _invoke_anthropic(
        self,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        log = logger.bind(provider="anthropic")
        response = await self._client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": max_tokens,
                "temperature": temperature,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_prompt}],
            },
        )
        response.raise_for_status()
        data = response.json()
        text = data.get("content", [{}])[0].get("text", "{}")
        log.debug("anthropic_response_received", tokens=data.get("usage", {}))
        return self._parse_json(text)

    @_RETRY_DECORATOR
    async def _invoke_openai(
        self,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
        response_format: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        log = logger.bind(provider="openai")
        body: dict[str, Any] = {
            "model": "gpt-4o",
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
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        response.raise_for_status()
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        log.debug("openai_response_received", tokens=data.get("usage", {}))
        return self._parse_json(text)

    @_RETRY_DECORATOR
    async def _invoke_google(
        self,
        api_key: str,
        system_prompt: str,
        user_prompt: str,
        temperature: float,
        max_tokens: int,
    ) -> dict[str, Any]:
        log = logger.bind(provider="google")
        response = await self._client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
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
        log.debug("google_response_received")
        return self._parse_json(text)

    @staticmethod
    def _parse_json(text: str) -> dict[str, Any]:
        try:
            return json.loads(text)  # type: ignore[no-any-return]
        except json.JSONDecodeError:
            # Try to extract JSON from markdown code blocks
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
