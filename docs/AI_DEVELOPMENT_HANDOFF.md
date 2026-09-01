# AI 开发交接入口

> 项目：战锤 40,000 背景的终端 LLM 生命历程文字游戏  
> 当前状态：设计与开发规格完成，Public Baseline 已确认，代码尚未创建  
> 默认玩家体验：约 8 岁帝国普通孩童开局，经历成长、职业、危机、衰老与死亡  
> 重要声明：本项目为非官方同人项目；未经核验的 Lore 不得标记为正史。

## 1. 接手顺序

开发 AI 必须按以下顺序阅读全部文档（全部位于 `docs/` 目录，变更记录见根目录 `CHANGELOG.md`）：

1. `docs/AI_DEVELOPMENT_HANDOFF.md`——当前文件，了解边界和起始任务。
2. `docs/WH40K_LLM_TEXT_GAME_DESIGN.md`——产品目标、原则和总体架构。
3. `docs/TECHNICAL_IMPLEMENTATION_SPEC.md`——技术栈、模块、状态机和运行管线。
4. `docs/DATA_PROTOCOL_SPEC.md`——稳定数据模型、事件、数据库和 LLM 协议。
5. `docs/PROMPT_GUARD_SPEC.md`——提示职责、Claim Guard 与安全降级。
6. `docs/LORE_CONTENT_SPEC.md`——来源、资料分层、反幻觉和审核流程。
7. `docs/LIFEPATH_CAMPAIGN_SPEC.md`——首个完整人生的章节与内容结构。
8. `docs/IMPLEMENTATION_BACKLOG.md`——任务 ID、依赖和完成定义。
9. `docs/TEST_ACCEPTANCE_PLAN.md`——测试矩阵与发布门槛。

若实现与文档冲突，优先级为：用户最新确认 > 交接入口中的冻结决策 > 数据/技术规格 > 总体设计 > 实现便利。

## 2. 已冻结的产品决策

以下事项无需开发 AI 再做产品选择：

- 单人终端游戏，首版界面简洁。
- Python 3.12+、Typer、Rich、Pydantic v2、SQLite/SQLAlchemy、FTS5。
- 不使用自主 Agent 框架；采用显式单回合管线。
- LLM 只解析意图和生成叙事，不掷骰、不直接改状态、不读写数据库。
- 规则使用原创简化 d100。
- 玩家默认约 8 岁开始，经历五个生命阶段，死亡是正式终局。
- 首版只支持普通帝国人类尺度；特殊种族/超人类/高权力背景由后续 Pack 提供。
- 首个舞台是正史兼容的原创帝国边疆星系；著名正史人物不在 MVP 客串。
- Lore 分为广覆盖 Galaxy Primer 和深覆盖 Campaign Canon Pack。
- 正史硬事实无批准来源则不能使用；局部原创必须显式标记。
- 孩童阶段禁止情色和性化内容，默认非图形化暴力。
- 简体中文输出，核心实体保留英文名与译名映射。
- 存档锁定规则、Prompt 和内容包版本/哈希。
- 首个人生目标 8–12 小时，至少四条职业路线、六类终局。

## 3. 尚未满足的外部条件

这些是内容发布条件，不阻塞工程骨架开发：

1. 用户已确认不提供私人官方资料；MVP 固定使用公开来源 Public Baseline，不得依赖付费书籍内容。
2. 具体公开官方页面、版本、发布日期和 URL 定位尚未由人工登记。
3. 原创星系和人物显示名尚未做全库同名/冲突检查。
4. 尚未指定 40K 人工 Lore 审核者。
5. 正式发布前尚未完成 Games Workshop IP/Fan Content Policy 专项复核。

因此，开发 AI 可以建立公开资料工具、Schema 和 `game_original` 测试内容，但不能自行从模型记忆生成并批准 40K 资料，也不能把书籍独有细节当成公开可用事实。

## 4. 第一批开发范围

严格执行 `IMPLEMENTATION_BACKLOG.md` 中：

```text
A-01 A-02 A-03
C-01 C-02
D-01
E-01
G-01
H-01
```

第一批目标是搭建无真实 Lore、无生产 LLM 的安全工程骨架。

