"""Task-card body rules; requirements never come from progress."""
import re

def parse_requirement(text):
    """Extract category and stated requirement; return None for unknown text."""
    # Instant-complete ignores all progress numbers.
    if "直接完成任务" in text:
        return "instant_complete", None
    rules = [
        ("survival_score", r"生存演习达到(\d+)分"),
        ("arena_win", r"获得(\d+)场[竞充克究]技场胜利"),
        ("arena_participation", r"进行(\d+)次[竞充克究]技场"),
        ("ranked_participation", r"进行(\d+)次排位[战成]"),
        ("escort_robbed", r"押.{0,2}被打[劫动](\d+)次"),
        ("escort", r"进行(\d+)次押"),
        ("wanted", r"完成(\d+)次通[缉辑缩给纷]任务"),
        ("quiz", r"测验答对(\d+)题"),
        # Quiz rounds and correctly answered questions are separate tasks.
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
    ]
    for category, pattern in rules:
        match = re.search(pattern, text)
        if match:
            value = {"一": 1, "三": 3, "五": 5}.get(match[1])
            return category, value if value is not None else int(match[1])
    if re.search(r"挖宝[变竞]身成功", text):
        # Transformation success has no numerical requirement.
        return "treasure_transform", None
    return None
