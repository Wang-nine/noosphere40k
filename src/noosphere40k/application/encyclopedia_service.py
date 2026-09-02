"""Encyclopedia, character knowledge and source commands (G-03).

Three distinct permission layers:
- ``/encyclopedia`` -> player-layer glossary (beginner/deep, spoiler-filtered),
- ``/know`` -> character knowledge only (KnowledgeRecords),
- ``/sources`` -> provenance for facts (SourceRecords).
Encyclopedia unlocks never alter character knowledge.
"""

from __future__ import annotations

from noosphere40k.domain.errors import LoreUncoveredError
from noosphere40k.lore.retrieval import LoreRepository


class EncyclopediaService:
    def __init__(self, lore: LoreRepository) -> None:
        self.lore = lore

    def encyclopedia_term(self, term_id: str) -> str:
        """Player-layer glossary entry (neutral, sourced, spoiler-aware)."""
        entry = self.lore.get_glossary(term_id)
        if entry is None:
            raise LoreUncoveredError(f"百科没有收录该术语：{term_id}")
        lines = [
            f"{entry.english_name}（{entry.standard_zh_cn}）",
            entry.beginner_explanation,
        ]
        if entry.viewpoint_warning:
            lines.append(f"[观点提示] {entry.viewpoint_warning}")
        if entry.source_refs:
            lines.append("来源：" + "、".join(entry.source_refs))
        return "\n".join(lines)

    def character_knowledge(self, owner_character_id: str, subject_id: str) -> str:
        """Character-layer knowledge only (never the player encyclopedia)."""
        record = self.lore.get_character_knowledge(owner_character_id, subject_id)
        if record is None:
            return f"角色对此一无所知：{subject_id}"
        status_zh = {
            "unknown": "未知",
            "heard_rumor": "听过传言",
            "believes": "相信",
            "doubts": "怀疑",
            "knows": "知道",
        }
        return f"角色状态：{status_zh.get(record.status, record.status)}（{subject_id}）"

    def sources_for(self, fact_id: str) -> str:
        """Provenance for a fact (source records + locators)."""
        fact = self.lore.get_fact(fact_id)
        if fact is None:
            raise LoreUncoveredError(f"没有该事实或未获批准：{fact_id}")
        lines = [f"事实 {fact_id}：{fact.claim}"]
        for source_ref in fact.source_refs:
            source = self.lore.get_source(source_ref)
            if source is None:
                lines.append(f"  - {source_ref}（来源记录缺失）")
                continue
            lines.append(f"  - {source.title}（{source.publisher}，{source.source_class.value}）")
            if source.locator:
                lines.append(f"    定位：{source.locator}")
        return "\n".join(lines)


__all__ = ["EncyclopediaService"]