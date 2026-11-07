import re

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_recognition import CustomRecognition


@AgentServer.custom_recognition("SummonDamageDealt")
class SummonDamageDealt(CustomRecognition):
    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg):
        health = context.run_recognition("SummonBossHealth", argv.image)
        if context.tasker.stopping or not health or not health.hit:
            return None

        text = health.best_result.text
        readings = re.fullmatch(r"([0-9]+)[/／]([1-9][0-9]*)", text)
        if readings:
            current, maximum = readings.groups()
        elif re.fullmatch(r"[0-9]+", text) and len(text) % 2 == 0:
            # 小字号会漏掉斜线，按首击前后血量同位数的格式读取。
            middle = len(text) // 2
            current, maximum = text[:middle], text[middle:]
            if current.startswith("0") or maximum.startswith("0"):
                return None
        else:
            return None

        current_hp, max_hp = int(current), int(maximum)
        if current_hp >= max_hp:
            return None
        return CustomRecognition.AnalyzeResult(
            box=health.box, detail={"current": current_hp, "maximum": max_hp}
        )
