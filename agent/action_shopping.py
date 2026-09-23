from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from common import (
    capture_image,
    click_box_center,
    get_detail_value,
    get_recognition_box,
    get_recognition_text,
    input_text,
    parse_digits,
    send_focus_message,
    wait_or_stop,
)
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

        return input_text(context, str(quantity))


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

        return input_text(context, friend_name)


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
        if context.tasker.stopping:
            return False
        image = capture_image(context)

        select_box = get_recognition_box(context, image, "ShoppingFestivalGiftSelectTemplate")
        minus_box = get_recognition_box(context, image, "ShoppingFestivalMinusTemplate")
        plus_box = get_recognition_box(context, image, "ShoppingFestivalPlusTemplate")
        send_box = get_recognition_box(context, image, "ShoppingFestivalSendTemplate")
        if not select_box or not minus_box or not plus_box or not send_box:
            return False

        gift_targets = []
        for index, gift_roi in enumerate(SHOPPING_GIFT_COUNT_ROIS, start=1):
            if context.tasker.stopping:
                return False
            gift_text = get_recognition_text(
                context,
                image,
                "ShoppingFestivalGiftCountOCR",
                {"ShoppingFestivalGiftCountOCR": {"roi": gift_roi}},
            )

            digits = parse_digits(gift_text)
            target_count = int(digits) if digits in {"1", "2", "3"} else 0

            if target_count > 0:
                gift_targets.append((index, target_count))

        if context.tasker.stopping:
            return False
        if not gift_targets:
            send_focus_message(context, "购物节未识别到任何需要送字的数量")
            return not context.tasker.stopping

        gift_chars = ("木", "叶", "购", "物", "狂", "欢")
        current_count = 1
        for index, target_count in gift_targets:
            if context.tasker.stopping:
                return False
            if not click_box_center(context, select_box):
                return False
            if not wait_or_stop(context, 0.2):
                return False

            if index > len(SHOPPING_GIFT_OPTION_CENTERS):
                return False
            if not click_box_center(context, SHOPPING_GIFT_OPTION_CENTERS[index - 1]):
                return False
            if not wait_or_stop(context, 0.2):
                return False

            delta = target_count - current_count
            button_box = plus_box if delta > 0 else minus_box
            for _ in range(abs(delta)):
                if not click_box_center(context, button_box):
                    return False
                if not wait_or_stop(context, 0.2):
                    return False

            if not click_box_center(context, send_box):
                return False
            if not wait_or_stop(context, 0.2):
                return False

            current_count = target_count
            gift_char = gift_chars[index - 1]
            send_focus_message(context, f"已赠送 {gift_char} 字，数量 {target_count}")

        return not context.tasker.stopping
