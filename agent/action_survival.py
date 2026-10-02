import re
from typing import Optional

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.pipeline import JActionType, JClick

from common import send_focus_message

SCORE_PATTERN = re.compile(r"(\d+)\s*/\s*(\d+)")

# 关卡：(名称, 点击位置, 每轮最多挑战次数)，按 SS→C 的顺序挑战。
# 重置后的次数就是这个上限；上一轮的次数未知，所以打到出现"次数已用尽"提示就把该关卡的剩余次数清零。
STAGES = [
    ("SS", (595, 178, 26, 28), 1),
    ("S", (822, 246, 26, 28), 2),
    ("A", (538, 328, 26, 28), 2),
    ("B", (762, 384, 26, 28), 3),
    ("C", (724, 468, 26, 28), 5),
]


def read_score(context: Context) -> Optional[tuple[int, int]]:
    """主界面的演习积分 (当前, 总数)。"""
    image = context.tasker.controller.post_screencap().wait().get()
    detail = context.run_recognition("SurvivalScoreOCR", image)
    if not detail or not detail.hit:
        return None
    for result in detail.all_results:
        match = SCORE_PATTERN.search(result.text)
        if match:
            return int(match.group(1)), int(match.group(2))
    return None


@AgentServer.custom_action("SurvivalPlayRound")
class SurvivalPlayRound(CustomAction):
    """打一轮生存演习：按 SS→C 依次挑战，直到积分满或次数用完。旧一轮和新一轮都用它。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        del argv
        remaining = {name: limit for name, _, limit in STAGES}

        for name, box, _ in STAGES:
            while remaining[name] > 0:
                if context.tasker.stopping:
                    return False
                score = read_score(context)
                if context.tasker.stopping:
                    return False
                if score is None:
                    print("生存演习：读取不到演习积分")
                    return False
                if score[0] >= score[1]:
                    send_focus_message(context, "演习积分已满")
                    return True

                click = context.run_action_direct(JActionType.Click, JClick(), box=box)
                if click is None or not click.success:
                    print(f"生存演习：点击关卡 {name} 失败")
                    return False

                # 点击后要么进入战斗（打完回到主界面），要么出现"次数已用尽"提示；由 pipeline 等待并处理
                outcome = context.run_task("SurvivalStageOutcome")
                if context.tasker.stopping:
                    return False
                reached = [node.name for node in outcome.nodes] if outcome else []
                if "SurvivalStageExhausted" in reached:
                    remaining[name] = 0
                    print(f"生存演习：{name} 次数已用尽，换下一个关卡")
                    break
                if not reached or reached[-1] != "SurvivalMainReady":
                    print(f"生存演习：关卡 {name} 点击后没有进入战斗，或战斗没有正常结束")
                    return False
                remaining[name] -= 1

        score = read_score(context)
        if context.tasker.stopping:
            return False
        if score is None:
            print("生存演习：读取不到演习积分")
            return False
        send_focus_message(
            context,
            "演习积分已满" if score[0] >= score[1] else "挑战次数已用完，积分未满",
        )
        return True
