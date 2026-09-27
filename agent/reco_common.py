import json

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context

from common import send_focus_message


@AgentServer.custom_recognition("FindTopEntry")
class FindTopEntry(CustomRecognition):
    """在顶部入口栏中识别目标入口，点击交给 pipeline 的 action。"""

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        template = json.loads(argv.custom_recognition_param)["template"]
        reco_detail = context.run_recognition(
            "TopEntryTemplate",
            argv.image,
            {
                "TopEntryTemplate": {
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


@AgentServer.custom_recognition("MatchPopup")
class MatchPopup(CustomRecognition):
    """按顺序识别多种弹窗, 命中后返回该弹窗对应的点击目标位置。
    target 可省略，默认使用识别框；也可指定固定点击框。

    custom_recognition_param 格式:
    {
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
        popups = json.loads(argv.custom_recognition_param)["popups"]

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
                argv.image,
                {
                    argv.node_name: {
                        "recognition": {
                            "type": "TemplateMatch",
                            "param": template_param,
                        }
                    }
                },
            )
            if not reco_detail or not reco_detail.hit:
                continue

            if popup.get("focus"):
                send_focus_message(context, popup["focus"])

            return CustomRecognition.AnalyzeResult(
                box=popup.get("target", reco_detail.box),
                detail={"popup": popup.get("name", "")},
            )

        return None
