import time

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from maa.pipeline import JActionType, JInputText

from common import click_center, get_latest_detail, parse_digits, send_focus_message
from constants import SHOPPING_GIFT_COUNT_ROIS, SHOPPING_GIFT_OPTION_CENTERS


@AgentServer.custom_action("PasteShoppingQuantity")
class PasteShoppingQuantity(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        target = get_latest_detail(context, "FindShoppingFestivalTarget")
        if not target:
            return False

        action = context.run_action_direct(
            JActionType.InputText, JInputText(input_text=str(target["quantity"]))
        )
        return bool(action and action.success)


@AgentServer.custom_action("ClickShoppingFriendInput")
class ClickShoppingFriendInput(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        return click_center(context, [535, 541, 67, 15])


@AgentServer.custom_action("PasteShoppingFriendName")
class PasteShoppingFriendName(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        friend = get_latest_detail(context, "GetShoppingFriendName")
        if not friend or not friend.get("friend_name"):
            return False

        action = context.run_action_direct(
            JActionType.InputText, JInputText(input_text=friend["friend_name"])
        )
        return bool(action and action.success)


@AgentServer.custom_action("ClickShoppingFriendOption")
class ClickShoppingFriendOption(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        return click_center(context, [517, 558, 108, 15])


@AgentServer.custom_action("FocusShoppingFestivalBeforeExit")
class FocusShoppingFestivalBeforeExit(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        return click_center(context, [680, 400, 1, 1])


@AgentServer.custom_action("ProcessShoppingFestivalGifts")
class ProcessShoppingFestivalGifts(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        image = context.tasker.controller.post_screencap().wait().get()

        buttons = []
        for reco_name in [
            "ShoppingFestivalGiftSelectTemplate",
            "ShoppingFestivalMinusTemplate",
            "ShoppingFestivalPlusTemplate",
            "ShoppingFestivalSendTemplate",
        ]:
            button = context.run_recognition(reco_name, image)
            if not button or not button.hit:
                return False
            buttons.append(button.box)
        select_box, minus_box, plus_box, send_box = buttons

        gift_targets = []
        for index, gift_roi in enumerate(SHOPPING_GIFT_COUNT_ROIS, start=1):
            gift_ocr = context.run_recognition(
                "ShoppingFestivalGiftCountOCR",
                image,
                {"ShoppingFestivalGiftCountOCR": {"roi": gift_roi}},
            )
            if not gift_ocr or not gift_ocr.hit:
                continue

            digits = parse_digits(gift_ocr.best_result.text)
            target_count = int(digits) if digits in {"1", "2", "3"} else 0

            if target_count > 0:
                gift_targets.append((index, target_count))

        if not gift_targets:
            send_focus_message(context, "购物节未识别到任何需要送字的数量")
            return True

        gift_chars = ("木", "叶", "购", "物", "狂", "欢")
        current_count = 1
        for index, target_count in gift_targets:
            if not click_center(context, select_box):
                return False
            time.sleep(0.2)

            if index > len(SHOPPING_GIFT_OPTION_CENTERS):
                return False
            if not click_center(context, SHOPPING_GIFT_OPTION_CENTERS[index - 1]):
                return False
            time.sleep(0.2)

            delta = target_count - current_count
            button_box = plus_box if delta > 0 else minus_box
            for _ in range(abs(delta)):
                if not click_center(context, button_box):
                    return False
                time.sleep(0.2)

            if not click_center(context, send_box):
                return False
            time.sleep(0.2)

            current_count = target_count
            gift_char = gift_chars[index - 1]
            send_focus_message(context, f"已赠送 {gift_char} 字，数量 {target_count}")

        return True
