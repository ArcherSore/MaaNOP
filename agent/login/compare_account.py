"""Compare an OCR number with the configured QQ; all UI flow lives in Pipeline.

不依赖 AgentServer，Agent 和多开对话框的独立进程都用它。
"""
import json
from difflib import SequenceMatcher

from maa.custom_recognition import CustomRecognition


class CompareAccount(CustomRecognition):
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
