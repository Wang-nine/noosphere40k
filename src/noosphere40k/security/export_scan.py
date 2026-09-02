"""Privacy and export safety (H-05).

Export/scan helpers: verify a directory or archive text does not contain API
keys, private-source material markers or secrets before release.
"""

from __future__ import annotations

from pathlib import Path

from noosphere40k.security.secrets import scan_for_keys

PRIVATE_SOURCE_MARKERS = (
    "private_lore",
    "local_owned_copy",
    "black library",
    "black_library",
    "codex",
)


def scan_directory(path: Path) -> list[str]:
    """Scan a directory tree for key-like patterns and private markers."""
    issues: list[str] = []
    text_suffixes = {".md", ".txt", ".yaml", ".yml", ".json", ".toml", ".py"}
    for file in path.rglob("*"):
        if not file.is_file() or file.suffix.lower() not in text_suffixes:
            continue
        try:
            content = file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if scan_for_keys([content]) > 0:
            issues.append(f"疑似密钥：{file.relative_to(path)}")
        lowered = content.lower()
        for marker in PRIVATE_SOURCE_MARKERS:
            if marker in lowered and "public_baseline" not in lowered:
                issues.append(f"疑似私有资料引用：{file.relative_to(path)}（{marker}）")
                break
    return issues


def verify_export_bundle(bundle_path: Path) -> list[str]:
    """Verify a (possibly zipped) export bundle contains no secrets or private text."""
    if bundle_path.is_dir():
        return scan_directory(bundle_path)
    import zipfile

    issues: list[str] = []
    with zipfile.ZipFile(bundle_path) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            if not info.filename.endswith((".md", ".txt", ".yaml", ".yml", ".json", ".toml")):
                continue
            try:
                content = zf.read(info).decode("utf-8", errors="ignore")
            except (KeyError, UnicodeDecodeError):
                continue
            if scan_for_keys([content]) > 0:
                issues.append(f"疑似密钥：{info.filename}")
            for marker in PRIVATE_SOURCE_MARKERS:
                if marker in content.lower():
                    issues.append(f"疑似私有资料引用：{info.filename}（{marker}）")
                    break
    return issues


__all__ = ["scan_directory", "verify_export_bundle"]