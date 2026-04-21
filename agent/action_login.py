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
    run_recognition,
    send_focus_message,
)
from constants import (
    SERVER_1000_LIST_ROI,
    SERVER_1000_SCROLL_CLICKS_PER_ATTEMPT,
    SERVER_1000_SEARCH_ATTEMPTS,
    SERVER_1_999_SCROLL_CLICKS_PER_ATTEMPT,
    SERVER_1_999_SEARCH_ATTEMPTS,
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

        if target_server_id >= 1000:
            max_search_attempts = SERVER_1000_SEARCH_ATTEMPTS
            scroll_clicks_per_attempt = SERVER_1000_SCROLL_CLICKS_PER_ATTEMPT
        else:
            max_search_attempts = SERVER_1_999_SEARCH_ATTEMPTS
            scroll_clicks_per_attempt = SERVER_1_999_SCROLL_CLICKS_PER_ATTEMPT

        for attempt in range(max_search_attempts):
            image = capture_image(context)
            reco_detail = run_recognition(
                context,
                "ChooseServerButton",
                image,
                {
                    "ChooseServerButton": {
                        "roi": SERVER_1000_LIST_ROI,
                        "expected": rf".*(^|[^0-9]){target_server_id}([^0-9]|$).*",
                    }
                },
            )
            if reco_detail and reco_detail.hit and reco_detail.best_result:
                return True

            if attempt == max_search_attempts - 1:
                break

            down_arrow = run_recognition(context, "FindDownArrow", image)
            if not down_arrow or not down_arrow.hit or not down_arrow.best_result:
                return False

            box = down_arrow.best_result.box
            for _ in range(scroll_clicks_per_attempt):
                if not click_box_center(context, box):
                    return False
                time.sleep(SERVER_SCROLL_CLICK_INTERVAL)

        return False


@AgentServer.custom_action("HandleLoginPopups")
class HandleLoginPopups(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        while True:
            has_popup = False
            image = capture_image(context)

            announcement = run_recognition(context, "CheckAnnouncement", image)
            if announcement and announcement.hit and announcement.best_result:
                has_popup = True
                time.sleep(0.2)
                click_box_center(context, announcement.best_result.box)
                time.sleep(0.2)

            welfare = run_recognition(context, "CheckWelfare", image)
            if welfare and welfare.hit and welfare.best_result:
                has_popup = True
                click_point(context, 680, 400)
                time.sleep(0.2)
                click_key(context, 27)
                time.sleep(0.2)

            return_gift = run_recognition(context, "CheckReturnGift", image)
            if return_gift and return_gift.hit and return_gift.best_result:
                has_popup = True
                click_point(context, 680, 400)
                time.sleep(0.2)
                click_key(context, 27)
                time.sleep(0.2)

            if not has_popup:
                break

        return True


@AgentServer.custom_action("fastESC")
class FastESC(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        for _ in range(5):
            click_key(context, 27)
            time.sleep(0.2)

        image = capture_image(context)
        remain_popup = run_recognition(context, "CheckRemainPopup", image)
        if remain_popup and remain_popup.hit and remain_popup.best_result:
            click_point(context, 680, 400)
            time.sleep(0.2)
            click_key(context, 27)

        return True
