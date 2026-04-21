from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition
from maa.context import Context

from common import get_detail_value, send_focus_message, strip_quotes


@AgentServer.custom_recognition("GenerateAccountName")
class GenerateAccountName(CustomRecognition):
    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        server_id = get_detail_value(context, "GetNextServer", "server_id")
        if server_id is None:
            return CustomRecognition.AnalyzeResult(box=None, detail={})

        prefix = strip_quotes(argv.custom_recognition_param)
        account_name = f"{prefix}_{server_id}"
        send_focus_message(context, f"生成账号名称: {account_name}")

        return CustomRecognition.AnalyzeResult(
            box=(0, 0, 0, 0),
            detail={"AccountName": account_name},
        )
