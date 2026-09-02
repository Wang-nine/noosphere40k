"""Lore pack registry: manifest, dependency resolution, loading (D-02).

Pack layout follows LORE_CONTENT_SPEC §4:
    lore_packs/<pack_id>/
        manifest.yaml
        sources.yaml
        entities/  facts/  relations/  glossary/  timelines/  tutorials/

Content is data only. Rejects missing dependencies, version conflicts,
duplicate IDs, illegal paths and unknown schema versions.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import Field

from noosphere40k.domain.errors import ContentMissingError
from noosphere40k.domain.models import StrictModel
from noosphere40k.lore.schemas import (
    GlossaryEntry,
    LoreEntity,
    LoreFact,
    SourceRecord,
)

PACK_SCHEMA_VERSION = 1

PACK_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._\-]*$")


class PackDependency(StrictModel):
    pack_id: str
    version_spec: str


class LorePack(StrictModel):
    pack_id: str
    version: str
    schema_version: int = PACK_SCHEMA_VERSION
    display_name: str
    coverage: dict[str, Any] = Field(default_factory=dict)
    dependencies: list[PackDependency] = Field(default_factory=list)
    rights_profile: str = "redistributable_metadata_only"
    review_status: str = "candidate"
    sources: list[SourceRecord] = Field(default_factory=list)
    entities: list[LoreEntity] = Field(default_factory=list)
    facts: list[LoreFact] = Field(default_factory=list)
    glossary: list[GlossaryEntry] = Field(default_factory=list)
    source_path: Path | None = None


def _load_yaml(path: Path) -> Any:
    if not path.exists():
        raise ContentMissingError(f"missing lore file: {path}", context={"path": str(path)})
    try:
        with path.open("r", encoding="utf-8") as fh:
            return yaml.safe_load(fh)
    except (yaml.YAMLError, OSError) as exc:
        raise ContentMissingError(
            f"invalid YAML in lore file: {path}", context={"path": str(path)}
        ) from exc


def _parse_version_spec(spec: str, pack_id: str) -> tuple[str, str]:
    """Return (op, version) for a dependency spec like '>=1.0.0,<2.0.0'."""
    ops: list[tuple[str, str]] = []
    for part in spec.split(","):
        part = part.strip()
        for op in (">=", "<=", ">", "<", "=="):
            if part.startswith(op):
                ops.append((op, part[len(op) :].strip()))
                break
        else:
            if part:
                ops.append(("==", part))
    return ops[0] if ops else ("*", "*")


def _version_tuple(version: str) -> tuple[int, ...]:
    parts = []
    for piece in version.split("."):
        digits = "".join(ch for ch in piece if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    return tuple(parts)


def _version_satisfies(version: str, op: str, required: str) -> bool:
    if op == "*":
        return True
    v = _version_tuple(version)
    r = _version_tuple(required)
    if op == "==":
        return v == r
    if op == ">=":
        return v >= r
    if op == "<=":
        return v <= r
    if op == ">":
        return v > r
    if op == "<":
        return v < r
    return False


def resolve_pack(
    pack: LorePack,
    *,
    installed: dict[str, str],
) -> None:
    """Check all declared dependencies exist and satisfy version specs."""
    for dep in pack.dependencies:
        if dep.pack_id not in installed:
            raise ContentMissingError(
                f"pack {pack.pack_id} depends on missing pack {dep.pack_id}",
                context={"pack_id": pack.pack_id, "dependency": dep.pack_id},
            )
        op, required = _parse_version_spec(dep.version_spec, pack.pack_id)
        if not _version_satisfies(installed[dep.pack_id], op, required):
            raise ContentMissingError(
                f"pack {pack.pack_id} requires {dep.pack_id}{dep.version_spec}, "
                f"installed {installed[dep.pack_id]}",
                context={"pack_id": pack.pack_id, "dependency": dep.pack_id},
            )


def load_lore_pack(pack_dir: Path, *, installed: dict[str, str] | None = None) -> LorePack:
    manifest_path = pack_dir / "manifest.yaml"
    manifest = _load_yaml(manifest_path)
    if not isinstance(manifest, dict):
        raise ContentMissingError(f"invalid manifest: {manifest_path}")

    pack_id = str(manifest.get("pack_id", ""))
    if not PACK_ID_RE.match(pack_id):
        raise ContentMissingError(f"illegal pack_id: {pack_id!r}", context={"path": str(pack_dir)})
    schema_version = int(manifest.get("schema_version", PACK_SCHEMA_VERSION))
    if schema_version != PACK_SCHEMA_VERSION:
        raise ContentMissingError(
            f"pack {pack_id} uses unknown schema version {schema_version}",
            context={"pack_id": pack_id},
        )

    dependencies = [
        PackDependency(pack_id=str(d.get("pack_id")), version_spec=str(d.get("version", "==*")))
        for d in manifest.get("dependencies", [])
        if isinstance(d, dict)
    ]

    pack = LorePack(
        pack_id=pack_id,
        version=str(manifest.get("version", "0.0.0")),
        schema_version=schema_version,
        display_name=str(manifest.get("display_name", pack_id)),
        coverage=manifest.get("coverage", {}),
        dependencies=dependencies,
        rights_profile=str(manifest.get("rights_profile", "redistributable_metadata_only")),
        review_status=str(manifest.get("review_status", "candidate")),
        source_path=pack_dir,
    )

    resolve_pack(pack, installed=installed or {})

    sources = _load_yaml(pack_dir / "sources.yaml")
    if isinstance(sources, dict):
        for record in sources.get("sources", []) if isinstance(sources.get("sources"), list) else []:
            pack.sources.append(SourceRecord.model_validate(record))

    _load_records(pack, pack_dir / "entities", LoreEntity, pack.entities)
    _load_records(pack, pack_dir / "facts", LoreFact, pack.facts)
    _load_records(pack, pack_dir / "glossary", GlossaryEntry, pack.glossary)

    _assert_unique_ids(pack)
    return pack


def _load_records[T: StrictModel](
    pack: LorePack,
    directory: Path,
    model: type[T],
    sink: list[T],
) -> None:
    if not directory.exists():
        return
    for file in sorted(directory.glob("*.yaml")):
        data = _load_yaml(file)
        records = data if isinstance(data, list) else [data]
        for record in records:
            if not isinstance(record, dict):
                raise ContentMissingError(f"invalid record in {file}")
            # unwrap a wrapped list like ``facts: [...]`` if present
            for key in ("facts", "entities", "glossary", "sources"):
                if key in record and isinstance(record[key], list) and len(record) == 1:
                    record = record[key]
                    break
            if not isinstance(record, dict):
                raise ContentMissingError(f"invalid record in {file}")
            record.setdefault("pack_id", pack.pack_id)
            record.setdefault("pack_version", pack.version)
            sink.append(model.model_validate(record))


def _assert_unique_ids(pack: LorePack) -> None:
    seen: set[str] = set()
    for record in (
        list(pack.sources),
        list(pack.entities),
        list(pack.facts),
        list(pack.glossary),
    ):
        for item in record:
            rid = (getattr(item, "source_id", None) or getattr(item, "fact_id", None)
                   or getattr(item, "entity_id", None) or getattr(item, "term_id", None))
            if rid is not None:
                if rid in seen:
                    raise ContentMissingError(
                        f"duplicate id in pack {pack.pack_id}: {rid}",
                        context={"pack_id": pack.pack_id, "id": rid},
                    )
                seen.add(rid)


__all__ = [
    "LorePack",
    "PackDependency",
    "resolve_pack",
    "load_lore_pack",
    "PACK_SCHEMA_VERSION",
]