import json

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context

from common import get_latest_detail, parse_digits, send_focus_message
from constants import SHOPPING_PRICE_OFFSET, SHOPPING_SLOT_ROIS, SHOPPING_TOTAL


def _locate_in_selected_slot(context: Context, image, reco_name: str) -> CustomRecognition.AnalyzeResult:
    selected_detail = get_latest_detail(context, "FindShoppingFestivalTarget")
    if not selected_detail:
        return None

    reco_detail = context.run_recognition(
        reco_name, image, {reco_name: {"roi": selected_detail["slot_roi"]}}
    )
    if not reco_detail or not reco_detail.hit:
        return None

    return CustomRecognition.AnalyzeResult(box=reco_detail.box, detail=selected_detail)


@AgentServer.custom_recognition("FindShoppingFestivalTarget")
class FindShoppingFestivalTarget(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        for index, slot_roi in enumerate(SHOPPING_SLOT_ROIS, start=1):
            price_roi = [
                slot_roi[0] + SHOPPING_PRICE_OFFSET[0],
                slot_roi[1] + SHOPPING_PRICE_OFFSET[1],
                SHOPPING_PRICE_OFFSET[2],
                SHOPPING_PRICE_OFFSET[3],
            ]

            price_ocr = context.run_recognition(
                "ShoppingFestivalPriceOCR",
                argv.image,
                {"ShoppingFestivalPriceOCR": {"roi": price_roi}},
            )
            if not price_ocr or not price_ocr.hit:
                continue

            digits = parse_digits(price_ocr.best_result.text)
            price = int(digits) if digits else 0

            if price > 0 and SHOPPING_TOTAL % price == 0:
                quantity = SHOPPING_TOTAL // price
                send_focus_message(
                    context,
                    f"购物节选中槽位 {index}，单价 {price}，购买数量 {quantity}",
                )
                return CustomRecognition.AnalyzeResult(
                    box=tuple(slot_roi),
                    detail={
                        "slot_index": index,
                        "slot_roi": slot_roi,
                        "price_roi": price_roi,
                        "price": price,
                        "quantity": quantity,
                    },
                )

        return None


@AgentServer.custom_recognition("LocateShoppingFestivalText")
class LocateShoppingFestivalText(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        return _locate_in_selected_slot(context, argv.image, "ShoppingFestivalTextTemplate")


@AgentServer.custom_recognition("LocateShoppingFestivalPurchase")
class LocateShoppingFestivalPurchase(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        return _locate_in_selected_slot(context, argv.image, "ShoppingFestivalPurchaseTemplate")


@AgentServer.custom_recognition("GenerateShoppingFriendName")
class GenerateShoppingFriendName(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        friend_name = json.loads(argv.custom_recognition_param)
        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"friend_name": friend_name},
        )
