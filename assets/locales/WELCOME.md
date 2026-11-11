## 新手先看

- [新手使用指南](https://www.bilibili.com/video/BV1VaJU65Ebm/)：从任务配置到自动运行。
- [真正意义上的「一键」日常](https://www.bilibili.com/video/BV13ZHT6AEYw/)：自动拉起 QQ 游戏大厅，一“键”日常。

## 小提示

- **运行托管任务前，先关掉忍考扫荡的弹窗。** 弹窗还开着时，托管会被它挡住。
- **打开软件时提示缺少 .NET？** 后续整合包会移除 .NET 运行库以减小体积。如果启动时提示必须安装 .NET Desktop，关掉它，运行目录里的「DependencySetup_依赖库安装」即可！
- **某个版本意外更新不了？** 从 [GitHub Releases](https://github.com/ArcherSore/MaaNOP/releases/latest) 下载完整包，把旧版本目录里的 `config` 文件夹移动到新版本目录里即可保留原有配置。

## 出问题时

1. 在「设置 → 调试」打开「保存识别标注图」。它默认关闭，重启后也会**自动关闭**，请在复现前打开。
2. 用同样的操作复现一次，再在「设置 → 调试 → 问题诊断」点「导出诊断包」。
3. 把诊断包和问题描述发到 [GitHub Issues](https://github.com/ArcherSore/MaaNOP/issues)，也可以加 QQ：368655734。

常见问题先看「帮助」页。软件免费开源，只从 [Releases](https://github.com/ArcherSore/MaaNOP/releases/latest) 下载完整整合包。
