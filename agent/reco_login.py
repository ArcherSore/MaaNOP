import json

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context

from common import get_latest_detail, recognize_server, send_focus_message
from constants import SERVER_1000_LIST_ROI, SERVER_TAB_BOXES
from server_session import (
    clear_server_session,
    initialize_server_session,
    is_server_session_finished,
    parse_server_range_string,
    take_next_server,
)


def _get_target_server(context: Context):
    """(server_id, region_type) chosen by the latest GetNextServer, or None when finished."""
    server = get_latest_detail(context, "GetNextServer")
    if not server or "server_id" not in server:
        return None
    return server["server_id"], server["region_type"]


@AgentServer.custom_recognition("SetServerRegion")
class SetServerRegion(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        region_type = json.loads(argv.custom_recognition_param)
        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"region_type": region_type},
        )


@AgentServer.custom_recognition("ParseServerRange")
class ParseServerRange(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        server_list = parse_server_range_string(json.loads(argv.custom_recognition_param))
        region_type = get_latest_detail(context, "SetServerRegion")["region_type"]

        initialize_server_session(
            argv.task_detail.task_id,
            server_list,
            region_type=region_type,
        )

        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 100, 100),
            detail={"server_list": server_list, "region_type": region_type},
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
            return None

        if not result.get("finished"):
            # max_hit 按任务累计；只在推进到新服时恢复一次刷新预算。
            context.clear_hit_count("RefreshStuckLoading")
            region_label = {"public": "公测", "non_wipe": "不删档", "alliance": "联盟"}[result["region_type"]]
            send_focus_message(
                context,
                f"准备处理{region_label}{result['server_id']} ({result['server_index']}/{result['server_cnt']})",
            )
            if context.tasker.stopping:
                return None

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
        target = _get_target_server(context)
        if target is None:
            return None
        target_server_id, region_type = target

        if region_type == "alliance":
            box = SERVER_TAB_BOXES["alliance"]["all"]
        elif region_type == "non_wipe":
            box = (
                SERVER_TAB_BOXES["non_wipe"][">=601"]
                if target_server_id >= 601
                else SERVER_TAB_BOXES["non_wipe"]["<601"]
            )
        else:
            box = (
                SERVER_TAB_BOXES["public"][">=1000"]
                if target_server_id >= 1000
                else SERVER_TAB_BOXES["public"]["<1000"]
            )

        return CustomRecognition.AnalyzeResult(
            box=box,
            detail={
                "server_id": target_server_id,
                "region_type": region_type,
                "box": box,
            },
        )


@AgentServer.custom_recognition("LocateServerButton")
class LocateServerButton(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        target = _get_target_server(context)
        if target is None:
            return None
        target_server_id, region_type = target

        matched_result, match_mode = recognize_server(
            context, argv.image, target_server_id, region_type
        )
        if matched_result is None:
            return None

        return CustomRecognition.AnalyzeResult(
            box=matched_result.box,
            detail={
                "server_id": target_server_id,
                "roi_used": SERVER_1000_LIST_ROI,
                "ocr_result": matched_result.text,
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
            return None

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
        task_mode = json.loads(argv.custom_recognition_param)
        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"task_mode": task_mode},
        )


TASK_MODE_BY_ENTRY = {
    "ShoppingFestivalTask": "shopping",
    "AccountLeveling": "leveling",
    "AccountClaims": "claiming",
}
TASK_MODE_NODES = ["SetShoppingFestivalTaskMode", "SetLevelingTaskMode", "SetClaimingTaskMode"]


def _get_task_mode(context: Context, argv: CustomRecognition.AnalyzeArg):
    task_mode = TASK_MODE_BY_ENTRY.get(argv.task_detail.entry)
    if task_mode:
        return task_mode

    for node_name in TASK_MODE_NODES:
        detail = get_latest_detail(context, node_name)
        if detail and detail.get("task_mode"):
            return detail["task_mode"]

    return None


def _match_task_mode(
    context: Context, argv: CustomRecognition.AnalyzeArg, task_mode: str
) -> CustomRecognition.AnalyzeResult:
    if _get_task_mode(context, argv) != task_mode:
        return None

    return CustomRecognition.AnalyzeResult(
        box=(0, 0, 0, 0),
        detail={"task_mode": task_mode},
    )


@AgentServer.custom_recognition("IsLevelingTask")
class IsLevelingTask(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        return _match_task_mode(context, argv, "leveling")


@AgentServer.custom_recognition("IsClaimingTask")
class IsClaimingTask(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        return _match_task_mode(context, argv, "claiming")


@AgentServer.custom_recognition("IsShoppingFestivalTask")
class IsShoppingFestivalTask(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        return _match_task_mode(context, argv, "shopping")

