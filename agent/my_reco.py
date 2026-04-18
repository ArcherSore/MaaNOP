from typing import List
from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context
import json

SHOPPING_TOTAL = 1500
SHOPPING_SLOT_ROIS = [
    [548, 309, 176, 95],
    [741, 310, 174, 92],
    [548, 408, 174, 94],
    [741, 408, 174, 93],
]
SHOPPING_PRICE_OFFSET = [148, 44, 20, 15]
SHOPPING_GIFT_COUNT_ROIS = [
    [573, 515, 13, 17],
    [639, 515, 13, 15],
    [703, 515, 16, 16],
    [768, 516, 14, 15],
    [835, 515, 13, 16],
    [900, 516, 12, 14],
]
SHOPPING_GIFT_OPTION_CENTERS = [
    [654, 564, 14, 13],
    [654, 581, 13, 12],
    [654, 598, 14, 12],
    [654, 615, 13, 12],
    [654, 631, 13, 12],
    [655, 648, 12, 12],
]

# 服务器ID到ROI的映射表
SERVER_ROI_MAP = {
    1013: [491, 432, 207, 116],
    1012: [600, 432, 206, 117],
    1011: [708, 433, 206, 115],
    1010: [385, 451, 206, 118],
    1009: [492, 452, 206, 115],
    1008: [600, 452, 206, 116],
    1007: [708, 451, 206, 117],
    1006: [385, 470, 204, 116],
    1005: [491, 470, 209, 116],
    1004: [600, 470, 205, 117],
    1003: [708, 470, 207, 117],
    1002: [385, 488, 205, 117],
    1001: [503, 489, 147, 115],
    1000: [610, 488, 146, 117],
    999: [383, 271, 205, 116],
    998: [491, 272, 207, 118],
    997: [601, 271, 205, 118],
    996: [708, 272, 207, 116],
    995: [384, 290, 207, 118],
    994: [491, 290, 209, 118],
    993: [601, 290, 204, 115],
    992: [709, 291, 205, 115],
    991: [385, 310, 203, 116],
    990: [493, 309, 205, 116],
    989: [601, 310, 203, 115],
    988: [708, 309, 207, 117],
    987: [384, 328, 206, 117],
    986: [493, 328, 206, 116],
    985: [600, 328, 206, 116],
    984: [708, 329, 207, 116],
    983: [385, 347, 206, 115],
    982: [492, 346, 208, 117],
    981: [602, 346, 206, 117],
    980: [708, 345, 205, 118],
    979: [384, 366, 207, 117],
    978: [492, 365, 207, 117],
    977: [610, 365, 143, 115],
    976: [719, 365, 141, 115]
}

"""
For server detection
"""

@AgentServer.custom_recognition("ParseServerRange")
class ParseServerRange(CustomRecognition):
    """
    解析服务器范围字符串
    输入: "978-1012,1015-1020"
    输出: [978, 979, ..., 1012, 1015, ..., 1020]
    """
    def analyze(
        self, 
        context: Context, 
        argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        server_range_str = argv.custom_recognition_param
        server_range_str = server_range_str.strip('"')
        
        server_list = []
        for range_part in server_range_str.split(','):
            range_part = range_part.strip()
            if '-' in range_part:
                start, end = map(int, range_part.split('-'))
                server_list.extend(range(start, end + 1))
            else:
                server_list.append(int(range_part))

        # print(f"服务器列表：{server_list}")
        
        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 100, 100),
            detail={
                "server_list": server_list,
            }
        )

