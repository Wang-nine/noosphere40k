"""Coverage reporting for Galaxy Primer and Campaign Canon packs (D-09/D-10).

Generates:
- per-domain coverage for the 12 Galaxy Primer theme domains,
- missing-topic lists,
- hard-requirement satisfaction rate for campaign content (must be 100%).

Placeholder content is never counted as approved facts.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import Connection, Engine, text

# Galaxy Primer theme domains (LORE_CONTENT_SPEC §1.1).
GALAXY_PRIMER_DOMAINS: list[str] = [
    "GP-01 world_basics",
    "GP-02 history_skeleton",
    "GP-03 imperium_institutions",
    "GP-04 imperium_society",
    "GP-05 imperium_military",
    "GP-06 warp_and_navigation",
    "GP-07 chaos",
    "GP-08 xenos",
    "GP-09 tech_and_life",
    "GP-10 major_conflicts",
    "GP-11 human_lifepath",
    "GP-12 terms_and_translations",
]


@dataclass
class DomainCoverage:
    domain_id: str
    total_facts: int
    approved_facts: int
    covered: bool

    @property
    def rate(self) -> float:
        if self.total_facts == 0:
            return 0.0
        return self.approved_facts / self.total_facts


@dataclass
class CoverageReport:
    pack_id: str
    domains: list[DomainCoverage] = field(default_factory=list)
    approved_facts_total: int = 0
    candidate_facts_total: int = 0
    missing_domains: list[str] = field(default_factory=list)

    def to_lines(self) -> list[str]:
        lines = [f"覆盖报告：{self.pack_id}"]
        lines.append(f"  已批准事实：{self.approved_facts_total}；候选：{self.candidate_facts_total}")
        for domain in self.domains:
            status = "覆盖" if domain.covered else "空缺"
            lines.append(f"  {domain.domain_id}: {status}（已批准 {domain.approved_facts}/{domain.total_facts}）")
        if self.missing_domains:
            lines.append("  空缺主题域：" + "、".join(self.missing_domains))
        return lines


def build_primer_report(engine: Engine, *, pack_id: str) -> CoverageReport:
    """Per-domain coverage for the Galaxy Primer (12 theme domains)."""
    domains: list[DomainCoverage] = []
    missing: list[str] = []
    with engine.connect() as conn:
        for domain in GALAXY_PRIMER_DOMAINS:
            domain_id = domain.split()[0]
            total = _count_facts(conn, pack_id, domain_id)
            approved = _count_approved_facts(conn, pack_id, domain_id)
            coverage = DomainCoverage(domain_id=domain_id, total_facts=total, approved_facts=approved, covered=approved > 0)
            domains.append(coverage)
            if not coverage.covered:
                missing.append(domain_id)
        approved_total = _count_approved_facts(conn, pack_id, None)
        candidate_total = _count_facts(conn, pack_id, None) - approved_total
    return CoverageReport(
        pack_id=pack_id,
        domains=domains,
        approved_facts_total=approved_total,
        candidate_facts_total=max(0, candidate_total),
        missing_domains=missing,
    )


def build_campaign_coverage(engine: Engine, *, pack_id: str, hard_requirements: dict[str, list[str]]) -> CoverageReport:
    """Hard-requirement satisfaction for a campaign pack.

    ``hard_requirements`` maps requirement_id -> list of fact_ids that would
    satisfy it. Rate must be 100% for a shippable pack.
    """
    missing: list[str] = []
    with engine.connect() as conn:
        for requirement_id, fact_ids in hard_requirements.items():
            if not _any_approved_fact(conn, fact_ids):
                missing.append(requirement_id)
        approved_total = _count_approved_facts(conn, pack_id, None)
        candidate_total = _count_facts(conn, pack_id, None) - approved_total
    return CoverageReport(
        pack_id=pack_id,
        approved_facts_total=approved_total,
        candidate_facts_total=max(0, candidate_total),
        missing_domains=missing,
    )


def hard_requirement_satisfaction_rate(engine: Engine, hard_requirements: dict[str, list[str]]) -> float:
    """Fraction of hard requirements satisfiable by approved facts (D-10)."""
    if not hard_requirements:
        return 1.0
    satisfied = 0
    with engine.connect() as conn:
        for fact_ids in hard_requirements.values():
            if _any_approved_fact(conn, fact_ids):
                satisfied += 1
    return satisfied / len(hard_requirements)


def _count_facts(conn: Connection, pack_id: str, domain_id: str | None) -> int:
    if domain_id is None:
        return int(conn.execute(
            text("SELECT COUNT(*) FROM lore_facts WHERE pack_id = :p"), {"p": pack_id}
        ).scalar() or 0)
    return int(conn.execute(
        text("SELECT COUNT(*) FROM lore_facts WHERE pack_id = :p AND entity_ids_json LIKE :d"),
        {"p": pack_id, "d": f"%{domain_id}%"},
    ).scalar() or 0)


def _count_approved_facts(conn: Connection, pack_id: str, domain_id: str | None) -> int:
    if domain_id is None:
        return int(conn.execute(
            text("SELECT COUNT(*) FROM lore_facts WHERE pack_id = :p AND review_status = 'approved'"),
            {"p": pack_id},
        ).scalar() or 0)
    return int(conn.execute(
        text("SELECT COUNT(*) FROM lore_facts WHERE pack_id = :p AND review_status = 'approved' "
             "AND entity_ids_json LIKE :d"),
        {"p": pack_id, "d": f"%{domain_id}%"},
    ).scalar() or 0)


def _any_approved_fact(conn: Connection, fact_ids: list[str]) -> bool:
    if not fact_ids:
        return False
    placeholders = ",".join(f":f{i}" for i in range(len(fact_ids)))
    params = {f"f{i}": fid for i, fid in enumerate(fact_ids)}
    count = conn.execute(
        text(f"SELECT COUNT(*) FROM lore_facts WHERE fact_id IN ({placeholders}) "
             "AND review_status = 'approved'"),
        params,
    ).scalar() or 0
    return int(count) > 0


__all__ = [
    "GALAXY_PRIMER_DOMAINS",
    "build_primer_report",
    "build_campaign_coverage",
    "hard_requirement_satisfaction_rate",
    "CoverageReport",
    "DomainCoverage",
]