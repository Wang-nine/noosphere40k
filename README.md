# Noosphere: A 40K Chronicle（诺斯菲尔纪事）

> 本项目是**非官方战锤 40,000 同人项目**，不代表 Games Workshop 立场，不暗示其背书。未经核验的 Lore 不得标记为正史。

## 项目简介

在终端中运行、由 LLM 驱动叙事、由确定性规则引擎负责数值与检定的单人文字角色扮演游戏。
玩家默认从约 8 岁的帝国普通儿童开始，经历家庭、教育、职业、服役、危机、衰老与死亡，从而逐步认识战锤 40,000 的世界。

核心设计主张：**资料库决定什么是真的，规则引擎决定发生了什么，LLM 决定如何讲述。**
成功标准不是"LLM 能讲一个像 40K 的故事"，而是"系统能证明关键设定来自哪里，并且 LLM 无权篡改规则结果、角色数据和已确认的世界事实"。

## 当前状态

- 阶段：仅规划，设计与开发规格已完成并冻结为 Public Baseline；**代码尚未创建**。
- 正式名称与 Lore 引用待审核；文档中的本地世界/人物/事件均为设计占位。

## 接手 AI 指南

开发 AI 必须按依赖顺序阅读以下全部文档（详见 `docs/AI_DEVELOPMENT_HANDOFF.md`）：

| 顺序 | 文档 | 内容 |
|---|---|---|
| 1 | `docs/AI_DEVELOPMENT_HANDOFF.md` | 边界、冻结决策、接手顺序 |
| 2 | `docs/WH40K_LLM_TEXT_GAME_DESIGN.md` | 产品目标、三大原则、MVP 范围 |
| 3 | `docs/TECHNICAL_IMPLEMENTATION_SPEC.md` | 技术栈、仓库结构、状态机、管线 |
| 4 | `docs/DATA_PROTOCOL_SPEC.md` | 稳定数据模型、事件、数据库、LLM 协议 |
| 5 | `docs/PROMPT_GUARD_SPEC.md` | 提示职责、Guard 校验与安全降级 |
| 6 | `docs/LORE_CONTENT_SPEC.md` | 资料分层、来源、反幻觉、审核流程 |
| 7 | `docs/LIFEPATH_CAMPAIGN_SPEC.md` | 首个完整人生的章节与内容结构 |
| 8 | `docs/IMPLEMENTATION_BACKLOG.md` | 任务 ID、依赖、完成定义、里程碑 |
| 9 | `docs/TEST_ACCEPTANCE_PLAN.md` | 测试矩阵与发布门槛 |

硬性约束（与文档冲突时按以下优先级仲裁：用户最新确认 > 交接入口冻结决策 > 数据/技术规格 > 总体设计 > 实现便利）：

- 技术栈：Python 3.12+、Typer、Rich、Pydantic v2、SQLite 3 + SQLAlchemy 2.x、FTS5；MVP 禁用 Agent 框架。
- LLM 只做意图解析与叙事生成；不掷骰、不直接改状态、不读写数据库。
- 无 LLM 时，启动、浏览、存档、规则重放与模板降级必须完整可用。
- 每项任务的完成定义：代码 + 测试 + 简短文档 + 无未解释 TODO + 验收命令通过。
- **任何文档或代码变更必须在 `CHANGELOG.md` 追加记录。**
- 正史硬事实必须有批准的来源（`source_id`）；无来源时不得编造。

## 里程碑

```
M0 仓库骨架
 -> M1 无 LLM 生命历程原型
 -> M2 存档与重放
 -> M3 Lore Pack 与 Coverage Gate
 -> M4 受控 LLM 叙事
 -> M5 完整首个人生内容
 -> M6 发布候选
```

## 版权与发布声明

- 不分发 Codex、小说、规则书全文；公共网页仅保存必要的事实摘要与来源引用。
- 原创简化规则，不复制既有战锤桌面 RPG 规则文本。
- 公开发布前需完成 Games Workshop 知识产权与 Fan Content Policy 专项审核。
