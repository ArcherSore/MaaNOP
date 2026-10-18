import json
import time

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from maa.pipeline import JActionType, JClickKey

from common import click_center


TEAM_TAB_Y = [235, 256, 276, 297, 317, 338, 358, 379]


@AgentServer.custom_action("SelectTeam")
class SelectTeam(CustomAction):
    """选中指定阵容并关闭忍者界面，编号从上到下为 1～8。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        team = int(json.loads(argv.custom_action_param))
        if not 1 <= team <= len(TEAM_TAB_Y):
            return False

        y = TEAM_TAB_Y[team - 1]
        roi = [358, y, 34, 12]
        selection = context.clone()
        result = selection.run_task(
            "SelectTeam",
            pipeline_override={
                "SelectTeamClose": {"recognition": {"param": {"roi": roi}}},
                "SelectTeamClick": {
                    "recognition": {"param": {"roi": roi}},
                    "action": {"param": {"target": [360, y + 1, 30, 11]}},
                },
            },
        )
        if context.tasker.stopping:
            return False
        nodes = result.nodes if result else []
        return bool(nodes and nodes[-1].name == "SelectTeamDone")


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


@AgentServer.custom_action("FalseAction")
class FalseAction(CustomAction):
    """Always fails. A terminal node for a recognized state that means the goal cannot be met; the failed action ends the task as Failed."""

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        return False
