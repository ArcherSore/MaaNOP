from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction


# Each slot specifies the remaining-count ROI, hover-color ROI, and card target.
CARDS = (
    ([609, 328, 29, 18], [500, 320, 145, 24], [574, 306, 14, 10]),
    ([797, 328, 29, 18], [688, 320, 145, 24], [762, 306, 14, 10]),
    ([609, 463, 29, 18], [500, 455, 145, 24], [574, 441, 14, 10]),
    ([797, 463, 29, 18], [688, 455, 145, 24], [762, 441, 14, 10]),
)


@AgentServer.custom_action("TreasureRoomDispatch")
class TreasureRoomDispatch(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        opened = context.run_task("TreasureRoomOpenNinja")
        if (
            context.tasker.stopping
            or not opened
            or not opened.nodes
            or opened.nodes[-1].name != "TreasureRoomOpened"
        ):
            return False

        for quota_roi, hover_roi, target in CARDS:
            while True:
                quota = context.run_task(
                    "TreasureRoomReadQuota",
                    {
                        "TreasureRoomReadQuota": {
                            "recognition": {
                                "param": {
                                    "roi": quota_roi
                                }
                            }
                        }
                    },
                )
                if context.tasker.stopping or not quota or not quota.nodes:
                    return False
                node = quota.nodes[-1]
                result = node.recognition.best_result if node.recognition else None
                if node.name != "TreasureRoomReadQuota" or result is None:
                    return False
                if result.text.replace(" ", "") == "0/3":
                    break

                battle = context.run_task(
                    "TreasureRoomHoverCard",
                    {
                        "TreasureRoomHoverCard": {
                            "action": {
                                "param": {
                                    "begin": target,
                                    "end": target
                                }
                            }
                        },
                        "TreasureRoomClickCard": {
                            "recognition": {
                                "param": {
                                    "roi": hover_roi
                                }
                            },
                            "action": {
                                "param": {
                                    "target": target
                                }
                            }
                        }
                    },
                )
                if (
                    context.tasker.stopping
                    or not battle
                    or not battle.nodes
                    or battle.nodes[-1].name != "TreasureRoomBattleReturned"
                ):
                    return False

                opened = context.run_task("TreasureRoomOpenNinja")
                if (
                    context.tasker.stopping
                    or not opened
                    or not opened.nodes
                    or opened.nodes[-1].name != "TreasureRoomOpened"
                ):
                    return False
        return True
