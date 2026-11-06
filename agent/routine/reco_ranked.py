import json
import re

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_recognition import CustomRecognition


@AgentServer.custom_recognition("RankedLowestPower")
class RankedLowestPower(CustomRecognition):
    """从识别到的对手中选择战斗力最低者。"""

    def analyze(
        self,
        context: Context,
        argv: CustomRecognition.AnalyzeArg,
    ) -> CustomRecognition.AnalyzeResult:
        param = json.loads(argv.custom_recognition_param)
        candidates = []
        powers = []
        for index, slot in enumerate(param["slots"]):
            power = context.run_recognition(
                "RankedPowerOCR",
                argv.image,
                {"RankedPowerOCR": {"recognition": {"param": {"roi": slot["roi"]}}}},
            )
            if context.tasker.stopping:
                return None
            # ROI 只覆盖战斗力一行，避免把区服、等级或名次拼进数值。
            text = power.best_result.text if power and power.hit else ""
            match = re.search(r"(?:战斗力\s*[:：]?\s*)?(\d[\d,，]*)\s*$", text)
            value = int(match[1].replace(",", "").replace("，", "")) if match else None
            powers.append(value)
            if value is not None and value > 0:
                candidates.append((value, index))

        if not candidates:
            return None
        selected = min(candidates)[1]
        return CustomRecognition.AnalyzeResult(
            box=tuple(param["slots"][selected]["target"]),
            detail={"slot": selected + 1, "powers": powers},
        )
