# 数据模型与协议规格

> 状态：v1.0 工程开发基线  
> 本文中的字段为 MVP 稳定契约；实现可增加内部字段，但不得改变语义。

## 1. 通用约定

- ID 使用小写命名空间字符串，例如 `character.pc.01`、`fact.imperium.adeptus_terra.001`。
- 数据库存 UUID 与内容 ID 分离：数据库主键可用 UUID，跨包引用使用稳定内容 ID。
- 时间全部保存 UTC；游戏内时间单独使用 `WorldTime`。
- 金额和规则数值使用整数，禁止浮点累计误差；置信度例外。
- 所有 Pydantic 模型默认 `extra="forbid"`。
- 事件和快照都保存 `schema_version`。
- 枚举写入数据库时保存稳定英文值，中文只用于显示。

## 2. Campaign

```python
class Campaign(BaseModel):
    campaign_id: str
    name: str
    status: Literal["creating", "active", "paused", "terminal", "archived", "read_only"]
    created_at: datetime
    updated_at: datetime
    state_version: int
    ruleset_version: str
    prompt_version: str
    schema_version: int
    seed: "CampaignSeed"
    settings: "CampaignSettings"
    player_character_id: str
    installed_pack_locks: list["PackLock"]
    last_event_sequence: int
    state_hash: str
```

```python
class CampaignSeed(BaseModel):
    era_id: str
    region_id: str
    faction_id: str
    origin_template_id: str
    start_age: int = 8
    lifepath_mode: Literal["full_life"] = "full_life"
    themes: list[str]
    tone: Literal["grim", "balanced", "heroic_but_costly"]
    power_scale: Literal["human"] = "human"
    opening_hook_id: str
    canon_validation: Literal["passed"]
    validation_evidence: list[str]
```

```python
class CampaignSettings(BaseModel):
    tutorial_level: Literal["concise", "standard", "detailed"]
    narration_length: Literal["short", "standard", "literary"]
    graphic_violence: Literal["fade", "moderate", "strong"]
    combat_frequency: Literal["low", "standard", "high"]
    irreversible_death: bool = False
    spoiler_policy: Literal["strict", "relaxed"] = "strict"
    cloud_private_source_access: bool = False
    max_cost_per_turn_minor: int | None = None
    disabled_content_tags: set[str]
```

## 3. PlayerCharacter

```python
class PlayerCharacter(BaseModel):
    character_id: str
    display_name: str
    pronouns: str | None
    birth_world_time: "WorldTime"
    chronological_age_days: int
    subjective_age_days: int
    life_stage: "LifeStage"
    origin_id: str
    guardian_ids: list[str]
    household_id: str | None
    social_class_tags: set[str]
    faction_memberships: list["Membership"]
    vocation_history: list["VocationPeriod"]
    attributes: dict["AttributeId", int]
    skills: dict[str, "SkillState"]
    traits: set[str]
    conditions: list["Condition"]
    wounds: list["Wound"]
    inventory: list["InventoryEntry"]
    resources: dict[str, int]
    beliefs: list["Belief"]
    goals: list["Goal"]
    knowledge_index_version: int
    legacy: "LegacyState"
```

`chronological_age_days` 随银河客观时间推进；`subjective_age_days` 排除低温休眠并按内容规则处理亚空间时间差。界面显示年龄时必须说明采用哪一种。

### 3.1 属性

稳定属性 ID：

```text
melee
ranged
body
agility
intellect
awareness
willpower
presence
```

### 3.2 SkillState

```python
class SkillState(BaseModel):
    skill_id: str
    rank: Literal["untrained", "trained", "specialist", "master"]
    progress: int
    learned_from_event_ids: list[str]
```

## 4. WorldTime 与生命阶段

```python
class WorldTime(BaseModel):
    era_id: str
    local_calendar_id: str
    local_year: int | None
    local_day: int | None
    local_second: int | None
    ordering_key: int
    precision: Literal["era", "year", "day", "second"]
    uncertainty_note: str | None
```

