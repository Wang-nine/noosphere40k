"""OpenAI-compatible provider (TECHNICAL_SPEC §8, §14; E-02).

Calls any OpenAI-compatible ``/chat/completions`` endpoint (cloud or local)
and parses structured output into the requested Pydantic model using
``response_format`` json_schema when supported. Network retries are handled
here; the application layer may repair a structured response at most once.
API key is never logged; requests/responses are sanitized before audit.
"""

from __future__ import annotations

from typing import Any

import httpx

from noosphere40k.domain.errors import (
    ProviderSchemaError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from noosphere40k.llm.base import Message, ProviderHealth

DEFAULT_TIMEOUT = 45.0
MAX_RETRIES = 2


class OpenAICompatibleProvider:
    """Structured-output provider for OpenAI-compatible endpoints (E-02)."""

    provider_id = "openai_compatible"

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        api_key: str,
        timeout_seconds: float = DEFAULT_TIMEOUT,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._api_key = api_key
        self.timeout_seconds = timeout_seconds
        self._client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(timeout_seconds),
        )

    @property
    def api_key_present(self) -> bool:
        return bool(self._api_key)

    async def generate_structured(
        self,
        *,
        messages: list[Message],
        response_model: type[Any],
        timeout_seconds: float,
        request_metadata: dict[str, str] | None = None,
    ) -> Any:
        url = f"{self.base_url}/chat/completions"
        json_schema = self._build_json_schema(response_model)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [m.model_dump() for m in messages],
            "temperature": 0.3,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "schema": json_schema,
                    "strict": True,
                },
            },
        }

        last_error: Exception | None = None
        for _attempt in range(MAX_RETRIES + 1):
            try:
                response = await self._client.post(
                    url,
                    json=payload,
                    headers=self._headers(),
                    timeout=timeout_seconds,
                )
            except httpx.TimeoutException as exc:
                raise ProviderTimeoutError("LLM provider timed out") from exc
            except httpx.HTTPError as exc:
                raise ProviderUnavailableError(f"LLM provider unavailable: {exc}") from exc

            if response.status_code == 200:
                return self._parse_response(response.json(), response_model)
            if response.status_code in (408, 429, 500, 502, 503, 504):
                last_error = ProviderUnavailableError(
                    f"LLM provider returned HTTP {response.status_code}"
                )
                continue
            raise ProviderUnavailableError(
                f"LLM provider error: HTTP {response.status_code}",
                context={"status_code": response.status_code},
            )

        assert last_error is not None
        raise last_error

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _build_json_schema(self, model: type[Any]) -> dict[str, Any]:
        schema = model.model_json_schema()
        assert isinstance(schema, dict)
        return schema

    def _parse_response(self, data: dict[str, Any], response_model: type[Any]) -> Any:
        try:
            choices = data["choices"]
            content = choices[0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderSchemaError("malformed chat completion response") from exc
        try:
            parsed = response_model.model_validate_json(content)
        except Exception as exc:
            raise ProviderSchemaError("response failed schema validation") from exc
        return parsed

    async def healthcheck(self) -> ProviderHealth:
        try:
            response = await self._client.get(f"{self.base_url}/models", headers=self._headers())
        except (httpx.TimeoutException, httpx.HTTPError) as exc:
            return ProviderHealth(
                provider=self.provider_id,
                model=self.model,
                status="unavailable",
                error_code="E_PROVIDER_UNAVAILABLE",
                detail=str(exc),
            )
        if response.status_code == 200:
            return ProviderHealth(provider=self.provider_id, model=self.model, status="ok")
        return ProviderHealth(
            provider=self.provider_id,
            model=self.model,
            status="unavailable",
            error_code="E_PROVIDER_UNAVAILABLE",
            detail=f"HTTP {response.status_code}",
        )

    async def aclose(self) -> None:
        await self._client.aclose()


__all__ = ["OpenAICompatibleProvider"]