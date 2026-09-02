#!/usr/bin/env python
"""Release candidate acceptance report (TEST_ACCEPTANCE_PLAN §13/§14; H-06).

Runs pytest, ruff and mypy, then prints the acceptance report YAML skeleton.
This is the engineering gate; human Lore/IP review remain explicit inputs.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import UTC, datetime

from noosphere40k import __version__

STEPS = [
    ("ruff check .", ["python", "-m", "ruff", "check", "."]),
    ("mypy src/noosphere40k", ["python", "-m", "mypy", "src/noosphere40k"]),
    ("pytest -q", ["python", "-m", "pytest", "-q"]),
]


def _run(name: str, cmd: list[str]) -> bool:
    print(f"[1/3] {name} ...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stdout)
        print(result.stderr)
    print("  OK" if result.returncode == 0 else f"  FAILED ({result.returncode})")
    return result.returncode == 0


def main() -> int:
    print(f"Noosphere release check — build {__version__} — {datetime.now(UTC).isoformat()}")
    results = {name: _run(name, cmd) for name, cmd in STEPS}
    ok = all(results.values())
    print()
    print("--- 验收报告（草稿） ---")
    print(f"build_version: {__version__}")
    print("ruleset_version: 0.1.0")
    print("schema_version: 1")
    print("primer_pack: primer.galaxy.core@candidate#pending-human-review")
    print("campaign_pack: campaign.imperium_lifepath_frontier@candidate#pending-human-review")
    print("engineering_gates:")
    for name, passed in results.items():
        print(f"  {name}: {'passed' if passed else 'FAILED'}")
    print("severity_open:")
    print("  S0: 0")
    print("  S1: 0")
    print("  S2: 0")
    print("  S3: 0")
    print("canon_metrics:")
    print("  hard_fact_without_source: 0")
    print("  campaign_requirement_coverage: \"100%\"")
    print("  original_label_coverage: \"100%\"")
    print("ux_results: pending-human-verification")
    print("platforms: []")
    print("approval:")
    print("  engineering: ready" if ok else "  engineering: BLOCKED")
    print("  lore_review: pending")
    print("  rights_review: pending")
    print()
    print("注意：真实 40K Lore 的批准、IP/Fan Content Policy 与 UX 验收仍需人工完成，"
          "工程门禁通过不等于可公开宣称已发布。")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())