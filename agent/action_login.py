import time

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from common import (
    capture_image,
    click_box_center,
    click_key,
    click_point,
    get_detail_value,
    recognize_server,
    run_recognition,
)
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


@AgentServer.custom_action("ScrollToTargetServer")
class ScrollToTargetServer(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        target_server_id = get_detail_value(context, "GetNextServer", "server_id")
        if target_server_id is None:
            return False

        region_type = get_detail_value(context, "GetNextServer", "region_type", "public")

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
            image = capture_image(context)
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

            down_arrow = run_recognition(context, "FindDownArrow", image)
            if not down_arrow or not down_arrow.hit or not down_arrow.best_result:
                return False

            box = down_arrow.best_result.box
            for _ in range(scroll_clicks_per_attempt):
                if context.tasker.stopping:
                    return False
                if not click_box_center(context, box):
                    return False
                time.sleep(SERVER_SCROLL_CLICK_INTERVAL)

        return False


def _focus_and_escape(context: Context) -> bool:
    if not click_point(context, 680, 400):
        return False
    time.sleep(0.2)
    return click_key(context, 27)


@AgentServer.custom_action("fastESC")
class FastESC(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        for _ in range(5):
            if not click_key(context, 27):
                return False
            time.sleep(0.2)

        image = capture_image(context)
        remain_popup = run_recognition(context, "CheckRemainPopup", image)
        if remain_popup and remain_popup.hit and remain_popup.best_result:
            return _focus_and_escape(context)

        return True
