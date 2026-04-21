from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from common import get_detail_value


@AgentServer.custom_action("PasteAccountName")
class PasteAccountName(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        account_name = get_detail_value(context, "GetAccountPrefix", "AccountName")
        if account_name is None:
            return False

        context.tasker.controller.post_input_text(account_name).wait()
        return True
