"""Lore importers: sanitized ingestion framework (D-07).

Imported web/docs text is treated as DATA, never as instructions. The cleaner
strips scripts, navigation text, hidden text and prompt-injection patterns.
Quoted material (in-world liturgy, dialogue, injunctions) is tagged with
``quoted_material``. Zip/archive extraction is guarded against path traversal
and decompression bombs.
"""

from __future__ import annotations

import re
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

# Prompt-injection heuristics (English + Chinese).
_INJECTION_PATTERNS = (
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions?", re.I),
    re.compile(r"ignore\s+your\s+system\s+prompt", re.I),
    re.compile(r"你.*(忽略|无视).*(指令|提示|规则)", re.I),
    re.compile(r"disregard\s+(the\s+)?(system|instructions)", re.I),
    re.compile(r"now\s+(output|reveal|print)\s+(the\s+)?(system|prompt|key)", re.I),
    re.compile(r"现在.*(输出|泄露).*(提示词|密钥|系统)", re.I),
    re.compile(r"(api[_-]?key|secret)\s*=\s*\S{6,}", re.I),
)

_SCRIPT_TAG = re.compile(r"<\s*script[\s\S]*?<\s*/\s*script\s*>", re.I)
_STYLE_TAG = re.compile(r"<\s*style[\s\S]*?<\s*/\s*style\s*>", re.I)
_HTML_TAG = re.compile(r"<[^>]+>")
_NAV_TEXT = re.compile(r"\b(home|menu|login|sign in|register|footer|subscribe|newsletter)\b", re.I)
_HIDDEN_STYLE = re.compile(r"(display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0)", re.I)

MAX_ZIP_RATIO = 100.0
MAX_ZIP_ENTRIES = 2000
MAX_ZIP_SIZE = 200 * 1024 * 1024


@dataclass
class SanitizedDocument:
    text: str
    quoted_material: list[str] = field(default_factory=list)
    injection_warnings: list[str] = field(default_factory=list)
    truncated: bool = False


def sanitize_html(raw_html: str, *, max_chars: int = 50000) -> SanitizedDocument:
    """Strip scripts/styles/tags/nav text; flag injection attempts."""
    warnings: list[str] = []
    body = raw_html

    for pattern in _INJECTION_PATTERNS:
        for match in pattern.finditer(raw_html):
            warnings.append(f"疑似提示注入：{match.group(0)[:60]!r}")
            break  # one warning per pattern

    if _HIDDEN_STYLE.search(raw_html):
        warnings.append("检测到隐藏文本样式（display:none 等）")

    body = _SCRIPT_TAG.sub(" ", body)
    body = _STYLE_TAG.sub(" ", body)
    body = _HTML_TAG.sub(" ", body)
    body = _NAV_TEXT.sub(" ", body)

    # collapse whitespace
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    text = "\n".join(lines)

    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars]

    return SanitizedDocument(text=text, injection_warnings=warnings, truncated=truncated)


def sanitize_plain_text(text: str, *, max_chars: int = 50000) -> SanitizedDocument:
    warnings: list[str] = []
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            warnings.append("疑似提示注入文本")
            break
    truncated = len(text) > max_chars
    cleaned = text[:max_chars] if truncated else text
    return SanitizedDocument(text=cleaned, injection_warnings=warnings, truncated=truncated)


def extract_quoted_material(text: str) -> list[str]:
    """Isolate quoted material (in-world liturgy/dialogue) for tagging."""
    quotes: list[str] = []
    for match in re.finditer(r"[“\"«「『]([^”\"»」』]{2,200})[”\"»」』]", text):
        quotes.append(match.group(1))
    return quotes


def safe_extract_zip(zip_path: Path, dest: Path, *, max_total_size: int = MAX_ZIP_SIZE) -> list[str]:
    """Extract a zip safely: reject traversal, symlinks, bombs and too many files."""
    extracted: list[str] = []
    with zipfile.ZipFile(zip_path) as zf:
        infos = zf.infolist()
        if len(infos) > MAX_ZIP_ENTRIES:
            raise ZipSafetyError(f"zip has too many entries: {len(infos)}")

        total = 0
        for info in infos:
            if info.is_dir():
                continue
            # symlink / special entry check
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ZipSafetyError(f"symlink entry rejected: {info.filename}")
            target = (dest / info.filename).resolve()
            if not target.is_relative_to(dest.resolve()):
                raise ZipSafetyError(f"path traversal rejected: {info.filename}")
            total += info.file_size
            if total > max_total_size:
                raise ZipSafetyError("zip exceeds total size budget (bomb)")
            if info.file_size > max_total_size:
                raise ZipSafetyError(f"entry too large: {info.filename}")
            ratio = info.compress_size and (info.file_size / info.compress_size)
            if ratio > MAX_ZIP_RATIO:
                raise ZipSafetyError(f"compression ratio suspicious: {info.filename}")

            target.parent.mkdir(parents=True, exist_ok=True)
            with zf.open(info) as src, target.open("wb") as out:
                shutil.copyfileobj(src, out)
            extracted.append(str(target))
    return extracted


class ZipSafetyError(Exception):
    pass


__all__ = [
    "SanitizedDocument",
    "sanitize_html",
    "sanitize_plain_text",
    "extract_quoted_material",
    "safe_extract_zip",
    "ZipSafetyError",
]