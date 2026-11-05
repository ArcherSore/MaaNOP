"""独立进程：在大厅的「游戏多开登录窗口」里点击目标 QQ 的头像。

AgentServer 里不能创建控制器（MaaAgentServer 未实现 MaaWin32ControllerCreate），
所以对话框这个另一个窗口由普通模式的 maafw 在本进程处理，选号流程在 TempAccount.json 的 TempDialog* 节点。
退出码：0 已点击目标头像；3 列表里没有该号；1 其他失败。
"""
import sys
import time
from pathlib import Path

from maa.controller import Win32Controller
from maa.define import MaaWin32InputMethodEnum, MaaWin32ScreencapMethodEnum
from maa.resource import Resource
from maa.tasker import Tasker
from maa.toolkit import Toolkit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from login.compare_account import CompareAccount  # noqa: E402

DIALOG_WAIT_SECONDS = 10  # 等待多开窗口出现的上限


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    uin = sys.argv[1]
    # 与 Agent 进程分开写日志，避免两个进程写同一个 maafw.log。
    Tasker.set_log_dir("./debug/temp_dialog")
    Tasker.set_save_on_error(True)

    started = time.monotonic()
    deadline = started + DIALOG_WAIT_SECONDS
    while not (window := next((w for w in Toolkit.find_desktop_windows()
                               if w.class_name == "GRootViewClass" and w.window_name == "游戏多开登录窗口"), None)):
        if time.monotonic() > deadline:
            print(f"没有出现游戏多开登录窗口（等了 {DIALOG_WAIT_SECONDS} 秒）")
            return 1
        time.sleep(0.1)
    print(f"多开窗口 hwnd={window.hwnd}，{time.monotonic() - started:.1f} 秒后出现")

    # 对话框必须用 PrintWindow：默认的后台截图在这个窗口上返回旧帧。
    controller = Win32Controller(
        window.hwnd,
        MaaWin32ScreencapMethodEnum.PrintWindow,
        MaaWin32InputMethodEnum.Seize,
        MaaWin32InputMethodEnum.Seize,
    )
    if not controller.post_connection().wait().succeeded:
        print("绑定对话框窗口失败")
        return 1

    # 发布包是 <根>/resource，开发目录是 <根>/assets/resource。
    root = Path(__file__).resolve().parents[2]
    bundle = next(path for path in (root / "resource", root / "assets" / "resource") if path.is_dir())
    resource = Resource()
    if not resource.post_bundle(bundle).wait().succeeded:
        print("加载资源包失败")
        return 1
    resource.register_custom_recognition("CompareWebAccount", CompareAccount())

    tasker = Tasker()
    if not tasker.bind(resource, controller):
        print("绑定 Tasker 失败")
        return 1
    detail = tasker.post_task("TempDialogStart", {
        "TempDialogAccountMatch": {"recognition": {"param": {"custom_recognition_param": {
            "uin": uin, "source": "TempDialogReadNumber", "threshold": 0.85}}}}
    }).wait().get()
    nodes = detail.nodes if detail else []
    print("路径：", " → ".join(node.name for node in nodes))

    # 读到的号码按顺序列出，找不到号或点错号时先看这里（OCR 误读、号码相近会误匹配）。
    seen = []
    for node in nodes:
        if node.name == "TempDialogReadNumber":
            ocr = node.recognition.best_result.sub_results[0]
            seen.append(ocr.best_result.text.strip() if ocr.hit and ocr.best_result else "（空槽）")
    print("读到的号码：", "、".join(seen) or "无")

    matched = next((node for node in nodes if node.name == "TempDialogAccountMatch"), None)
    if matched:
        compare = matched.recognition.best_result.detail
        print(f"命中 {compare['uin']}，与 {uin} 相似度 {compare['similarity']:.2f}")
        return 0
    return 3 if any(node.name == "TempDialogNotListed" for node in nodes) else 1


if __name__ == "__main__":
    sys.exit(main())
