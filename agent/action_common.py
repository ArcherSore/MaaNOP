import json
import time

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context
from maa.pipeline import JActionType, JClickKey

from common import click_center


TEAM_TAB_Y = [214, 235, 255, 276, 296, 317, 337, 358]


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


@AgentServer.custom_action("CloseAllPopupsWithEsc")
class CloseAllPopupsWithEsc(CustomAction):
    """按 5 次 ESC；只对 check_node 指定的残留窗口补焦点和 ESC。"""

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        check_node = json.loads(argv.custom_action_param)["check_node"]
        for _ in range(5):
            if context.tasker.stopping:
                return False
            escaped = context.run_action_direct(JActionType.ClickKey, JClickKey(key=[ESC_KEY]))
            if context.tasker.stopping or not escaped or not escaped.success:
                return False
            time.sleep(0.2)
            if context.tasker.stopping:
                return False

        image = context.tasker.controller.post_screencap().wait().get()
        if context.tasker.stopping or image is None:
            return False
        remain_popup = context.run_recognition(check_node, image)
        if context.tasker.stopping or not remain_popup:
            return False
        if remain_popup.hit:
            focused = click_center(context, FOCUS_BOX)
            if context.tasker.stopping or not focused:
                return False
            time.sleep(0.2)
            if context.tasker.stopping:
                return False
            escaped = context.run_action_direct(JActionType.ClickKey, JClickKey(key=[ESC_KEY]))
            if context.tasker.stopping or not escaped or not escaped.success:
                return False

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
