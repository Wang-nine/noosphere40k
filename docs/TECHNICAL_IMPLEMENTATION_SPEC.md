# 技术实现规格

> 状态：v1.0 工程开发基线  
> 适用范围：MVP 终端版、单人、本地存档、可插拔 LLM  
> 上位文档：`WH40K_LLM_TEXT_GAME_DESIGN.md`

## 1. 固定技术决策

接手开发的 AI 除非提交 ADR 并说明兼容迁移，不应自行替换以下基础决策：

| 项目 | 决策 |
|---|---|
| 语言 | Python 3.12+ |
| 项目管理 | `pyproject.toml`，优先使用 `uv`，保持标准 pip 可安装 |
| CLI | Typer |
| 终端渲染 | Rich；业务逻辑不得依赖颜色和终端宽度 |
| 数据校验 | Pydantic v2 |
| 持久化 | SQLite 3 + SQLAlchemy 2.x + 编号迁移 |
| 全文检索 | SQLite FTS5，MVP 必须可在无向量库时运行 |
| 向量检索 | 可选插件，不作为 MVP 启动条件 |
| LLM | 自定义 Provider Adapter；禁止业务层直接调用厂商 SDK |
| 测试 | pytest、固定事件夹具、Provider stub |
| 静态质量 | Ruff + MyPy（核心域 strict） |
| Agent 框架 | MVP 禁用；采用显式单回合管线 |

## 2. 非功能指标

- 无 LLM 时，启动、角色/百科浏览、存档、规则重放和模板降级均可运行。
- 普通本地命令 P95 小于 200 ms；FTS5 检索 P95 小于 500 ms（10 万事实以内的开发机基准）。
- LLM 超时默认 45 秒，可配置；期间允许 `Ctrl+C` 安全取消，不提交半回合。
- 每次已提交回合必须满足数据库事务原子性。
- 进程在任意写入点崩溃后，最近已提交回合可正常加载。
- Windows Terminal、常见 Linux 终端和 macOS Terminal 均可使用；提供 `--no-color`。
- 所有外部文本都按不可信输入处理，包括玩家输入、网页、文档和 LLM 输出。

## 3. 仓库结构

```text
pyproject.toml
README.md
.env.example                 # 只列变量名，不含值
src/noosphere40k/
  __init__.py
  cli/
    app.py
    render.py
    commands.py
  application/
    turn_service.py
    campaign_service.py
    save_service.py
    encyclopedia_service.py
  domain/
    models.py
    events.py
    enums.py
    errors.py
  rules/
    checks.py
    combat.py
    wounds.py
    aging.py
    lifepath.py
    rng.py
  lore/
    registry.py
    retrieval.py
    coverage_gate.py
    claim_guard.py
    knowledge_filter.py
    importers/
  llm/
    base.py
    openai_compatible.py
    stub.py
    prompts.py
    schemas.py
  persistence/
    db.py
    repositories.py
    migrations/
    backup.py
  content/
    loader.py
    validator.py
  security/
    secrets.py
    sanitization.py
  observability/
    logging.py
    audit.py
content/
  lore_packs/
  scenario_packs/
tests/
  unit/
  integration/
  contract/
  canon/
  fixtures/
scripts/
docs/
```

依赖方向必须是：

```text
cli -> application -> domain
application -> rules/lore/llm/persistence/content
rules -> domain
lore -> domain
llm -> domain schemas
persistence -> domain
domain -> Python 标准库/Pydantic（不得依赖 CLI、数据库或厂商 SDK）
```

## 4. CLI 契约

### 4.1 程序级命令

```text
noosphere new
noosphere continue [CAMPAIGN_ID]
noosphere saves list
noosphere saves export CAMPAIGN_ID PATH
noosphere saves import PATH
noosphere lore search QUERY
noosphere lore source FACT_OR_ENTITY_ID
noosphere lore validate PACK_PATH
noosphere content validate PACK_PATH
noosphere doctor
noosphere version
```

### 4.2 游戏内命令

自然语言默认解释为角色行动。以 `/` 开头的内容只作为元命令：

```text
/help
/suggest
/why <内容>
/encyclopedia <术语>
/know <主题>
/relations
/recap
/character
/lifepath
/roll-details
/sources
/save [名称]
/settings
/pause
/skip
/quit
```

- 中文别名可用，但内部命令 ID 使用英文。
- 未识别的 `/command` 不发送给 LLM。
- 所有命令返回结构化 `CommandResult`，渲染层负责输出。

## 5. 核心状态机

### 5.1 CampaignStatus

```text
CREATING -> ACTIVE -> TERMINAL -> ARCHIVED
                \-> PAUSED
任何状态 -> READ_ONLY（缺少内容包或迁移失败）
```

### 5.2 LifeStage

```text
CHILDHOOD -> ADOLESCENCE -> YOUTH -> ADULTHOOD -> LATE_LIFE -> TERMINAL
     \             \          \          \             \
      +-------------+----------+-----------+---------------> TERMINAL
```

