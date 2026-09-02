# 跨平台安装与打包（H-04）

目标平台：Windows / Linux / macOS。项目使用标准 `pyproject.toml`，无需平台专有代码；业务逻辑不依赖颜色或终端宽度。

## 安装

```bash
python -m pip install .            # 发布安装
python -m pip install -e ".[dev]"  # 开发安装（含 pytest/ruff/mypy）
```

或使用 `uv`（保持标准 pip 可安装）：

```bash
uv pip install -e ".[dev]"
```

## 数据目录（不写当前工作目录）

| 平台 | 默认目录 |
|---|---|
| Windows | `%LOCALAPPDATA%\Noosphere` |
| macOS | `~/Library/Application Support/Noosphere` |
| Linux | `$XDG_DATA_HOME/noosphere40k` 或 `~/.noosphere40k` |

可用 `NOOSPHERE_DATA_DIR` 覆盖。数据库为 SQLite（WAL 模式），存档与私有资料目录绝不入仓库。

## 单文件分发（可选，后续批次）

如需单文件可执行文件，使用 PyInstaller 或 Nuitka 在目标平台分别构建；`--no-color` 模式保证纯文本终端可用。本批不内置打包器，仅确保标准 wheel 可在三平台安装与启动。

## 平台验证清单

- [ ] Windows：`noosphere version` / `doctor` / `new` + `/quit` 正常
- [ ] Linux：同上
- [ ] macOS：同上
- [ ] `--no-color` 下信息不丢失
- [ ] 无 LLM（无 API key）时完整可玩

> 跨平台人工验证属于发布门槛（H-06），需在真实三平台上执行并记录。