import json
import os
import subprocess
from itertools import groupby
from pathlib import Path

from maa.agent.agent_server import AgentServer
from maa.context import Context
from maa.custom_action import CustomAction
from maa.custom_recognition import CustomRecognition


PAGE_TOLERANCE = 3
VK_CONTROL = 0x11
VK_V = 0x56


def final_recognition(context, result, expected_node):
    if context.tasker.stopping or not result or not result.status.succeeded or not result.nodes:
        return None
    node = result.nodes[-1]
    if node.name == expected_node and node.recognition and node.recognition.hit:
        return node.recognition
    return None


@AgentServer.custom_recognition("GeneralStoreThumbAt")
class GeneralStoreThumbAt(CustomRecognition):
    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg):
        page = context.run_recognition("GeneralStorePage", argv.image)
        expected_y = int(argv.custom_recognition_param)
        if context.tasker.stopping or not page or not page.hit:
            return None
        if abs(page.box.y - expected_y) <= PAGE_TOLERANCE:
            return page.box
        return None


def drag_action(thumb, target_y):
    x = thumb.x + thumb.w // 2
    y = thumb.y + thumb.h // 2
    return {"action": {"param": {"begin": [x, y], "end": [x, y + target_y - thumb.y]}}}


def move_to_page(context, thumb, target_y):
    if abs(thumb.y - target_y) <= PAGE_TOLERANCE:
        return thumb
    result = context.run_task("GeneralStoreDrag", {
        "GeneralStoreDrag": drag_action(thumb, target_y),
        "GeneralStoreAtPage": {
            "recognition": {"param": {"custom_recognition_param": target_y}},
        },
    })
    page = final_recognition(context, result, "GeneralStoreAtPage")
    return page.box if page else None


def product_overrides(product_id, product):
    return {
        "GeneralStoreProduct": {
            "recognition": {"param": {
                "template": f"routine/general_store/{product_id}.png",
                "roi": product["icon_roi"],
            }},
        },
        "GeneralStoreProductLabel": {
            "recognition": {"param": {
                "expected": product["label"],
                "roi": product["label_roi"],
            }},
        },
    }


@AgentServer.custom_recognition("GeneralStorePageProducts")
class GeneralStorePageProducts(CustomRecognition):
    def analyze(self, context: Context, argv: CustomRecognition.AnalyzeArg):
        shop = context.run_recognition("GeneralStoreMoonReady", argv.image)
        if context.tasker.stopping or not shop or not shop.hit:
            return None
        products = context.get_node_data("GeneralStore")["attach"]["products"]
        sold_out = []
        for product_id in json.loads(argv.custom_recognition_param):
            overrides = product_overrides(product_id, products[product_id])
            available = context.run_recognition("GeneralStoreProduct", argv.image, overrides)
            if context.tasker.stopping:
                return None
            if available and available.hit:
                continue
            verified = context.run_recognition("GeneralStorePurchaseVerified", argv.image, overrides)
            if context.tasker.stopping or not verified or not verified.hit:
                return None
            sold_out.append(product_id)
        return self.AnalyzeResult(box=shop.box, detail={"sold_out": sold_out})


def wait_for_products(context, thumb, target_y, product_ids):
    overrides = {
        "GeneralStorePageProducts": {
            "recognition": {"param": {"custom_recognition_param": product_ids}},
        },
    }
    entry = "GeneralStoreWaitForProducts"
    if abs(thumb.y - target_y) > PAGE_TOLERANCE:
        entry = "GeneralStoreDrag"
        overrides[entry] = drag_action(thumb, target_y)
        overrides[entry]["next"] = ["GeneralStorePageProducts"]
    result = context.run_task(entry, overrides)
    return final_recognition(context, result, "GeneralStorePageProducts")


