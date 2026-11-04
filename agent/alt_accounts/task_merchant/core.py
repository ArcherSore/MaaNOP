"""任务卡分类与赠送/删除决策。"""
import re

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition


# 卡片正文规则；要求数值只取自正文，不取进度。
# 按顺序取第一条命中：更具体的规则须排在前面（如 arena_win 先于 arena_participation、escort_robbed 先于 escort）。
RULES = (
    ("survival_score", r"生存演习达到(\d+)分"),
    ("arena_win", r"获得(\d+)场[竞充克究]技场胜利"),
    ("arena_participation", r"进行(\d+)次[竞充克究]技场"),
    ("ranked_participation", r"进行(\d+)次排位[战成]"),
    ("escort_robbed", r"押.{0,2}被打[劫动](\d+)次"),
    ("escort", r"进行(\d+)次押"),
    ("wanted", r"完成(\d+)次通[缉辑缩给纷]任务"),
    ("quiz", r"测验答对(\d+)题"),
    ("quiz_participation", r"完成(\d+)次忍[者省]测验"),
    ("gift_cards", r"[赠婚]送(\d+)个任务卡"),
    ("delete_cards", r"删(?:除)?(\d+)个任务卡"),
    ("charge", r"充值(\d+)元宝"),
    ("spend", r"消费(\d+)元宝"),
    ("paid_exploration", r"洞穴中进行(\d+)次付费"),
    ("red_name_win", r"主动挑战并战胜(\d+)次红名劫掠"),
    ("red_name_challenge", r"主动挑战(\d+)次红名劫掠"),
    ("dungeon", r"通关(\d+)次.{0,10}副本"),
    ("treasure", r"完成([一三五\d]+)次挖宝"),
)
CHINESE_NUMBERS = {"一": 1, "三": 3, "五": 5}


def parse_requirement(text):
    """返回 (类别, 要求数值)；无法解析时返回 ("unknown", None)。"""
    # 直接完成类卡片忽略所有进度数字。
    if "直接完成任务" in text:
        return "instant_complete", None
    for category, pattern in RULES:
        match = re.search(pattern, text)
        if match:
            return category, CHINESE_NUMBERS.get(match[1]) or int(match[1])
    if re.search(r"挖宝[变竞]身成功", text):
        # 挖宝变身成功没有数值要求。
        return "treasure_transform", None
    return "unknown", None


@AgentServer.custom_recognition("TaskMerchantClassify")
class Classify(CustomRecognition):
    def analyze(self, context, argv):
        result = context.run_recognition("TaskMerchantBodyOCR", argv.image)
        # 读不到文字说明卡片尚未显示，返回 None 继续等待，不当作无法识别的卡。
        if context.tasker.stopping or not result or not result.hit:
            return None
        words = result.raw_detail.get("filtered", [])
        text = " ".join(word["text"] for word in sorted(words, key=lambda w: (w["box"][1], w["box"][0])))
        # unknown 不在阈值表中，与不可赠送的类别一样按删除处理。
        category, required = parse_requirement(text)
        # 阈值见 TaskMerchant.json 的 TaskMerchantConfigure.attach。
        thresholds = context.get_node_data("TaskMerchantConfigure")["attach"]
        gift = category == "instant_complete" or (category in thresholds and required <= thresholds[category])
        return CustomRecognition.AnalyzeResult(
            box=[574, 283, 256, 14],
            detail={"category": category, "required": required, "decision": "gift" if gift else "delete", "text": text},
        )


@AgentServer.custom_action("TaskMerchantRouteCard")
class RouteCard(CustomAction):
    def run(self, context, argv):
        gift = argv.reco_detail.best_result.detail["decision"] == "gift"
        destination = "TaskMerchantGiftFocus" if gift else "TaskMerchantOldDeleteToastGone"
        return context.override_next(argv.node_name, [destination])
