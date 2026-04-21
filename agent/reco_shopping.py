from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context

from common import get_latest_detail, parse_digits, run_recognition, send_focus_message, strip_quotes
from constants import SHOPPING_PRICE_OFFSET, SHOPPING_SLOT_ROIS, SHOPPING_TOTAL


def _get_selected_shopping_detail(context: Context):
    return get_latest_detail(context, "FindShoppingFestivalTarget")


def _locate_in_selected_slot(context: Context, image, reco_name: str) -> CustomRecognition.AnalyzeResult:
    selected_detail = _get_selected_shopping_detail(context)
    if not selected_detail:
        return CustomRecognition.AnalyzeResult(box=None, detail={})

    slot_roi = selected_detail.get("slot_roi")
    reco_detail = run_recognition(
        context,
        reco_name,
        image,
        {reco_name: {"roi": slot_roi}},
    )

    return CustomRecognition.AnalyzeResult(
        box=reco_detail.best_result.box if reco_detail and reco_detail.hit else None,
        detail=selected_detail,
    )


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

            reco_detail = run_recognition(
                context,
                "ShoppingFestivalPriceOCR",
                argv.image,
                {"ShoppingFestivalPriceOCR": {"roi": price_roi}},
            )

            price_text = ""
            if reco_detail and reco_detail.hit and reco_detail.best_result:
                price_text = reco_detail.best_result.text or ""

            digits = parse_digits(price_text)
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

        return CustomRecognition.AnalyzeResult(
            box=None,
            detail={"error": "No valid shopping slot found"},
        )


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
        friend_name = strip_quotes(argv.custom_recognition_param)
        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"friend_name": friend_name},
        )
