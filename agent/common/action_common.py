import json
from time import monotonic

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from common.utils import click_center


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
ESC_CLOSE_TIMEOUT_SECONDS = 8


@AgentServer.custom_action("CloseAllPopupsWithEsc")
class CloseAllPopupsWithEsc(CustomAction):
    """逐次按 ESC，直到识别到目标界面或本次关闭超时。"""

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        target_node = json.loads(argv.custom_action_param)["target_node"]
        deadline = monotonic() + ESC_CLOSE_TIMEOUT_SECONDS
        controller = context.tasker.controller

        while monotonic() < deadline and not context.tasker.stopping:
            image = controller.post_screencap().wait().get()
            if context.tasker.stopping or image is None or monotonic() >= deadline:
                return False
            target = context.run_recognition(target_node, image)
            if context.tasker.stopping or not target or monotonic() >= deadline:
                return False
            if target.hit:
                return True
            escaped = controller.post_click_key(ESC_KEY).wait()
            if context.tasker.stopping or not escaped.succeeded:
                return False

        return False


@AgentServer.custom_action("FalseAction")
class FalseAction(CustomAction):
    """始终失败。用作已识别到无法达成目标的状态的终止节点，失败的动作使任务以 Failed 结束。"""

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        return False
