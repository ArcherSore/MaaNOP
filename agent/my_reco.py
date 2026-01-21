from typing import List
from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context
import json

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
    def __init__(self):
        super().__init__()
        self.server_list: List[int] = []
    
    def analyze(
        self, 
        context: Context, 
        argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        server_range_str = argv.custom_recognition_param
        server_range_str = server_range_str.strip('"')
        
        self.server_list = []
        for range_part in server_range_str.split(','):
            range_part = range_part.strip()
            if '-' in range_part:
                start, end = map(int, range_part.split('-'))
                self.server_list.extend(range(start, end + 1))
            else:
                self.server_list.append(int(range_part))

        print(f"服务器列表：{self.server_list}")
        
        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 100, 100),
            detail={
                "server_list": self.server_list,
            }
        )


@AgentServer.custom_recognition("GetNextServer")
class GetNextServer(CustomRecognition):
    """
    获取下一个要处理的服务器
    返回服务器 ID 或标记已完成
    """
    
    def analyze(
        self, 
        context: Context, 
        argv: CustomRecognition.AnalyzeArg
    ) -> CustomRecognition.AnalyzeResult:
        # 获取 server_list 和 current_server_index
        node_detail = context.tasker.get_latest_node("ParseServer")
        server_list = node_detail.recognition.best_result.detail.get("server_list")
        node_detail = context.tasker.get_latest_node("GetNextServer")
        if not node_detail:
            current_server_index = 0
        else :
            current_server_index = node_detail.recognition.best_result.detail.get("server_index")
        
        if current_server_index >= len(server_list):
            return CustomRecognition.AnalyzeResult(
                box=(0, 0, 0, 0),
                detail={
                    "finished": True
                }
            )
        
        current_server = server_list[current_server_index]
        current_server_index += 1
        
        print(f"准备处理服务器 {current_server}")
        
        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={
                "server_id": current_server,
                "server_index": current_server_index,
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

        roi = [403, 216, 236, 131]
        expected = ".*1000.*" if target_server_id >= 1000 else ".*1-999.*"
        
        reco_detail = context.run_recognition(
            "MyCheckPage",
            argv.image,
            pipeline_override={
                "MyCheckPage": {
                    "recognition": "OCR",
                    "roi": roi,
                    "expected": [expected]
                }
            }
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
            "MyServerButton",
            argv.image,
            pipeline_override={
                "MyServerButton": {
                    "recognition": "OCR",
                    "roi": roi,
                    "expected": f".*{target_server_id}.*"
                }
            }
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
    ) -> bool:
        # 获取当前 server_id
        node_detail = context.tasker.get_latest_node("GetNextServer")
        if not node_detail or not node_detail.recognition:
            return False
        server_id = node_detail.recognition.best_result.detail.get("server_id")
        if server_id is None:
            return False
        
        prefix = argv.custom_recognition_param
        prefix = prefix.strip('"')

        account_name = f"{prefix}_{server_id}"

        print(f"账号名称: {account_name}")

        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"AccountName": account_name}
        )