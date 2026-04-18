from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
import time


def _click_box_center(context: Context, box) -> bool:
    if not box:
        return False

    center_x = box[0] + box[2] // 2
    center_y = box[1] + box[3] // 2
    controller = context.tasker.controller
    controller.post_click(center_x, center_y).wait()
    return True

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


@AgentServer.custom_action("ClickShoppingGiftOption")
class ClickShoppingGiftOption(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        node_detail = context.tasker.get_latest_node("GetNextShoppingFestivalGift")
        if not node_detail or not node_detail.recognition:
            return False

        option_center = node_detail.recognition.best_result.detail.get("gift_option_center")
        if not option_center:
            return False

        return _click_box_center(context, option_center)


@AgentServer.custom_action("AdjustAndSendShoppingGift")
class AdjustAndSendShoppingGift(CustomAction):

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        node_detail = context.tasker.get_latest_node("GetNextShoppingFestivalGift")
        if not node_detail or not node_detail.recognition:
            return False

        detail = node_detail.recognition.best_result.detail
        target_count = detail.get("target_count")
        gift_index = detail.get("gift_index")
        if target_count is None:
            return False

        controller = context.tasker.controller

        for _ in range(6):
            image = controller.post_screencap().wait().get()
            current_reco = context.run_recognition("ShoppingFestivalCurrentSendCountOCR", image)
            if not current_reco or not current_reco.hit or not current_reco.best_result:
                return False

            digits = "".join(ch for ch in (current_reco.best_result.text or "") if ch.isdigit())
            if not digits:
                return False

            current_count = int(digits)
            if current_count == target_count:
                break

            reco_name = (
                "ShoppingFestivalMinusTemplate"
                if current_count > target_count
                else "ShoppingFestivalPlusTemplate"
            )
            button_reco = context.run_recognition(reco_name, image)
            if not button_reco or not button_reco.hit or not button_reco.best_result:
                return False

            if not _click_box_center(context, button_reco.best_result.box):
                return False
            time.sleep(0.2)
        else:
            return False

        image = controller.post_screencap().wait().get()
        send_reco = context.run_recognition("ShoppingFestivalSendTemplate", image)
        if not send_reco or not send_reco.hit or not send_reco.best_result:
            return False

        if not _click_box_center(context, send_reco.best_result.box):
            return False

        context.run_action(
            "LoginMsg",
            pipeline_override={
                "LoginMsg": {
                    "focus": {
                        "Node.Action.Succeeded": f"已赠送第 {gift_index} 个文字，数量 {target_count}",
                    }
                }
            }
        )
        return True
