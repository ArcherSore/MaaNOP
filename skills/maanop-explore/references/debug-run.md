# 首轮逐帧调试与页面就绪

粗粒度 Pipeline 初稿完成后读取。按项目锁定的 maafw 运行，在已授权范围内执行一遍，再从成功与失败转换中收紧识别和等待条件。

## 执行前配置

由代理准备调试入口，先确认实际持有 Controller/Tasker 的宿主以管理员身份运行。MaaMCP 执行任务时，设置应作用于 MaaMCP 宿主；单独脚本执行时，作用于该脚本。仅在 Agent 子进程设置全局调试选项，不能保证宿主的截图被录制。

项目 maafw 5.12.3 的配置区别如下；版本变化时重新核对绑定和实现：

| 方式 | 实际作用 |
| --- | --- |
| `Tasker.set_debug_mode(True)` | 提供识别 raw/draws 调试数据和节点回调，不等于每次截图落盘 |
| `Tasker.set_save_draw(True)` | 保存识别可视化到日志目录的 `vision/`，不覆盖所有原始截图 |
| `Tasker.set_save_on_error(True)` | 保存错误截图到 `on_error/`，单独使用不满足本流程 |
| `Tasker.set_recording(True)` | 已废弃，返回 False，不使用 |
| `RecordController(inner_controller, recording_path)` | 记录通过包装器的操作，并保存每次成功、非空的实际截图 |

在实际宿主、任务启动前设置，检查每个配置调用的返回值：

```python
from pathlib import Path
from maa.controller import RecordController
from maa.tasker import Tasker

# run_dir 取本次唯一的新目录；inner_controller/resource 使用已核对的项目配置。
run_dir = Path(run_dir).resolve()
run_dir.mkdir(parents=True, exist_ok=False)
if not Tasker.set_log_dir(run_dir):
    raise RuntimeError("Cannot set debug log directory")
if not Tasker.set_debug_mode(True):
    raise RuntimeError("Cannot enable debug mode")
if not Tasker.set_save_draw(True):
    raise RuntimeError("Cannot save recognition drawings")
if not Tasker.set_save_on_error(True):
    raise RuntimeError("Cannot save error screenshots")
recorded_controller = RecordController(inner_controller, run_dir / "recording.jsonl")
# 在包装器上重新应用生产控制器的截图尺寸/缩放等选项，再连接。
# 不能认为包装器继承了 inner_controller 的全部选项。
if not recorded_controller.post_connection().wait().succeeded:
    raise RuntimeError("Cannot connect recorded controller")
tasker = Tasker()
if not tasker.bind(resource, recorded_controller):
    raise RuntimeError("Cannot bind recorded controller")
```

以上是宿主集成片段，不包含窗口选择、资源加载和 Agent 启动。代理按项目已有入口接好这些条件，不复制另一版本的参数。MaaMCP 工具没有录制开关时，不给 `run_pipeline` 臆造 debug 参数、不修改已安装第三方包；在独立管理员调试入口使用相同资源、控制器配置和必要的 Agent，并避免与其他会话同时操作窗口。任务运行中不替换控制器，持有原控制器与包装器引用直到结束。

先通过包装器请求一次无副作用截图，确认本地 `recording.jsonl` 和 `recording-Screenshot/screencap_*.png` 真实产生，再运行本轮流程；配置返回成功但文件未落盘仍不能开始首轮取证。日志目录还会包含 `maa.log`、`vision/` 和按需生成的 `on_error/`。

录制覆盖每次实际请求到的有效截图，不是连续视频，也不保证保留请求间的所有动画帧。失败截图没有有效 PNG 时记录失败，不能伪称完整取证。全部截图请求、手动操作与等待须走包装器，绕过它的调用不在录制范围内。

RecordController 保存底层 ControlUnit 图像，位于控制器后处理之前，因此录制 PNG 可能与 Tasker 识别图尺寸不同。记录底层图、识别图及其变换；包装器须重新设置生产尺寸。不要直接把录制原图坐标用作 Pipeline ROI，或把它冒充完整控制器图交给预览脚本；必要时另存对应的识别输入图。

## 按界面转换审查

对每个转换按“动作前 → 动作后 → 加载中 → 就绪 → 下一动作”关联日志和本地帧，成功转换也要核对：

- 旧页面或弹窗是否已经退出，加载遮罩/进度是否结束。
- 标题、背景、列表内容、图标和按钮的出现顺序；先出现的标题是否早于资源与控件加载。
- 能证明业务目标已就绪的文字、图标或控件状态，及其与实际可点击区域的时序关系。
- 点击是否被丢弃、界面是否未变、刷新是否延迟，下一动作是否发生得过早。

将选定的就绪条件、容易提前命中的标志及相关帧写到业务节点附近，再修改 `next`、识别条件或局部冻结等待。画面稳定不是资源加载完成的充分条件，标题出现也不是目标已可点击的充分条件。没有可靠画面信号时才使用有实测依据的延迟，记录限制。

首轮只跑出一个成功样本不能代替稳定性验证；修正后按项目要求验证受影响小段及相关失败分支。调试保存会增加磁盘 I/O，正式验证时注意时序差异，调试开关不永久写入无关生产入口。

## 本地截图与上传

保存日志、PNG、录制 JSONL 到本地本身不会把图像加入会话上下文。仅把必要帧的预算内预览或相关识别结果返回给模型；不要遍历回传整套录制、整份日志或将 PNG 编码进文本。工具若自行返回图片，仍按 `maamcp.md` 的回传前检查处理。
