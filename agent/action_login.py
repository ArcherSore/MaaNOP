import time

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from common import click_center, get_latest_detail, recognize_server
from constants import (
    SERVER_1000_SCROLL_CLICKS_PER_ATTEMPT,
    SERVER_1000_SEARCH_ATTEMPTS,
    SERVER_1_999_SCROLL_CLICKS_PER_ATTEMPT,
    SERVER_1_999_SEARCH_ATTEMPTS,
    SERVER_ALLIANCE_SCROLL_CLICKS_PER_ATTEMPT,
    SERVER_ALLIANCE_SEARCH_ATTEMPTS,
    SERVER_NON_WIPE_SCROLL_CLICKS_PER_ATTEMPT,
    SERVER_NON_WIPE_SEARCH_ATTEMPTS,
    SERVER_SCROLL_CLICK_INTERVAL,
)


@AgentServer.custom_action("CloseMatchedLoginPopup")
class CloseMatchedLoginPopup(CustomAction):
    """关闭本次识别的弹窗，交给 pipeline 等待消失，最多补点一次。"""

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        result = argv.reco_detail.best_result if argv.reco_detail else None
        if not result or not isinstance(result.detail, dict):
            return False
        recognition = result.detail.get("recognition")
        if not recognition:
            return False

        override = {
            "CurrentLoginPopup": {"recognition": recognition},
            "ClickCurrentLoginPopup": {
                "action": {
                    "type": "Click",
                    "param": {"target": list(argv.box)},
                }
            },
        }
        for _ in range(2):
            if context.tasker.stopping:
                return False
            # 每次尝试先检查消失，再重新识别并点击，避免使用超时前的旧画面。
            detail = context.run_task("CloseMatchedLoginPopupTask", override)
            if context.tasker.stopping:
                return False
            if detail and any(node.name == "CurrentLoginPopupGone" for node in detail.nodes):
                return True

        return False


@AgentServer.custom_action("ScrollToTargetServer")
class ScrollToTargetServer(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        server = get_latest_detail(context, "GetNextServer")
        if not server or "server_id" not in server:
            return False
        target_server_id = server["server_id"]
        region_type = server["region_type"]

        if region_type == "alliance":
            max_search_attempts = SERVER_ALLIANCE_SEARCH_ATTEMPTS
            scroll_clicks_per_attempt = SERVER_ALLIANCE_SCROLL_CLICKS_PER_ATTEMPT
        elif region_type == "non_wipe":
            max_search_attempts = SERVER_NON_WIPE_SEARCH_ATTEMPTS
            scroll_clicks_per_attempt = SERVER_NON_WIPE_SCROLL_CLICKS_PER_ATTEMPT
        elif target_server_id >= 1000:
            max_search_attempts = SERVER_1000_SEARCH_ATTEMPTS
            scroll_clicks_per_attempt = SERVER_1000_SCROLL_CLICKS_PER_ATTEMPT
        else:
            max_search_attempts = SERVER_1_999_SEARCH_ATTEMPTS
            scroll_clicks_per_attempt = SERVER_1_999_SCROLL_CLICKS_PER_ATTEMPT

        for attempt in range(max_search_attempts):
            if context.tasker.stopping:
                return False
            image = context.tasker.controller.post_screencap().wait().get()
            if context.tasker.stopping:
                return False
            matched_result, _ = recognize_server(
                context, image, target_server_id, region_type
            )
            if context.tasker.stopping:
                return False
            if matched_result:
                return True

            if attempt == max_search_attempts - 1:
                break

            down_arrow = context.run_recognition("FindDownArrow", image)
            if not down_arrow or not down_arrow.hit:
                return False

            for _ in range(scroll_clicks_per_attempt):
                if context.tasker.stopping:
                    return False
                if not click_center(context, down_arrow.box):
                    return False
                time.sleep(SERVER_SCROLL_CLICK_INTERVAL)

        return False
