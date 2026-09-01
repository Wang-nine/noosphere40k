"""LLM provider contract (TECHNICAL_SPEC §8; E-01).

Business code only ever sees this Protocol. Providers own auth, retries,
error mapping and vendor response parsing.
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from pydantic import BaseModel

from noosphere40k.domain.models import StrictModel


class Message(StrictModel):
    role: Literal["system", "user", "assistant"]
    content: str


class ProviderHealth(StrictModel):
    provider: str
    model: str | None = None
    status: Literal["ok", "unavailable", "timeout", "unsupported"]
    error_code: str | None = None
    detail: str | None = None


@runtime_checkable
class LLMProvider(Protocol):
    provider_id: str

    async def generate_structured(
        self,
        *,
        messages: list[Message],
        response_model: type[BaseModel],
        timeout_seconds: float,
        request_metadata: dict[str, str],
    ) -> BaseModel: ...

    async def healthcheck(self) -> ProviderHealth: ...