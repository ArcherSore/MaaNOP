import json

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

# 忍者界面队伍标签的 y 坐标，从上到下编号 1~8（和丰饶之间的队伍选项用的是同一组标签）
TEAM_TAB_Y = [235, 256, 276, 297, 317, 338, 358, 379]


@AgentServer.custom_action("SetBossTeam")
class SetBossTeam(CustomAction):
    """把丰饶之间的选队伍节点改成点第 N 个队伍标签；N 来自 custom_action_param（1~8）。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        team = int(json.loads(argv.custom_action_param))
        if not 1 <= team <= len(TEAM_TAB_Y):
            return False

        y = TEAM_TAB_Y[team - 1]
        roi = [358, y, 34, 12]
        return context.override_pipeline(
            {
                "AbundanceTeamSelected": {"recognition": {"param": {"roi": roi}}},
                "AbundanceClickTeam": {
                    "recognition": {"param": {"roi": roi}},
                    "action": {"param": {"target": [360, y + 1, 30, 11]}},
                },
            }
        )
