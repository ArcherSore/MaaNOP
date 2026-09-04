# MaaNOP

MaaNOP 是基于 [MaaFramework](https://github.com/MaaXYZ/MaaFramework) 的《火影忍者 Online》自动化项目。

> **特色：Windows 后台运行，不抢占鼠标。** 任务运行于独立 Windows Session，前台鼠标与键盘完全不受影响——挂机的同时照样办公、看视频、玩游戏。

## 下载与快速开始

普通用户请直接从 [MaaNOP Releases](https://github.com/ArcherSore/MaaNOP/releases) 下载完整的 Windows x64 包，解压即可使用，无需自行编译。

1. 从 [Releases](https://github.com/ArcherSore/MaaNOP/releases) 下载最新的 Windows x64 压缩包。
2. 将压缩包**完整解压**到一个目录（不要只解压部分文件，也不要在压缩软件里直接双击运行）。
3. 准备好**火影忍者 Online 客户端**，并登录到可进入游戏的账号（QQ游戏大厅和360游戏大厅目前不支持）。
4. 以管理员身份运行解压目录中的 `NarutoAutoGUI.exe`。
5. 在界面中选择并配置要执行的任务与参数。
6. 确认后开始任务，运行过程中可在界面查看实时预览与日志。

**当前运行环境要求：**

- Windows 10 / Windows 11 x64 系统
- 管理员权限（用于窗口控制与后台会话）
- Windows x64 发行包已内置 Python 运行时（Python 3.12.9）与 `maafw` 等 Agent 依赖，无需用户单独安装 Python、pip 或配置环境变量。

## 当前功能

MaaNOP 当前提供三个顶层任务，均可在 NarutoAutoGUI 中开关与配置。三个任务共享一个全局的**服务器范围**设置（格式如 `10-16,18-20`），任务会按该范围依次处理对应服务器。

### 注册并练级

对应 `AccountLeveling` 任务，用于批量注册新账号并练级（1～16 级）。关键可配置项：

- **账号前缀**：用于生成新账号名称。

### 批量领取

对应 `AccountClaims` 任务，面向已经注册并完成练级的账号。日常经验、邮件附件、幻象奖励、回归奖励可分别开关。

### 购物节送字

对应 `ShoppingFestivalTask` 任务，按设定的服务器范围依次登录、处理登录弹窗，并执行木叶购物节送字流程。关键可配置项：

- **好友名称**：购物节赠送对象的好友名称。

> 任务的具体执行节点会随版本调整，请以 `interface.json` 与界面中展示的选项为准，此处不逐一罗列。

## 使用要求与已知限制

为避免误解，这里如实说明当前的真实限制：

- 三个任务都要求从**选服务器界面**开始，请确保游戏停在正确界面再启动任务。
- `AccountLeveling` 暂不支持断点续跑，需从新账号注册完整执行；中途若异常停止需手动处理。
- 部分**领取功能存在游戏内前置条件**：领回归需当前可领；领幻象需已解锁且未触发战力提升弹窗（若触发需先手动通关一次）；领经验需铜币充足。不满足时会报错。

## Windows GUI

[NarutoAutoGUI](https://github.com/ArcherSore/NarutoAutoGUI) 是 MaaNOP 在 Windows 上的图形前端，负责：

- 任务配置与参数填写
- 运行控制（启动 / 停止）
- Child Session（独立会话后台运行）
- 实时画面预览（Preview）
- 运行日志查看

<!-- 截图占位（推荐）：NarutoAutoGUI 运行中界面——任务/参数 + Preview 实时画面 + 运行日志同框。 -->

它通过 `interface.json` 读取 MaaNOP 的任务与选项，并以 Python 子进程方式拉起 `agent/main.py` 执行具体逻辑。

## 开发

MaaNOP 基于 [MaaFramework](https://github.com/MaaXYZ/MaaFramework) 开发。如需参与开发：

- 仓库开发与格式化配置见 [`docs/zh_cn/个性化配置.md`](./docs/zh_cn/个性化配置.md)。
- 核心目录：`assets/`（资源、图像、OCR 模型与 `interface.json`）、`agent/`（Python 任务执行逻辑，由 GUI 作为 Child Session 拉起）、`tools/`（打包与校验脚本）。
- MaaFramework 本身的开发文档见其[仓库](https://github.com/MaaXYZ/MaaFramework)。

完整的编译流程与 CI 细节不在本 README 范围内，请参考仓库内对应目录。

## 遇到问题

- 运行日志可直接在 NarutoAutoGUI 界面查看；提交 Bug 时请附上日志与复现步骤。
- 功能建议与问题反馈请前往 [Issues](https://github.com/ArcherSore/MaaNOP/issues)。
- 与 MaaFramework 本身相关的问题，请前往 [MaaFramework Issues](https://github.com/MaaXYZ/MaaFramework/issues)。

## 鸣谢

- 本项目由 **[MaaFramework](https://github.com/MaaXYZ/MaaFramework)** 强力驱动。
- 后台运行、不抢占鼠标的实现思路受 **[BetterGI](https://github.com/babalae/better-genshin-impact) v0.63** 版本启发。
- 感谢 MAA 社区积累的自动化实践经验。
