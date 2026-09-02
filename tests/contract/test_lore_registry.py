"""D-02: lore pack loader, manifest, dependencies."""

from __future__ import annotations

from pathlib import Path

import pytest

from noosphere40k.domain.errors import ContentMissingError
from noosphere40k.lore.registry import load_lore_pack, resolve_pack


def _write_pack(tmp_path: Path, name: str, version: str = "1.0.0", deps=None) -> Path:
    pack_dir = tmp_path / name
    pack_dir.mkdir(exist_ok=True)
    dep_lines = ""
    if deps:
        dep_lines = "dependencies:\n" + "".join(
            f"  - pack_id: \"{d['id']}\"\n    version: \"{d['ver']}\"\n" for d in deps
        )
    (pack_dir / "manifest.yaml").write_text(
        f'pack_id: "{name}"\nversion: "{version}"\nschema_version: 1\n'
        f'display_name: "{name}"\n{dep_lines}',
        encoding="utf-8",
    )
    (pack_dir / "sources.yaml").write_text("sources: []\n", encoding="utf-8")
    (pack_dir / "facts").mkdir(exist_ok=True)
    (pack_dir / "entities").mkdir(exist_ok=True)
    return pack_dir


def test_load_simple_pack(tmp_path: Path) -> None:
    pack_dir = _write_pack(tmp_path, "primer.galaxy.core")
    pack = load_lore_pack(pack_dir)
    assert pack.pack_id == "primer.galaxy.core"
    assert pack.version == "1.0.0"


def test_missing_dependency_rejected(tmp_path: Path) -> None:
    pack_dir = _write_pack(tmp_path, "campaign.lifepath", deps=[{"id": "primer.galaxy.core", "ver": ">=1.0.0"}])
    with pytest.raises(ContentMissingError):
        load_lore_pack(pack_dir, installed={})


def test_version_conflict_rejected(tmp_path: Path) -> None:
    pack_dir = _write_pack(tmp_path, "campaign.lifepath", deps=[{"id": "primer.galaxy.core", "ver": ">=2.0.0"}])
    with pytest.raises(ContentMissingError):
        load_lore_pack(pack_dir, installed={"primer.galaxy.core": "1.5.0"})


def test_version_satisfies(tmp_path: Path) -> None:
    pack_dir = _write_pack(tmp_path, "campaign.lifepath", deps=[{"id": "primer.galaxy.core", "ver": ">=1.0.0,<2.0.0"}])
    pack = load_lore_pack(pack_dir, installed={"primer.galaxy.core": "1.9.0"})
    assert pack.dependencies[0].version_spec == ">=1.0.0,<2.0.0"


def test_illegal_pack_id_rejected(tmp_path: Path) -> None:
    pack_dir = _write_pack(tmp_path, "Campaign Evil")
    with pytest.raises(ContentMissingError):
        load_lore_pack(pack_dir)


def test_unknown_schema_version_rejected(tmp_path: Path) -> None:
    pack_dir = tmp_path / "p"
    pack_dir.mkdir()
    (pack_dir / "manifest.yaml").write_text(
        'pack_id: "p"\nversion: "1.0.0"\nschema_version: 99\n', encoding="utf-8"
    )
    with pytest.raises(ContentMissingError):
        load_lore_pack(pack_dir)


def test_duplicate_ids_rejected(tmp_path: Path) -> None:
    pack_dir = _write_pack(tmp_path, "dup.pack")
    facts = pack_dir / "facts"
    (facts / "a.yaml").write_text(
        "facts:\n"
        '- fact_id: "fact.dup"\n'
        '  claim: "第一"'
        '\n  fact_type: "canon_editorial"\n'
        '  pack_id: "dup.pack"\n'
        '  pack_version: "1.0.0"\n',
        encoding="utf-8",
    )
    (facts / "b.yaml").write_text(
        '- fact_id: "fact.dup"\n'
        '  claim: "第二"\n'
        '  fact_type: "canon_editorial"\n'
        '  pack_id: "dup.pack"\n'
        '  pack_version: "1.0.0"\n',
        encoding="utf-8",
    )
    with pytest.raises(ContentMissingError):
        load_lore_pack(pack_dir)


def test_resolve_pack_missing_rejected() -> None:
    from noosphere40k.lore.registry import LorePack, PackDependency

    pack = LorePack(
        pack_id="x",
        version="1.0.0",
        display_name="x",
        dependencies=[PackDependency(pack_id="missing", version_spec=">=1.0.0")],
    )
    with pytest.raises(ContentMissingError):
        resolve_pack(pack, installed={})