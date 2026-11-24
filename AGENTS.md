# MaaNOP 智能体须知

基于 MaaFramework，为《火影忍者 Online》Windows 客户端实现自动化。

## 提交规范

- Git 提交消息使用中文 Conventional Commits 格式（`<type>: <中文摘要>`）。类型使用标准英文标识，正文如有需要也用中文。不写 `type(scope)` 形式的范围。

## 修改范围与证据

- 默认用 Pipeline 实现；只有流水线无法表达的跨节点状态、动态计算和历史结果分支才在 `agent/` 写 Python。
- 节点名、任务入口、自定义注册名和图片路径都是接口：重命名或移动前，搜索 `agent/`、流水线和 `interface.json` 中的引用（含任务模式映射和 `pipeline_override`）。
- 优先复用现有节点和 `common/` 组件；多个调用方只差业务条件时由调用方传入条件，不复制局部分支。扩展公共入口须保留其他调用方的默认行为，并验证默认调用和新调用。
- 新增或修改协议字段时，按 `agent/requirements.txt` 锁定的 maafw 版本核对名称、类型和语义；不要直接套用最新版文档或其他项目的协议。
- 根目录仅保留跨任务规则。任务专属的弹窗顺序、等待条件和按钮状态写在对应节点附近，只维护一处。
- 节点注释只写后续开发者改动时需要知道的约束：为什么这样写、为什么不能换成别的写法。不写测量数据、日期、来源、试错过程、未验证清单或对配置的复述；测量和证据留在任务记录（`artifacts/<功能>-<日期>/`）。
- 不得仅凭旧注释或人为构造的测试画面新增游戏状态分支；先用真实截图或运行记录确认该状态及其触发条件。
- JSON 排版：数组写在同一行且括号内留空格（`[ "A", "B" ]`），大括号内的字段逐行展开，不压行。

## MaaMCP 探索

- 使用 MaaMCP 探索新功能、把观察转成 Pipeline 或诊断实际流程失败时，读取项目技能 [maanop-explore](skills/maanop-explore/SKILL.md)，其中包含截图回传与上下文预算。`skills/` 是唯一维护源，各模型的技能发现入口按需单独接入，不复制多份正文。已有明确设计的普通代码修改无需重新探索游戏。

## 识别与点击

- 点击前先识别按钮就绪。按钮出现时资源可能仍未加载完成，点击会被吞；点击已发送却未推进且找不到根因时，把它列为排查假设。
- 有可区分悬停反馈的按钮用「悬停 → 点击」：悬停节点识别按钮并移动鼠标，`next` 直连点击节点，点击节点只等待同一按钮的悬停高亮再点击。证据不足时询问用户悬停后按钮哪里变亮或变色，接受用户的实测描述。
- 依赖 OCR 或模板识别前，用真实截图验证，覆盖相关状态并为设备渲染差异留余量。模板阈值依据目标与易混淆画面的测量结果设置，不照搬其他节点。
- 小字和带文字的按钮优先考虑 OCR，或 OCR 识别标识后点击固定位置；此类小模板跨设备渲染差异较大，容易低于阈值。图标等稳定图像可使用模板，最终以截图验证结果选择。
- 用标识识别配合固定位置点击时，验证标识与点击目标的出现时序：只有标识能证明目标已出现且可点击时才能直接点击；目标晚于标识出现时，须继续等待目标就绪，不能仅凭先出现的标题等标识点击。
- 不要将 ROI 重叠的 OCR 节点放在同一个 `next` 列表中，会导致结果损坏。
- `And.all_of` 引用节点名只借用识别参数，忽略其 `inverse`；在 `And` 之外不能用 `"recognition": "OtherNode"`。表达“A 且非 B”可串联识别并对 B 设置 `inverse`；必须同帧判断时使用 `agent/common/reco_common.py` 中的 `MatchWithout`。
- 同一按钮的悬停和点击默认共用按钮内部的小区域，整个区域须严格位于可交互范围内。Click 在目标框内随机落点，以模板匹配框作为目标时也须满足此条件。需要精确中心点击时，使用 `PreciseClick` 或 `agent/common/utils.py` 的 `click_center`。

## 流程与失败语义

- **根据识别到的状态推进。** `Node.Action.Succeeded` 只表示动作已发送；打开、关闭、领取、确认等操作后，须由后继 `next` 识别到结果状态再推进。
- 点击后用 `next` 等待结果；超时才经 `on_error` 回原节点，重新识别“仍待处理”后再点。
- 优先通过状态识别或 `post_wait_freezes` 等待。仅在没有可用画面信号时使用延迟，并在节点旁说明原因；不要照搬其他任务的静默期。
- **框架语义：** A 的 `next` 识别超时进入 A 的 `on_error`；命中 B 但 B 动作失败，进入 B 的 `on_error`。错误分支成功执行后会继续正常流程；若最终正常结束，任务报告 Succeeded，先前错误不会自动使最终结果失败。参见 [Pipeline 协议](https://maafw.com/docs/3.1-PipelineProtocol.html)；最终结果逻辑已对照 v5.12.3 的 `PipelineTask::run`。
- **项目约束：** 正常完成和“无事可做”通过 `next` 识别；`on_error` 仅用于恢复、清理或明确需要的持续等待。禁止把“未识别到预期画面”当作“无事可做”，直接转入成功终止节点或下一任务；重试前仍须识别当前状态。若清理后目标仍未达成，应以失败结束。
- 没有 `on_error` 时，超时或动作失败会自然结束为 Failed，无需另加报告节点。已识别到无法达成目标的状态时，使用 `agent/common/action_common.py` 的 `FalseAction` 主动失败；不要用永不匹配的节点强制超时。

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
- 模拟 `CustomController` 只检查流程逻辑：点击落点、点击被丢弃后的重试、状态未改变、延迟刷新和超时失败。画面优先用已保存的真实截图，按点击映射切换；缺真实截图时可局部合成，须在脚本中标明，不能作为识别准确率、阈值或新增状态的依据。
- 真实游戏中有消耗或不可逆的步骤，只能在检查当前画面并获得批准后执行。
