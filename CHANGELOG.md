# 更新文档（CHANGELOG）

> 规则：任何文档或代码变更必须在顶部追加记录：日期、变更类型（新增/修改/整理）及摘要。接手的 AI 改动后先更新本文件。

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