不要求把所有 40K 日期强制转换成一个自称绝对准确的公历。`ordering_key`只用于同一内容包中的排序，资料有争议时保留不确定性。

```text
childhood
adolescence
youth
adulthood
late_life
terminal
```

## 5. NPC 与关系

```python
class NPC(BaseModel):
    character_id: str
    display_name: str
    origin: Literal["canon", "authored_original", "generated_original"]
    entity_id: str | None
    template_id: str
    age_state: "AgeState"
    roles: list[str]
    faction_memberships: list["Membership"]
    motivations: list[str]
    fears: list[str]
    resources: dict[str, int]
    conditions: list["Condition"]
    frozen_profile: bool
    source_refs: list[str]
```

```python
class Relationship(BaseModel):
    relationship_id: str
    subject_id: str
    object_id: str
    type: str
    direction: Literal["directed", "mutual"]
    trust: int
    obligation: int
    suspicion: int
    hostility: int
    public_visibility: Literal["public", "private", "secret"]
    valid_from_event_id: str
    valid_to_event_id: str | None
    evidence_event_ids: list[str]
    origin: Literal["canon", "authored_original", "campaign_event"]
```

各关系轴范围 `-100..100`。不要自动计算为一个“好感度”。

## 6. Lore 数据

```python
class SourceRecord(BaseModel):
    source_id: str
    title: str
    publisher: str
    source_class: Literal["A1", "A2", "A3", "B"]
    edition: str | None
    publication_date: date | None
    language: str
    locator: str
    access_type: Literal["public_web", "local_owned_copy", "metadata_only"]
    canon_scope: list[str]
    viewpoint: Literal["editorial", "in_universe", "character_limited"]
    rights_profile: str
    review_status: Literal["candidate", "approved", "rejected", "superseded"]
    reviewed_by: str | None
    reviewed_at: datetime | None
```

```python
class LoreFact(BaseModel):
    fact_id: str
    claim: str
    fact_type: Literal[
        "canon_editorial", "canon_perspective", "licensed_derived",
        "disputed", "game_original", "campaign_event", "inference"
    ]
    entity_ids: list[str]
    relation_ids: list[str]
    valid_time: list[str]
    valid_regions: list[str]
    source_refs: list[str]
    confidence: Literal["confirmed", "disputed", "perspective_only"]
    conflicts_with: list[str]
    spoiler_level: int
    review_status: Literal["candidate", "approved", "rejected", "superseded"]
    pack_id: str
    pack_version: str
```

```python
class LoreEntity(BaseModel):
    entity_id: str
    canonical_name: str
    entity_type: str
    aliases: list["LocalizedAlias"]
    parent_entity_ids: list[str]
    origin: Literal["canon", "licensed", "game_original"]
    valid_time: list[str]
    source_refs: list[str]
    review_status: Literal["candidate", "approved", "rejected", "superseded"]
```

```python
class GlossaryEntry(BaseModel):
    term_id: str
    entity_id: str | None
    english_name: str
    standard_zh_cn: str
    aliases_zh_cn: list[str]
    deprecated_translations: list[str]
    child_explanation: str
    beginner_explanation: str
    deep_explanation: str
    viewpoint_warning: str | None
    spoiler_level: int
    source_refs: list[str]
```

## 7. 角色知识

```python
class KnowledgeRecord(BaseModel):
    owner_character_id: str
    subject_id: str                 # fact_id/entity_id/topic_id
    status: Literal["unknown", "heard_rumor", "believes", "doubts", "knows"]
    reliability_basis_points: int   # 0..10000
    learned_at_event_id: str | None
    learned_from_character_id: str | None
    source_viewpoint: str | None
    superseded_by_event_id: str | None
```

玩家百科解锁另存 `EncyclopediaUnlock`，禁止复用 `KnowledgeRecord`。

## 8. 场景与生命路径内容

