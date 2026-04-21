from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context

from common import get_detail_value, get_latest_detail, has_node_hit, run_recognition, send_focus_message, strip_quotes
from constants import SERVER_1000_LIST_ROI, SERVER_ROI_MAP


@AgentServer.custom_recognition("ParseServerRange")
class ParseServerRange(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        server_range_str = strip_quotes(argv.custom_recognition_param)

        server_list = []
        for range_part in server_range_str.split(","):
            range_part = range_part.strip()
            if not range_part:
                continue
            if "-" in range_part:
                start, end = map(int, range_part.split("-"))
                server_list.extend(range(start, end + 1))
            else:
                server_list.append(int(range_part))

        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 100, 100),
            detail={"server_list": server_list},
        )


@AgentServer.custom_recognition("GetNextServer")
class GetNextServer(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        prev_detail = get_latest_detail(context, "GetNextServer")
        if prev_detail is None:
            parse_detail = get_latest_detail(context, "ParseServer")
            if parse_detail is None:
                return CustomRecognition.AnalyzeResult(
                    box=None,
                    detail={"error": "ParseServer not found"},
                )
            server_list = parse_detail.get("server_list", [])
            current_server_index = 0
        else:
            server_list = prev_detail.get("server_list", [])
            current_server_index = prev_detail.get("server_index", 0)

        if current_server_index >= len(server_list):
            return CustomRecognition.AnalyzeResult(
                box=(0, 0, 0, 0),
                detail={
                    "server_list": server_list,
                    "server_index": current_server_index,
                    "server_cnt": len(server_list),
                    "finished": True,
                },
            )

        current_server = server_list[current_server_index]
        next_server_index = current_server_index + 1
        send_focus_message(
            context,
            f"准备处理服务器 {current_server} ({next_server_index}/{len(server_list)})",
        )

        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={
                "server_list": server_list,
                "server_id": current_server,
                "server_index": next_server_index,
                "server_cnt": len(server_list),
                "finished": False,
            },
        )


@AgentServer.custom_recognition("DetectServerPage")
class DetectServerPage(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        target_server_id = get_detail_value(context, "GetNextServer", "server_id")
        if target_server_id is None:
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        roi = [403, 216, 236, 131]
        expected = ".*1000.*" if target_server_id >= 1000 else ".*1-999.*"
        reco_detail = run_recognition(
            context,
            "ChooseServerType",
            argv.image,
            {"ChooseServerType": {"roi": roi, "expected": [expected]}},
        )

        return CustomRecognition.AnalyzeResult(
            box=reco_detail.best_result.box if reco_detail and reco_detail.hit else None,
            detail={
                "server_id": target_server_id,
                "roi_used": roi,
                "ocr_result": reco_detail.best_result.text if reco_detail and reco_detail.hit else None,
                "hit": reco_detail.hit if reco_detail else False,
            },
        )


@AgentServer.custom_recognition("LocateServerButton")
class LocateServerButton(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        target_server_id = get_detail_value(context, "GetNextServer", "server_id")
        if target_server_id is None:
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        if target_server_id >= 1000:
            roi = SERVER_1000_LIST_ROI
        else:
            roi = SERVER_ROI_MAP.get(target_server_id)
            if roi is None:
                return CustomRecognition.AnalyzeResult(
                    box=None,
                    detail={
                        "server_id": target_server_id,
                        "error": "Server ROI not configured",
                    },
                )

        reco_detail = run_recognition(
            context,
            "ChooseServerButton",
            argv.image,
            {"ChooseServerButton": {"roi": roi, "expected": f".*{target_server_id}.*"}},
        )

        return CustomRecognition.AnalyzeResult(
            box=reco_detail.best_result.box if reco_detail and reco_detail.hit else None,
            detail={
                "server_id": target_server_id,
                "roi_used": roi,
                "ocr_result": reco_detail.best_result.text if reco_detail and reco_detail.hit else None,
                "hit": reco_detail.hit if reco_detail else False,
            },
        )


@AgentServer.custom_recognition("AllCompleted")
class AllCompleted(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        finished = get_detail_value(context, "GetNextServer", "finished")
        if not finished:
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"finished": True},
        )


@AgentServer.custom_recognition("SetTaskMode")
class SetTaskMode(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        task_mode = strip_quotes(argv.custom_recognition_param)
        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"task_mode": task_mode},
        )


def _get_task_mode(context: Context, argv: CustomRecognition.AnalyzeArg):
    entry = argv.task_detail.entry
    if entry == "ShoppingFestivalTask":
        return "shopping"
    if entry == "AccountTraining":
        return "training"

    if has_node_hit(context, "SetShoppingFestivalTaskMode"):
        shopping_mode = get_detail_value(context, "SetShoppingFestivalTaskMode", "task_mode")
        if shopping_mode:
            return shopping_mode

    if has_node_hit(context, "SetTrainingTaskMode"):
        return get_detail_value(context, "SetTrainingTaskMode", "task_mode")

    return None


@AgentServer.custom_recognition("IsTrainingTask")
class IsTrainingTask(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        if _get_task_mode(context, argv) != "training":
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"task_mode": "training"},
        )


@AgentServer.custom_recognition("IsShoppingFestivalTask")
class IsShoppingFestivalTask(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        if _get_task_mode(context, argv) != "shopping":
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"task_mode": "shopping"},
        )


@AgentServer.custom_recognition("DetectLoginPopup")
class DetectLoginPopup(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        for reco_name in ["CheckAnnouncement", "CheckWelfare", "CheckReturnGift"]:
            reco_detail = run_recognition(context, reco_name, argv.image)
            if reco_detail and reco_detail.hit and reco_detail.best_result:
                return CustomRecognition.AnalyzeResult(
                    box=reco_detail.best_result.box,
                    detail={"popup_type": reco_name},
                )

        return CustomRecognition.AnalyzeResult(box=None, detail={})
