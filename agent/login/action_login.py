from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.context import Context

from common.utils import click_center, get_latest_detail, recognize_server
from login.server_session import clear_server_session
from login.constants import (
    SERVER_AIM_ROW,
    SERVER_GRID_COLUMNS,
    SERVER_SCROLL_MAX_DRAGS,
    SERVER_THUMB_OVERSHOOT,
    SERVER_THUMB_TRACKS,
    SERVER_VISIBLE_ROWS,
)


@AgentServer.custom_action("RefreshLoginPage")
class RefreshLoginPage(CustomAction):
    """刷新前清除选服点击计数，让同一任务的每次刷新各有 3 次机会。"""

    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        if not context.clear_hit_count("ReChooseServer"):
            return False
        clicked = click_center(context, argv.box)
        if context.tasker.stopping:
            return False
        return clicked


@AgentServer.custom_action("ScrollToTargetServer")
class ScrollToTargetServer(CustomAction):
    """读屏幕上的服号，按滑块与服号的线性关系拖到目标所在位置；拖完重读，只补剩余偏差。"""

    def run(
        self,
        context: Context,
        argv: CustomAction.RunArg,
    ) -> bool:
        server = get_latest_detail(context, "GetNextServer")
        if not server or "server_id" not in server:
            return False
        target_server_id = server["server_id"]
        region_type = server["region_type"]

        ids_per_px = None
        last = None
        pushed = None
        for drag_count in range(SERVER_SCROLL_MAX_DRAGS + 1):
            image = context.tasker.controller.post_screencap().wait().get()
            if context.tasker.stopping:
                return False
            matched_result, _, grid_base = recognize_server(
                context, image, target_server_id, region_type
            )
            if context.tasker.stopping:
                return False
            if matched_result:
                return True
            if drag_count == SERVER_SCROLL_MAX_DRAGS:
                break

            for thumb_node, track in SERVER_THUMB_TRACKS.items():
                thumb = context.run_recognition(thumb_node, image)
                if context.tasker.stopping:
                    return False
                if thumb and thumb.hit:
                    break
            else:
                return False
            if grid_base is None:
                return False
            x, y, w, h = thumb.box
            center_y = y + h // 2

            # 滑块高度与可见比例成正比，先验误差约 2-5%；拖动后改用实测比例，列表变长到滑块被夹成最小高度时也不会失准。
            if last and abs(center_y - last[0]) >= 15 and last[1] != grid_base:
                measured = (last[1] - grid_base) / (center_y - last[0])
                if measured > 0:
                    ids_per_px = measured
            if ids_per_px is None:
                ids_per_px = SERVER_GRID_COLUMNS * SERVER_VISIBLE_ROWS / h
            last = (center_y, grid_base)

            aim_base = target_server_id + SERVER_AIM_ROW * SERVER_GRID_COLUMNS + 1
            track_top, track_bottom = track
            estimated_y = round(center_y + (grid_base - aim_base) / ids_per_px)
            end_y = max(track_top + h // 2, min(track_bottom - h // 2, estimated_y))
            if end_y != estimated_y:
                # 目标在列表头或尾：终点拖过端点才能真正推到头；已推过一次仍没看到目标就失败。
                direction = 1 if estimated_y > end_y else -1
                if pushed == direction:
                    return False
                pushed = direction
                end_y += direction * SERVER_THUMB_OVERSHOOT
            else:
                pushed = None
                if end_y == center_y:
                    return False

            begin_x = x + w // 2
            result = context.run_task(
                "ServerListDrag",
                {"ServerListDrag": {"action": {"param": {
                    "begin": [begin_x, center_y],
                    "end": [begin_x, end_y],
                }}}},
            )
            if context.tasker.stopping or not result or not result.status.succeeded:
                return False

        return False


@AgentServer.custom_action("ClearServerSession")
class ClearServerSession(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        clear_server_session(argv.task_detail.task_id)
        return True
