import json
import time

import numpy as np
from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context

# 白字的最暗通道 > TEXT_BRIGHT 算文字；两帧同一像素亮度差 > PIXEL_DIFF 且其中一帧是文字，算变了。
# 实测（1340x720）：面板底色半透明，背后场景变化、切地图后重新画出，变化像素都是 0；
# 只差时间戳最后一位的两行日志（09:02:07 → 09:02:08）变 7~10 个像素，换一行别的日志变 90~700 个。
TEXT_BRIGHT = 140
PIXEL_DIFF = 60
MIN_CHANGED_PIXELS = 3


@AgentServer.custom_recognition("AutoManageLogQuiet")
class AutoManageLogQuiet(CustomRecognition):
    """托管面板上的最新一行日志连续 quiet_seconds 秒没有变化、托管也没在做别的事时命中。

    require_nodes 里有一个认不出来（面板没了：忍者考试扫荡、切地图；地图被遮罩压暗：托管自己开了窗口），
    或 busy_nodes 里有一个认出来（不写日志的动作，例如浇水的提示），都算还在忙，重新计时。
    计时从本任务第一次调用开始。
    custom_recognition_param:
    {
        "require_nodes": ["面板节点", ...],  // 都要认出来才算闲着；返回第一个的识别框
        "busy_nodes": ["节点名", ...],       // 认出任意一个就算还在忙，可省略
        "line_roi": [x, y, w, h],           // 面板上日志文字的区域
        "quiet_seconds": 10
    }
    """

    def __init__(self):
        super().__init__()
        self._task_id = None
        self._text = None
        self._changed_at = 0.0

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        param = json.loads(argv.custom_recognition_param)
        now = time.monotonic()
        if argv.task_detail.task_id != self._task_id:
            self._task_id = argv.task_detail.task_id
            self._text = None
            self._changed_at = now

        required = [context.run_recognition(node, argv.image) for node in param["require_nodes"]]
        if not all(detail and detail.hit for detail in required):
            self._changed_at = now
            return None

        for node in param.get("busy_nodes", []):
            busy = context.run_recognition(node, argv.image)
            if busy and busy.hit:
                self._changed_at = now
                return None

        x, y, w, h = param["line_roi"]
        text = argv.image[y : y + h, x : x + w].min(axis=2).astype(np.int16)
        if self._text is not None:
            changed = (np.abs(text - self._text) > PIXEL_DIFF) & (np.maximum(text, self._text) > TEXT_BRIGHT)
            if np.count_nonzero(changed) >= MIN_CHANGED_PIXELS:
                self._changed_at = now
        self._text = text

        quiet = now - self._changed_at
        if quiet < param["quiet_seconds"]:
            return None
        return CustomRecognition.AnalyzeResult(box=required[0].box, detail={"quiet_seconds": round(quiet)})