```python
class SceneDefinition(BaseModel):
    scene_id: str
    pack_id: str
    title: str
    allowed_life_stages: set[str]
    entry_conditions: list["Predicate"]
    exit_conditions: list["Predicate"]
    location_id: str
    participant_selectors: list["ParticipantSelector"]
    lore_requirements: "LoreRequirementSet"
    content_tags: set[str]
    objectives: list["ObjectiveDefinition"]
    action_templates: list["ActionTemplate"]
    fallback_narration_template_id: str
    next_scene_rules: list["TransitionRule"]
```

```python
class LifeTransitionDefinition(BaseModel):
    transition_id: str
    from_stage: str
    to_stage: str
    min_time_days: int
    required_milestones: list[str]
    choice_prompts: list[str]
    aging_ruleset_id: str
    summary_template_id: str
    confirmation_required: bool = True
```

每个场景必须具有模板降级文本。模板可以插值规则结果和已批准实体显示名，但不能调用新 Lore。

## 9. ActionIntent

```python
class ActionIntent(BaseModel):
    intent_id: str
    actor_id: str
    action_type: Literal[
        "observe", "move", "speak", "ask", "use_item", "work",
        "study", "rest", "attack", "defend", "flee", "custom"
    ]
    target_ids: list[str]
    free_text_summary: str
    declared_goal: str | None
    proposed_method: str | None
    requested_meta_command: str | None
    parser_confidence_basis_points: int
    unresolved_references: list[str]
```

解析置信度低或目标不唯一时，返回澄清选项；不得猜测攻击目标、资源消费或不可逆行为。

## 10. 规则请求与结果

```python
class CheckRequest(BaseModel):
    check_id: str
    actor_id: str
    attribute_id: str
    skill_id: str | None
    difficulty_modifier: int
    situation_modifiers: list["Modifier"]
    risk: Literal["trivial", "low", "standard", "high", "lethal"]
    visibility: Literal["open", "hidden"]
    stakes: list[str]
```

```python
class Modifier(BaseModel):
    modifier_id: str
    value: int
    source_type: Literal["rule", "skill", "trait", "item", "condition", "scene"]
    source_id: str
    display_reason: str
```

```python
class RuleResolution(BaseModel):
    checks: list["CheckResult"]
    deterministic_events: list["EventProposal"]
    narration_constraints: list[str]
    hidden_information_refs: list[str]
```

## 11. LLM NarrationRequest

只发送完成叙事所需的最小上下文：

```python
class NarrationRequest(BaseModel):
    trace_id: str
    campaign_id: str
    turn_number: int
    player_input: str
    action_intent: ActionIntent
    visible_scene: "VisibleScene"
    visible_character_state: "VisibleCharacterState"
    visible_relationships: list["VisibleRelationship"]
    allowed_lore_facts: list["PromptFact"]
    allowed_original_entity_ids: list[str]
    forbidden_claim_topics: list[str]
    rule_resolution: RuleResolution
    tutorial_payload: list["TutorialHint"]
    style_settings: "NarrationStyle"
    content_limits: set[str]
```

`PromptFact` 只包含最小事实陈述、fact ID、视角标签和可用范围，不包含未经批准的整页原文。

## 12. LLM NarrationResponse

```python
class NarrationResponse(BaseModel):
    narration: str
    dialogue: list["DialogueLine"]
    suggested_actions: list["SuggestedAction"]
    proposed_events: list["EventProposal"]
    lore_claims: list["LoreClaim"]
    glossary_term_ids: list[str]
    uncertainties: list["NarrativeUncertainty"]
```

```python
class LoreClaim(BaseModel):
    text: str
    claim_type: Literal["canon", "perspective", "game_original", "campaign_event", "decorative"]
    supporting_fact_ids: list[str]
    supporting_entity_ids: list[str]
```

响应约束：

- `proposed_events` 只能使用第 13 节白名单。
- `canon` 必须至少一个批准 fact ID。
- `game_original` 只能引用已允许原创实体或提交合法的新原创实体提案。
- `decorative` 不能包含专名、历史、机构权限、科技能力或时间断言。
- `uncertainties` 不得被叙述成确定事实。

## 13. 事件白名单

MVP 稳定事件类型：

