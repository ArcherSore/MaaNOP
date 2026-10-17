import json

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context


@AgentServer.custom_action("EnterDailyTask")
class EnterDailyTask(CustomAction):
    """打开日常并选中目标详情，参与和收尾交给调用方的 next。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        param = json.loads(argv.custom_action_param)
        pages = {
            "daily": ("DailyTab", [378, 207, 50, 14]),
            "limited": ("DailyLimitedTab", [478, 207, 50, 14]),
        }
        page = pages.get(param.get("page", "daily"))
        if page is None:
            return False

        # 行和标题使用任务已有识别；覆盖仅在本次导航中生效。
        navigation = context.clone()
        result = navigation.run_task(
            "DailyTask",
            pipeline_override={
                "DailyTargetPage": {
                    "recognition": {"param": {"all_of": [page[0]]}}
                },
                "DailySwitchPage": {"action": {"param": {"target": page[1]}}},
                "DailySelectTask": {
                    "recognition": {
                        "param": {
                            "all_of": ["DailyTargetPage", param["row"]],
                            "box_index": 1,
                        }
                    }
                },
                "DailyTaskSelected": {
                    "recognition": {
                        "param": {"all_of": ["DailyTargetPage", param["title"]]}
                    }
                },
            },
        )
        if context.tasker.stopping:
            return False
        nodes = result.nodes if result else []
        return bool(nodes and nodes[-1].name == "DailyTaskReady")


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
