"""Content pack loader (F-01/F-02).

Loads a :class:`ScenePack` from a JSON file or directory and validates it.
Content is treated as untrusted data: never imported as code.
"""

from __future__ import annotations

import json
from pathlib import Path

from noosphere40k.content.schemas import ScenePack
from noosphere40k.content.validator import validate_pack, validate_template_variables
from noosphere40k.domain.errors import ContentMissingError


def load_pack_json(path: Path) -> ScenePack:
    """Load and validate a scenario pack from a single JSON file."""
    if not path.exists():
        raise ContentMissingError(
            f"content pack file not found: {path}",
            context={"path": str(path)},
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ContentMissingError(
            f"invalid content pack JSON: {path}",
            context={"path": str(path)},
        ) from exc
    pack = ScenePack.model_validate(data)
    validate_pack(pack)
    validate_template_variables(pack)
    return pack


def load_pack_dir(path: Path) -> ScenePack:
    """Load a pack from a directory containing pack.json."""
    return load_pack_json(path / "pack.json")