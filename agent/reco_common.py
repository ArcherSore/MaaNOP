import json

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context

from common import send_focus_message


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


@AgentServer.custom_recognition("MatchWithout")
class MatchWithout(CustomRecognition):
    """同一张截图上 match 节点命中、without 节点不命中时命中，返回 match 的识别框。

    pipeline 里「A 且非 B」只能拆成两个节点，分别在两帧上判断；两帧之间画面变了（比如切地图的加载画面）就会误判。
    custom_recognition_param: {"match": "节点名", "without": "节点名"}
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        param = json.loads(argv.custom_recognition_param)
        matched = context.run_recognition(param["match"], argv.image)
        if not matched or not matched.hit:
            return None
        excluded = context.run_recognition(param["without"], argv.image)
        if excluded and excluded.hit:
            return None
        return CustomRecognition.AnalyzeResult(box=matched.box, detail={})


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
                        "recognition": {"type": "TemplateMatch", "param": template_param}
                    }
                },
            )
            if context.tasker.stopping:
                return None
            if not reco_detail or not reco_detail.hit:
                continue

            if popup.get("focus"):
                send_focus_message(context, popup["focus"])
                if context.tasker.stopping:
                    return None

            return CustomRecognition.AnalyzeResult(
                box=popup.get("target", reco_detail.box),
                detail={"popup": popup.get("name", "")},
            )

        return None
