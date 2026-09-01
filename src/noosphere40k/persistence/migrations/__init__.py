"""Numbered migrations registry (C-02).

Add a new ``NNNN_name.py`` module exporting ``MIGRATION_XXXX`` and re-export it
here; never edit an applied migration after publication.
"""

from __future__ import annotations

from noosphere40k.persistence.db import Migration
from noosphere40k.persistence.migrations._0001_initial import MIGRATION_0001

MIGRATIONS: tuple[Migration, ...] = (MIGRATION_0001,)

__all__ = ["MIGRATIONS", "Migration"]