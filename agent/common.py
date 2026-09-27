from collections import Counter
from typing import Any, Optional

from maa.context import Context

from constants import SERVER_1000_LIST_ROI


def get_latest_detail(context: Context, node_name: str) -> Optional[dict[str, Any]]:
    """Detail of the node's latest hit, only if it was hit in the current task."""
    if context.get_hit_count(node_name) == 0:
        return None

    node = context.tasker.get_latest_node(node_name)
    if not node or not node.recognition or not node.recognition.best_result:
        return None
    detail = node.recognition.best_result.detail
    return detail if isinstance(detail, dict) else None


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


def click_center(context: Context, box) -> bool:
    """Click the exact center of box; a pipeline Click picks a random point inside it."""
    if not box:
        return False

    x, y, w, h = box
    return context.tasker.controller.post_click(x + w // 2, y + h // 2).wait().succeeded


def parse_digits(text: Optional[str]) -> str:
    return "".join(ch for ch in (text or "") if ch.isdigit())


SERVER_REGION_MARK = "区"
SERVER_NUMBER_CHARS = set("0123456789|")
SERVER_GRID_ROW_TOLERANCE = 9
SERVER_GRID_COL_TOLERANCE = 45
SERVER_GRID_MIN_BASE_VOTES = 3
# Alliance's descending grid slots 73, 72, 71, 70 contain servers 70, 73, 72, 71.
ALLIANCE_GRID_TO_SERVER = {73: 70, 72: 73, 71: 72, 70: 71}
ALLIANCE_SERVER_TO_GRID = {server: grid for grid, server in ALLIANCE_GRID_TO_SERVER.items()}


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


def _infer_server_grid_base(entries: list[dict[str, Any]], region_type: str) -> Optional[int]:
    base_votes = Counter()
    for entry in entries:
        number = _entry_anchor_number(entry)
        if number is None:
            continue

        if region_type == "alliance":
            number = ALLIANCE_SERVER_TO_GRID.get(number, number)
        base_votes[number + entry["grid_index"]] += 1

    if not base_votes:
        return None

    [(best_base, best_count), *rest] = base_votes.most_common()
    second_count = rest[0][1] if rest else 0
    if best_count < SERVER_GRID_MIN_BASE_VOTES or best_count <= second_count:
        return None

    return best_base


def _find_server_by_layout(reco_detail, target_server_id: int, region_type: str):
    entries = _build_server_ocr_entries(getattr(reco_detail, "all_results", []) if reco_detail else [])
    grid_base = _infer_server_grid_base(entries, region_type)
    if grid_base is None:
        return None

    for entry in entries:
        entry["corrected_server_id"] = grid_base - entry["grid_index"]
        if region_type == "alliance":
            entry["corrected_server_id"] = ALLIANCE_GRID_TO_SERVER.get(
                entry["corrected_server_id"], entry["corrected_server_id"]
            )
        if entry["corrected_server_id"] == target_server_id:
            return entry["result"]

    return None


def find_server_ocr_result(reco_detail, target_server_id: int, region_type: str):
    if reco_detail and reco_detail.hit and reco_detail.best_result:
        return reco_detail.best_result, "exact"

    layout_result = _find_server_by_layout(reco_detail, target_server_id, region_type)
    if layout_result:
        return layout_result, "layout_inferred"

    return None, None


def recognize_server(context: Context, image, server_id: int, region_type: str):
    reco_detail = context.run_recognition(
        "ChooseServerButton",
        image,
        {
            "ChooseServerButton": {
                "roi": SERVER_1000_LIST_ROI,
                "expected": (
                    rf"^\s*{server_id}\s*区.*"
                    if region_type == "non_wipe"
                    else rf".*(^|[^0-9]){server_id}\s*区.*"
                ),
            }
        },
    )
    return find_server_ocr_result(reco_detail, server_id, region_type)