阶段跳转只能由规则引擎接受 `LifeTransitionProposal` 后产生。LLM 可以建议时间跳跃，不能直接改变年龄。

默认阶段参考：

| 阶段 | 普通帝国人类参考年龄 | 主要系统 |
|---|---:|---|
| CHILDHOOD | 6–11 | 家庭依附、基础学习、观察、性格倾向 |
| ADOLESCENCE | 12–16 | 教育/训导、职业筛选、同伴、制度压力 |
| YOUTH | 17–25 | 正式职业、服役、独立关系、重大风险 |
| ADULTHOOD | 26–45 | 职业深化、家庭/组织责任、权力与代价 |
| LATE_LIFE | 46+ | 健康、继承、记忆、影响力、终局准备 |

这些年龄不能硬编码为银河通则；内容包可以根据世界、阶层、延寿、航行和休眠进行覆盖。

### 5.3 TurnState

```text
IDLE
 -> PARSING_INTENT
 -> PRECHECK
 -> LORE_GATE
 -> RULE_RESOLUTION
 -> NARRATION
 -> VALIDATION
 -> COMMITTING
 -> IDLE
```

任一步失败都不得留下部分状态。`NARRATION` 超时可进入 `TEMPLATE_FALLBACK`，然后继续 `VALIDATION`。

## 6. 单回合应用管线

```python
async def play_turn(campaign_id: str, raw_input: str) -> TurnResult:
    snapshot = repo.load_consistent_snapshot(campaign_id)
    intent = intent_parser.parse(raw_input, snapshot.visible_context)
    precheck = action_policy.validate(intent, snapshot)
    lore_context = lore_gate.resolve(precheck.lore_requirements, snapshot)
    rule_result = rules.resolve(precheck.rule_requests, snapshot)
    request = context_builder.build(snapshot, intent, lore_context, rule_result)
    draft = await narrator.generate(request)
    validated = output_guard.validate(draft, request, snapshot)
    events = event_factory.from_validated(validated, rule_result)
    new_state = reducer.apply(snapshot, events)
    repo.commit_turn(snapshot.version, events, new_state)
    return presenter.build(validated, rule_result, new_state)
```

必须实现乐观版本检查。若提交时 `snapshot.version` 已变化，整个回合放弃并提示重新执行，不合并 LLM 输出。

## 7. 规则引擎

### 7.1 属性与目标值

- 属性存储范围 `1..100`，普通可玩人类创建时通常 `20..45`。
- 最终目标值默认钳制到 `5..95`；特殊特性可以改变上下限，但必须由规则内容定义。
- 标准难度修正：`-30, -20, -10, 0, +10, +20, +30`。
- 技能状态：`UNTRAINED, TRAINED, SPECIALIST, MASTER`；具体加值由规则版本表配置。
- 01 为特殊成功，100 为特殊失败；具体后果由行动风险等级决定，不自动制造世界观事实。

### 7.2 检定结果

```python
class CheckResult(BaseModel):
    check_id: str
    roll: int
    target: int
    success: bool
    margin_degrees: int
    special: Literal["none", "critical_success", "critical_failure"]
    modifiers: list[Modifier]
    rng_event_id: str
```

所有修正必须有 `source`：规则、装备、状态、场景或玩家选择。禁止提交没有来源说明的临时数值。

### 7.3 随机数

- RNG 只存在于 `rules/rng.py`。
- 每个骰点先产生 `RandomDrawn` 事件，再进行规则计算。
- 事件保存实际结果，因此重放不依赖 Python 后续版本是否保持相同随机算法。
- 测试可注入序列 RNG；生产环境不得让 LLM、提示词或前端提供骰点。

### 7.4 年龄成长

- 不使用单一等级系统。
- `LifeTransition` 输入包括时间跨度、阶段、经历标签、教育、职业、伤病和关系。
- 成长结算器输出属性变化提案、技能经验、健康变化和关系老化事件。
- 每项永久变化必须能追溯到经历或年龄规则。
- 时间跳跃前显示不可逆影响摘要并要求玩家确认。

## 8. LLM Provider 接口

```python
class LLMProvider(Protocol):
    async def generate_structured(
        self,
        *,
        messages: list[Message],
        response_model: type[BaseModel],
        timeout_seconds: float,
        request_metadata: dict[str, str],
    ) -> BaseModel: ...

    async def healthcheck(self) -> ProviderHealth: ...
```

要求：

- 业务层只接触上述接口。
- Provider 负责鉴权、重试、限流错误映射和厂商响应解析。
- 应用层最多允许一次“结构化修复”重试；网络重试由 Provider 处理且必须保证不重复提交状态。
- 原始请求/响应日志默认关闭；开启后也必须脱敏。
- 模型名称、提示版本、token 和估算费用记录到回合审计，但 API key 永不记录。

## 9. LLM 职责拆分

