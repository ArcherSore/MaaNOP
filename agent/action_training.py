from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from maa.pipeline import JActionType, JInputText

from common import get_latest_detail


@AgentServer.custom_action("PasteAccountName")
class PasteAccountName(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        detail = get_latest_detail(context, "GetAccountPrefix")
        if not detail:
            return False

        action = context.run_action_direct(
            JActionType.InputText, JInputText(input_text=detail["AccountName"])
        )
        return bool(action and action.success)
