"""Compare an OCR number with the configured QQ; all UI flow lives in Pipeline."""
import json
from difflib import SequenceMatcher

from maa.agent.agent_server import AgentServer
from maa.custom_recognition import CustomRecognition


@AgentServer.custom_recognition("CompareWebAccount")
class CompareWebAccount(CustomRecognition):
    def analyze(self, context, argv):
        param = json.loads(argv.custom_recognition_param)
        number = ""
        if source := param.get("source"):
            node = context.tasker.get_latest_node(source)
            if context.tasker.stopping:
                return None
            if not node or not node.recognition or not node.recognition.best_result:
                return None
            ocr = node.recognition.best_result.sub_results[0]
            if not ocr.hit or not ocr.best_result:
                return None
            number = ocr.best_result.text.strip()
        # An empty source compares "" with the configured QQ for manual login.
        similarity = SequenceMatcher(None, number, param["uin"]).ratio()
        if similarity >= param["threshold"]:
            return CustomRecognition.AnalyzeResult(
                box=argv.roi, detail={"uin": number, "similarity": similarity}
            )
        return None
