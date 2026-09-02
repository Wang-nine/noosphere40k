# Noosphere: A 40K Chronicle（诺斯菲尔纪事）

> 本项目是**非官方战锤 40,000 同人项目**，不代表 Games Workshop 立场，不暗示其背书。未经核验的 Lore 不得标记为正史。

## 项目简介

在终端中运行、由 LLM 驱动叙事、由确定性规则引擎负责数值与检定的单人文字角色扮演游戏。
玩家默认从约 8 岁的帝国普通儿童开始，经历家庭、教育、职业、服役、危机、衰老与死亡，从而逐步认识战锤 40,000 的世界。

核心设计主张：**资料库决定什么是真的，规则引擎决定发生了什么，LLM 决定如何讲述。**
成功标准不是"LLM 能讲一个像 40K 的故事"，而是"系统能证明关键设定来自哪里，并且 LLM 无权篡改规则结果、角色数据和已确认的世界事实"。

## 当前状态

- 阶段：工程开发进行中。第一至五批已完成：工程骨架、确定性教程、Lore 与反幻觉管线、完整生命系统（年龄/职业/伤势/战斗/纪事）、资料导入审核与生命内容；第六批（UX 与发布）进行中。
- 正式名称与 Lore 引用待人工审核；文档与内容包中的本地世界/人物/事件均为 `game_original` 占位，不得标记为正史或已批准官方资料。
- 尚未接入生产 LLM 与真实已批准 40K Lore；离线模式（Stub Provider + 模板叙事）完整可玩。

## 安装与运行

```bash
python -m pip install -e ".[dev]"
noosphere version          # 版本
noosphere doctor           # 环境诊断（不泄露密钥）
noosphere new "人生" --character "Ada"   # 创建并进入离线教程游戏循环
noosphere continue         # 继续战役
noosphere saves list         # 列出战役
noosphere saves delete       # 删除战役（交互确认，跨表清理）
```

游戏内元命令：`/help` `/character` `/recap` `/timejump` `/encyclopedia <术语>` `/know <主题>` `/sources <fact_id>` `/roll-details` `/settings` `/skip` `/quit`。

## 隐私与数据处理（H-05）

- API key 仅通过环境变量（`NOOSPHERE_LLM_API_KEY`）提供，永不写入日志、存档或导出包；`doctor` 只报告是否存在。
- 私有资料（私人 Codex/小说等）不进入仓库、日志或云端请求；导出包会做密钥与私有来源扫描。
- 玩家输入与 LLM 输出按不可信数据处理。

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

- 本项目为**非官方战锤 40,000 同人项目**；不代表 Games Workshop（GW）立场，不暗示任何背书。
- 不分发 Codex、小说、规则书全文；公共网页仅保存必要的事实摘要与来源引用（Public Baseline）。
- 原创简化规则，不复制既有战锤桌面 RPG 规则文本。
- 公开发布前需完成 Games Workshop 知识产权与 Fan Content Policy 专项审核。
- 用户责任：只有拥有合法副本的私有资料才允许本地建立私人索引；原文不得上传到云端或第三方服务。

## 发布候选验收（H-06）

```bash
python scripts/release_check.py   # 运行 Ruff + MyPy + pytest 并输出验收报告草稿
python -m pytest tests -q
```

发布门槛的最终确认仍需：至少一名 40K 人工 Lore 审核者、IP/Fan Content Policy 审核结论、以及跨平台人工 UX 验证。
