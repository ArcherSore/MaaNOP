"""Dynamic map selection; all native recognitions/actions remain in Navigation.json."""
import json
import math
import re

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition


def _scroll(context, image):
    # Same unscaled ribbon templates pass both world/submap real frames (1101).
    outer = context.run_recognition("TaskMerchantScrollOuter", image)
    if context.tasker.stopping or not outer or not outer.hit:
        return None
    x, y, w, h = outer.box
    inner = context.run_recognition("TaskMerchantScrollInner", image, {
        "TaskMerchantScrollInner": {"recognition": {"type": "TemplateMatch", "param": {"roi": [x + 4, y + 4, 7, 26]}}}})
    if context.tasker.stopping or not inner or not inner.hit:
        return None
    # Measured on both clear world/submap captures: outer starts at full+(25,4).
    # Only the reference box is reconstructed; no full-scroll image is matched.
    return {"box": [x - 25, y - 4, 38, 42], "ribbon_box": [x, y, w, h]}


def _region(box, landmarks):
    # Scroll is immediately above its region landmark; source 1101 real map captures.
    x, y, w, h = box
    distances = [(math.hypot(x+w/2-p[0], y+h/2+28-p[1]), name)
                 for name, p in landmarks.items()]
    distance, name = min(distances)
    return name if distance <= 65 else None


@AgentServer.custom_recognition("TaskMerchantMapReady")
class TaskMerchantMapReady(CustomRecognition):
    def analyze(self, context, argv):
        located = _scroll(context, argv.image)
        if not located:
            return None
        return CustomRecognition.AnalyzeResult(box=tuple(located["box"]), detail=located)


@AgentServer.custom_action("TaskMerchantPrepareNavigation")
class TaskMerchantPrepareNavigation(CustomAction):
    def run(self, context, argv):
        config = json.loads(argv.custom_action_param)
        frame = context.tasker.controller.post_screencap().wait().get()
        if context.tasker.stopping or frame is None:
            return False
        header = context.run_recognition("TaskMerchantCurrentScene", frame)
        if context.tasker.stopping:
            return False
        text = header.best_result.text if header and header.hit else ""
        current = next((name for name in config["profiles"] if name in text), None)
        if current is None:
            current = next((name for prefix, name in (("川之国", "川之国峡谷"), ("热沙", "热沙荒野"), ("木山后山", "妙木山后山")) if prefix in text), None)
        opened = context.run_task("TaskMerchantOpenWorldMap")
        if context.tasker.stopping:
            return False
        ready = next((n for n in opened.nodes if n.name == "TaskMerchantWorldMapReady"), None) if opened else None
        if not ready:
            return False
        located = ready.recognition.best_result.detail
        name = _region(located["box"], config["world"])
        in_submap = False
        if name == "木叶村":
            opened = context.run_task("TaskMerchantOpenKonohaMap")
            if context.tasker.stopping:
                return False
            if not opened or not any(n.name == "TaskMerchantKonohaMapReady" for n in opened.nodes):
                return False
            frame = context.tasker.controller.post_screencap().wait().get()
            if context.tasker.stopping or frame is None:
                return False
            located = _scroll(context, frame)
            if not located:
                return False
            name = _region(located["box"], config["submap"])
            in_submap = True
        profile = config["profiles"].get(name)
        if not profile:
            return False
        position = profile.get("position")
        if not position:
            return False
        variants = profile.get("coordinate_variants") or [{"position": position, "point": profile["point"]}]
        coordinate_pattern = "|".join(str(v["position"][0])+r"[^0-9]+"+str(v["position"][1]) for v in variants)
        coordinate_pattern = profile.get("coordinate_pattern", coordinate_pattern)
        receipt_roi = profile.get("receipt_roi", [400,260,550,200] if name == "妙木山后山" else [550,319,240,42])
        landmark = [1134,86] if name == current else (config["submap"] if in_submap else config["world"])[name]
        scene = {"recognition": {"type": "OCR", "param": {"roi":[1205,81,130,19],
                 "expected":[{"川之国峡谷":"川之国", "热沙荒野":"热沙", "妙木山后山":"[妙炒]木山后山"}.get(name,re.escape(name))],"only_rec":True}}}
        return context.override_pipeline({
            "TaskMerchantOldReceiptGone": {"recognition":{"type":"OCR","param":{"roi":receipt_roi}}},
            "TaskMerchantClaimReceipt": {"recognition":{"type":"OCR","param":{"roi":receipt_roi}}},
            "TaskMerchantEnterSelected": {"action":{"type":"LongPress","param":{"target":[*landmark,1,1],"duration":100}}},
            "TaskMerchantSelectedScene": scene,
            "TaskMerchantPark": {"action":{"type":"LongPress","param":{"target":[*profile["parking"],1,1],"duration":100}}},
            "TaskMerchantParked": {"recognition":{"type":"OCR","param":{"roi":profile.get("parking_roi", [1254,81,49,17] if name == "妙木山后山" else [1205,81,130,19]),
                "expected":[coordinate_pattern],"only_rec":profile.get("parking_only_rec", name == "妙木山后山")}},
                "post_wait_freezes":{"time":300,"target":profile["freeze_roi"],"rate_limit":100,"timeout":5000}},
            "TaskMerchantSelectFixedPoint": {"action":{"type":"Custom","param":{"custom_action":"TaskMerchantSelectFixedPoint",
                "custom_action_param":{"variants":variants,"point":profile["point"]}}}},
            "TaskMerchantClickFixedName": {"action":{"type":"LongPress","param":{"target":[*profile["point"],1,1],"duration":100}}},
        })


@AgentServer.custom_action("TaskMerchantSelectFixedPoint")
class TaskMerchantSelectFixedPoint(CustomAction):
    def run(self, context, argv):
        params = json.loads(argv.custom_action_param)
        point = params["point"]
        if len(params["variants"]) > 1:
            node = context.tasker.get_latest_node("TaskMerchantParked")
            if not node or not node.recognition or not node.recognition.hit:
                return False
            text = node.recognition.best_result.text
            match = next((v for v in params["variants"] if re.search(
                str(v["position"][0])+r"[^0-9]+"+str(v["position"][1]), text)), None)
            if not match:
                return False
            point = match["point"]
        return context.override_pipeline({"TaskMerchantClickFixedName":{
            "action":{"type":"LongPress","param":{"target":[*point,1,1],"duration":100}}}})


@AgentServer.custom_action("TaskMerchantRouteClaimReceipt")
class TaskMerchantRouteClaimReceipt(CustomAction):
    def run(self, context, argv):
        text = argv.reco_detail.best_result.text
        destination = "TaskMerchantOpenPanel" if "10" in text and "任务" in text and "最多" in text else "TaskMerchantPark"
        return context.override_pipeline({"TaskMerchantAfterReceipt":{"next":[destination]}})
