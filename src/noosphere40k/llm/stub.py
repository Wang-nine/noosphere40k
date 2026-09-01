"""Stub LLM provider for offline development and contract tests (E-01).

Returns a fixed scripted response; supports failure injection for
unavailable/timeout/schema cases without any network access.
"""

from __future__ import annotations

import asyncio
from typing import Literal

from pydantic import BaseModel, ValidationError

from noosphere40k.domain.errors import (
    ProviderSchemaError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from noosphere40k.llm.base import Message, ProviderHealth

StubFailMode = Literal["none", "unavailable", "timeout", "schema"]


class StubProvider:
    """Deterministic offline provider (E-01; never used in production paths)."""

    provider_id = "stub"

    def __init__(
        self,
        response: BaseModel | None = None,
        *,
        model: str = "stub-model",
        fail_mode: StubFailMode = "none",
        sleep_seconds: float = 0.0,
    ) -> None:
        self.response = response
        self.model = model
        self.fail_mode = fail_mode
        self.sleep_seconds = sleep_seconds
        self.request_count = 0

    async def generate_structured(
        self,
        *,
        messages: list[Message],
        response_model: type[BaseModel],
        timeout_seconds: float,
        request_metadata: dict[str, str] | None = None,
    ) -> BaseModel:
        self.request_count += 1
        if self.response is None:
            raise ProviderUnavailableError("stub provider has no configured response")
        if self.sleep_seconds:
            try:
                await asyncio.wait_for(asyncio.sleep(self.sleep_seconds), timeout_seconds)
            except TimeoutError as exc:
                raise ProviderTimeoutError("stub provider timed out") from exc
        if self.fail_mode == "timeout":
            raise ProviderTimeoutError("stub provider timed out")
        if self.fail_mode == "schema":
            raise ProviderSchemaError("stub provider returned an invalid schema")
        try:
            return response_model.model_validate(self.response.model_dump())
        except ValidationError as exc:
            raise ProviderSchemaError("stub response failed schema validation") from exc

    async def healthcheck(self) -> ProviderHealth:
        if self.fail_mode == "unavailable":
            return ProviderHealth(
                provider=self.provider_id,
                model=self.model,
                status="unavailable",
                error_code="E_PROVIDER_UNAVAILABLE",
            )
        if self.fail_mode == "timeout":
            return ProviderHealth(
                provider=self.provider_id,
                model=self.model,
                status="timeout",
                error_code="E_PROVIDER_TIMEOUT",
            )
        return ProviderHealth(provider=self.provider_id, model=self.model, status="ok")


class UnconfiguredProvider:
    """Explicit default meaning 'no provider configured'."""

    provider_id = "none"

    async def generate_structured(
        self,
        *,
        messages: list[Message],
        response_model: type[BaseModel],
        timeout_seconds: float,
        request_metadata: dict[str, str],
    ) -> BaseModel:
        raise ProviderUnavailableError("no LLM provider configured")

    async def healthcheck(self) -> ProviderHealth:
        return ProviderHealth(
            provider=self.provider_id,
            status="unavailable",
            error_code="E_PROVIDER_UNAVAILABLE",
        )


__all__ = [
    "StubProvider",
    "UnconfiguredProvider",
    "Message",
    "ProviderHealth",
]