```text
CampaignCreated
CampaignSettingChanged
PlayerInputAccepted
ActionIntentResolved
RandomDrawn
CheckResolved
TimeAdvanced
LifeStageChanged
AttributeChanged
SkillProgressed
TraitAdded
TraitRemoved
ConditionApplied
ConditionRemoved
WoundApplied
WoundChanged
CharacterDied
InventoryAdded
InventoryRemoved
ResourceChanged
RelationshipChanged
KnowledgeChanged
EncyclopediaUnlocked
GoalAdded
GoalUpdated
GoalCompleted
VocationStarted
VocationEnded
LocationChanged
NPCIntroduced
NPCProfileFrozen
SceneStarted
SceneCompleted
LoreClaimUsed
NarrationRecorded
CampaignTerminated
SnapshotCreated
```

LLM 永远不能直接提交：`RandomDrawn`、`CheckResolved`、`AttributeChanged`、`CharacterDied`、`CampaignTerminated`、`SnapshotCreated`。它只能提出叙事相关事件，由规则层派生最终事件。

## 14. EventEnvelope

```python
class EventEnvelope(BaseModel):
    event_id: str
    campaign_id: str
    sequence: int
    turn_id: str
    event_type: str
    schema_version: int
    occurred_at_utc: datetime
    world_time: WorldTime
    actor_id: str | None
    causation_event_id: str | None
    correlation_id: str
    origin: Literal["player", "rules", "content", "llm_validated", "system"]
    payload: dict
    prior_state_hash: str
    resulting_state_hash: str
```

事件 reducer 必须纯函数化：`new_state = reduce(old_state, event)`。

## 15. SQLite 表

最低表集合：

```text
campaigns
campaign_events
campaign_snapshots
characters
relationships
knowledge_records
encyclopedia_unlocks
lore_sources
lore_entities
lore_facts
lore_relations
lore_fact_sources
glossary_entries
content_packs
content_pack_locks
scenes
llm_audit
schema_migrations
```

要求：

- `campaign_events(campaign_id, sequence)` 唯一。
- `lore_facts(review_status, pack_id)`、实体别名、时间范围建立索引。
- Lore FTS 表只同步批准事实和可检索词条。
- 私有来源原文不进入上述主数据库；只保存不可反推出内容的本地引用 ID。
- 快照保存压缩 JSON 与 SHA-256，加载后重新计算状态哈希。

## 16. Pack Validator

内容包构建必须拒绝：

- 未知 Schema 版本。
- 跨包引用但 manifest 未声明依赖。
- `approved` 事实没有来源。
- `game_original` 实体没有父级世界约束。
- 场景缺少硬 LoreRequirement 或 fallback 模板。
- 童年场景含成人情色标签或强制高强度暴力。
- 同一内容 ID 在同版本重复定义。
- 时间范围不相交的实体被同场景强制引用。
- 模板包含任意代码执行、文件读取或网络调用。

## 17. 向后兼容

- 事件 payload 只能增加可选字段；删除/改名需要新事件版本和迁移器。
- 已发布枚举值不得改变含义。
- Pack 使用语义版本；破坏性 Schema 变化提升主版本。
- 存档锁定 pack 精确版本和哈希。
- 迁移失败时保留原数据库和导出备份，战役以只读模式打开。

## 18. 支撑模型最低定义

为避免实现者自行猜测，前文引用的支撑模型最低字段如下。业务需要可以增加字段，但不得删除这些语义。