@AgentServer.custom_recognition("GetNextServer")
class GetNextServer(CustomRecognition):
    """
    获取下一个要处理的服务器
    返回服务器 ID 或标记已完成
    
    首次调用：从 ParseServerRange 获取服务器列表
    后续调用：从自己上一次的结果中获取服务器列表和索引
    """
    
    def analyze(
        self, 
        context: Context, 
        argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        # 尝试获取自己上一次的结果
        prev_node = context.tasker.get_latest_node("GetNextServer")
        
        if not prev_node or not prev_node.recognition:
            # 首次调用：从 ParseServer 获取服务器列表
            parse_node = context.tasker.get_latest_node("ParseServer")
            if not parse_node or not parse_node.recognition:
                return CustomRecognition.AnalyzeResult(
                    box=None,
                    detail={"error": "ParseServer not found"}
                )
            
            server_list = parse_node.recognition.best_result.detail.get("server_list", [])
            current_server_index = 0
            # print(f"首次获取服务器列表：{server_list}")
        else:
            # 后续调用：从自己上一次的结果中获取
            prev_detail = prev_node.recognition.best_result.detail
            server_list = prev_detail.get("server_list", [])
            current_server_index = prev_detail.get("server_index", 0)
        
        if current_server_index >= len(server_list):
            # todo add focus with pipelineoverride
            # print("所有服务器已处理完成")
            return CustomRecognition.AnalyzeResult(
                box=(0, 0, 0, 0),
                detail={
                    "server_list": server_list,
                    "server_index": current_server_index,
                    "server_cnt": len(server_list),
                    "finished": True
                }
            )
        
        # 获取当前服务器并递增索引
        current_server = server_list[current_server_index]
        next_server_index = current_server_index + 1
        
        context.run_action(
            "LoginMsg",
            pipeline_override={
                "LoginMsg": {
                    "focus": {
                        "Node.Action.Succeeded": f"准备处理服务器 {current_server} ({next_server_index}/{len(server_list)})",
                    }
                }
            }    
        )
        
        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={
                "server_list": server_list,
                "server_id": current_server,
                "server_index": next_server_index,
                "server_cnt": len(server_list),
                "finished": False
            }
        )


@AgentServer.custom_recognition("DetectServerPage")
class DetectServerPage(CustomRecognition):
    """
    根据服务器ID
    返回"1000+"或"1-999"页面的box区域
    """

    ROI_1000_PLUS = [379, 247, 163, 117]
    ROI_1_999 = [442, 249, 161, 115]
    
    def analyze(
        self, 
        context: Context, 
        argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        # 获取target_server
        node_detail = context.tasker.get_latest_node("GetNextServer")
        if not node_detail or not node_detail.recognition:
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail={}
            )
        target_server_id = node_detail.recognition.best_result.detail.get("server_id")
        if target_server_id is None:
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail={}
            )

        roi = [403, 216, 236, 131]
        expected = ".*1000.*" if target_server_id >= 1000 else ".*1-999.*"
        
        reco_detail = context.run_recognition(
            "ChooseServerType",
            argv.image,
            { "ChooseServerType": { "roi": roi, "expected": [expected] } }
        )
        
        return CustomRecognition.AnalyzeResult(
            box=reco_detail.best_result.box if reco_detail and reco_detail.hit else None,
            detail={
                "server_id": target_server_id,
                "roi_used": roi,
                "ocr_result": reco_detail.best_result.text if reco_detail and reco_detail.hit else None,
                "hit": reco_detail.hit if reco_detail else False
            }
        )


@AgentServer.custom_recognition("LocateServerButton")
class LocateServerButton(CustomRecognition):
    """
    根据服务器ID和ROI映射表定位服务器按钮
    返回box区域
    """
    
    def analyze(
        self, 
        context: Context, 
        argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        # 获取targer_server
        node_detail = context.tasker.get_latest_node("GetNextServer")
        if not node_detail or not node_detail.recognition:
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail={}
            )
        target_server_id = node_detail.recognition.best_result.detail.get("server_id")
        if target_server_id is None:
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail={}
            )
        
        roi = SERVER_ROI_MAP[target_server_id]

        reco_detail = context.run_recognition(
            "ChooseServerButton",
            argv.image,
            { "ChooseServerButton": { "roi": roi, "expected": f".*{target_server_id}.*" } }
        )

        return CustomRecognition.AnalyzeResult(
            box=reco_detail.best_result.box if reco_detail and reco_detail.hit else None,
            detail={
                "server_id": target_server_id,
                "roi_used": roi,
                "ocr_result": reco_detail.best_result.text if reco_detail and reco_detail.hit else None,
                "hit": reco_detail.hit if reco_detail else False
            }
        )
    
@AgentServer.custom_recognition("AllCompleted")
class AllCompleted(CustomRecognition):
    """
    根据服务器ID和ROI映射表定位服务器按钮
    返回box区域
    """
    
    def analyze(
        self, 
        context: Context, 
        argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        # 获取 finished 状态
        node_detail = context.tasker.get_latest_node("GetNextServer")
        if not node_detail or not node_detail.recognition:
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail={}
            )
        finished = node_detail.recognition.best_result.detail.get("finished")

        if not finished:  
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail={}
            )  
        else:  
            return CustomRecognition.AnalyzeResult(
                box=(0, 0, 0, 0),
                detail={"finished": True}
            )
        
"""
For Creating Account 
"""

