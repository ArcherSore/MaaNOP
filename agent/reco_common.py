import json
import time

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context

from common import get_latest_detail, send_focus_message

POPUP_CLOSE_POLL_INTERVAL = 0.2


def find_entry(
    context: Context,
    argv: CustomRecognition.AnalyzeArg,
    node_name: str,
) -> CustomRecognition.AnalyzeResult:
    """用 node_name 节点的 ROI 找 custom_recognition_param 里的模板，点击交给 pipeline 的 action。"""
    template = json.loads(argv.custom_recognition_param)["template"]
    reco_detail = context.run_recognition(
        node_name,
        argv.image,
        {
            node_name: {
                "recognition": {
                    "type": "TemplateMatch",
                    "param": {"template": template},
                }
            }
        },
    )
    if not reco_detail or not reco_detail.hit:
        return None
    return CustomRecognition.AnalyzeResult(box=reco_detail.box, detail={})


@AgentServer.custom_recognition("FindTopEntry")
class FindTopEntry(CustomRecognition):
    """在顶部入口栏中识别目标入口。"""

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        return find_entry(context, argv, "TopEntryTemplate")


@AgentServer.custom_recognition("FindBottomEntry")
class FindBottomEntry(CustomRecognition):
    """在底部入口栏中识别目标入口。"""

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        return find_entry(context, argv, "BottomEntryTemplate")


@AgentServer.custom_recognition("MatchPopup")
class MatchPopup(CustomRecognition):
    """按顺序识别多种弹窗, 命中后返回该弹窗对应的点击目标位置。
    target 可省略，默认使用识别框；也可指定固定点击框。

    custom_recognition_param 格式:
    {
        "close_timeout": 5,                    // 可省略; 秒。刚点过的弹窗仍在画面里时, 等它消失再识别,
                                               // 超时才视为点击失效并重新命中 (游戏画面刷新有延迟,
                                               // 不等的话会对同一位置再点一次, 弹窗已消失就点到了底下)
        "popups": [
            {
                "name": "弹窗名称",
                "template": "arena/Xxx.png",   // 识别弹窗种类的模板, 支持数组
                "roi": [x, y, w, h],           // 可省略, 默认全屏
                "target": [x, y, w, h],        // 可省略, 默认使用识别框
                "focus": "识别到xxx弹窗"        // 可选, 命中时发送的通知消息
            }
        ]
    }
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        param = json.loads(argv.custom_recognition_param)
        popups = param["popups"]
        close_timeout = param.get("close_timeout", 0)
        last = get_latest_detail(context, argv.node_name) if close_timeout else None
        last_popup = last.get("popup") if last else None
        deadline = time.monotonic() + close_timeout

        image = argv.image
        while True:
            for popup in popups:
                if context.tasker.stopping:
                    return None

                template = popup.get("template")
                if not template:
                    continue

                template_param = {
                    "template": template,
                    "roi": popup.get("roi", [0, 0, 0, 0]),
                }
                if "threshold" in popup:
                    template_param["threshold"] = popup["threshold"]

                reco_detail = context.run_recognition(
                    argv.node_name,
                    image,
                    {
                        argv.node_name: {
                            "recognition": {
                                "type": "TemplateMatch",
                                "param": template_param,
                            }
                        }
                    },
                )
                if reco_detail and reco_detail.hit:
                    break
            else:
                return None

            name = popup.get("name", "")
            if name != last_popup or time.monotonic() >= deadline:
                break

            # 刚点过的弹窗还在画面里, 等它消失
            time.sleep(POPUP_CLOSE_POLL_INTERVAL)
            if context.tasker.stopping:
                return None
            image = context.tasker.controller.post_screencap().wait().get()

        if popup.get("focus"):
            send_focus_message(context, popup["focus"])

        return CustomRecognition.AnalyzeResult(
            box=popup.get("target", reco_detail.box),
            detail={"popup": name},
        )
