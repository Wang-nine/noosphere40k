# 更新文档（CHANGELOG）

> 规则：任何文档或代码变更必须在顶部追加记录：日期、变更类型（新增/修改/整理）及摘要。接手的 AI 改动后先更新本文件。

## 2026-09-02

- 开发（E-02 补充 + 真实 LLM 验证）：接入 OpenAI-compatible Provider。
  - 新增 `llm/openai_compatible.py`：`OpenAICompatibleProvider`——调用 `/chat/completions`，`response_format=json_schema` 严格结构化输出，5xx/429 自动重试，超时/HTTP/解析错误映射为稳定错误码；key 仅存内存、日志脱敏；`/models` healthcheck。
  - 新增 `llm/factory.py`：`build_provider`——有 key+base_url+model 时用真实 Provider，否则回退离线 Stub（永不误发网络）。
  - 新增 `scripts/verify_llm.py`：真实 LLM 冒烟验证（healthcheck + 一次结构化生成，key 只读环境变量、不打印不落盘）；`scripts/probe_auth.py`：网关鉴权方式探测工具。
  - 依赖：新增 `httpx>=0.27`。
  - 真实验证：`https://opencode.ai/zen/go/v1` + `deepseek-v4-flash`，healthcheck ok，`NarrationResponse` 结构化中文叙事解析成功。
  - 测试：262 项通过（新增 openai provider 离线 MockTransport 契约测试与 factory 测试），Ruff 与 MyPy strict（62 文件）全绿。
  - 状态：真实 LLM 通道已打通；测试数据与 key 均未上传，key 仅以临时环境变量使用。

## 2026-09-02

- 开发（第六批）：UX 与发布 G-03…G-05、H-02…H-06。
  - 新增 `application/encyclopedia_service.py`（G-03）：`/encyclopedia`（玩家层词条）、`/know`（仅角色知识，百科解锁不改角色认知）、`/sources`（事实溯源），三个权限层分离；`LoreRepository` 增加 `get_character_knowledge`/`store_knowledge`。
  - 新增 G-04：`/roll-details` 从已提交的 `CheckResolved` 事件读取骰点/目标/成功幅度/特殊结果，绝不询问 LLM。
  - 新增 G-05：`/settings` 写入 `CampaignSettings` 到存档（影响规则的设置不可静默改变）、`/skip` 跳过场景（审核后摘要事件）；儿童阶段情色/性化/成人恋爱标签仍由校验与 Guard 双层拒绝。
  - 新增 `canon_guard/test_framework.py`（H-02）：Canon 测试框架——正确/陷阱（未批准事实）/无资料/视角冲突/提示注入五类用例，全部基于 Lore Gate 与 Claim Guard 的可重复裁决。
  - 新增 H-03 故障注入测试：Provider 超时稳定错误、非法 LLM 输出永不提交（二次失败走模板）、损坏存档哈希检测、缺失内容包拒绝。
  - 新增 `security/export_scan.py`（H-05）：目录/ZIP 导出扫描，检出 API key 与私有来源标记（black library/codex 等）。
  - 更新 README：当前状态、安装运行、隐私与数据处理声明、非官方/IP 声明、发布候选验收；新增 `PACKAGING.md`（H-04：三平台安装、数据目录、无颜色模式验证清单）。
  - 新增 `scripts/release_check.py`（H-06）：运行 Ruff + MyPy + pytest 并输出 `TEST_ACCEPTANCE_PLAN §14` 格式验收报告草稿（工程门禁；人工 Lore/IP/UX 验收保持 pending）。
  - 测试：251 项通过（Unit + Contract），Ruff 与 MyPy strict（60 文件）全绿；`python scripts/release_check.py` 三处工程门禁通过。
  - 状态：六批开发任务全部完成；真实 40K Lore 批准、IP/Fan Content Policy 审核与三平台人工 UX 验收仍为发布前提（pending human review）。

## 2026-09-02

