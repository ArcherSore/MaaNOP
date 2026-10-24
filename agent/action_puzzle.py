import json

import numpy as np
from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.pipeline import JTemplateMatch, JWaitFreezes


# The left board shows the picture dimmed to DIM_FACTOR of its brightness; the
# loose pieces are piled in the right panel in full color, at the same scale.
BOARD = (388, 240, 296, 296)
PILE = (776, 241, 176, 294)
DIM_FACTOR = 0.295

# Only the middle of a cell is identical on every piece shape; the tabs and
# notches live in the outer quarter.
CORE_MARGIN = 0.26
# TemplateMatch method 10001: inverted TM_SQDIFF_NORMED, 1.0 is a perfect color match.
MATCH_METHOD = 10001
# Matches closer than this to a rejected drag point count as the same piece.
SAME_PIECE_DISTANCE = 10
# A cell counts as filled once this share of its core pixels differ from the
# dimmed picture by more than FILLED_DELTA (a placed piece is ~3x brighter).
FILLED_DELTA = 4
FILLED_SHARE = 0.5

DRAG_DURATION = 300
# After a drop, wait for the board and the pile to stop changing: an accepted
# piece sits on the board, a rejected one flies back to the pile within ~0.3 s.
FREEZE_TIME = 300
FREEZE_THRESHOLD = 0.98
FREEZE_POLL = 100
FREEZE_TIMEOUT = 3000
MAX_DRAGS_PER_PIECE = 6
# Cells are tried most distinctive first: the margin over the runner-up piece,
# relative to how far the score falls short of a perfect 1.0 (softened so that a
# near-perfect score cannot blow the ratio up).
RANK_SOFTENING = 0.02


def cell_cores(count: int) -> list[tuple[slice, slice]]:
    """Row/column slices of every cell's core within the board, indexed by row * count + column."""
    size = BOARD[2] / count
    margin = size * CORE_MARGIN
    return [
        (slice(round(row * size + margin), round((row + 1) * size - margin)),
         slice(round(col * size + margin), round((col + 1) * size - margin)))
        for row in range(count)
        for col in range(count)
    ]


def filled_cells(image: np.ndarray, picture: np.ndarray, cores: list[tuple[slice, slice]]) -> set[int]:
    """Cells whose core no longer looks like the dimmed picture, i.e. holds a piece."""
    x, y, w, h = BOARD
    # int16 so that subtracting uint8 pixels cannot wrap around.
    delta = np.abs(image[y:y + h, x:x + w].astype(np.int16) - picture).max(axis=2) > FILLED_DELTA
    return {cell for cell, core in enumerate(cores) if delta[core].mean() >= FILLED_SHARE}


def find_in_pile(
    context: Context, image: np.ndarray, template_name: str, rejected: list[tuple[int, int]]
) -> tuple[float, float, tuple[int, int]] | None:
    """Best match of a cell's template in the pile as (score, margin, center),
    ignoring spots where a drag of this cell was already rejected. The margin is
    how far the best match beats the best one on another piece: a dark or plain
    cell matches every piece alike, so its margin is near zero."""
    detail = context.run_recognition_direct(
        "TemplateMatch",
        # Threshold 0 keeps every candidate, so a rejected spot can be skipped.
        JTemplateMatch(template=[template_name], roi=PILE, threshold=[0.0], method=MATCH_METHOD),
        image,
    )
    if detail is None:
        raise RuntimeError(f"识别未启动：{template_name}")
    candidates = [
        (result.score, (result.box[0] + result.box[2] // 2, result.box[1] + result.box[3] // 2))
        for result in detail.all_results
    ]
    candidates = sorted(
        (
            candidate for candidate in candidates
            if all(abs(candidate[1][0] - x) > SAME_PIECE_DISTANCE or abs(candidate[1][1] - y) > SAME_PIECE_DISTANCE
                   for x, y in rejected)
        ),
        reverse=True,
    )
    if not candidates:
        return None
    score, (best_x, best_y) = candidates[0]
    runner_up = next(
        (
            other for other, (x, y) in candidates[1:]
            if abs(x - best_x) > SAME_PIECE_DISTANCE or abs(y - best_y) > SAME_PIECE_DISTANCE
        ),
        0.0,
    )
    return score, score - runner_up, (best_x, best_y)


@AgentServer.custom_action("SolveJigsawPuzzle")
class SolveJigsawPuzzle(CustomAction):
    """Drag every piece from the pile onto its cell. The param is the grid size.

    The board (dimmed picture) is the answer. A piece dropped on a wrong cell is
    rejected, so the color match only ranks the guesses and the board shows
    which cells are filled."""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        try:
            count = json.loads(argv.custom_action_param)
            controller = context.tasker.controller

            image = controller.post_screencap().wait().get()
            x, y, w, h = BOARD
            picture = image[y:y + h, x:x + w].astype(np.int16)
            cores = cell_cores(count)
            # What each cell's piece should look like in the pile: the dimmed core, brightened back.
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
                cell = max(guesses, key=lambda c: guesses[c][1] / (1 - guesses[c][0] + RANK_SOFTENING))
                score, _, (piece_x, piece_y) = guesses[cell]

                drags += 1
                if drags > MAX_DRAGS_PER_PIECE * len(cores):
                    raise RuntimeError(f"拖拽 {drags} 次后仍剩 {len(remaining)} 块")
                row, col = divmod(cell, count)
                target = (round(x + (col + 0.5) * size), round(y + (row + 0.5) * size))
                print(f"拼图：第{cell + 1}块 ({piece_x},{piece_y}) → {target} 匹配度 {score:.3f}")
                if not controller.post_swipe(piece_x, piece_y, *target, DRAG_DURATION).wait().succeeded:
                    raise RuntimeError(f"第{cell + 1}块拖拽失败")

                for region in (BOARD, PILE):
                    context.wait_freezes(wait_freezes_param=JWaitFreezes(
                        time=FREEZE_TIME, target=region, threshold=FREEZE_THRESHOLD,
                        rate_limit=FREEZE_POLL, timeout=FREEZE_TIMEOUT,
                    ))
                image = controller.post_screencap().wait().get()
                filled = filled_cells(image, picture, cores)
                if cell in filled:
                    # Progress: a spot that failed before only changes when the piece covering it leaves, so forget just the spots under the body of the piece that left.
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
