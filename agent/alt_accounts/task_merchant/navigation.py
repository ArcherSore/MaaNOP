"""地图选点与停靠的动态覆盖；原生识别与动作均在 Navigation.json 中。

Python 只负责判断并用 override_pipeline 写入节点参数，不直接点击；覆盖在本次任务内持续有效。
"""
import json
import math
import re
import time

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition


# 目标场景 -> (入口场景, 入口选点节点)：从别处前往会先到入口场景，须先在入口场景找商人，未找到再绕行。
DETOURS = {
    "终末谷上方": ("终末谷下方", "TaskMerchantSelectValleyLocation"),
    "沙忍村北": ("沙忍村南", "TaskMerchantSelectSandLocation"),
}


def _navigation_config(context):
    return context.get_node_data("TaskMerchantBeginRefill")["action"]["param"]["custom_action_param"]


def _scene_pattern(profiles, scene):
    return profiles[scene].get("scene_pattern", re.escape(scene))


def _coordinate_regex(x, y):
    # 数字边界防止 70,52 误匹配 170,52 或 70,521。
    return rf"(?<![0-9]){x}[^0-9]+{y}(?![0-9])"


def _scroll(context, image):
    # 同一组未缩放的丝带模板在世界地图与子地图实图上均可通过。
    outer = context.run_recognition("TaskMerchantScrollOuter", image)
    if context.tasker.stopping or not outer or not outer.hit:
        return None
    x, y, w, h = outer.box
    inner = context.run_recognition("TaskMerchantScrollInner", image, {
        "TaskMerchantScrollInner": {"recognition": {"type": "TemplateMatch", "param": {"roi": [x + 3, y + 3, 9, 28]}}}})
    if context.tasker.stopping or not inner or not inner.hit:
        return None
    # 外框位于完整卷轴的 (25,4) 处, 只还原参考框，不匹配完整卷轴图像。
    return [x - 25, y - 4, 38, 42]


def _region(box, landmarks):
    # 卷轴紧贴在所属区域地标的正上方；28 与 65 为实图测量的偏移和容差。
    x, y, w, h = box
    distance, name = min((math.hypot(x+w/2-p[0], y+h/2+28-p[1]), name) for name, p in landmarks.items())
    return name if distance <= 65 else None


def _map_box(context, entry, ready):
    opened = context.run_task(entry)
    node = next((n for n in opened.nodes if n.name == ready), None) if opened else None
    return node.recognition.box if node else None


def _locate(context, profile):
    """返回绿点可见的位置列表；截图失败或任务停止时返回 None。"""
    frame = context.tasker.controller.post_screencap().wait().get()
    if context.tasker.stopping or frame is None:
        return None
    # 同一帧判断全部候选，结果才可比较。
    matches = []
    for location in profile["locations"]:
        result = context.run_recognition(location["recognition"], frame)
        if context.tasker.stopping:
            return None
        if result and result.hit:
            matches.append(location)
    return matches


def _parking_overrides(location, scene):
    """把一个商人位置写入停靠链：点停靠点 → 确认坐标 → 点商人；并记下本次任务已定位的目标场景。"""
    parking_action = {"type": "LongPress", "param": {"target": [*location["parking"], 1, 1], "duration": 100}}
    pattern = location.get("coordinate_pattern", _coordinate_regex(*location["position"]))
    # 覆盖会保留到任务结束，Park.next 等可能被上一个位置（如顶楼路线）改过的字段每次都要完整写入。
    overrides = {
        # 仅在本次任务内有效；PrepareNavigation 据此跳过同一场景的再次绿点识别。
        "TaskMerchantBeginRefill": {"attach": {"located": scene}},
        "TaskMerchantPark": {"action": parking_action, "next": ["TaskMerchantParked"]},
        "TaskMerchantParked": {"recognition": {"type": "OCR", "param": {
            "roi": location.get("parking_roi", [1205, 81, 130, 19]),
            "expected": [pattern],
            "only_rec": location.get("parking_only_rec", False)}},
            "post_wait_freezes": {"time": 300, "target": location["freeze_roi"], "rate_limit": 100, "timeout": 5000}},
        "TaskMerchantClickFixedName": {"action": {"type": "LongPress", "param": {"target": [*location["point"], 1, 1], "duration": 100}}},
    }
    if location.get("cloud_roof_route"):
        # 云隐村顶楼需分段停靠：CloudRoute 走到终点后仍经 Parked 确认坐标并等待商人附近静止。
        overrides["TaskMerchantPark"] = {
            "action": {"type": "Custom", "param": {"custom_action": "TaskMerchantCloudRoute", "custom_action_param": {"target": pattern}}},
            "next": ["TaskMerchantParked"],
        }
        overrides["TaskMerchantCloudPark"] = {"action": parking_action}
    return overrides


