import re

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_recognition import CustomRecognition
from maa.pipeline import JInputText


@AgentServer.custom_recognition("CommonPasswordConfigured")
class CommonPasswordConfigured(CustomRecognition):
    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg):
        node = context.get_node_object("CommonInputSecondaryPassword")
        if context.tasker.stopping or not node or not isinstance(node.action.param, JInputText):
            return None

        configured = re.fullmatch(r"[0-9]{6}", node.action.param.input_text) is not None
        if configured == (argv.custom_recognition_param == "true"):
            return argv.roi
        return None