禁止在第一批中：

- 抓取或打包 Codex、小说、Wiki 全文。
- 要求用户提供付费资料，或把 Private Library 模式当作 MVP 前置条件。
- 写入任何声称 `approved` 的真实 40K 事实。
- 添加生产 API key。
- 实现自由 Agent 循环。
- 让 CLI、LLM 或内容文件绕过事件 reducer 修改状态。
- 为了演示而提前硬编码未经审核的正史背景。

## 5. 第一批交付物

接手 AI 完成后必须提供：

- 可安装的 Python 项目骨架。
- `noosphere version`、`doctor`和存档命令占位接口。
- 领域枚举、错误码、事件 Envelope 和纯 reducer。
- SQLite 初始 Schema、迁移器和基础 Repository。
- Lore Source/Fact/Entity/Glossary/Knowledge 模型。
- Stub LLM Provider。
- lint、typecheck、unit/contract CI。
- 测试执行结果和未完成任务清单。
- 若改变任何冻结决策，提供 ADR；未获用户批准不得合并破坏性变化。

## 6. 推荐给开发 AI 的任务提示词

```text
你正在实现一个已经完成规划的 Python 终端 LLM 文字游戏。

先完整阅读以下文件，按顺序执行：
AI_DEVELOPMENT_HANDOFF.md
WH40K_LLM_TEXT_GAME_DESIGN.md
TECHNICAL_IMPLEMENTATION_SPEC.md
DATA_PROTOCOL_SPEC.md
PROMPT_GUARD_SPEC.md
LORE_CONTENT_SPEC.md
LIFEPATH_CAMPAIGN_SPEC.md
IMPLEMENTATION_BACKLOG.md
TEST_ACCEPTANCE_PLAN.md

本轮只实现 backlog 的 A-01、A-02、A-03、C-01、C-02、D-01、E-01、G-01、H-01。
使用 Stub Provider，不使用生产 API key，不抓取网络 Lore，不创建或批准真实 40K 事实。
所有状态变化必须通过事件 reducer；LLM 不得直接修改存档。
实现后运行 lint、typecheck 和测试，报告结果、变更文件和剩余任务。
遇到文档冲突或需要改变冻结决策时停止并提出 ADR，不要自行选择。
```

## 7. 后续批次交接

第一批通过后按以下批次推进：

1. 确定性教程片段：B-01/B-02/B-03、C-03/C-04、F-01/F-02、G-02。
2. Lore 与反幻觉：D-02 至 D-06、E-03 至 E-06。
3. 完整生命系统：B-04 至 B-08、G-06、E-07。
4. 资料与内容：D-07 至 D-10、F-03 至 F-07。
5. UX 与发布：G-03 至 G-05、H-02 至 H-06。

每一批都必须先通过对应测试再进入下一批，尤其不能在 Coverage Gate 和 Claim Guard 完成前接入自由叙事。

## 8. 完整交付定义

项目只有同时满足下列条件才可称为“可发布 MVP”：

- 完整人生五阶段可玩，包含提前死亡与晚年自然终局。
- 规则、随机、年龄、存档和关系完全由确定性系统管理。
- Galaxy Primer 达到覆盖门槛，Campaign Pack 剧情需求覆盖率 100%。
- 所有关键正史断言有来源，所有原创内容有标签。
- 恶意/错误 LLM 输出不能改变事实和状态。
- 新手 UX、儿童内容边界、存档恢复、隐私和跨平台验收通过。
- 人工 Lore 审核与 IP/权利审查完成。

## 9. 当前可交付结论

当前文档包已经足以交给其他 AI 开始**工程骨架、规则引擎、存档、数据 Schema 和 Lore 审核工具**的开发。

当前文档包尚不足以授权其他 AI 宣称“40K 背景内容已经完整并可发布”，原因不是设计缺失，而是权威资料需要合法取得、逐条登记并经过人工审核。这一边界必须在所有后续交接中保留。

已确认的来源限制不会阻塞工程开发。内容团队必须通过公开官方资料建立 Galaxy Primer；公开资料未覆盖的书籍细节保持未知，局部剧情则使用经过约束并标记为 `game_original` 的内容。
