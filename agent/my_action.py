from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
import time

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
        print(f"Scrolling to server ID: {target_server_id}")

        if target_server_id >= 1000:
            controller = context.tasker.controller
            # 识别倒三角
            image = controller.post_screencap().wait().get()  
            reco_detail = context.run_recognition(
                "FindDownArrow",
                image,
                pipeline_override={
                    "FindDownArrow": {  
                        "recognition": {  
                            "type": "TemplateMatch",  
                            "param": {  
                                "roi" : [867,475,98,107], 
                                "template": "down_arrow.png",  
                                "threshold": 0.8  
                            }  
                        }  
                    }  
                }
            )

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
            reco_anno = context.run_recognition(
                "CheckAnnouncement",
                image,
                pipeline_override={
                    "CheckAnnouncement": {
                        "recognition": {
                            "type": "TemplateMatch",
                            "param": {
                                "template": [ "popup/closeanno.png" ],
                                "roi" : [ 901, 297, 119, 117 ]
                            }
                        }
                    }
                }
            )
            if reco_anno and reco_anno.hit and reco_anno.best_result:
                flag = True
                print("检测到更新公告，尝试关闭")
                box = reco_anno.best_result.box
                x, y = box[0] + box[2] // 2, box[1] + box[3] // 2
                controller.post_click(x, y).wait()
            
            # step2 检测【福利大厅】
            reco_welf = context.run_recognition(
                "CheckWelfare",
                image,
                pipeline_override={
                    "CheckWelfare": {
                        "recognition": {
                            "type": "TemplateMatch",
                            "param": {
                                "template": [ "popup/welfare.png"],
                                "roi": [ 806, 192, 145, 140 ]
                            }
                        }
                    }
                }
            )
            if reco_welf and reco_welf.hit and reco_welf.best_result:
                flag = True
                print("检测到福利大厅，尝试关闭")
                controller.post_click(680, 400).wait()
                time.sleep(0.2)
                controller.post_click_key(27).wait()

            # step3 检测【回归好礼】
            reco_retn = context.run_recognition(
                "CheckReturnGift",
                image,
                pipeline_override={
                    "CheckReturnGift": {
                        "recognition": {
                            "type": "TemplateMatch",
                            "param": {
                                "template": "popup/return.png",
                                "roi": [ 671, 182, 260, 136 ]
                            }
                        }
                    }
                }
            )
            if reco_retn and reco_retn.hit and reco_retn.best_result:
                flag = True
                print("检测到回归好礼，尝试关闭")
                controller.post_click(680, 400).wait()
                time.sleep(0.2)
                controller.post_click_key(27).wait()

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

        print(box)
          
        if box:  
            center_x = box[0] + box[2] // 2  
            center_y = box[1] + box[3] // 2  
              
            controller = context.tasker.controller  
            controller.post_click(center_x, center_y).wait()  
              
            return True  
        else:  
            return False
        
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
        reco = context.run_recognition(
            "CheckRemainPopup",
            image,
            pipeline_override={
                "CheckRemainPopup": {
                    "recognition": {
                        "type": "TemplateMatch",
                        "param": {
                            "template": [ "popup/return.png" ],
                            "roi": [ 671, 182, 260, 136 ],
                            "order_by": "Score"
                        }
                    }
                }
            }
        )
        if reco and reco.hit and reco.best_result:
            controller.post_click(680, 400).wait()
            time.sleep(0.2)
            controller.post_click_key(27).wait()
        return True

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