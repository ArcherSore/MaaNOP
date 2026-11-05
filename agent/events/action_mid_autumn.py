import time
from typing import Optional, Sequence

import numpy as np
from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.pipeline import JActionType, JClick


# 以求解器的颜色编号为下标；顺序沿五边形从顶部顺时针排列，相邻元素相容，不相邻元素冲突。
# (名称, RGB 下限, RGB 上限, 像素数) - 含义与 ColorMatch 节点相同。
# 火和土靠 G 通道区分：点亮的火格在土的颜色范围内也有一部分像素（亮条纹），
# 所以土的像素数下限必须高于它。
LANTERN_COLORS = [
    ("火", [200, 40, 0], [255, 115, 30], 200),
    ("土", [200, 125, 0], [255, 215, 30], 200),
    ("风", [0, 130, 0], [100, 255, 90], 200),
    ("水", [0, 60, 140], [60, 200, 255], 200),
    ("雷", [110, 20, 130], [230, 130, 210], 200),
]

# 按行优先编号，cell = 4 * row + column。既用于读颜色，也作为点击框。
CELL_ROIS = [
    [554, 301, 25, 25], [610, 301, 25, 25], [667, 301, 25, 25], [723, 301, 25, 25],
    [554, 355, 25, 25], [610, 355, 25, 25], [667, 355, 25, 25], [723, 355, 25, 25],
    [554, 410, 25, 25], [610, 410, 25, 25], [667, 410, 25, 25], [723, 410, 25, 25],
    [554, 464, 25, 25], [610, 464, 25, 25], [667, 464, 25, 25], [723, 464, 25, 25],
]
# 颜色弹窗中五个灯笼的点击框，以求解器的颜色编号为下标。
POPUP_COLOR_BOXES = [
    [638, 336, 14, 14],  # 火
    [687, 373, 14, 14],  # 土
    [668, 430, 14, 14],  # 风
    [609, 430, 14, 14],  # 水
    [589, 373, 14, 14],  # 雷
]

POPUP_TIMEOUT = 2.0
POLL_INTERVAL = 0.2
MAX_CLICK_RETRIES = 3


class LanternSolver:
    """按返回的顺序涂满 14 个空格后，每种颜色至少有 3 个灯笼。"""

    F = (0, 0, 1, 2,
         0, 1, 2, 3,
         1, 2, 3, 4,
         2, 3, 4, 4)

    G = (0, 1, 2, 2,
         4, 0, 1, 2,
         3, 4, 0, 1,
         3, 3, 4, 0)

    ROW_ORDER = tuple(range(16))
    RIGHT_COLUMNS_DOWN = tuple(4 * r + c for c in range(3, -1, -1) for r in range(4))
    LEFT_COLUMNS_UP = tuple(4 * r + c for c in range(4) for r in range(3, -1, -1))

    # 每条规则是 (涂色模板, 遍历顺序)。
    RULES = {
        "A": (tuple((c + 2) % 5 for c in F), ROW_ORDER),
        "B": (tuple((c + 3) % 5 for c in F), ROW_ORDER),
        "C": (tuple((1 - c) % 5 for c in G), RIGHT_COLUMNS_DOWN),
        "D": (G, LEFT_COLUMNS_UP),
        "E": (tuple((c - 1) % 5 for c in G), LEFT_COLUMNS_UP),
        "X": (F[:6] + (3,) + F[7:], RIGHT_COLUMNS_DOWN),  # 把 F 的第 6 格设为 3
    }

    # 规范化的位置对 -> 颜色距离为 0、1、2 时的规则。
    CHOICES = {
        (0, 1): "CDA",  (0, 2): "DCC",  (0, 3): "AAA",
        (0, 5): "DCD",  (0, 6): "AAA",  (0, 7): "ABC",
        (0, 10): "ABD", (0, 11): "BAB", (0, 15): "BAB",
        (1, 2): "XCC",  (1, 4): "ABA",  (1, 5): "CCC",
        (1, 6): "AAA",  (1, 7): "ABC",  (1, 9): "AAA",
        (1, 10): "ABC", (1, 11): "BAB", (1, 13): "ABE",
        (1, 14): "BAB", (5, 6): "CDE",  (5, 10): "DCD",
    }

    def __init__(self) -> None:
        # maps[s][p]：格子 p 在旋转/翻转 s 之后的位置。
        self.maps = tuple(
            tuple(self.transform(p, s) for p in range(16)) for s in range(8)
        )
        self.inverses = tuple(
            tuple(mapping.index(p) for p in range(16)) for mapping in self.maps
        )

    @staticmethod
    def transform(p: int, symmetry: int) -> int:
        """把格子 p 按棋盘 8 种旋转/翻转之一做映射。"""
        r, c = divmod(p, 4)
        if symmetry >= 4:
            c = 3 - c
        for _ in range(symmetry % 4):
            r, c = c, 3 - r
        return 4 * r + c

    def solve(self, p1: int, c1: int, p2: int, c2: int) -> list[tuple[int, int]]:
        """针对颜色为 c1、c2 的两个点亮格 p1、p2，返回 14 步 (格子, 颜色)。"""
        # 旋转/翻转棋盘，使两个点亮格落在规范化的位置对上。
        (p, q), symmetry = min(
            (tuple(sorted((mapping[p1], mapping[p2]))), s)
            for s, mapping in enumerate(self.maps)
        )
        base, other = (c1, c2) if self.maps[symmetry][p1] == p else (c2, c1)

        # 只有五边形上的颜色距离及其方向有影响。
        difference = (other - base) % 5
        sign = 1 if difference <= 2 else -1
        distance = min(difference, 5 - difference)

        target, order = self.RULES[self.CHOICES[(p, q)][distance]]
        inverse = self.inverses[symmetry]
        return [(inverse[v], (base + sign * target[v]) % 5)
                for v in order if v != p and v != q]