@AgentServer.custom_recognition("GenerateAccountName")
class GenerateAccountName(CustomRecognition):
    """
    拼接游戏名称 prefix_serverID
    返回游戏名称
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg
    )  -> CustomRecognition.AnalyzeResult:
        # 获取当前 server_id
        node_detail = context.tasker.get_latest_node("GetNextServer")
        if not node_detail or not node_detail.recognition:
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail={}
            )
        server_id = node_detail.recognition.best_result.detail.get("server_id")
        if server_id is None:
            return CustomRecognition.AnalyzeResult(
                box=None,
                detail={}
            )
        
        prefix = argv.custom_recognition_param
        prefix = prefix.strip('"')

        account_name = f"{prefix}_{server_id}"

        run_detail = context.run_action(
            "LoginMsg",
            pipeline_override={
                "LoginMsg": {
                    "focus": {
                        "Node.Action.Succeeded": f"生成账号名称: {account_name}",
                    }
                }
            }    
        )

        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"AccountName": account_name}
        )


def _send_focus_message(context: Context, message: str) -> None:
    context.run_action(
        "LoginMsg",
        pipeline_override={
            "LoginMsg": {
                "focus": {
                    "Node.Action.Succeeded": message,
                }
            }
        }
    )


def _get_selected_shopping_detail(context: Context):
    node_detail = context.tasker.get_latest_node("FindShoppingFestivalTarget")
    if not node_detail or not node_detail.recognition:
        return None
    return node_detail.recognition.best_result.detail


def _get_latest_shopping_gift_detail(context: Context):
    node_detail = context.tasker.get_latest_node("GetNextShoppingFestivalGift")
    if not node_detail or not node_detail.recognition:
        return None
    return node_detail.recognition.best_result.detail


def _get_task_mode(context: Context):
    shopping_node = context.tasker.get_latest_node("SetShoppingFestivalTaskMode")
    if shopping_node and shopping_node.recognition:
        return shopping_node.recognition.best_result.detail.get("task_mode")

    training_node = context.tasker.get_latest_node("SetTrainingTaskMode")
    if training_node and training_node.recognition:
        return training_node.recognition.best_result.detail.get("task_mode")

    return None


@AgentServer.custom_recognition("FindShoppingFestivalTarget")
class FindShoppingFestivalTarget(CustomRecognition):
    """
    依次扫描四个商品格，找到价格为 1500 因数的目标格子
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        for index, slot_roi in enumerate(SHOPPING_SLOT_ROIS, start=1):
            price_roi = [
                slot_roi[0] + SHOPPING_PRICE_OFFSET[0],
                slot_roi[1] + SHOPPING_PRICE_OFFSET[1],
                SHOPPING_PRICE_OFFSET[2],
                SHOPPING_PRICE_OFFSET[3],
            ]

            reco_detail = context.run_recognition(
                "ShoppingFestivalPriceOCR",
                argv.image,
                {
                    "ShoppingFestivalPriceOCR": {
                        "roi": price_roi,
                    }
                }
            )

            price_text = ""
            if reco_detail and reco_detail.hit and reco_detail.best_result:
                price_text = reco_detail.best_result.text or ""

            digits = "".join(ch for ch in price_text if ch.isdigit())
            price = int(digits) if digits else 0
            _send_focus_message(
                context,
                f"购物节槽位 {index} 识别数值: {price if price else '无效'}"
            )

            if price > 0 and SHOPPING_TOTAL % price == 0:
                quantity = SHOPPING_TOTAL // price
                _send_focus_message(
                    context,
                    f"购物节选中槽位 {index}，单价 {price}，购买数量 {quantity}"
                )
                return CustomRecognition.AnalyzeResult(
                    box=tuple(slot_roi),
                    detail={
                        "slot_index": index,
                        "slot_roi": slot_roi,
                        "price_roi": price_roi,
                        "price": price,
                        "quantity": quantity,
                    }
                )

        return CustomRecognition.AnalyzeResult(
            box=None,
            detail={"error": "No valid shopping slot found"}
        )


