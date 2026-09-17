import time
from enum import Enum
from typing import Sequence

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.pipeline import JActionType, JClick

from common import capture_image, run_recognition


MAX_SLOTS = 6

SLOT_ROIS = [ [515, 351, 77, 78], [589, 275, 81, 78], [637, 375, 81, 76],
              [690, 289, 80, 77], [735, 369, 79, 77], [801, 312, 88, 84] ]

SEAL_TEMPLATES = {
    "Rat": "NinjutsuTraining/handSeals/HandSeal_1.png",
    "Ox": "NinjutsuTraining/handSeals/HandSeal_2.png",
    "Tiger": "NinjutsuTraining/handSeals/HandSeal_3.png",
    "Hare": "NinjutsuTraining/handSeals/HandSeal_4.png",
    "Dragon": "NinjutsuTraining/handSeals/HandSeal_5.png",
    "Snake": "NinjutsuTraining/handSeals/HandSeal_6.png",
    "Horse": "NinjutsuTraining/handSeals/HandSeal_7.png",
    "Ram": "NinjutsuTraining/handSeals/HandSeal_8.png",
    "Monkey": "NinjutsuTraining/handSeals/HandSeal_9.png",
    "Bird": "NinjutsuTraining/handSeals/HandSeal_10.png",
    "Dog": "NinjutsuTraining/handSeals/HandSeal_11.png",
    "Boar": "NinjutsuTraining/handSeals/HandSeal_12.png",
}

SEAL_CLICK_POSITIONS: dict[str, tuple[int, int, int, int]] = {
    "Rat": (567, 492, 20, 16),
    "Ox": (629, 487, 24, 21),
    "Tiger": (692, 489, 21, 19),
    "Hare": (754, 490, 22, 19),
    "Dragon": (818, 490, 20, 18),
    "Snake": (881, 488, 20, 20),
    "Horse": (566, 539, 22, 21),
    "Ram": (629, 539, 22, 21),
    "Monkey": (692, 537, 23, 22),
    "Bird": (755, 541, 22, 18),
    "Dog": (818, 539, 21, 19),
    "Boar": (881, 539, 22, 19),
}

SEAL_LOG_NAMES = {
    "Rat": "子",
    "Ox": "丑",
    "Tiger": "寅",
    "Hare": "卯",
    "Dragon": "辰",
    "Snake": "巳",
    "Horse": "午",
    "Ram": "未",
    "Monkey": "申",
    "Bird": "酉",
    "Dog": "戌",
    "Boar": "亥",
}

SEAL_RECOGNITION_NODES = {
    seal_name: f"HandSeal{seal_name}Template" for seal_name in SEAL_TEMPLATES
}
COMPLETED_RECOGNITION_NODE = "HandSealCompletedColor"
EMPTY_SLOT_RECOGNITION_NODE = "HandSealEmptySlotTemplate"
COMPLETE_ONCE_RECOGNITION_NODE = "HandSealCompleteOnceTemplate"
COMPLETE_ONCE_ROI = [663, 480, 114, 65]

SLOT_VERIFY_TIMEOUT = 2.0
ROUND_FINISH_TIMEOUT = 5.0
MAX_ROUND_RESTARTS = 2
MAX_RETRIES_PER_SLOT = 3
VERIFY_POLL_INTERVAL = 0.2

HAND_SEALS_ROI = [515, 275, 374, 176]


def recognize(context: Context, image, node_name: str, roi: Sequence[int]):
    detail = run_recognition(
        context, node_name, image, {node_name: {"roi": list(roi)}}
    )
    if detail is None:
        raise RuntimeError(f"识别未启动：{node_name}")
    return detail


def is_completed(context: Context, image, slot_index: int) -> bool:
    return recognize(
        context, image, COMPLETED_RECOGNITION_NODE, SLOT_ROIS[slot_index]
    ).hit


def round_finished(context: Context, image) -> bool:
    return recognize(
        context, image, COMPLETE_ONCE_RECOGNITION_NODE, COMPLETE_ONCE_ROI
    ).hit


def recognize_round(context: Context, image) -> list[tuple[int, str]]:
    """Read the entire round before clicking; preserve slot order and repeats."""
    best = {}
    for seal_name, node_name in SEAL_RECOGNITION_NODES.items():
        if context.tasker.stopping:
            raise RuntimeError("任务已停止")
        detail = recognize(context, image, node_name, HAND_SEALS_ROI)
        # filtered_results contains every threshold-passing match, not just best.
        for result in detail.filtered_results:
            x, y, w, h = result.box
            cx, cy = x + w / 2, y + h / 2
            candidates = []
            for slot_index in range(MAX_SLOTS):
                sx, sy, sw, sh = SLOT_ROIS[slot_index]
                if sx <= cx < sx + sw and sy <= cy < sy + sh:
                    distance = (cx - sx - sw / 2) ** 2 + (cy - sy - sh / 2) ** 2
                    candidates.append((distance, slot_index))
            if not candidates:
                continue
            slot_index = min(candidates)[1]
            if slot_index not in best or result.score > best[slot_index][0]:
                best[slot_index] = (result.score, seal_name)

    if not best:
        raise RuntimeError("未识别到本轮手印")
    # Slots 1-5 share the same empty-slot image. Slot 6 has no empty check.
    slot_count = MAX_SLOTS if MAX_SLOTS - 1 in best else MAX_SLOTS - 1
    for slot_index in range(MAX_SLOTS - 1):
        if recognize(
            context, image, EMPTY_SLOT_RECOGNITION_NODE, SLOT_ROIS[slot_index]
        ).hit:
            slot_count = slot_index
            break
    if not slot_count:
        raise RuntimeError("未识别到本轮手印")
    active_slots = range(slot_count)
    missing = [str(i + 1) for i in active_slots if i not in best]
    if missing:
        raise RuntimeError(f"无法识别槽位：{', '.join(missing)}")
    for slot_index in active_slots:
        if is_completed(context, image, slot_index):
            raise RuntimeError(f"第{slot_index + 1}个槽位在本轮开始前已点亮")
    return [(i, best[i][1]) for i in active_slots]


