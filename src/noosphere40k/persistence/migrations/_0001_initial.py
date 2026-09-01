"""Migration 0001: initial SQLite schema (DATA_PROTOCOL_SPEC §15)."""

from __future__ import annotations

from noosphere40k.persistence.db import Migration

_STATEMENTS: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS campaigns (
        campaign_id TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at_utc TEXT NOT NULL,
        updated_at_utc TEXT NOT NULL,
        state_version INTEGER NOT NULL DEFAULT 0,
        ruleset_version TEXT NOT NULL DEFAULT '0.1.0',
        prompt_version TEXT NOT NULL,
        schema_version INTEGER NOT NULL,
        seed_json TEXT NOT NULL,
        settings_json TEXT NOT NULL,
        pack_locks_json TEXT NOT NULL DEFAULT '[]',
        last_event_sequence INTEGER NOT NULL DEFAULT 0,
        state_hash TEXT NOT NULL DEFAULT ''
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS campaign_events (
        campaign_id TEXT NOT NULL,
        sequence INTEGER NOT NULL,
        event_id TEXT NOT NULL,
        turn_id TEXT NOT NULL,
        event_type TEXT NOT NULL,
        event_schema_version INTEGER NOT NULL,
        occurred_at_utc TEXT NOT NULL,
        world_time_json TEXT,
        actor_id TEXT,
        causation_event_id TEXT,
        correlation_id TEXT NOT NULL,
        origin TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        prior_state_hash TEXT NOT NULL DEFAULT '',
        resulting_state_hash TEXT NOT NULL DEFAULT '',
        PRIMARY KEY (campaign_id, sequence)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS campaign_snapshots (
        campaign_id TEXT NOT NULL,
        snapshot_id TEXT NOT NULL,
        up_to_sequence INTEGER NOT NULL,
        state_json TEXT NOT NULL,
        state_hash TEXT NOT NULL,
        created_at_utc TEXT NOT NULL,
        PRIMARY KEY (campaign_id, up_to_sequence)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS characters (
        character_id TEXT PRIMARY KEY,
        campaign_id TEXT NOT NULL,
        display_name TEXT NOT NULL,
        birth_world_time_json TEXT NOT NULL,
        life_stage TEXT NOT NULL,
        state_json TEXT NOT NULL,
        updated_at_utc TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS relationships (
        relationship_id TEXT PRIMARY KEY,
        campaign_id TEXT NOT NULL,
        subject_id TEXT NOT NULL,
        object_id TEXT NOT NULL,
        relation_type TEXT NOT NULL,
        direction TEXT NOT NULL,
        trust INTEGER NOT NULL DEFAULT 0,
        obligation INTEGER NOT NULL DEFAULT 0,
        suspicion INTEGER NOT NULL DEFAULT 0,
        hostility INTEGER NOT NULL DEFAULT 0,
        public_visibility TEXT NOT NULL,
        origin TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS knowledge_records (
        owner_character_id TEXT NOT NULL,
        subject_id TEXT NOT NULL,
        status TEXT NOT NULL,
        reliability_basis_points INTEGER NOT NULL DEFAULT 0,
        learned_at_event_id TEXT,
        learned_from_character_id TEXT,
        source_viewpoint TEXT,
        superseded_by_event_id TEXT,
        PRIMARY KEY (owner_character_id, subject_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS encyclopedia_unlocks (
        owner_character_id TEXT NOT NULL,
        term_id TEXT NOT NULL,
        visibility TEXT NOT NULL,
        unlocked_at_event_id TEXT NOT NULL,
        PRIMARY KEY (owner_character_id, term_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS lore_sources (
        source_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        publisher TEXT NOT NULL,
        source_class TEXT NOT NULL,
        edition TEXT,
        publication_date TEXT,
        language TEXT NOT NULL,
        locator TEXT NOT NULL,
        access_type TEXT NOT NULL,
        canon_scope_json TEXT NOT NULL DEFAULT '[]',
        viewpoint TEXT NOT NULL,
        rights_profile TEXT NOT NULL,
        review_status TEXT NOT NULL DEFAULT 'candidate',
        reviewed_by TEXT,
        reviewed_at_utc TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS lore_entities (
        entity_id TEXT PRIMARY KEY,
        canonical_name TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        aliases_json TEXT NOT NULL DEFAULT '[]',
        parent_entity_ids_json TEXT NOT NULL DEFAULT '[]',
        origin TEXT NOT NULL,
        valid_time_json TEXT NOT NULL DEFAULT '[]',
        source_refs_json TEXT NOT NULL DEFAULT '[]',
        review_status TEXT NOT NULL DEFAULT 'candidate',
        pack_id TEXT NOT NULL DEFAULT ''
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS lore_facts (
        fact_id TEXT PRIMARY KEY,
        claim TEXT NOT NULL,
        fact_type TEXT NOT NULL,
        entity_ids_json TEXT NOT NULL DEFAULT '[]',
        relation_ids_json TEXT NOT NULL DEFAULT '[]',
        valid_time_json TEXT NOT NULL DEFAULT '[]',
        valid_regions_json TEXT NOT NULL DEFAULT '[]',
        source_refs_json TEXT NOT NULL DEFAULT '[]',
        confidence TEXT NOT NULL,
        conflicts_with_json TEXT NOT NULL DEFAULT '[]',
        spoiler_level INTEGER NOT NULL DEFAULT 0,
        review_status TEXT NOT NULL DEFAULT 'candidate',
        pack_id TEXT NOT NULL,
        pack_version TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS lore_relations (
        relation_id TEXT PRIMARY KEY,
        relation_type TEXT NOT NULL,
        subject_entity_id TEXT NOT NULL,
        object_entity_id TEXT NOT NULL,
        valid_time_json TEXT NOT NULL DEFAULT '[]',
        source_refs_json TEXT NOT NULL DEFAULT '[]',
        review_status TEXT NOT NULL DEFAULT 'candidate',
        pack_id TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS lore_fact_sources (
        fact_id TEXT NOT NULL,
        source_id TEXT NOT NULL,
        PRIMARY KEY (fact_id, source_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS glossary_entries (
        term_id TEXT PRIMARY KEY,
        entity_id TEXT,
        english_name TEXT NOT NULL,
        standard_zh_cn TEXT NOT NULL,
        aliases_zh_cn_json TEXT NOT NULL DEFAULT '[]',
        deprecated_translations_json TEXT NOT NULL DEFAULT '[]',
        child_explanation TEXT NOT NULL,
        beginner_explanation TEXT NOT NULL,
        deep_explanation TEXT NOT NULL,
        viewpoint_warning TEXT,
        spoiler_level INTEGER NOT NULL DEFAULT 0,
        source_refs_json TEXT NOT NULL DEFAULT '[]'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_packs (
        pack_id TEXT NOT NULL,
        version TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        display_name TEXT NOT NULL,
        installed_at_utc TEXT NOT NULL,
        PRIMARY KEY (pack_id, version)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_pack_locks (
        campaign_id TEXT NOT NULL,
        pack_id TEXT NOT NULL,
        version TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        PRIMARY KEY (campaign_id, pack_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scenes (
        scene_id TEXT PRIMARY KEY,
        pack_id TEXT NOT NULL,
        title TEXT NOT NULL,
        fallback_narration_template_id TEXT NOT NULL,
        definition_json TEXT NOT NULL,
        review_status TEXT NOT NULL DEFAULT 'candidate'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS llm_audit (
        trace_id TEXT NOT NULL,
        turn_id TEXT NOT NULL,
        campaign_id TEXT NOT NULL,
        provider TEXT NOT NULL,
        model TEXT,
        prompt_version TEXT,
        tokens_prompt INTEGER,
        tokens_completion INTEGER,
        estimated_cost_minor TEXT,
        validation_decision TEXT NOT NULL DEFAULT 'pending',
        created_at_utc TEXT NOT NULL,
        PRIMARY KEY (trace_id, turn_id)
    )
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_campaign_events_type
        ON campaign_events (campaign_id, event_type)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_lore_facts_review_pack
        ON lore_facts (review_status, pack_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_knowledge_owner
        ON knowledge_records (owner_character_id)
    """,
)

MIGRATION_0001 = Migration(version=1, name="initial_schema", statements=_STATEMENTS)