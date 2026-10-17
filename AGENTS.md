# MaaNOP 智能体须知

基于 MaaFramework，为《火影忍者 Online》Windows 客户端实现自动化。

## 修改范围与证据

- 默认使用 `assets/resource/pipeline/` 中的 Pipeline JSON，模板位于 `assets/resource/image/`，GUI 任务和选项位于 `assets/interface.json`。只有流水线无法表达的跨节点状态、动态计算和历史结果分支才在 `agent/` 中添加 Python。
- 节点、任务入口和自定义注册名称是接口。重命名前搜索 `agent/`、流水线和 `interface.json` 中的引用，包括任务模式映射和 `pipeline_override`。
- 修改保持局部化，尤其是经过运行调优的 `Leveling.json`；新增节点或 Python 实现前，先检查现有流水线和公共组件能否复用。
- 新增或修改协议字段时，按 `agent/requirements.txt` 锁定的 maafw 版本核对名称、类型和语义；不要直接套用最新版文档或其他项目的协议。
- 根目录仅保留跨任务规则。任务专属的弹窗顺序、等待条件、按钮状态和测量数据写在对应节点附近，只维护一处；有截图或运行记录时注明来源。
- 不得仅凭旧注释或人为构造的测试画面新增游戏状态分支；先用真实截图或运行记录确认该状态及其触发条件。

## 识别与点击

- 依赖 OCR 或模板识别前，用真实截图验证，覆盖相关状态并为设备渲染差异留余量。模板阈值依据目标与易混淆画面的测量结果设置，不照搬其他节点。
- 小字和带文字的按钮优先考虑 OCR，或 OCR 识别标识后点击固定位置；此类小模板跨设备渲染差异较大，容易低于阈值。图标等稳定图像可使用模板，最终以截图验证结果选择。
- 用标识识别配合固定位置点击时，验证标识与点击目标的出现时序：只有标识能证明目标已出现且可点击时才能直接点击；目标晚于标识出现时，须继续等待目标就绪，不能仅凭先出现的标题等标识点击。
- 不要将 ROI 重叠的 OCR 节点放在同一个 `next` 列表中，会导致结果损坏。
- `And.all_of` 引用节点名只借用识别参数，忽略其 `inverse`；在 `And` 之外不能用 `"recognition": "OtherNode"`。表达“A 且非 B”可串联识别并对 B 设置 `inverse`；必须同帧判断时使用 `agent/reco_common.py` 中的 `MatchWithout`。
- Click 在目标框内随机落点，点击框须严格位于可点击区域内部；以模板匹配框作为目标时也要满足此条件。精确中心点击使用 `PreciseClick` 或 Python 的 `click_center`。

## 流程与失败语义

- **根据识别到的状态推进。** `Node.Action.Succeeded` 只表示动作已发送。打开、关闭、领取、消耗或确认后，须识别到结果状态才能继续；已有后继识别可以承担验证，不必额外新增确认节点。验证条件应反映业务目标，不能把必须完成的操作降为可跳过。
- 重试点击必须以识别到“仍待处理”为前提，不能仅因计时结束而补点。
- 优先通过状态识别或 `post_wait_freezes` 等待。仅在没有可用画面信号时使用延迟，并在节点旁说明原因；不要照搬其他任务的静默期。
- `next` 覆盖预期画面，包括中途恢复、对话框、加载和正常完成。无 `recognition` 的节点总会命中，应放在需要优先判断的状态之后。等待的 `timeout` 写在持有该 `next` 的节点上。
- **框架语义：** A 的 `next` 识别超时进入 A 的 `on_error`；命中 B 但 B 动作失败，进入 B 的 `on_error`。错误分支成功执行后会继续正常流程；若最终正常结束，任务报告 Succeeded，先前错误不会自动使最终结果失败。参见 [Pipeline 协议](https://maafw.com/docs/3.1-PipelineProtocol.html)；最终结果逻辑已对照 v5.12.3 的 `PipelineTask::run`。
- **项目约束：** 正常完成和“无事可做”通过 `next` 识别；`on_error` 仅用于恢复、清理或明确需要的持续等待。禁止把“未识别到预期画面”当作“无事可做”，直接转入成功终止节点或下一任务；重试前仍须识别当前状态。若清理后目标仍未达成，应以失败结束。
- 没有 `on_error` 时，超时或动作失败会自然结束为 Failed，无需另加报告节点。已识别到无法达成目标的状态时，使用 `agent/action_common.py` 的 `FalseAction` 主动失败；不要用永不匹配的节点强制超时。
- 有消耗或不可逆操作须以前一步已验证的状态为前提，并设置 `max_hit` 安全上限；不能依靠上限结束正常循环。

## 用户消息

- 未要求时不新增 `focus`；保留行为未变的已有消息，不为输出消息增加节点或分支。
- 必须添加时，一个原因只报告一次；不用每轮轮询都会触发的 `Node.NextList.Failed`，不在将由 `on_error` 恢复的节点上提前报告任务失败。

## Python 动作

- 直接调用 maafw API，不添加仅再次封装 API 的辅助函数。
- 用 `context.run_task("Node")` 执行流水线等待，根据 `TaskDetail.nodes` 中的节点名判断路径。`status` 无法区分正常完成和经 `on_error` 处理的超时。
- 每次阻塞调用后检查 `context.tasker.stopping`。

## 验证

- **`npx @nekosu/maa-tools check` 仅交给 CI 执行**：曾在 Windows 本地运行时删除已跟踪模板图片。
- Schema 校验命令：`python tools/validate_schema.py --schema-dir deps/tools --resource-dirs assets/resource --exclude-dirs assets/resource/announcement --interface-files assets/interface.json`。流水线含 `//` 注释，不能直接用 `json.loads` 解析。
- 修改 `agent/` 后运行 `python -m compileall agent`，CI 不检查 Python。
- 修改流水线后，用项目 `.venv` 中的 maafw 执行 `Resource.post_bundle` 加载资源包。Schema 校验无法发现不存在的 `next` / `on_error` 引用或非法的节点名识别引用；这些会使引擎拒绝加载。
- 对修改后的任务使用模拟 `CustomController`：提供已保存的真实截图，按点击映射切换画面，覆盖点击被丢弃、状态未改变和延迟刷新。
- 真实游戏中有消耗或不可逆的步骤，只能在检查当前画面并获得批准后执行。
