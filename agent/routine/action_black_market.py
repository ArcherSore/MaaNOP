from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction


@AgentServer.custom_action("BlackMarketSetPurchaseMessage")
class BlackMarketSetPurchaseMessage(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        item = argv.reco_detail.best_result.sub_results[-1].best_result.text
        size = "大" if item == "体力药水" else "小"
        return context.override_pipeline({
            "BlackMarketPurchaseSucceeded": {
                "focus": {
                    "Node.Recognition.Succeeded": f"叮~恭喜蹲到了{size}体力药水！",
                },
            },
        })
