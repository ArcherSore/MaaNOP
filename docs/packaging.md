# Windows x64 打包

直接修改 `.github/workflows/install.yml` 顶部的配置：

```yaml
env:
  BUNSHIN_VERSION: ""
  PYTHON_VERSION: "3.12.9"
```

- `BUNSHIN_VERSION` 留空时自动选择 Bunshin（仓库 `ArcherSore/NarutoAutoGUI`）的最新 Release：MaaNOP 正式发布排除预发布版，开发构建及预发布允许使用上游预发布版；填写 tag（例如 `v1.13.0`；`v1.13.0` 之前的 Release 资产名和文件名不同，不能使用）时使用指定 Release。
- `PYTHON_VERSION` 指定随包携带的 Windows x64 嵌入式 Python 版本。

工作流参照 MaaEnd：先在 `meta` 阶段使用 `step-security/github-action-get-latest-release` 确定 GUI 版本，再将版本传给 `robinraju/release-downloader` 下载并解压。随后运行 `tools/install.py` 补齐 Python、`agent/requirements.txt` 中的依赖和 MaaNOP 资源，写入包版本及 `agent.child_exec`。包内 `maafw` 按 Worker 的 MaaFramework 版本安装。`requirements.txt` 中的版本用于开发环境。打包时生成 `sitecustomize.py`，让 Agent 和 Python 前置任务在启动时使用 Worker 自带的 MaaFramework。清理 `maa/bin` 等不需要的文件后，分别验证 Agent 导入与前置任务使用 Toolkit。

Bunshin 自 `v1.13.0` 起不再携带 .NET 运行库，需要用户电脑安装 .NET 10 Desktop Runtime。解压出的 `DependencySetup_依赖库安装.bat` 由 Bunshin 随包提供并维护（安装 VC++ 与 .NET 10），MaaNOP 保留整份 GUI 和 Worker 文件，不再自带该脚本。完整包仅发布 Windows x64，用户无需另装 Python。

GUI 发布新版本后，再次运行 MaaNOP 打包流程才会采用它。
