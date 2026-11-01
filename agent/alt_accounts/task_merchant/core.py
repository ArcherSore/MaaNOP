"""Task-card business decisions; screenshots remain native 720p Pipeline input."""
import json
import subprocess

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition

from .parser import parse_requirement


OPTIONS = {
    "survival_score": (70, 120, 170),
    "ranked_participation": (1, 2, 3),
    "wanted": (1, 3, 5),
    "escort": (1, 3),
    "arena_participation": (1, 2, 3, 6),
}


def selection_limits(config):
    """Independent checkbox flags preserve accidental multiple selections."""
    selections = config.get("selections", {})
    known = {
        f"{category}_{value}" for category, values in OPTIONS.items() for value in values
    }
    if not isinstance(selections, dict) or set(selections) - known:
        raise ValueError("Unknown merchant checkbox")
    if any(not isinstance(value, bool) for value in selections.values()):
        raise ValueError("Merchant selections must be booleans")
    limits = {}
    for category, values in OPTIONS.items():
        selected = [value for value in values if selections.get(f"{category}_{value}", False)]
        if len(selected) > 1:
            raise ValueError(f"Select at most one threshold for {category}")
        if selected:
            limits[category] = selected[0]
    return limits, True


def merchant_config(context):
    node = context.get_node_data("TaskMerchantConfigure")
    # v5.12.3 merges attach keys; custom_action_param is replaced as a whole.
    config = node["attach"]
    return {"recipient": config["recipient"],
            "selections": {key: value for key, value in config.items() if key != "recipient"}}


@AgentServer.custom_action("TaskMerchantConfigure")
class Configure(CustomAction):
    def run(self, context, argv):
        try:
            config = merchant_config(context)
            if not isinstance(config.get("recipient"), str) or not config["recipient"].strip():
                return False
            selection_limits(config)
        except (ValueError, TypeError, KeyError):
            return False
        # Keep screenshot and control coordinates at720p.
        return bool(context.tasker.controller.set_screenshot_use_raw_size(False)
                    and context.tasker.controller.set_screenshot_target_short_side(720)
                    and context.override_next("TaskMerchantProcessCard", []))


@AgentServer.custom_recognition("TaskMerchantClassify")
class Classify(CustomRecognition):
    def analyze(self, context, argv):
        if argv.image.shape[:2] != (720, 1340):
            return None
        result = context.run_recognition("TaskMerchantBodyOCR", argv.image)
        if context.tasker.stopping or not result or not result.hit:
            return None
        words = result.raw_detail.get("filtered", [])
        text = " ".join(word["text"] for word in sorted(words, key=lambda w: (w["box"][1], w["box"][0])))
        parsed = parse_requirement(text)
        if parsed is None:
            return None  # Unknown cards are not deleted.
        try:
            limits, _ = selection_limits(merchant_config(context))
        except (ValueError, TypeError, KeyError):
            return None
        category, required = parsed
        gift = category == "instant_complete" or (
            category in limits and required is not None and required <= limits[category]
        )
        return CustomRecognition.AnalyzeResult(
            box=[574, 283, 256, 14],
            detail={"category": category, "required": required, "decision": "gift" if gift else "delete", "text": text},
        )


@AgentServer.custom_action("TaskMerchantRouteCard")
class RouteCard(CustomAction):
    def run(self, context, argv):
        detail = argv.reco_detail.best_result.detail
        destination = {"gift": "TaskMerchantGiftFocus", "delete": "TaskMerchantOldDeleteToastGone"}.get(detail.get("decision"))
        return bool(destination and context.override_next(argv.node_name, [destination]))


@AgentServer.custom_action("TaskMerchantPasteRecipient")
class PasteRecipient(CustomAction):
    def run(self, context, argv):
        recipient = merchant_config(context)["recipient"].strip()
        try:
            # Pass the recipient as data, not shell code.
            completed = subprocess.run(
                ["powershell.exe", "-NoProfile", "-NonInteractive", "-STA", "-Command",
                 "[Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false); Set-Clipboard -Value ([Console]::In.ReadToEnd())"],
                input=recipient, text=True, encoding="utf-8", capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW, timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        if context.tasker.stopping or completed.returncode:
            return False
        controller = context.tasker.controller
        held = controller.post_key_down(17).wait()
        if context.tasker.stopping or not held.succeeded:
            controller.post_key_up(17).wait()
            return False
        try:
            selected = controller.post_click_key(65).wait()
            if context.tasker.stopping or not selected.succeeded:
                return False
            pasted = controller.post_click_key(86).wait()
        finally:
            released = controller.post_key_up(17).wait()
        return bool(not context.tasker.stopping and pasted.succeeded and released.succeeded)
