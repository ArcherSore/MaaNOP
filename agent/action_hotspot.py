import json

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context


@AgentServer.custom_action("EnterHotspotActivity")
class EnterHotspotActivity(CustomAction):
    """打开限时热点并在侧栏找到具体活动入口"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        expected = json.loads(argv.custom_action_param)["expected"]
        # OCR 目标只在本次导航中生效，避免污染其他任务的公共节点。
        navigation = context.clone()
        result = navigation.run_task(
            "HotspotEntry",
            pipeline_override={
                "ClickHotspotEntry": {
                    "recognition": {
                        "type": "OCR",
                        "param": {"expected": expected},
                    }
                }
            },
        )
        return result is not None and result.status.succeeded
