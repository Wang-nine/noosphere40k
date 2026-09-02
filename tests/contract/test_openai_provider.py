"""E-02: OpenAI-compatible provider — offline via MockTransport."""

from __future__ import annotations

import httpx
import pytest
from pydantic import BaseModel

from noosphere40k.domain.errors import (
    ProviderSchemaError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from noosphere40k.llm.base import Message
from noosphere40k.llm.openai_compatible import OpenAICompatibleProvider


class Pong(BaseModel):
    value: str


def _provider(handler) -> OpenAICompatibleProvider:
    transport = httpx.MockTransport(handler)
    client = httpx.AsyncClient(transport=transport)
    return OpenAICompatibleProvider(
        base_url="https://example.test/v1",
        model="test-model",
        api_key="sk-test-not-real",
        client=client,
    )


def _ok_handler(request: httpx.Request) -> httpx.Response:
    return httpx.Response(200, json={
        "choices": [{"message": {"content": '{"value": "pong"}'}}],
    })


async def test_generates_structured_from_json_schema() -> None:
    provider = _provider(_ok_handler)
    result = await provider.generate_structured(
        messages=[Message(role="user", content="ping")],
        response_model=Pong,
        timeout_seconds=5.0,
        request_metadata={"trace_id": "t1"},
    )
    assert isinstance(result, Pong)
    assert result.value == "pong"


async def test_retries_on_5xx() -> None:
    calls = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json={
            "choices": [{"message": {"content": '{"value": "ok"}'}}],
        })

    provider = _provider(handler)
    result = await provider.generate_structured(
        messages=[], response_model=Pong, timeout_seconds=5.0, request_metadata={}
    )
    assert result.value == "ok"
    assert calls["n"] == 3


async def test_timeout_raises_stable_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow")

    provider = _provider(handler)
    with pytest.raises(ProviderTimeoutError):
        await provider.generate_structured(
            messages=[], response_model=Pong, timeout_seconds=0.1, request_metadata={}
        )


async def test_http_error_maps_to_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401)

    provider = _provider(handler)
    with pytest.raises(ProviderUnavailableError):
        await provider.generate_structured(
            messages=[], response_model=Pong, timeout_seconds=5.0, request_metadata={}
        )


async def test_malformed_json_raises_schema_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    provider = _provider(handler)
    with pytest.raises(ProviderSchemaError):
        await provider.generate_structured(
            messages=[], response_model=Pong, timeout_seconds=5.0, request_metadata={}
        )


async def test_healthcheck_ok() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/models"
        return httpx.Response(200, json={"data": []})

    provider = _provider(handler)
    health = await provider.healthcheck()
    assert health.status == "ok"


async def test_healthcheck_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    provider = _provider(handler)
    health = await provider.healthcheck()
    assert health.status == "unavailable"
    assert health.error_code == "E_PROVIDER_UNAVAILABLE"


def test_api_key_present_flag() -> None:
    provider = _provider(_ok_handler)
    assert provider.api_key_present is True
    # the key must not appear in plain repr
    assert "sk-test-not-real" not in repr(provider)