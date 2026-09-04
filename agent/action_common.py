from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from common import click_box_center, send_focus_message


@AgentServer.custom_action("PreciseClick")
class PreciseClick(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        return click_box_center(context, argv.box)


@AgentServer.custom_action("ResetServerRuntime")
class ResetServerRuntime(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        context.tasker.clear_cache()
        return True