- 开发（第五批）：资料与内容 D-07…D-10、F-03…F-07。
  - 新增 `lore/importers/cleaner.py` 与 `lore/importers/importer.py`（D-07）：HTML/文本净化（剥离脚本/样式/导航/隐藏文本）、提示注入检测（中英文）、引用材料提取、ZIP 安全解压（路径穿越/符号链接/压缩炸弹/条目数拒绝）；`PlainTextImporter` 只产出 `candidate`，从不自动批准。
  - 新增 `lore/review.py`（D-08）：`ReviewService` 审核工作流——candidate 不能直接变 approved，必须显式 `approve/reject` 并记录审核者与时间；非法状态迁移拒绝；批准后事实才可查询。
  - 迁移 0003：`lore_facts`/`lore_entities` 增加 `reviewed_by`/`reviewed_at_utc` 审核列。
  - 新增 `lore/coverage_report.py`（D-09/D-10）：Galaxy Primer 12 主题域覆盖报告与空缺列表；Campaign Pack hard 需求满足率计算（candidate 不满足 hard 需求）。
  - 新增 `content/life_content.py` + `content/life_content/pack.yaml`（F-03…F-07）：三种童年出身（各 ≥5 必经/≥8 可选/≥3 生活事件 + 儿童安全标签校验）、少年章节（含角色观点/百科对照）、四条青年职业路线（各 ≥5 场景/≥3 证据/≥2 非战斗方案）、壮年汇合 6 种立场（均 ≥2 路线可达、无单骰点关键线索）、晚年 ≥6 类终局 + 童年关系回响场景；全部本地事实为 `game_original` 占位，不冒充已批准官方 Lore。
  - 测试：232 项通过（Unit + Contract），Ruff 与 MyPy strict（57 文件）全绿。
  - 状态：仍未接入生产 LLM 与真实已批准 40K Lore；下一批为 UX 与发布（G-03…G-05、H-02…H-06）。

## 2026-09-02

- 开发（第四批）：完整生命系统 B-04…B-08、G-06、E-07。
  - 新增 `rules/aging.py`（B-04）：生命阶段参考年龄区间、阶段只能向前/进入 terminal、`LifeTransitionService`（预览纯函数无副作用、结算确定性、未知 aging_ruleset/倒推阶段/from_stage 不匹配拒绝）；LLM 无直接改龄接口。
  - 扩展 reducer：`TimeAdvanced` 推进年龄天数、`SkillProgressed` 更新技能与等级（进度→untrained/trained/specialist/master）、`ConditionApplied/Removed`、`WoundApplied/Changed`、`VocationStarted/Ended`、`GoalAdded/Updated`；`CharacterDied` 使战役进入 TERMINAL。
  - 新增 `rules/lifepath.py`（B-05）：`VocationDefinition` 职业前置检查（年龄、技能等级、关系、内容包）、技能进度→等级映射。
  - 新增 `rules/wounds.py`（B-06）：腐化阈值（notable/terminal，终局可溯源事件链）、压力阈值（疲劳/崩溃）、伤势严重度映射。
  - 新增 `rules/combat.py`（B-07）：确定性简化战斗——命中检定、伤害、护甲、穿透、掩体、伤势→死亡；撤退/压制等非杀伤选项；LLM 无权改数值。
  - 新增 `application/chronicle.py`（B-08/E-07）：`build_chronicle` 从已提交事件生成一致年表（死亡→TERMINAL），`generate_recap` 只总结不新增。
  - 新增 G-06：CLI `/timejump`（先预览→确认→结算；取消产生零事件）与 `/recap`（E-07 回顾）。
  - 测试：202 项通过（Unit + Contract），Ruff 与 MyPy strict（50 文件）全绿。
  - 状态：仍未接入生产 LLM 与真实 40K Lore；下一批为资料与内容（D-07…D-10、F-03…F-07）。

## 2026-09-02

- 开发（第三批）：Lore 与反幻觉 D-02…D-06、E-03…E-06。
  - 新增 `llm/schemas.py`（E-03）：`NarrationRequest`/`NarrationResponse`、`ActionIntent`、`RuleResolution`、显示模型与 LLM 提议事件白名单；全部 `extra=forbid` 严格校验。
  - 新增 `lore/registry.py`（D-02）：Lore Pack 目录加载、`manifest.yaml` 解析、依赖版本解析（缺依赖/版本冲突/重复 ID/非法 pack_id/未知 Schema 拒绝）。
  - 新增 `lore/retrieval.py`（D-03）：`LoreRepository`——FTS5（trigram 分词，中英均可检索）+ 别名 LIKE 回退；所有读取路径强制 `review_status='approved'`，未批准事实永不泄漏。
  - 新增 `lore/coverage_gate.py`（D-04）：七类裁决（ALLOW_CANON/PERSPECTIVE/ORIGINAL/DECORATIVE/RETRY_CONSTRAINED/BLOCK_UNCOVERED/BLOCK_CONFLICT）；hard 需求缺失时 `hard_blocked`，禁止调用 Narrator。
  - 新增 `lore/knowledge_filter.py`（D-05）：角色知识（knows/believes/doubts/heard_rumor/unknown）阈值过滤；百科解锁绝不改变角色知识。
  - 新增 `canon_guard/claim_guard.py`（D-06）：canon claim 必须有批准的 fact_id、越界原创实体、decorative 夹带断言、引用不在请求中的事实一律拒绝。
  - 新增 `llm/intent.py`（E-04）：IntentParser——元命令永不进入 LLM；低置信度攻击/消耗/不可逆行动与未解析引用要求澄清；离线关键词回退。
  - 新增 `llm/context_builder.py`（E-05）：上下文只含角色可见状态 + 通过 Lore Gate 与知识过滤的批准事实。
  - 新增 `llm/output_guard.py`（E-06）：Schema/事件白名单/状态权威/Claim/年龄适配守卫，失败仅重试一次，再失败走模板降级，非法文本永不提交。
  - 迁移 0002：`lore_facts_fts` FTS5 虚拟表（trigram）。
  - 测试：154 项通过（Unit + Contract），Ruff 与 MyPy strict（45 文件）全绿。
  - 状态：仍未接入生产 LLM 与真实 40K Lore；下一批为完整生命系统（B-04…B-08、G-06、E-07）。