def check_stopping(context: Context) -> None:
    if context.tasker.stopping:
        raise RuntimeError("任务已停止")


def click_box(context: Context, box: Sequence[int], name: str) -> None:
    check_stopping(context)
    detail = context.run_action_direct(JActionType.Click, JClick(), box=list(box))
    if detail is None or not detail.success:
        raise RuntimeError(f"{name}点击失败")


def read_cell(image: np.ndarray, cell: int) -> Optional[int]:
    """返回格子的求解器颜色编号；未点亮时返回 None。"""
    x, y, w, h = CELL_ROIS[cell]
    # 截图是 BGR；反转通道即得 RGB，无需拷贝。
    rgb = image[y:y + h, x:x + w, ::-1]
    for color, (_, lower, upper, count) in enumerate(LANTERN_COLORS):
        # 每个像素的 R、G、B 都在范围内时为 True。
        in_range = np.all((rgb >= lower) & (rgb <= upper), axis=-1)
        if np.count_nonzero(in_range) >= count:
            return color
    return None


def popup_visible(context: Context, image) -> bool:
    detail = context.run_recognition("LanternColorPopupTemplate", image)
    if detail is None:
        raise RuntimeError("识别未启动：LanternColorPopupTemplate")
    return detail.hit


def wait_popup(context: Context, visible: bool) -> bool:
    """持续截图直到弹窗出现（或消失），最长 POPUP_TIMEOUT。"""
    deadline = time.monotonic() + POPUP_TIMEOUT
    while True:
        check_stopping(context)
        if popup_visible(context, context.tasker.controller.post_screencap().wait().get()) == visible:
            return True
        if time.monotonic() > deadline:
            return False
        time.sleep(POLL_INTERVAL)


def open_popup(context: Context, cell: int) -> None:
    for _ in range(MAX_CLICK_RETRIES):
        click_box(context, CELL_ROIS[cell], f"第{cell + 1}格")
        if wait_popup(context, visible=True):
            return
    raise RuntimeError(f"点击第{cell + 1}格后未出现选色弹窗")


def choose_color(context: Context, color: int) -> None:
    name = LANTERN_COLORS[color][0]
    for _ in range(MAX_CLICK_RETRIES):
        click_box(context, POPUP_COLOR_BOXES[color], f"{name}灯笼")
        if wait_popup(context, visible=False):
            return
    raise RuntimeError(f"选择{name}后弹窗未关闭")


@AgentServer.custom_action("SolveLanternPuzzle")
class SolveLanternPuzzle(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        del argv
        try:
            image = context.tasker.controller.post_screencap().wait().get()
            lit = [(cell, read_cell(image, cell)) for cell in range(16)]
            lit = [(cell, color) for cell, color in lit if color is not None]
            if len(lit) != 2:
                raise RuntimeError(f"初始应有 2 个亮灯，实际识别到 {len(lit)} 个：{lit}")
            (p1, c1), (p2, c2) = lit

            moves = LanternSolver().solve(p1, c1, p2, c2)
            for step, (cell, color) in enumerate(moves, start=1):
                print(f"中秋盛典：第{step}/14步 第{cell + 1}格 → {LANTERN_COLORS[color][0]}")
                open_popup(context, cell)
                choose_color(context, color)
            return True
        except Exception as exc:
            print(f"中秋盛典失败：{exc}")
            return False