@AgentServer.custom_recognition("LocateShoppingFestivalText")
class LocateShoppingFestivalText(CustomRecognition):
    """
    在选中的商品格内定位文字输入框
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        selected_detail = _get_selected_shopping_detail(context)
        if not selected_detail:
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        slot_roi = selected_detail.get("slot_roi")
        reco_detail = context.run_recognition(
            "ShoppingFestivalTextTemplate",
            argv.image,
            {
                "ShoppingFestivalTextTemplate": {
                    "roi": slot_roi,
                }
            }
        )

        return CustomRecognition.AnalyzeResult(
            box=reco_detail.best_result.box if reco_detail and reco_detail.hit else None,
            detail=selected_detail,
        )


@AgentServer.custom_recognition("LocateShoppingFestivalPurchase")
class LocateShoppingFestivalPurchase(CustomRecognition):
    """
    在选中的商品格内定位购买按钮
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        selected_detail = _get_selected_shopping_detail(context)
        if not selected_detail:
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        slot_roi = selected_detail.get("slot_roi")
        reco_detail = context.run_recognition(
            "ShoppingFestivalPurchaseTemplate",
            argv.image,
            {
                "ShoppingFestivalPurchaseTemplate": {
                    "roi": slot_roi,
                }
            }
        )

        return CustomRecognition.AnalyzeResult(
            box=reco_detail.best_result.box if reco_detail and reco_detail.hit else None,
            detail=selected_detail,
        )


@AgentServer.custom_recognition("GenerateShoppingFriendName")
class GenerateShoppingFriendName(CustomRecognition):
    """
    读取交互界面输入的购物节好友名称
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        friend_name = (argv.custom_recognition_param or "").strip('"')
        _send_focus_message(context, f"购物节好友名称: {friend_name}")
        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"friend_name": friend_name}
        )


@AgentServer.custom_recognition("SetTaskMode")
class SetTaskMode(CustomRecognition):
    """
    标记当前运行的任务模式
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        task_mode = (argv.custom_recognition_param or "").strip('"')
        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"task_mode": task_mode}
        )


@AgentServer.custom_recognition("IsTrainingTask")
class IsTrainingTask(CustomRecognition):
    """
    判断当前是否为练小号任务
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        if _get_task_mode(context) != "training":
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"task_mode": "training"}
        )


@AgentServer.custom_recognition("IsShoppingFestivalTask")
class IsShoppingFestivalTask(CustomRecognition):
    """
    判断当前是否为购物节送字任务
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        if _get_task_mode(context) != "shopping":
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"task_mode": "shopping"}
        )


@AgentServer.custom_recognition("GetNextShoppingFestivalGift")
class GetNextShoppingFestivalGift(CustomRecognition):
    """
    扫描六个文字数量，并逐个返回需要赠送的目标
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        prev_detail = _get_latest_shopping_gift_detail(context)
        if not prev_detail:
            gift_targets = []
            for index, gift_roi in enumerate(SHOPPING_GIFT_COUNT_ROIS, start=1):
                reco_detail = context.run_recognition(
                    "ShoppingFestivalGiftCountOCR",
                    argv.image,
                    {
                        "ShoppingFestivalGiftCountOCR": {
                            "roi": gift_roi,
                        }
                    }
                )

                gift_text = ""
                if reco_detail and reco_detail.hit and reco_detail.best_result:
                    gift_text = reco_detail.best_result.text or ""

                digits = "".join(ch for ch in gift_text if ch.isdigit())
                gift_count = int(digits) if digits in {"1", "2", "3"} else 0
                _send_focus_message(
                    context,
                    f"购物节第 {index} 个文字需赠送: {gift_count}"
                )

                if gift_count > 0:
                    gift_targets.append(
                        {
                            "gift_index": index,
                            "target_count": gift_count,
                            "gift_count_roi": gift_roi,
                            "gift_option_center": SHOPPING_GIFT_OPTION_CENTERS[index - 1],
                        }
                    )
            current_target_index = 0
        else:
            gift_targets = prev_detail.get("gift_targets", [])
            current_target_index = prev_detail.get("target_index", 0)

        if current_target_index >= len(gift_targets):
            return CustomRecognition.AnalyzeResult(
                box=(0, 0, 0, 0),
                detail={
                    "gift_targets": gift_targets,
                    "target_index": current_target_index,
                    "finished": True,
                }
            )

        current_target = gift_targets[current_target_index]
        next_target_index = current_target_index + 1
        _send_focus_message(
            context,
            f"准备赠送第 {current_target['gift_index']} 个文字，数量 {current_target['target_count']}"
        )
        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={
                "gift_targets": gift_targets,
                "target_index": next_target_index,
                "finished": False,
                **current_target,
            }
        )


@AgentServer.custom_recognition("AllShoppingFestivalGiftsCompleted")
class AllShoppingFestivalGiftsCompleted(CustomRecognition):
    """
    判断购物节所有文字是否已处理完成
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        latest_detail = _get_latest_shopping_gift_detail(context)
        if not latest_detail or not latest_detail.get("finished"):
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"finished": True}
        )
