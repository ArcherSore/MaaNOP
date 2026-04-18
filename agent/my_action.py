from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
import time

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


def _click_box_center(context: Context, box) -> bool:
    if not box:
        return False

    center_x = box[0] + box[2] // 2
    center_y = box[1] + box[3] // 2
    controller = context.tasker.controller
    controller.post_click(center_x, center_y).wait()
    return True


def _run_login_message(context: Context, message: str) -> None:
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


def _recognize_box(context: Context, image, reco_name: str):
    reco_detail = context.run_recognition(reco_name, image)
    if not reco_detail or not reco_detail.hit or not reco_detail.best_result:
        return None
    return reco_detail.best_result.box

@AgentServer.custom_action("ScrollToTargetServer")
class ScrollToTargetServer(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        # 获取targer_server
        node_detail = context.tasker.get_latest_node("GetNextServer")
        if not node_detail or not node_detail.recognition:
            return False
        target_server_id = node_detail.recognition.best_result.detail.get("server_id")
        if target_server_id is None:
            return False
        # print(f"Scrolling to server ID: {target_server_id}")

        if target_server_id >= 1000:
            controller = context.tasker.controller
            # 识别倒三角
            image = controller.post_screencap().wait().get()  
            reco_detail = context.run_recognition("FindDownArrow", image)

            if reco_detail and reco_detail.hit and reco_detail.best_result:
                box = reco_detail.best_result.box
                x, y = box[0] + box[2] // 2, box[1] + box[3] // 2
                
                controller.post_click(x, y).wait
                time.sleep(0.2)
                controller.post_click(x, y).wait
            else:
                print("未识别到 down_arrow.png")
                return False
        return True
    
@AgentServer.custom_action("HandleLoginPopups")
class HandleLoginPopups(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        
        # 保证登录弹窗已出现
        while True:
            flag = False
            controller = context.tasker.controller

            image = controller.post_screencap().wait().get()
            # step1 检测【更新公告】
            reco_anno = context.run_recognition("CheckAnnouncement", image)
            if reco_anno and reco_anno.hit and reco_anno.best_result:
                flag = True
                print("检测到更新公告，尝试关闭")
                box = reco_anno.best_result.box
                x, y = box[0] + box[2] // 2, box[1] + box[3] // 2
                time.sleep(0.2)
                controller.post_click(x, y).wait()
                time.sleep(0.2)
            
            # step2 检测【福利大厅】
            reco_welf = context.run_recognition("CheckWelfare", image)
            if reco_welf and reco_welf.hit and reco_welf.best_result:
                flag = True
                print("检测到福利大厅，尝试关闭")
                controller.post_click(680, 400).wait()
                time.sleep(0.2)
                controller.post_click_key(27).wait()
                time.sleep(0.2)

            # step3 检测【回归好礼】
            reco_retn = context.run_recognition("CheckReturnGift", image)
            if reco_retn and reco_retn.hit and reco_retn.best_result:
                flag = True
                print("检测到回归好礼，尝试关闭")
                controller.post_click(680, 400).wait()
                time.sleep(0.2)
                controller.post_click_key(27).wait()
                time.sleep(0.2)

            if not flag:
                print("弹窗已全部关闭")
                break
        
        return True
    
@AgentServer.custom_action("PreciseClick")
class PreciseClick(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        box = argv.box

        # print(box)
          
        if box:  
            center_x = box[0] + box[2] // 2  
            center_y = box[1] + box[3] // 2  
              
            controller = context.tasker.controller  
            controller.post_click(center_x, center_y).wait()  
              
            return True  
        else:  
            return False

"""
快速关闭登录弹窗
"""
@AgentServer.custom_action("fastESC")
class FastESC(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        
        controller = context.tasker.controller
        for i in range(5):
            controller.post_click_key(27).wait()
            time.sleep(0.2)

        image = controller.post_screencap().wait().get()
        reco = context.run_recognition("CheckRemainPopup", image)
        if reco and reco.hit and reco.best_result:
            controller.post_click(680, 400).wait()
            time.sleep(0.2)
            controller.post_click_key(27).wait()
        return True

"""
账号注册时在文字框黏贴{prefix_serverid}的账号名称
"""
@AgentServer.custom_action("PasteAccountName")
class PasteAccountName(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        # 获取拼接后的账号名称
        node_detail = context.tasker.get_latest_node("GetAccountPrefix")
        if not node_detail or not node_detail.recognition:
            return False
        account_name = node_detail.recognition.best_result.detail.get("AccountName")
        if account_name is None:
            return False
        
        controller = context.tasker.controller  
        controller.post_input_text(account_name).wait()

        return True


@AgentServer.custom_action("PasteShoppingQuantity")
class PasteShoppingQuantity(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        node_detail = context.tasker.get_latest_node("FindShoppingFestivalTarget")
        if not node_detail or not node_detail.recognition:
            return False

        quantity = node_detail.recognition.best_result.detail.get("quantity")
        if quantity is None:
            return False

        controller = context.tasker.controller
        controller.post_input_text(str(quantity)).wait()
        return True


@AgentServer.custom_action("ClickShoppingFriendInput")
class ClickShoppingFriendInput(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        return _click_box_center(context, [535, 541, 67, 15])


@AgentServer.custom_action("PasteShoppingFriendName")
class PasteShoppingFriendName(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        node_detail = context.tasker.get_latest_node("GetShoppingFriendName")
        if not node_detail or not node_detail.recognition:
            return False

        friend_name = node_detail.recognition.best_result.detail.get("friend_name")
        if not friend_name:
            return False

        controller = context.tasker.controller
        controller.post_input_text(friend_name).wait()
        return True


@AgentServer.custom_action("ClickShoppingFriendOption")
class ClickShoppingFriendOption(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        return _click_box_center(context, [517, 558, 108, 15])


@AgentServer.custom_action("FocusShoppingFestivalBeforeExit")
class FocusShoppingFestivalBeforeExit(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        return _click_box_center(context, [680, 400, 1, 1])


@AgentServer.custom_action("ProcessShoppingFestivalGifts")
class ProcessShoppingFestivalGifts(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        controller = context.tasker.controller
        image = controller.post_screencap().wait().get()

        select_box = _recognize_box(context, image, "ShoppingFestivalGiftSelectTemplate")
        minus_box = _recognize_box(context, image, "ShoppingFestivalMinusTemplate")
        plus_box = _recognize_box(context, image, "ShoppingFestivalPlusTemplate")
        send_box = _recognize_box(context, image, "ShoppingFestivalSendTemplate")
        if not select_box or not minus_box or not plus_box or not send_box:
            return False

        gift_targets = []
        for index, gift_roi in enumerate(SHOPPING_GIFT_COUNT_ROIS, start=1):
            reco_detail = context.run_recognition(
                "ShoppingFestivalGiftCountOCR",
                image,
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
            target_count = int(digits) if digits in {"1", "2", "3"} else 0
            _run_login_message(context, f"购物节第 {index} 个字需要赠送 {target_count}")

            if target_count > 0:
                gift_targets.append((index, target_count))

        if not gift_targets:
            _run_login_message(context, "购物节未识别到需要赠送的文字数量")
            return True

        current_count = 1
        for index, target_count in gift_targets:
            if not _click_box_center(context, select_box):
                return False
            time.sleep(0.2)

            if not _click_box_center(context, SHOPPING_GIFT_OPTION_CENTERS[index - 1]):
                return False
            time.sleep(0.2)

            delta = target_count - current_count
            button_box = plus_box if delta > 0 else minus_box
            for _ in range(abs(delta)):
                if not _click_box_center(context, button_box):
                    return False
                time.sleep(0.2)

            if not _click_box_center(context, send_box):
                return False
            time.sleep(0.2)

            current_count = target_count
            _run_login_message(context, f"已赠送第 {index} 个文字，数量 {target_count}")

        return True
