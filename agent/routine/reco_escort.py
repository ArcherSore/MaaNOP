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
            after = context.run_recognition(refresh_button, argv.image)
        if context.tasker.stopping or not after or not after.hit:
            return None

        if remaining:
            current_count = re.search(r"[1-4]", after.best_result.text)
            if not current_count or int(current_count[0]) != remaining:
                return None
        return after.box
