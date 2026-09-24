# MaaNOP

<p align="center">
  <img alt="MaaFramework" src="https://img.shields.io/badge/MaaFramework-Powered-00BFFF?style=flat-square">
  <img alt="Platform" src="https://img.shields.io/badge/platform-Windows%20x64-blueviolet?style=flat-square">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.12-blue?style=flat-square">
  <img alt="License" src="https://img.shields.io/github/license/ArcherSore/MaaNOP?style=flat-square">
  <a href="https://github.com/ArcherSore/MaaNOP/releases" target="_blank"><img alt="Release" src="https://img.shields.io/github/v/release/ArcherSore/MaaNOP?style=flat-square"></a>
</p>

**MaaNOP** 是面向《火影忍者 Online》官方微端的 Windows 自动化辅助工具。

通过 Windows 桌面分身在独立环境中运行游戏与自动化任务，**不占用当前桌面的鼠标、键盘和窗口焦点**。任务配置、运行控制、实时截图和版本更新均可直接通过图形界面完成。

目前支持 **自动练级、批量资源领取、竞技场一键六道、木叶购物节** 等功能。

<p align="center">
  <a href="https://github.com/ArcherSore/MaaNOP/releases/latest"><strong>下载最新版</strong></a>
  ·
  <a href="https://github.com/ArcherSore/MaaNOP/issues"><strong>反馈问题</strong></a>
  ·
  <a href="https://afdian.com/a/archersore"><strong>❤️支持项目</strong></a>
</p>
<p align="center">
  <img src="docs/images/homePage.png" width="90%" alt="MaaNOP 首页" />
</p>

---

## ✨ 主要特点

* **后台运行**：游戏和自动化任务运行在独立桌面中，不持续占用前台键鼠与窗口焦点。
* **开箱即用**：Windows 完整包已经包含 Python、MaaFramework 及所需运行组件，无需额外配置环境。
* **图形化操作**：任务选择、参数配置、运行控制、日志和实时截图均可在 GUI 中完成。
* **批量区服**：部分任务支持按服务器范围连续处理多个区服。
* **自动更新**：客户端可检查新版本、展示更新说明并完成完整包更新。

---

## 🚀 快速开始

### 1. 下载完整包

