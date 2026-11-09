import re

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_recognition import CustomRecognition


@AgentServer.custom_recognition("EscortFreeRefreshApplied")
class EscortFreeRefreshApplied(CustomRecognition):
    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg):
        refresh_button = "EscortHoverFreeRefreshButton"
        before = context.tasker.get_latest_node(refresh_button)
        if context.tasker.stopping or not before or not before.recognition or not before.recognition.hit:
            return None

        previous_count = re.search(r"[1-4]", before.recognition.best_result.text)
        if not previous_count:
            return None

        remaining = int(previous_count[0]) - 1
        if remaining == 0:
            after = context.run_recognition("EscortNoRefresh", argv.image)
        else:
            # 刷新期间可能暂时读不到次数，轮询不能覆盖点击前的读数。
            after = context.run_recognition("EscortReadRefreshedCount", argv.image)
        if context.tasker.stopping or not after or not after.hit:
            return None

        if remaining:
            current_count = re.search(r"[1-4]", after.best_result.sub_results[0].best_result.text)
            if not current_count or int(current_count[0]) != remaining:
                return None
        return after.box


@AgentServer.custom_recognition("EscortSameExtraSS")
class EscortSameExtraSS(CustomRecognition):
    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg):
        initial_node = "EscortHoverExtraSS"
        if context.get_hit_count(initial_node) == 0:
            return None
        before = context.tasker.get_latest_node(initial_node)
        if context.tasker.stopping or not before or not before.recognition or not before.recognition.hit:
            return None

        # 复核时使用另一识别节点，避免覆盖初次选中的任务记录。
        after = context.run_recognition("EscortExtraSSRow", argv.image)
        if context.tasker.stopping or not after or not after.hit:
            return None

        initial = before.recognition.best_result.sub_results[0]
        initial_destination = initial.best_result.sub_results[-1].best_result.text
        current_destination = after.best_result.sub_results[-1].best_result.text
        if abs(initial.box.y - after.box.y) <= 7 and initial_destination == current_destination:
            return after.box
        return None
