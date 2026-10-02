import re

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_recognition import CustomRecognition

SCORE_PATTERN = re.compile(r"(\d+)\s*/\s*(\d+)")


@AgentServer.custom_recognition("SurvivalScoreFull")
class SurvivalScoreFull(CustomRecognition):
    """
    演习积分已满（当前积分 >= 总积分）时命中。
    """

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        reco_detail = context.run_recognition("SurvivalScoreOCR", argv.image)
        if not reco_detail or not reco_detail.hit:
            return None

        for result in reco_detail.all_results:
            match = SCORE_PATTERN.search(result.text)
            if not match:
                continue
            current, total = int(match.group(1)), int(match.group(2))
            if total > 0 and current >= total:
                return CustomRecognition.AnalyzeResult(
                    box=result.box, detail={"current": current, "total": total}
                )
        return None
