import json

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context

from common import get_latest_detail, send_focus_message


@AgentServer.custom_recognition("GenerateAccountName")
class GenerateAccountName(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        server = get_latest_detail(context, "GetNextServer")
        if not server or "server_id" not in server:
            return None

        prefix = json.loads(argv.custom_recognition_param)
        account_name = f"{prefix}{server['server_id']}"
        send_focus_message(context, f"生成账号名称: {account_name}")

        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"AccountName": account_name},
        )
