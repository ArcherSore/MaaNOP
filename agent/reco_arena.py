import json

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context

from common import run_recognition, send_focus_message


@AgentServer.custom_recognition("MatchPopup")
class MatchPopup(CustomRecognition):
    """按顺序识别多种弹窗, 命中后返回该弹窗对应的点击目标位置。
    Tips: 目标位置非识别位置, 而是按钮硬编码位置

    custom_recognition_param 格式:
    {
        "popups": [
            {
                "name": "弹窗名称",
                "template": "arena/Xxx.png",   // 识别弹窗种类的模板, 支持数组
                "roi": [x, y, w, h],           // 可省略, 默认全屏
                "target": [x, y, w, h],        // 命中后要点击的目标框
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
        param = json.loads(argv.custom_recognition_param or "{}")
        popups = param.get("popups", [])

        for popup in popups:
            template = popup.get("template")
            if not template:
                continue

            template_param = {
                "template": template,
                "roi": popup.get("roi", [0, 0, 0, 0]),
            }
            if "threshold" in popup:
                template_param["threshold"] = popup["threshold"]

            reco_detail = run_recognition(
                context,
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
            if not reco_detail or not reco_detail.hit or not reco_detail.best_result:
                continue

            target_box = popup.get("target")
            if not target_box:
                continue

            if popup.get("focus"):
                send_focus_message(context, popup["focus"])

            return CustomRecognition.AnalyzeResult(
                box=target_box,
                detail={"popup": popup.get("name", "")},
            )

        return CustomRecognition.AnalyzeResult(box=None, detail={})