def checkout(context, product_id, product_config, layout):
    product_node = "GeneralStoreProduct"
    overrides = product_overrides(product_id, product_config)
    result = context.run_task("GeneralStoreFindProduct", overrides)
    if final_recognition(context, result, "GeneralStorePurchaseVerified"):
        return result
    product = final_recognition(context, result, "GeneralStoreProductVisible")
    if not product:
        return None

    x, y, w, h = product.box
    overrides[product_node]["recognition"]["param"]["roi"] = [x - 3, y - 3, w + 6, h + 6]
    stock_roi, quantity_roi, buy_roi = (
        [x + dx, y + dy, width, height] for dx, dy, width, height in
        (layout[key] for key in ("stock", "quantity", "buy"))
    )
    overrides["GeneralStoreStock"] = {"recognition": {"param": {"roi": stock_roi}}}
    result = context.run_task("GeneralStoreReadProduct", overrides)
    details = final_recognition(context, result, "GeneralStoreProductDetails")
    if not details:
        return None
    _, stock_result = details.best_result.sub_results
    stock = int(stock_result.best_result.text.removeprefix("库存"))

    qx, qy, qw, qh = quantity_roi
    bx, by, bw, bh = buy_roi
    buy_center = [bx + bw // 2, by + bh // 2]
    overrides.update({
        "GeneralStoreQuantity": {
            "recognition": {"param": {"roi": quantity_roi, "expected": f"^{stock}$"}},
        },
        "GeneralStoreQuantitySelected": {"recognition": {"param": {"roi": quantity_roi}}},
        "GeneralStoreSelectQuantity": {
            "action": {"param": {"custom_action_param": [qx + qw // 2, qy + qh // 2]}},
        },
        "GeneralStorePasteQuantity": {"action": {"param": {"custom_action_param": stock}}},
        "GeneralStoreHoverBuy": {"action": {"param": {"begin": buy_center, "end": buy_center}}},
        "GeneralStoreBuyHighlighted": {"recognition": {"param": {"roi": buy_roi}}},
        "GeneralStoreClickBuy": {
            "action": {"param": {"target": [bx + 14, by + 4, 20, 10]}},
        },
    })
    # 子任务共享命中次数。每个商品只在开始结算时重置，二级密码重入沿用本次上限。
    if not context.clear_hit_count("GeneralStoreClickBuy") or not context.clear_hit_count("GeneralStoreConfirm"):
        return None
    return context.run_task("GeneralStoreCheckout", overrides)


@AgentServer.custom_action("GeneralStoreBuyItems")
class GeneralStoreBuyItems(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        config = context.get_node_data(argv.node_name)["attach"]
        selected = sorted(
            (product for product in config["products"].items() if config.get(product[0]) is True),
            key=lambda product: product[1]["page"],
        )
        if not selected:
            return True

        result = context.run_task("GeneralStoreOpen")
        if not final_recognition(context, result, "GeneralStoreMoonReady"):
            return False

        top = config["scroll_top"]
        step = config["scroll_step"]
        for target_page, group in groupby(selected, key=lambda product: product[1]["page"]):
            items = list(group)
            result = context.run_task("GeneralStoreReadPage")
            page = final_recognition(context, result, "GeneralStorePage")
            if not page:
                return False
            thumb = page.box
            if target_page == selected[0][1]["page"]:
                thumb = move_to_page(context, thumb, top)
                if thumb is None:
                    return False
            target_y = min(top + target_page * step, config["track_bottom"] - thumb.h)
            while thumb.y + step + PAGE_TOLERANCE < target_y:
                thumb = move_to_page(context, thumb, thumb.y + step)
                if thumb is None:
                    return False
            ready = wait_for_products(context, thumb, target_y, [product_id for product_id, _ in items])
            if not ready:
                return False
            sold_out = ready.best_result.detail["sold_out"]
            for product_id, product in items:
                if product_id in sold_out:
                    continue
                result = checkout(context, product_id, product, config["layout"])
                if final_recognition(context, result, "LoginMapVisible"):
                    return True
                if not final_recognition(context, result, "GeneralStorePurchaseVerified"):
                    return False

        result = context.run_task("GeneralStoreLeave")
        return final_recognition(context, result, "LoginMapVisible") is not None


@AgentServer.custom_action("GeneralStoreDoubleClick")
class GeneralStoreDoubleClick(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        x, y = json.loads(argv.custom_action_param)
        controller = context.tasker.controller
        for _ in range(2):
            job = controller.post_click(x, y).wait()
            if context.tasker.stopping or not job.succeeded:
                return False
        return True


@AgentServer.custom_action("GeneralStorePaste")
class GeneralStorePaste(CustomAction):
    def run(self, context: Context, argv: CustomAction.RunArg) -> bool:
        quantity = int(argv.custom_action_param)
        try:
            subprocess.run(
                [Path(os.environ["SystemRoot"]) / "System32" / "clip.exe"],
                input=str(quantity).encode("ascii"),
                creationflags=subprocess.CREATE_NO_WINDOW,
                check=True,
                timeout=3,
            )
        except (OSError, subprocess.SubprocessError):
            return False
        if context.tasker.stopping:
            return False

        controller = context.tasker.controller
        pressed = controller.post_key_down(VK_CONTROL).wait()
        pasted = False
        try:
            if pressed.succeeded and not context.tasker.stopping:
                pasted = controller.post_click_key(VK_V).wait().succeeded
        finally:
            released = controller.post_key_up(VK_CONTROL).wait()
        return not context.tasker.stopping and pasted and released.succeeded
