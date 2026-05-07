from collections import Counter
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


SERVER_REGION_MARK = "\u533a"
SERVER_NUMBER_CHARS = set("0123456789|")
SERVER_GRID_ROW_TOLERANCE = 9
SERVER_GRID_COL_TOLERANCE = 45
SERVER_GRID_MIN_BASE_VOTES = 3


def _extract_number_like_tokens(text: str) -> list[str]:
    numbers = []
    current = []

    for ch in text:
        if ch in SERVER_NUMBER_CHARS:
            current.append(ch)
        else:
            if current:
                numbers.append("".join(current))
                current = []

    if current:
        numbers.append("".join(current))

    return numbers


def _extract_server_number_tokens(text: str) -> list[str]:
    if SERVER_REGION_MARK not in text:
        return []

    return _extract_number_like_tokens(text.split(SERVER_REGION_MARK, 1)[0])


def _get_ocr_box(result):
    box = getattr(result, "box", None)
    if box is None:
        return None

    try:
        return [int(box[0]), int(box[1]), int(box[2]), int(box[3])]
    except (IndexError, TypeError, ValueError):
        return None


def _cluster_entries(entries: list[dict[str, Any]], coord_key: str, tolerance: int) -> dict[int, int]:
    clusters = []

    for entry in sorted(entries, key=lambda item: item[coord_key]):
        coord = entry[coord_key]
        for cluster in clusters:
            if abs(coord - cluster["coord"]) <= tolerance:
                cluster["members"].append(entry)
                cluster["coord"] = sum(item[coord_key] for item in cluster["members"]) / len(cluster["members"])
                break
        else:
            clusters.append({"coord": coord, "members": [entry]})

    entry_to_cluster = {}
    for cluster_index, cluster in enumerate(sorted(clusters, key=lambda item: item["coord"])):
        for entry in cluster["members"]:
            entry_to_cluster[entry["index"]] = cluster_index

    return entry_to_cluster


def _build_server_ocr_entries(results) -> list[dict[str, Any]]:
    entries = []
    for index, result in enumerate(results or []):
        text = getattr(result, "text", "") or ""
        if SERVER_REGION_MARK not in text:
            continue

        box = _get_ocr_box(result)
        if box is None:
            continue

        entries.append(
            {
                "index": index,
                "result": result,
                "text": text,
                "box": box,
                "x": box[0],
                "y": box[1],
                "numbers": _extract_server_number_tokens(text),
            }
        )

    if not entries:
        return []

    row_by_index = _cluster_entries(entries, "y", SERVER_GRID_ROW_TOLERANCE)
    col_by_index = _cluster_entries(entries, "x", SERVER_GRID_COL_TOLERANCE)
    col_count = max(col_by_index.values(), default=-1) + 1
    if col_count <= 0:
        return []

    for entry in entries:
        row = row_by_index[entry["index"]]
        col = col_by_index[entry["index"]]
        entry["grid_index"] = row * col_count + col

    return entries


def _entry_anchor_number(entry: dict[str, Any]) -> Optional[int]:
    if len(entry["numbers"]) != 1:
        return None

    token = entry["numbers"][0]
    if not token.isdigit():
        return None

    number = int(token)
    return number if number > 0 else None


def _infer_server_grid_base(entries: list[dict[str, Any]]) -> Optional[int]:
    base_votes = Counter()
    for entry in entries:
        number = _entry_anchor_number(entry)
        if number is None:
            continue

        base_votes[number + entry["grid_index"]] += 1

    if not base_votes:
        return None

    [(best_base, best_count), *rest] = base_votes.most_common()
    second_count = rest[0][1] if rest else 0
    if best_count < SERVER_GRID_MIN_BASE_VOTES or best_count <= second_count:
        return None

    return best_base


def _find_server_by_layout(reco_detail, target_server_id: int):
    entries = _build_server_ocr_entries(getattr(reco_detail, "all_results", []) if reco_detail else [])
    grid_base = _infer_server_grid_base(entries)
    if grid_base is None:
        return None

    for entry in entries:
        entry["corrected_server_id"] = grid_base - entry["grid_index"]
        if entry["corrected_server_id"] == target_server_id:
            return entry["result"]

    return None


def find_server_ocr_result(reco_detail, target_server_id: int):
    if reco_detail and reco_detail.hit and reco_detail.best_result:
        return reco_detail.best_result, "exact"

    layout_result = _find_server_by_layout(reco_detail, target_server_id)
    if layout_result:
        return layout_result, "layout_inferred"

    return None, None
