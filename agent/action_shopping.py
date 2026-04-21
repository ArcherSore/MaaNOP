import time

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from common import capture_image, click_box_center, get_detail_value, get_recognition_box, parse_digits, run_recognition, send_focus_message
from constants import SHOPPING_GIFT_COUNT_ROIS, SHOPPING_GIFT_OPTION_CENTERS


@AgentServer.custom_action("PasteShoppingQuantity")
class PasteShoppingQuantity(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        quantity = get_detail_value(context, "FindShoppingFestivalTarget", "quantity")
        if quantity is None:
            return False

        context.tasker.controller.post_input_text(str(quantity)).wait()
        return True


@AgentServer.custom_action("ClickShoppingFriendInput")
class ClickShoppingFriendInput(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        return click_box_center(context, [535, 541, 67, 15])


@AgentServer.custom_action("PasteShoppingFriendName")
class PasteShoppingFriendName(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        friend_name = get_detail_value(context, "GetShoppingFriendName", "friend_name")
        if not friend_name:
            return False

        context.tasker.controller.post_input_text(friend_name).wait()
        return True


@AgentServer.custom_action("ClickShoppingFriendOption")
class ClickShoppingFriendOption(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        return click_box_center(context, [517, 558, 108, 15])


@AgentServer.custom_action("FocusShoppingFestivalBeforeExit")
class FocusShoppingFestivalBeforeExit(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        return click_box_center(context, [680, 400, 1, 1])


@AgentServer.custom_action("ProcessShoppingFestivalGifts")
class ProcessShoppingFestivalGifts(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        image = capture_image(context)

        select_box = get_recognition_box(context, image, "ShoppingFestivalGiftSelectTemplate")
        minus_box = get_recognition_box(context, image, "ShoppingFestivalMinusTemplate")
        plus_box = get_recognition_box(context, image, "ShoppingFestivalPlusTemplate")
        send_box = get_recognition_box(context, image, "ShoppingFestivalSendTemplate")
        if not select_box or not minus_box or not plus_box or not send_box:
            return False

        gift_targets = []
        for index, gift_roi in enumerate(SHOPPING_GIFT_COUNT_ROIS, start=1):
            reco_detail = run_recognition(
                context,
                "ShoppingFestivalGiftCountOCR",
                image,
                {"ShoppingFestivalGiftCountOCR": {"roi": gift_roi}},
            )

            gift_text = ""
            if reco_detail and reco_detail.hit and reco_detail.best_result:
                gift_text = reco_detail.best_result.text or ""

            digits = parse_digits(gift_text)
            target_count = int(digits) if digits in {"1", "2", "3"} else 0
            send_focus_message(context, f"购物节第 {index} 个字需要赠送 {target_count}")

            if target_count > 0:
                gift_targets.append((index, target_count))

        if not gift_targets:
            send_focus_message(context, "购物节未识别到需要赠送的文字数量")
            return True

        current_count = 1
        for index, target_count in gift_targets:
            if not click_box_center(context, select_box):
                return False
            time.sleep(0.2)

            if index > len(SHOPPING_GIFT_OPTION_CENTERS):
                return False
            if not click_box_center(context, SHOPPING_GIFT_OPTION_CENTERS[index - 1]):
                return False
            time.sleep(0.2)

            delta = target_count - current_count
            button_box = plus_box if delta > 0 else minus_box
            for _ in range(abs(delta)):
                if not click_box_center(context, button_box):
                    return False
                time.sleep(0.2)

            if not click_box_center(context, send_box):
                return False
            time.sleep(0.2)

            current_count = target_count
            send_focus_message(context, f"已赠送第 {index} 个文字，数量 {target_count}")

        return True
