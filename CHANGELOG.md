# 更新文档（CHANGELOG）

> 规则：任何文档或代码变更必须在顶部追加记录：日期、变更类型（新增/修改/整理）及摘要。接手的 AI 改动后先更新本文件。

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