前往 [MaaNOP Releases](https://github.com/ArcherSore/MaaNOP/releases/latest)。

绝大多数 Windows 10 / 11 电脑请选择：

```text
MaaNOP-win-x86_64-*.zip
```

> [!NOTE]
> Release 页面还可能包含 Android、Linux、macOS、Windows ARM 等自动构建产物。普通 Windows x64 用户请选择 `win-x86_64`。

### 2. 完整解压

将压缩包完整解压到本地文件夹，例如：

```text
D:\MaaNOP\
```

不要直接在压缩包内运行程序，也不要只单独复制 `NarutoAutoGUI.exe`。

### 3. 启动程序

确保电脑已经安装 **《火影忍者 Online》官方微端**，然后运行：

```text
NarutoAutoGUI.exe
```

首次启动时请允许管理员权限请求。

### 4. 准备运行环境

在首页准备运行环境。

程序会创建独立桌面。进入该桌面后，正常登录《火影忍者 Online》。

### 5. 开始任务

回到 MaaNOP 主界面：

1. 选择任务
2. 配置对应参数
3. 点击开始任务

任务启动后，可以隐藏桌面分身并继续使用当前桌面。

---

## 🎮 支持的功能

| 功能         | 说明                         | 多区服 |
| ---------- | -------------------------- | :-: |
| 🐣 注册并练级   | 自动创建新角色并推进新手流程，目前支持练至 16 级 |  ✅  |
| 🎁 日常与资源领取 | 批量处理日常经验、邮件附件、幻象奖励和回归奖励    |  ✅  |
| ⚔️ 竞技场一键六道 | 自动进行竞技场挑战，直到当前角色达到六道段位     |  ❌  |
| 🎪 木叶购物节   | 自动购买活动商品、刮奖并赠送给指定好友        |  ✅  |

### 区服范围

支持多区服的任务可以使用类似下面的格式：

```text
1-10
```

或：

```text
1-10,15,20-25
```

程序会按照配置范围依次处理对应服务器。

目前大区支持情况：

* ✅ 公测大区
* ✅ 不删档大区
* ❌ 联盟大区

### 🐣 注册并练级

用于批量创建新角色并自动推进前期流程。

当前要求从新角色创建阶段开始，异常中断后**暂不支持可靠的断点续跑**。

### 🎁 日常与资源领取

用于已经完成练级的角色，可批量处理：

* 日常经验及相关奖励
* 邮件及附件
* 忍者幻象奖励
* 回归奖励

部分功能会受到角色当前状态、资源和活动资格影响。

### ⚔️ 竞技场一键六道

自动处理竞技场入口、挑战、战斗过程、结果界面和相关弹窗，直到当前角色达到六道段位。

> [!NOTE]
> 该任务仅处理当前已登录角色，不会自动切换服务器或批量处理多个角色。

### 🎪 木叶购物节

用于活动期间批量处理木叶购物节流程，包括：

* 进入活动
* 购买指定商品
* 刮奖
* 向指定好友赠送奖励

使用前需要在任务配置中填写目标好友名称。

---

## ⚠️ 使用前须知

使用 MaaNOP 前，请确认以下条件：

* **系统**：Windows 10 / Windows 11 x64
* **权限**：需要管理员权限
* **游戏客户端**：仅支持《火影忍者 Online》官方微端
* **不支持客户端**：QQ 游戏大厅、360 游戏大厅及其他第三方版本
* **挂机要求**：可以关闭显示器或隐藏桌面分身，但电脑不能进入睡眠、休眠或关机
* **运行环境**：普通用户无需自行安装 Python、MaaFramework 或其他开发依赖

### 关于桌面分身

MaaNOP 使用 Windows 原生 Child Session 创建独立运行桌面。

游戏与自动化任务在该桌面中执行，因此正常情况下不会持续占用当前桌面的鼠标、键盘和窗口焦点。

该方案无需安装 RDP Wrapper，也不会替换 Windows 系统文件。

---

## ❓ 常见问题

### 1. 准备运行环境失败怎么办？

如果首次运行时出现 Child Session、RDP 或运行环境创建失败，建议依次尝试：

1. 完全退出 MaaNOP
2. **重启电脑**
3. 重新运行 `NarutoAutoGUI.exe`
4. 确认已经授予管理员权限
5. 检查火绒、360 等安全软件是否拦截本地会话、进程或 RPC 通信

如果问题仍然存在，请附带日志提交 Issue。

### 2. 为什么程序找不到或无法启动游戏？

首先确认使用的是官网独立的《火影忍者 Online》微端，并确保游戏本身可以正常手动启动。

QQ 游戏大厅、360 游戏大厅等版本目前不受支持。

### 3. 遇到 Bug 怎么反馈？

请前往：

**[GitHub Issues](https://github.com/ArcherSore/MaaNOP/issues)**

提交问题时建议说明：

* MaaNOP 版本
* Windows 版本
* 出问题的任务
* 实际表现
* 可以稳定复现时的复现步骤

如果属于程序运行或自动化脚本异常，请同时压缩程序目录下的：

```text
debug/
```

并附在 Issue 中。

> [!TIP]
> 上传前请自行检查日志中是否包含不希望公开的信息。

---

## 🧩 项目组成

MaaNOP 的完整使用体验主要由以下三个项目组成。

### MaaNOP

当前仓库，主要维护：

* 自动化任务流程
* 图像识别与 OCR 资源
* MaaFramework Pipeline
* Python 自定义识别器与动作
* 任务参数定义
* 完整发布包

### [NarutoAutoGUI](https://github.com/ArcherSore/NarutoAutoGUI)

MaaNOP 使用的 Windows 图形客户端，负责：

* 桌面分身与运行环境管理
* 任务配置与运行控制
* 状态、日志和实时截图展示
* MaaNOP 完整包更新

普通用户**无需单独下载 NarutoAutoGUI**，Windows 完整包已经包含对应 GUI 与运行组件。

### [MaaFramework](https://github.com/MaaXYZ/MaaFramework)

MaaNOP 使用的自动化基础框架，提供图像识别、OCR、Pipeline 行为编排和底层自动化执行能力。

---

## 🛠️ 开发

本仓库同时也是 MaaNOP 自动化任务与资源的开发仓库。

主要目录：

```text
MaaNOP/
├── agent/                  # Python 自定义 Agent
├── assets/
│   ├── interface.json      # 任务与参数定义
│   └── resource/
│       ├── pipeline/       # MaaFramework Pipeline
│       ├── image/          # 图像识别资源
│       └── model/          # OCR 等模型资源
├── docs/                   # 项目文档
└── tools/                  # 校验与发布辅助工具
```

参与开发可进一步参考：

* [MaaFramework](https://github.com/MaaXYZ/MaaFramework)
* [NarutoAutoGUI](https://github.com/ArcherSore/NarutoAutoGUI)
* 本仓库 `docs/` 目录

---

## ❤️ 支持项目

如果 MaaNOP 对你有帮助，欢迎通过 [爱发电](https://afdian.com/a/archersore) 赞助，支持项目的持续开发与维护。

感谢每一份支持，也感谢通过反馈问题、提出建议和贡献代码帮助项目改进的朋友！

---

## 🙏 鸣谢

感谢以下项目及相关开源社区：

* [MaaFramework](https://github.com/MaaXYZ/MaaFramework) — 自动化执行、图像识别、OCR 与 Pipeline 能力
* [NarutoAutoGUI](https://github.com/ArcherSore/NarutoAutoGUI) — MaaNOP 的 Windows 图形客户端
* [BetterGI](https://github.com/babalae/better-genshin-impact) — Windows Child Session 桌面分身方案的重要参考

其他第三方组件与许可信息请参阅：

[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)

---

## ⚠️ 免责声明

MaaNOP 是由社区维护的开源自动化项目，与《火影忍者 Online》及其运营方不存在官方关联。

本项目仅提供自动化技术实现。使用者应自行了解并遵守游戏服务条款、相关规则以及所在地区适用的法律法规，并自行承担使用自动化工具可能产生的风险。
