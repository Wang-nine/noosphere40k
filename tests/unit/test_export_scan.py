"""H-05: export privacy scan."""

from __future__ import annotations

from pathlib import Path

from noosphere40k.security.export_scan import scan_directory, verify_export_bundle


def test_scan_directory_flags_keys(tmp_path: Path) -> None:
    (tmp_path / "clean.md").write_text("项目说明。", encoding="utf-8")
    (tmp_path / "secret.md").write_text("api_key=sk-abcdef123456", encoding="utf-8")
    issues = scan_directory(tmp_path)
    assert any("secret.md" in i for i in issues)
    assert not any("clean.md" in i for i in issues)


def test_scan_directory_flags_private_markers(tmp_path: Path) -> None:
    (tmp_path / "notes.md").write_text("我读过的 black library 小说原文", encoding="utf-8")
    issues = scan_directory(tmp_path)
    assert any("notes.md" in i for i in issues)


def test_verify_export_bundle_zip(tmp_path: Path) -> None:
    import zipfile

    bundle = tmp_path / "export.zip"
    with zipfile.ZipFile(bundle, "w") as zf:
        zf.writestr("campaign/notes.md", "api_key=sk-evilkey123456")
    issues = verify_export_bundle(bundle)
    assert any("notes.md" in i for i in issues)


def test_verify_export_bundle_dir_clean(tmp_path: Path) -> None:
    (tmp_path / "ok.md").write_text("一切正常", encoding="utf-8")
    assert verify_export_bundle(tmp_path) == []