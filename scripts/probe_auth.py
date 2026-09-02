#!/usr/bin/env python
"""Auth-header probe for OpenAI-compatible gateways (troubleshooting only).

Tries several auth styles against /v1/chat/completions and reports which one
is accepted. NEVER prints the API key.

Usage:
    set NOOSPHERE_LLM_BASE_URL / NOOSPHERE_LLM_MODEL / NOOSPHERE_LLM_API_KEY
    python scripts/probe_auth.py
"""

from __future__ import annotations

import asyncio
import os
import sys

import httpx

AUTH_STYLES = [
    ("Authorization: Bearer", lambda k: {"Authorization": f"Bearer {k}"}),
    ("Authorization: raw", lambda k: {"Authorization": k}),
    ("x-api-key", lambda k: {"x-api-key": k}),
    ("x-api-key + Authorization", lambda k: {"x-api-key": k, "Authorization": f"Bearer {k}"}),
]


def _settings() -> tuple[str, str, str]:
    base = os.environ.get("NOOSPHERE_LLM_BASE_URL", "")
    model = os.environ.get("NOOSPHERE_LLM_MODEL", "")
    key = os.environ.get("NOOSPHERE_LLM_API_KEY", "")
    if not (base and model and key):
        raise SystemExit("需要 NOOSPHERE_LLM_BASE_URL / NOOSPHERE_LLM_MODEL / NOOSPHERE_LLM_API_KEY")
    return base.rstrip("/"), model, key


async def main() -> int:
    base, model, key = _settings()
    url = f"{base}/chat/completions"
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "ping"}],
        "max_tokens": 8,
    }
    print(f"目标：{url}")
    print(f"Model: {model}")
    async with httpx.AsyncClient(timeout=20.0) as client:
        for label, build_headers in AUTH_STYLES:
            headers = {"Content-Type": "application/json", **build_headers(key)}
            try:
                resp = await client.post(url, json=payload, headers=headers)
            except httpx.HTTPError as exc:
                print(f"  {label}: 网络错误 {exc}")
                continue
            status = resp.status_code
            body = resp.text[:120].replace("\n", " ")
            print(f"  {label}: HTTP {status}  {body}")
            if status == 200:
                print(f"  >>> 成功：鉴权方式 [{label}] 可用")
                return 0
    print("所有鉴权方式均未通过。请检查 key 是否正确/是否已过期。")
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))