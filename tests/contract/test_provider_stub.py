"""E-01: stub provider contract tests (offline, deterministic)."""

from __future__ import annotations

import asyncio

import pytest
from pydantic import BaseModel

from noosphere40k.domain.errors import (
    ProviderSchemaError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from noosphere40k.llm.base import Message
from noosphere40k.llm.stub import StubProvider


class Pong(BaseModel):
    value: str


async def test_stub_returns_scripted_response_offline() -> None:
    provider = StubProvider(response=Pong(value="pong"))
    result = await provider.generate_structured(
        messages=[Message(role="user", content="ping")],
        response_model=Pong,
        timeout_seconds=5.0,
        request_metadata={"trace_id": "t1"},
    )
    assert isinstance(result, Pong)
    assert result.value == "pong"


async def test_stub_without_response_is_unavailable() -> None:
    with pytest.raises(ProviderUnavailableError) as exc_info:
        await StubProvider().generate_structured(
            messages=[], response_model=Pong, timeout_seconds=1.0, request_metadata={}
        )
    assert exc_info.value.code.value == "E_PROVIDER_UNAVAILABLE"


async def test_stub_timeout_mode() -> None:
    with pytest.raises(ProviderTimeoutError):
        await StubProvider(response=Pong(value="x"), fail_mode="timeout").generate_structured(
            messages=[], response_model=Pong, timeout_seconds=1.0, request_metadata={}
        )


async def test_stub_sleep_longer_than_timeout_raises() -> None:
    with pytest.raises(ProviderTimeoutError):
        await StubProvider(response=Pong(value="x"), sleep_seconds=2.0).generate_structured(
            messages=[], response_model=Pong, timeout_seconds=0.01, request_metadata={}
        )


async def test_stub_schema_mismatch_raises_schema_error() -> None:
    class Other(BaseModel):
        nope: int

    with pytest.raises(ProviderSchemaError):
        await StubProvider(response=Pong(value="x")).generate_structured(
            messages=[], response_model=Other, timeout_seconds=1.0, request_metadata={}
        )


async def test_stub_healthcheck_matches_fail_mode() -> None:
    ok = await StubProvider(response=Pong(value="x")).healthcheck()
    assert ok.status == "ok"
    down = await StubProvider(response=Pong(value="x"), fail_mode="unavailable").healthcheck()
    assert down.status == "unavailable"
    assert down.error_code == "E_PROVIDER_UNAVAILABLE"


async def test_cancellation_does_not_commit_anything() -> None:
    provider = StubProvider(response=Pong(value="x"), sleep_seconds=1.0)
    task = asyncio.create_task(
        provider.generate_structured(
            messages=[], response_model=Pong, timeout_seconds=0.01, request_metadata={}
        )
    )
    with pytest.raises(ProviderTimeoutError):
        await task
    assert provider.request_count == 1