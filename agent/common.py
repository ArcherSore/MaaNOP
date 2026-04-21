from typing import Any, Optional

from maa.context import Context


def strip_quotes(value: Optional[str]) -> str:
    return (value or "").strip('"')


def has_node_hit(context: Context, node_name: str) -> bool:
    return context.get_hit_count(node_name) > 0


def get_latest_detail(context: Context, node_name: str) -> Optional[dict[str, Any]]:
    if not has_node_hit(context, node_name):
        return None

    node = context.tasker.get_latest_node(node_name)
    if not node or not node.recognition or not node.recognition.best_result:
        return None
    detail = node.recognition.best_result.detail
    return detail if isinstance(detail, dict) else None


def get_detail_value(context: Context, node_name: str, key: str, default: Any = None) -> Any:
    detail = get_latest_detail(context, node_name)
    if detail is None:
        return default
    return detail.get(key, default)


def send_focus_message(context: Context, message: str) -> None:
    context.run_action(
        "LoginMsg",
        pipeline_override={
            "LoginMsg": {
                "focus": {
                    "Node.Action.Succeeded": message,
                }
            }
        },
    )


def run_recognition(context: Context, reco_name: str, image, override: Optional[dict[str, Any]] = None):
    if override is None:
        return context.run_recognition(reco_name, image)
    return context.run_recognition(reco_name, image, override)


def get_recognition_box(
    context: Context,
    image,
    reco_name: str,
    override: Optional[dict[str, Any]] = None,
):
    reco_detail = run_recognition(context, reco_name, image, override)
    if not reco_detail or not reco_detail.hit or not reco_detail.best_result:
        return None
    return reco_detail.best_result.box


def capture_image(context: Context):
    return context.tasker.controller.post_screencap().wait().get()


def click_point(context: Context, x: int, y: int) -> bool:
    context.tasker.controller.post_click(x, y).wait()
    return True


def click_key(context: Context, key: int) -> bool:
    context.tasker.controller.post_click_key(key).wait()
    return True


def click_box_center(context: Context, box) -> bool:
    if not box:
        return False

    center_x = box[0] + box[2] // 2
    center_y = box[1] + box[3] // 2
    return click_point(context, center_x, center_y)


def parse_digits(text: Optional[str]) -> str:
    return "".join(ch for ch in (text or "") if ch.isdigit())