## 2026-09-02

- 开发（第二批）：确定性教程片段 B-01/B-02/B-03、C-03/C-04、F-01/F-02、G-02。
  - 新增 `rules/rng.py`（单一随机入口，可注入骰点、可复现种子）与 `rules/checks.py`（属性范围、难度档位、技能加值表、Modifier 去重与来源校验、d100 目标钳制 5–95、01/100 特殊结果、成功幅度）。
  - 新增 `persistence/repositories.py`：`CampaignRepository`（事件追加、乐观版本冲突、快照+尾部重放、从零重放、篡改检测）、`commit_turn`（回合原子提交 + 每 20 回合快照）。`CampaignCreated` 支持初始属性。
  - 新增 `content/schemas.py`、`content/validator.py`、`content/loader.py`（F-01：场景/转换/预测/LoreRequirement Schema，含 fallback 模板、儿童年龄标签与重复 ID 校验）。
  - 新增 `content/scenario_packs/tutorial_hive_worker/pack.json`（F-02：巢都工人家庭“配给日→红袍人→邻居消失”三段无 LLM 教程）。
  - 新增 `application/campaign_service.py`（离线教程管线：创建、编号/自然语言行动、d100 检定、事件哈希盖章）与 `cli/render.py`、`cli/game.py`（G-02：游戏循环，支持编号与自由输入，`--no-color`）。
  - `noosphere new`/`continue`/`saves list` 从占位变为可用；`saves export/import` 仍为占位（C-06）。
  - 测试：100 项通过（Unit + Contract + 端到端教程），Ruff 与 MyPy strict（34 文件）全绿。
  - 状态：仍未接入真实 40K Lore 与生产 LLM；下一批为 Lore 与反幻觉（D-02…D-06、E-03…E-06）。

## 2026-09-01

- 开发（第一批）：交付 `IMPLEMENTATION_BACKLOG.md` 首批范围 A-01/A-02/A-03、C-01/C-02、D-01、E-01、G-01、H-01 的可安装工程骨架。
  - 新增：`pyproject.toml`（Python 3.12+，Typer/Rich/Pydantic v2/SQLAlchemy 2.x，pytest/Ruff/MyPy 门禁）、`.env.example`、`.gitignore`。
  - 新增：领域层 `src/noosphere40k/domain/`——稳定枚举、稳定错误码、支撑模型、`EventEnvelope` 与纯函数 reducer、确定性状态哈希；未知事件/乱序/哈希不匹配均拒绝。
  - 新增：配置 `config/settings.py`（CLI > 环境变量 > 用户 TOML > 平台默认值；密钥仅环境变量）与 `security/secrets.py`（`doctor` 不泄露密钥）。
  - 新增：Lore 契约模型 `lore/schemas.py`（Source/Fact/Entity/Glossary/Knowledge，`extra=forbid`）。
  - 新增：LLM Provider 协议与离线 Stub `llm/`（超时/取消/不可用/Schema 错误稳定映射）。
  - 新增：SQLite 持久化 `persistence/`——WAL、外键、编号迁移器（幂等、失败回滚保留原库），首个迁移建全部最低表集合。
  - 新增：CLI `cli/`——`noosphere version`、`doctor` 可用；`new`/`continue`/`saves` 为占位（依赖 C-03）。
  - 新增：CI workflow `.github/workflows/ci.yml`（Ruff、MyPy strict、pytest）。
  - 测试：57 项通过（Unit + Contract），Ruff 与 MyPy strict 全绿。
  - 状态：项目仍无真实 40K Lore 与生产 LLM；进入下一批（B-01/B-02/B-03、C-03/C-04、F-01/F-02、G-02）。

## 2026-09-01（首版）

- 新增：仓库初始化；根目录新增 `README.md`（接手 AI 指南）与本文件。
- 整理：9 份规格文档从根目录移入 `docs/`，`docs/AI_DEVELOPMENT_HANDOFF.md` 中的文档路径引用同步改为 `docs/` 前缀。
- 配置：本地 git `user.name=Wang-nine`、`user.email=1826967276@qq.com`（仅当前项目，未修改全局配置）。
- 状态：仍为规划阶段，代码尚未创建。
