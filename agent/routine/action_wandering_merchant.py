import json

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction


@AgentServer.custom_action("WanderingMerchantPurchaseSlots")
class WanderingMerchantPurchaseSlots(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        for origin in json.loads(argv.custom_action_param)["slots"]:
            slot = context.run_task("WanderingMerchantInspectSlot", {
                "WanderingMerchantInspectSlot": {
                    "recognition": {
                        "type": "DirectHit",
                        "param": {"roi": [*origin, 1, 1]},
                    },
                },
            })
            if context.tasker.stopping or not slot or not slot.status.succeeded or not slot.nodes:
                return False
            last = slot.nodes[-1]
            if not last.completed:
                return False
            # 点券不足或二级密码未通过时，公共购买流程已经关闭商店。
            if last.name == "LoginMapVisible":
                return True
            if last.name not in ("WanderingMerchantSlotSoldOut", "WanderingMerchantOtherItem"):
                return False

        close = context.run_task("CommonMerchantHoverClose")
        if context.tasker.stopping or not close or not close.status.succeeded or not close.nodes:
            return False
        last = close.nodes[-1]
        return last.completed and last.name == "LoginMapVisible"
