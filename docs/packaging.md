# Windows x64 打包

直接修改 `.github/workflows/install.yml` 顶部的配置：

```yaml
env:
  NARUTO_VERSION: ""
  PYTHON_VERSION: "3.12.9"
```

- `NARUTO_VERSION` 留空时自动选择 NarutoAutoGUI 的最新 Release：MaaNOP 正式发布排除预发布版，开发构建及预发布允许使用上游预发布版；填写 tag（例如 `v1.11.0`）时使用指定 Release。
- `PYTHON_VERSION` 指定随包携带的 Windows x64 嵌入式 Python 版本。

工作流参照 MaaEnd：先在 `meta` 阶段使用 `step-security/github-action-get-latest-release` 确定 GUI 版本，再将版本传给 `robinraju/release-downloader` 下载并解压。随后运行 `tools/install.py` 补齐 Python、`agent/requirements.txt` 中的依赖和 MaaNOP 资源，写入包版本及 `agent.child_exec`。MaaNOP 跟随 GUI：Agent 通过 `MAAFW_BINARY_PATH` 使用 Worker 的 MaaFramework，所以包内 `maafw` 按 Worker 的版本安装，`requirements.txt` 中的版本只用于开发环境。然后清理包内 Python 中运行不需要的文件，包括 `maa/bin`。最后使用包内 Python 验证 Agent 能否导入。

.NET 运行时由 NarutoAutoGUI 的 self-contained Release 提供，MaaNOP 保留整份 GUI 和 Worker 文件。完整包仅发布 Windows x64，用户解压即可使用，无需另装 .NET 或 Python。

GUI 发布新版本后，再次运行 MaaNOP 打包流程才会采用它。
