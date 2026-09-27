import time

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from maa.pipeline import JActionType, JClickKey

from common import click_center


@AgentServer.custom_action("PreciseClick")
class PreciseClick(CustomAction):
    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        return click_center(context, argv.box)


ESC_KEY = 27
# A blank spot in the middle of the game window; clicking it gives the window key focus.
FOCUS_BOX = (680, 400, 1, 1)


def _focus_and_escape(context: Context) -> None:
    click_center(context, FOCUS_BOX)
    time.sleep(0.2)
    context.run_action_direct(JActionType.ClickKey, JClickKey(key=[ESC_KEY]))


@AgentServer.custom_action("CloseAllPopupsWithEsc")
class CloseAllPopupsWithEsc(CustomAction):
    """Press ESC repeatedly to close every stacked popup, then clear a return-gift popup left behind."""

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        for _ in range(5):
            context.run_action_direct(JActionType.ClickKey, JClickKey(key=[ESC_KEY]))
            time.sleep(0.2)

        image = context.tasker.controller.post_screencap().wait().get()
        remain_popup = context.run_recognition("CheckRemainPopup", image)
        if remain_popup and remain_popup.hit:
            _focus_and_escape(context)

        return True
