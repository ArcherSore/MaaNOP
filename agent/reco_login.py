from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context

from common import (
    find_server_ocr_result,
    get_detail_value,
    has_node_hit,
    run_recognition,
    send_focus_message,
    strip_quotes,
)
from constants import SERVER_1000_LIST_ROI
from server_session import (
    clear_server_session,
    initialize_server_session,
    is_server_session_finished,
    parse_server_range_string,
    take_next_server,
)


@AgentServer.custom_recognition("ParseServerRange")
class ParseServerRange(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        server_range_str = strip_quotes(argv.custom_recognition_param)
        server_list = parse_server_range_string(server_range_str)

        initialize_server_session(argv.task_detail.task_id, server_list)

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
        result = take_next_server(argv.task_detail.task_id)
        if result is None:
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail={"error": "ServerSession not found"},
            )

        if not result.get("finished"):
            send_focus_message(
                context,
                f"准备处理服务器 {result['server_id']} ({result['server_index']}/{result['server_cnt']})",
            )

        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail=result,
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

        reco_detail = run_recognition(
            context,
            "ChooseServerButton",
            argv.image,
            {
                "ChooseServerButton": {
                    "roi": SERVER_1000_LIST_ROI,
                    "expected": rf".*(^|[^0-9]){target_server_id}([^0-9]|$).*",
                }
            },
        )
        matched_result, match_mode = find_server_ocr_result(reco_detail, target_server_id)

        return CustomRecognition.AnalyzeResult(
            box=matched_result.box if matched_result else None,
            detail={
                "server_id": target_server_id,
                "roi_used": SERVER_1000_LIST_ROI,
                "ocr_result": matched_result.text if matched_result else None,
                "hit": bool(matched_result),
                "match_mode": match_mode,
            },
        )


@AgentServer.custom_recognition("AllCompleted")
class AllCompleted(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        task_id = argv.task_detail.task_id
        if not is_server_session_finished(task_id):
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        clear_server_session(task_id)

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
    if entry == "AccountLeveling":
        return "leveling"
    if entry == "AccountClaims":
        return "claiming"

    if has_node_hit(context, "SetShoppingFestivalTaskMode"):
        shopping_mode = get_detail_value(context, "SetShoppingFestivalTaskMode", "task_mode")
        if shopping_mode:
            return shopping_mode

    if has_node_hit(context, "SetLevelingTaskMode"):
        return get_detail_value(context, "SetLevelingTaskMode", "task_mode")

    if has_node_hit(context, "SetClaimingTaskMode"):
        return get_detail_value(context, "SetClaimingTaskMode", "task_mode")

    return None


@AgentServer.custom_recognition("IsLevelingTask")
class IsLevelingTask(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        if _get_task_mode(context, argv) != "leveling":
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"task_mode": "leveling"},
        )


@AgentServer.custom_recognition("IsClaimingTask")
class IsClaimingTask(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        if _get_task_mode(context, argv) != "claiming":
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"task_mode": "claiming"},
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