```python
class PackLock(BaseModel):
    pack_id: str
    version: str
    content_hash: str

class Membership(BaseModel):
    faction_id: str
    role_id: str
    rank_id: str | None
    started_event_id: str
    ended_event_id: str | None

class VocationPeriod(BaseModel):
    vocation_id: str
    started_event_id: str
    ended_event_id: str | None
    organization_id: str | None
    outcome_tags: set[str]

class Condition(BaseModel):
    condition_id: str
    severity: int
    applied_event_id: str
    expires_world_time: WorldTime | None

class Wound(BaseModel):
    wound_id: str
    location: str
    severity: Literal["minor", "major", "critical", "terminal"]
    cause_event_id: str
    treatment_state: str

class InventoryEntry(BaseModel):
    instance_id: str
    item_template_id: str
    quantity: int
    condition: int
    provenance_event_id: str

class Belief(BaseModel):
    belief_id: str
    statement: str
    strength: int
    origin_event_id: str

class Goal(BaseModel):
    goal_id: str
    description: str
    status: Literal["active", "completed", "failed", "abandoned"]
    created_event_id: str

class LegacyState(BaseModel):
    successor_character_ids: list[str]
    entrusted_item_ids: list[str]
    entrusted_fact_ids: list[str]
    reputation_tags: set[str]
    terminal_summary_id: str | None

class AgeState(BaseModel):
    chronological_age_days: int
    subjective_age_days: int
    life_stage: str

class LocalizedAlias(BaseModel):
    language: str
    text: str
    alias_type: Literal["official", "common", "deprecated", "transliteration"]
```

## 19. 内容支撑模型

```python
class Predicate(BaseModel):
    predicate_type: str
    subject_id: str | None
    operator: str
    expected: object

class ParticipantSelector(BaseModel):
    slot_id: str
    required_tags: set[str]
    preferred_character_ids: list[str]
    create_from_template_id: str | None

class LoreRequirement(BaseModel):
    requirement_id: str
    fact_id: str | None
    topic_id: str | None
    purpose: str
    minimum_source_class: Literal["A1", "A2", "A3", "B"]
    hard: bool
    fallback_template_id: str | None

class LoreRequirementSet(BaseModel):
    hard: list[LoreRequirement]
    optional: list[LoreRequirement]
    forbidden_topics: set[str]

class ObjectiveDefinition(BaseModel):
    objective_id: str
    display_text: str
    completion_predicates: list[Predicate]
    failure_predicates: list[Predicate]

class ActionTemplate(BaseModel):
    action_template_id: str
    display_text: str
    action_type: str
    target_selector: ParticipantSelector | None
    check_template_id: str | None
    content_tags: set[str]

class TransitionRule(BaseModel):
    priority: int
    predicates: list[Predicate]
    next_scene_id: str | None
    terminal_outcome_id: str | None
```

## 20. 事件提案与显示模型

```python
class EventProposal(BaseModel):
    proposal_type: str
    target_id: str | None
    values: dict[str, int | str | bool | None]
    reason: str
    supporting_event_ids: list[str]
    supporting_fact_ids: list[str]

class CheckResult(BaseModel):
    check_id: str
    roll: int
    target: int
    success: bool
    margin_degrees: int
    special: Literal["none", "critical_success", "critical_failure"]
    modifiers: list[Modifier]
    rng_event_id: str

class VisibleScene(BaseModel):
    scene_id: str
    title: str
    location_display: str
    visible_character_ids: list[str]
    visible_objects: list[str]
    active_objectives: list[str]
    immediate_pressures: list[str]

class VisibleCharacterState(BaseModel):
    display_name: str
    displayed_age: str
    life_stage: str
    visible_conditions: list[str]
    visible_resources: dict[str, int]
    role_summary: str

class VisibleRelationship(BaseModel):
    character_id: str
    display_name: str
    player_known_summary: str

class PromptFact(BaseModel):
    fact_id: str
    statement: str
    viewpoint: str
    allowed_usage: Literal["objective", "perspective_only"]
    source_ref_ids: list[str]

class TutorialHint(BaseModel):
    term_id: str
    level: Literal["child", "beginner", "deep"]
    text: str
    player_layer: bool

class NarrationStyle(BaseModel):
    language: Literal["zh-CN"]
    length: Literal["short", "standard", "literary"]
    tutorial_level: Literal["concise", "standard", "detailed"]
    max_suggested_actions: int
```

任何未在稳定契约中定义的复合模型，必须在实现 PR 中补充 Schema 和契约测试，不能用无约束 `dict` 穿过应用边界。
