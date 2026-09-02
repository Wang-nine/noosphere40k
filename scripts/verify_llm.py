#!/usr/bin/env python
"""Real-LLM smoke verification (E-02) — NEVER logs or stores the API key.

Usage:
    set NOOSPHERE_LLM_BASE_URL / NOOSPHERE_LLM_MODEL / NOOSPHERE_LLM_API_KEY
    (key entered as a temporary environment variable, not committed)
    python scripts/verify_llm.py

Performs: healthcheck + one structured generation (NarrationResponse),
then prints a sanitized report. The key is never printed.
"""

from __future__ import annotations

import asyncio
import sys

from noosphere40k.config.settings import load_settings
from noosphere40k.llm.base import Message
from noosphere40k.llm.factory import build_provider
from noosphere40k.llm.schemas import (
    NarrationRequest,
    NarrationResponse,
    VisibleCharacterState,
    VisibleScene,
)
from noosphere40k.security.secrets import redact_text


def _build_request() -> NarrationRequest:
    return NarrationRequest(
        trace_id="verify-llm-001",
        campaign_id="verify.campaign",
        turn_number=1,
        player_input="观察走廊里的红袍人",
        visible_scene=VisibleScene(
            scene_id="scene.verify",
            title="验证场景",
            location_display="工人居住层",
        ),
        visible_character_state=VisibleCharacterState(
            display_name="Ada",
            displayed_age="8 岁",
            life_stage="childhood",
            role_summary="巢都工人家庭",
        ),
    )


async def _run(settings) -> int:
    provider = build_provider(settings)
    print(f"[1/2] healthcheck: provider={provider.provider_id} model={settings.llm.model or 'stub'}")
    health = await provider.healthcheck()
    print(f"      status={health.status}")
    if health.status != "ok":
        print(f"      error_code={health.error_code} detail={redact_text(health.detail or '')}")
        print("验证失败：健康检查未通过。")
        return 1

    request = _build_request()
    print("[2/2] structured generation (NarrationResponse) ...")
    try:
        response = await provider.generate_structured(
            messages=[
                Message(role="system", content=(
                    "你是一个受约束的中文叙事器。只描述已确定的结果，"
                    "不生成世界观事实，不更改骰点/状态。严格输出 NarrationResponse JSON。"
                )),
                Message(role="user", content=request.player_input),
            ],
            response_model=NarrationResponse,
            timeout_seconds=30.0,
            request_metadata={"trace_id": request.trace_id, "purpose": "verify"},
        )
    except Exception as exc:  # noqa: BLE001
        print(f"      generation failed: {redact_text(str(exc))}")
        return 1

    assert isinstance(response, NarrationResponse)
    print("      成功生成结构化叙事：")
    print("      " + redact_text(response.narration[:200]))
    print(f"      提议事件：{len(response.proposed_events)}  lore_claims：{len(response.lore_claims)}")
    print("验证通过：真实 LLM 结构化输出解析正常。")
    return 0


def main() -> int:
    settings = load_settings()
    if not settings.has_api_key:
        print("未配置 NOOSPHERE_LLM_API_KEY。请用临时环境变量设置后重试。")
        print("例如：$env:NOOSPHERE_LLM_API_KEY = '...'（仅在当前终端会话有效，不落盘）")
        return 2
    if not settings.llm.base_url or not settings.llm.model:
        print("需要 NOOSPHERE_LLM_BASE_URL 与 NOOSPHERE_LLM_MODEL。")
        return 2
    print(f"Base URL: {settings.llm.base_url}  Model: {settings.llm.model}")
    print("（API key 仅存在于本次进程环境变量中，不会打印或保存）")
    return asyncio.run(_run(settings))


if __name__ == "__main__":
    sys.exit(main())