def click_seal(context: Context, slot_index: int, seal_name: str) -> None:
    if context.tasker.stopping:
        raise RuntimeError("任务已停止")
    detail = context.run_action_direct(
        JActionType.Click, JClick(), box=SEAL_CLICK_POSITIONS[seal_name]
    )
    if detail is None or not detail.success:
        raise RuntimeError(f"第{slot_index + 1}个手印点击失败")


class RoundResetError(RuntimeError):
    pass


class ClickState(Enum):
    RESET = "reset"
    NOT_TRIGGERED = "not_triggered"
    UNKNOWN = "unknown"


def detect_after_click(
    context: Context, image, sequence: list[tuple[int, str]], position: int
) -> ClickState:
    slot_index, seal_name = sequence[position]
    first_index, first_name = sequence[0]
    if recognize(
        context, image, SEAL_RECOGNITION_NODES[first_name], SLOT_ROIS[first_index]
    ).hit:
        return ClickState.RESET

    if slot_index == first_index:
        return ClickState.UNKNOWN
    if recognize(
        context, image, SEAL_RECOGNITION_NODES[seal_name], SLOT_ROIS[slot_index]
    ).hit:
        return ClickState.NOT_TRIGGERED
    return ClickState.UNKNOWN


def verify_slot(
    context: Context, sequence: list[tuple[int, str]], position: int
) -> None:
    """Follow PipelineTask: accept hits, then check timeout and rate-limit misses."""
    slot_index, seal_name = sequence[position]
    last_slot = position == len(sequence) - 1
    timeout = ROUND_FINISH_TIMEOUT if last_slot else SLOT_VERIFY_TIMEOUT
    for retries in range(MAX_RETRIES_PER_SLOT + 1):
        deadline = time.monotonic() + timeout
        while True:
            if context.tasker.stopping:
                raise RuntimeError("任务已停止")
            poll_start = time.monotonic()
            image = capture_image(context)
            confirmed = False
            if image is not None and image.size > 0:
                confirmed = (
                    round_finished(context, image)
                    if last_slot
                    else is_completed(context, image, slot_index)
                )
            if context.tasker.stopping:
                raise RuntimeError("任务已停止")
            if confirmed:
                return
            if time.monotonic() > deadline:
                break
            remaining = poll_start + VERIFY_POLL_INTERVAL - time.monotonic()
            if remaining > 0:
                time.sleep(remaining)

        if context.tasker.stopping:
            raise RuntimeError("任务已停止")
        print(f"忍术特训：第{slot_index + 1}个手印确认超时")
        state = detect_after_click(context, capture_image(context), sequence, position)
        if state == ClickState.RESET:
            raise RoundResetError("手印进度已重置")
        if state == ClickState.NOT_TRIGGERED:
            if retries >= MAX_RETRIES_PER_SLOT:
                raise RuntimeError(f"第{slot_index + 1}个手印补点后仍未成功")
            click_seal(context, slot_index, seal_name)
            print(f"忍术特训：补点第{slot_index + 1}个手印（{SEAL_LOG_NAMES[seal_name]}）")
            continue
        raise RuntimeError(f"第{slot_index + 1}个手印确认超时，无法判断失败原因")


@AgentServer.custom_action("ExecuteHandSealRound")
class ExecuteHandSealRound(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        del argv
        try:
            for attempt in range(MAX_ROUND_RESTARTS + 1):
                sequence = recognize_round(context, capture_image(context))
                names = " → ".join(SEAL_LOG_NAMES[name] for _, name in sequence)
                print(f"忍术特训：本轮手印 {names}")
                try:
                    for position, (slot_index, seal_name) in enumerate(sequence):
                        click_seal(context, slot_index, seal_name)
                        verify_slot(context, sequence, position)
                except RoundResetError:
                    if attempt >= MAX_ROUND_RESTARTS:
                        raise RuntimeError("本轮重复重置，停止执行")
                    print("忍术特训：检测到重置，重新识别本轮")
                    continue
                print("忍术特训：本轮完成")
                return True
            return False
        except Exception as exc:
            print(f"忍术特训失败：{exc}")
            return False