MVP 可以让同一模型承担多个调用，但逻辑角色必须分开：

1. `IntentParser`：自然语言转 `ActionIntent`，不做规则裁决。
2. `Narrator`：只基于获准事实和规则结果生成叙述。
3. `ClaimExtractor`：抽取输出中的世界观断言供程序比对。
4. `RecapWriter`：把已提交事件转成玩家回顾，不产生新事件。

所有角色都使用不同 JSON Schema 和最小上下文。禁止建立可自由循环调用工具的自主 Agent。

## 10. Lore 检索接口

```python
class LoreRepository(Protocol):
    def retrieve(self, query: LoreQuery) -> LoreRetrievalResult: ...
    def get_fact(self, fact_id: str) -> Fact | None: ...
    def get_entity(self, entity_id: str) -> Entity | None: ...
    def coverage(self, requirement: LoreRequirement) -> CoverageDecision: ...
```

检索顺序：

1. 精确实体 ID/别名匹配。
2. 年代、地域、来源状态和知识权限过滤。
3. FTS5/BM25 召回。
4. 可选向量重排。
5. 按事实最小单元返回，不把整章材料交给模型。

任何 `review_status != approved` 的资料必须在查询层过滤，而不是依赖调用方记得过滤。

## 11. 存档与事务

- 应用数据库默认路径由平台数据目录决定，不写死当前工作目录。
- SQLite 开启 foreign keys；运行期优先 WAL；导出前执行 checkpoint。
- 事件表只追加，不更新业务字段；撤销由新事件表示。
- 每 20 个已提交回合或生命阶段转换时创建快照。
- 每次启动验证内容包哈希、Schema 版本和最后快照校验和。
- 导出使用 SQLite backup API，不直接复制正在写入的数据库文件。
- 死亡后战役进入 `TERMINAL`；允许回顾和导出，不允许继续提交角色行动。

## 12. 配置

优先级从高到低：CLI 参数、环境变量、用户配置、项目默认值。

建议环境变量：

```text
NOOSPHERE_LLM_PROVIDER
NOOSPHERE_LLM_BASE_URL
NOOSPHERE_LLM_MODEL
NOOSPHERE_LLM_API_KEY
NOOSPHERE_DATA_DIR
NOOSPHERE_LOG_LEVEL
```

要求：

- `.env` 仅用于本地开发，加入 `.gitignore`。
- `doctor` 只报告密钥是否存在，不打印值或前后缀。
- 用户配置保存教学密度、内容限制、费用上限和终端偏好。
- 战役级设置在创建后写入存档，影响规则的设置不能静默改变。

## 13. 错误与降级

稳定错误码：

```text
E_CONFIG_INVALID
E_PROVIDER_UNAVAILABLE
E_PROVIDER_TIMEOUT
E_PROVIDER_SCHEMA
E_LORE_UNCOVERED
E_LORE_CONFLICT
E_CANON_VIOLATION
E_RULE_INVALID_ACTION
E_SAVE_CONFLICT
E_SAVE_CORRUPT
E_CONTENT_MISSING
E_MIGRATION_FAILED
```

降级顺序：

1. 结构化响应不合法：同模型约束修复一次。
2. 仍失败：使用规则结果和审核模板完成回合。
3. Lore 硬需求未覆盖：阻止对应事实，提供可行替代行动。
4. Provider 不可用：保持未提交状态，允许重试、切换 Provider 或进入离线浏览。
5. 存档校验失败：只读打开，先备份后尝试恢复。

## 14. 日志与审计

日志分为：

- `application.log`：结构化运行日志，不保存完整玩家文本和资料原文。
- `audit_events`：回合 ID、规则结果、事实 ID、来源 ID、验证决策、模型元数据和状态 diff。
- `debug_llm`：显式开启才保存，自动脱敏，可单独删除。

每个回合共享 `trace_id`。玩家执行 `/sources`、`/roll-details` 时从审计记录读取，不能让模型回忆。

## 15. 安全边界

- 玩家输入永远不能直接变成 SQL、路径、模板代码或系统提示。
- 导入压缩包防止路径穿越、压缩炸弹和符号链接逃逸。
- 内容包必须校验 Schema、哈希和 pack ID；未来签名机制预留字段。
- 禁止加载内容包中的可执行 Python。
- LLM 输出只接受枚举事件类型；未知字段按严格模式拒绝。
- 私有资料路径和内容不进入云端请求，除非用户显式允许该来源。

## 16. 完成定义

技术骨架只有在以下条件同时满足时才算可交付：

- `new -> 首回合 -> save -> continue -> 死亡终局 -> 导出`端到端测试通过。
- Stub Provider 可在无网络环境完成至少一个固定生命阶段。
- 同一事件夹具重放得到相同状态哈希。
- LLM 提交未知事件、伪造骰点或无来源 Lore 时被拒绝。
- 缺少内容包时只读打开，不损坏存档。
- 所有公开接口、事件类型和迁移规则有文档与契约测试。