@AgentServer.custom_recognition("TaskMerchantMapReady")
class TaskMerchantMapReady(CustomRecognition):
    def analyze(self, context, argv):
        box = _scroll(context, argv.image)
        if box is None:
            return None
        params = json.loads(argv.custom_recognition_param)
        # 子地图复用丝带；地标约束排除点击未生效时残留的世界地图。
        if "map" in params and _region(box, _navigation_config(context)[params["map"]]) is None:
            return None
        return CustomRecognition.AnalyzeResult(box=box, detail={})


@AgentServer.custom_action("TaskMerchantPrepareNavigation")
class TaskMerchantPrepareNavigation(CustomAction):
    def run(self, context, argv):
        config = json.loads(argv.custom_action_param)
        profiles = config["profiles"]
        box = _map_box(context, "TaskMerchantOpenWorldMap", "TaskMerchantWorldMapReady")
        if context.tasker.stopping or box is None:
            return False
        landmarks = config["world"]
        name = _region(box, landmarks)
        # 世界地图上木叶村只是入口，商人实际在子地图的木叶村东 / 木叶村北 / 妙木山后山。
        if name == "木叶村":
            box = _map_box(context, "TaskMerchantOpenKonohaMap", "TaskMerchantKonohaMapReady")
            if context.tasker.stopping or box is None:
                return False
            landmarks = config["submap"]
            name = _region(box, landmarks)
        profile = profiles.get(name)
        if profile is None:
            return False
        # 已在该场景时点地标只会关闭地图、原地不动；不在时自动寻路，因此总是点地标。
        # 绕行场景点完后可能在目标场景，也可能在入口场景，两者都接受，由 SelectEntryLocation 分辨。
        detour = DETOURS.get(name)
        scenes = [name, detour[0]] if detour else [name]
        # 绿点阈值按未遮挡收紧；本次任务已在该场景定位过时，角色可能正挡住绿点，直接沿用已写入的停靠参数。
        # 不考虑商人在同一场景内换位置。
        if context.get_node_data("TaskMerchantBeginRefill")["attach"].get("located") == name:
            scene_next = "TaskMerchantPark"
        else:
            scene_next = detour[1] if detour else "TaskMerchantLocateMerchant"
        return context.override_pipeline({
            "TaskMerchantEnterSelected": {"action": {"type": "LongPress", "param": {"target": [*landmarks[name], 1, 1], "duration": 100}}},
            "TaskMerchantSelectedScene": {
                "recognition": {"type": "OCR", "param": {
                    "roi": profile.get("scene_roi", [1205, 81, 130, 19]),
                    "expected": [_scene_pattern(profiles, scene) for scene in scenes],
                    "only_rec": profile.get("scene_only_rec", True)}},
                "next": [scene_next]},
            "TaskMerchantLocateMerchant": {"action": {"type": "Custom", "param": {"custom_action": "TaskMerchantLocateMerchant",
                "custom_action_param": {"scene": name}}}},
        })


@AgentServer.custom_action("TaskMerchantSelectEntryLocation")
class TaskMerchantSelectEntryLocation(CustomAction):
    """已在目标场景则直接找商人；在入口场景则有商人就地停靠，没有则走 approach 绕行到目标场景。"""
    def run(self, context, argv):
        params = json.loads(argv.custom_action_param)
        profiles = _navigation_config(context)["profiles"]
        text = context.tasker.get_latest_node("TaskMerchantSelectedScene").recognition.best_result.text
        if re.search(_scene_pattern(profiles, params["target"]), text):
            return context.override_next(argv.node_name, ["TaskMerchantLocateMerchant"])
        profile = profiles[params["scene"]]
        matches = _locate(context, profile)
        # 多处同时命中说明有干扰（如角色标记），不猜。
        if matches is None or len(matches) > 1:
            return False
        if not matches:
            return context.override_next(argv.node_name, [params["approach"]])
        return (context.override_pipeline(_parking_overrides(matches[0], params["target"]))
                and context.override_next(argv.node_name, ["TaskMerchantPark"]))


