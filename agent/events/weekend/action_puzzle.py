import json
import time

import numpy as np
from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.pipeline import JTemplateMatch


# 左侧棋盘显示压暗到 DIM_FACTOR 亮度的图片；散落的碎片以原色、同样的缩放堆在右侧面板。
BOARD = (388, 240, 296, 296)
PILE = (776, 241, 176, 294)
DIM_FACTOR = 0.295

# 只有格子中间部分在各种碎片形状上完全一致；凸起和凹口在外侧四分之一处。
CORE_MARGIN = 0.26
# TemplateMatch 方法 10001：反转的 TM_SQDIFF_NORMED，1.0 表示颜色完全匹配。
MATCH_METHOD = 10001
# 与被拒绝的拖放点距离小于该值的匹配视为同一块碎片。
SAME_PIECE_DISTANCE = 10
# 格子核心像素中，与压暗图片相差超过 FILLED_DELTA 的比例达到该值，即视为已填（放上的碎片亮得多）。
FILLED_DELTA = 4
FILLED_SHARE = 0.5

DRAG_DURATION = 300
# 被拒绝的碎片要过一会儿才回到堆里，所以固定等待。
SETTLE_DELAY = 0.3
MAX_DRAGS_PER_PIECE = 6


def cell_cores(count: int) -> list[tuple[slice, slice]]:
    """棋盘内每个格子核心区域的行/列切片，下标为 row * count + column。"""
    size = BOARD[2] / count
    margin = size * CORE_MARGIN
    return [
        (slice(round(row * size + margin), round((row + 1) * size - margin)),
         slice(round(col * size + margin), round((col + 1) * size - margin)))
        for row in range(count)
        for col in range(count)
    ]


def filled_cells(image: np.ndarray, picture: np.ndarray, cores: list[tuple[slice, slice]]) -> set[int]:
    """核心区域不再像压暗图片的格子，即已放上碎片的格子。"""
    x, y, w, h = BOARD
    # 用 int16，避免 uint8 像素相减时回绕。
    delta = np.abs(image[y:y + h, x:x + w].astype(np.int16) - picture).max(axis=2) > FILLED_DELTA
    return {cell for cell, core in enumerate(cores) if delta[core].mean() >= FILLED_SHARE}


def find_in_pile(
    context: Context, image: np.ndarray, template_name: str, rejected: list[tuple[int, int]]
) -> tuple[float, tuple[int, int]] | None:
    """格子模板在碎片堆中的最佳匹配 (得分, 中心)，忽略该格子已被拒绝过的拖放位置。"""
    detail = context.run_recognition_direct(
        "TemplateMatch",
        # 阈值为 0 保留所有候选，以便跳过被拒绝的位置。
        JTemplateMatch(template=[template_name], roi=PILE, threshold=[0.0], method=MATCH_METHOD),
        image,
    )
    if detail is None:
        raise RuntimeError(f"识别未启动：{template_name}")
    candidates = [
        (result.score, (result.box[0] + result.box[2] // 2, result.box[1] + result.box[3] // 2))
        for result in detail.all_results
    ]
    return max(
        (
            candidate for candidate in candidates
            if all(abs(candidate[1][0] - x) > SAME_PIECE_DISTANCE or abs(candidate[1][1] - y) > SAME_PIECE_DISTANCE
                   for x, y in rejected)
        ),
        default=None,
    )


@AgentServer.custom_action("SolveJigsawPuzzle")
class SolveJigsawPuzzle(CustomAction):
    """把碎片堆里的每块碎片拖到对应格子。参数是棋盘边长。

    棋盘（压暗的图片）就是答案。碎片放错格子会被拒绝，所以颜色匹配只用来给猜测排序，
    棋盘用来判断哪些格子已填。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        try:
            count = json.loads(argv.custom_action_param)
            controller = context.tasker.controller

            image = controller.post_screencap().wait().get()
            x, y, w, h = BOARD
            picture = image[y:y + h, x:x + w].astype(np.int16)
            cores = cell_cores(count)
            # 每个格子的碎片在堆里应有的样子：把压暗的核心区域还原亮度。
            names = []
            for cell, core in enumerate(cores):
                names.append(f"JigsawCell{cell}")
                template = np.clip(picture[core] / DIM_FACTOR, 0, 255).astype(np.uint8)
                if not context.override_image(names[cell], template):
                    raise RuntimeError(f"注册第{cell + 1}格模板失败")
            size = w / count
            filled = set()
            rejected = {cell: [] for cell in range(len(cores))}
            drags = 0
            while not context.tasker.stopping:
                detail = context.run_recognition("PuzzleTimeUp", image)
                if detail is None:
                    raise RuntimeError("识别未启动：PuzzleTimeUp")
                if detail.hit:
                    raise RuntimeError("时间到")

                remaining = [cell for cell in range(len(cores)) if cell not in filled]
                if not remaining:
                    return True
                guesses = {cell: find_in_pile(context, image, names[cell], rejected[cell]) for cell in remaining}
                guesses = {cell: guess for cell, guess in guesses.items() if guess is not None}
                if not guesses:
                    raise RuntimeError(f"剩余 {len(remaining)} 块都找不到可拖的碎片")
                cell = max(guesses, key=lambda c: guesses[c][0])
                score, (piece_x, piece_y) = guesses[cell]

                drags += 1
                if drags > MAX_DRAGS_PER_PIECE * len(cores):
                    raise RuntimeError(f"拖拽 {drags} 次后仍剩 {len(remaining)} 块")
                row, col = divmod(cell, count)
                target = (round(x + (col + 0.5) * size), round(y + (row + 0.5) * size))
                print(f"拼图：第{cell + 1}块 ({piece_x},{piece_y}) → {target} 匹配度 {score:.3f}")
                if not controller.post_swipe(piece_x, piece_y, *target, DRAG_DURATION).wait().succeeded:
                    raise RuntimeError(f"第{cell + 1}块拖拽失败")

                if context.tasker.stopping:
                    return False
                time.sleep(SETTLE_DELAY)
                if context.tasker.stopping:
                    return False
                image = controller.post_screencap().wait().get()
                filled = filled_cells(image, picture, cores)
                if cell in filled:
                    # 有进展：失败过的位置只有在覆盖它的碎片离开后才会变化，所以只忘掉离开的碎片所覆盖的位置。
                    rejected = {
                        other: [
                            spot for spot in spots
                            if abs(spot[0] - piece_x) > size / 2 or abs(spot[1] - piece_y) > size / 2
                        ]
                        for other, spots in rejected.items()
                    }
                else:
                    rejected[cell].append((piece_x, piece_y))
            return False
        except Exception as exc:
            print(f"拼图失败：{exc}")
            return False