@AgentServer.custom_action("TaskMerchantLocateMerchant")
class TaskMerchantLocateMerchant(CustomAction):
    def run(self, context, argv):
        params = json.loads(argv.custom_action_param)
        profile = _navigation_config(context)["profiles"][params["scene"]]
        matches = _locate(context, profile)
        # 0 处：商人在未记录的新位置，需补充探索；多处：有干扰。都不猜。
        if matches is None or len(matches) != 1:
            return False
        return context.override_pipeline(_parking_overrides(matches[0], params["scene"]))


# 走路时坐标持续变化：读数连续 0.4 秒不变视为角色已停下；点击后 2 秒坐标未变视为点击未生效。
# 轮询间隔与流水线 rate_limit 一致，避免截图 + OCR（约 20ms）空转。
CLOUD_STOP_SECONDS = 0.4
CLOUD_START_SECONDS = 2
CLOUD_POLL_SECONDS = 0.1


def _cloud_text(context):
    """读右上角场景名与坐标；未读到返回空串，截图失败或任务停止返回 None。"""
    frame = context.tasker.controller.post_screencap().wait().get()
    if context.tasker.stopping or frame is None:
        return None
    result = context.run_recognition("TaskMerchantCloudCoordinate", frame)
    if context.tasker.stopping:
        return None
    return result.best_result.text if result and result.hit else ""


def _coords(text):
    # 只比较坐标数字，场景名的 OCR 误字（隐/险）不影响"是否停下"的判断。
    match = re.search(r"(\d+)[^0-9]+(\d+)[^0-9]*$", text)
    return match.groups() if match else None


@AgentServer.custom_action("TaskMerchantCloudRoute")
class TaskMerchantCloudRoute(CustomAction):
    """云隐村顶楼：寻路可能提前停在不固定的中途点，停下后未到终点就再点一次停靠点。

    目前只有这个位置有此问题；其他位置若出现再考虑通用化。
    """
    def run(self, context, argv):
        target = json.loads(argv.custom_action_param)["target"]
        for _ in range(6):
            text = _cloud_text(context)
            if text is None:
                return False
            if re.search(target, text):
                return True
            start = _coords(text)
            action = context.run_action("TaskMerchantCloudPark")
            if context.tasker.stopping or not action or not action.success:
                return False
            # 等起步：坐标变化前最多等 2 秒，未变化则回到循环开头重新点击。
            begin = time.monotonic()
            while (current := _coords(text)) in (None, start) and time.monotonic() - begin < CLOUD_START_SECONDS:
                time.sleep(CLOUD_POLL_SECONDS)
                text = _cloud_text(context)
                if text is None:
                    return False
            if current in (None, start):
                continue
            # 等停下：坐标连续 0.4 秒不变；30 秒仍未停下则失败。
            last, since = current, time.monotonic()
            while time.monotonic() - since < CLOUD_STOP_SECONDS:
                if time.monotonic() - begin > 30:
                    return False
                time.sleep(CLOUD_POLL_SECONDS)
                text = _cloud_text(context)
                if text is None:
                    return False
                current = _coords(text)
                if current and current != last:
                    last, since = current, time.monotonic()
        return False


@AgentServer.custom_action("TaskMerchantRouteClaimReceipt")
class TaskMerchantRouteClaimReceipt(CustomAction):
    def run(self, context, argv):
        text = argv.reco_detail.best_result.text
        # ClaimReceipt 只命中"最多只能领取10个任务"或"恭喜你…获得了N张任务卡"两种文字。
        # 没满时回 Park 重新停靠：点商人后角色会走到商人身边，镜头变化使固定点击点失效。
        full = "最多" in text
        return context.override_pipeline({"TaskMerchantAfterReceipt": {"next": ["TaskMerchantOpenPanel" if full else "TaskMerchantPark"]}})
