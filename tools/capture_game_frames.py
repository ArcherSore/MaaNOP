"""Capture a sequence of lossless PNGs from the MaaNOP game window."""

import argparse
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
from maa.controller import Win32Controller
from maa.define import MaaWin32ScreencapMethodEnum
from maa.toolkit import Toolkit


def select_game_window(hwnd):
    windows = [
        window
        for window in Toolkit.find_desktop_windows()
        if window.class_name.startswith("MainView_")
        and "火影忍者online" in window.window_name.lower()
    ]
    if hwnd is not None:
        windows = [window for window in windows if window.hwnd == hwnd]
    if not windows:
        raise RuntimeError("未找到目标游戏窗口。请在游戏所在的 Windows 桌面会话运行脚本。")
    if len(windows) > 1:
        choices = "\n".join(f"  {window.hwnd:#x}  {window.window_name}" for window in windows)
        raise RuntimeError(f"找到多个游戏窗口，请用 --hwnd 指定一个句柄：\n{choices}")
    return windows[0]


def capture_frames(window, output, fps, raw):
    controller = Win32Controller(
        window.hwnd,
        screencap_method=MaaWin32ScreencapMethodEnum.PrintWindow,
    )
    if raw:
        configured = controller.set_screenshot_use_raw_size(True)
    else:
        configured = controller.set_screenshot_target_short_side(720)
    if not configured:
        raise RuntimeError("无法设置控制器截图尺寸。")
    if not controller.post_connection().wait().succeeded:
        raise RuntimeError("无法连接游戏窗口。")

    stop_requested = False

    def request_stop(_signal, _frame):
        # Finish writing the current PNG before exiting.
        nonlocal stop_requested
        stop_requested = True

    count = 0
    previous_handler = signal.signal(signal.SIGINT, request_stop)
    start = time.monotonic()
    try:
        while not stop_requested:
            frame_start = time.monotonic()
            job = controller.post_screencap().wait()
            if not job.succeeded:
                raise RuntimeError("控制器截图失败，请检查游戏窗口是否仍然打开。")
            frame = job.get()
            if not frame.size:
                raise RuntimeError("控制器返回了空图像。")
            if count == 0:
                output.mkdir(parents=True, exist_ok=False)
                height, width = frame.shape[:2]
                print(f"正在采集 {width}×{height} PNG 至 {output}", flush=True)
                print("请操作游戏。采集结束后回到此终端，按 Ctrl+C 停止。", flush=True)

            ok, png = cv2.imencode(".png", frame, [cv2.IMWRITE_PNG_COMPRESSION, 1])
            if not ok:
                raise RuntimeError("无法编码 PNG。")
            elapsed_ms = round((frame_start - start) * 1000)
            (output / f"{count + 1:06d}_{elapsed_ms:08d}ms.png").write_bytes(png.tobytes())
            count += 1
            if not stop_requested:
                time.sleep(max(0, 1 / fps - (time.monotonic() - frame_start)))
    finally:
        signal.signal(signal.SIGINT, previous_handler)
        if count:
            print(f"已保存 {count} 帧：{output}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="用 MaaFramework 控制器连续采集游戏画面的 PNG。")
    parser.add_argument("--fps", type=int, default=15, help="目标帧率，1–60，默认 15")
    parser.add_argument("--hwnd", type=lambda value: int(value, 0), help="窗口句柄，支持十进制和 0x 十六进制")
    parser.add_argument("--raw", action="store_true", help="保持客户区原始尺寸，默认按短边 720 输出")
    args = parser.parse_args()
    if not 1 <= args.fps <= 60:
        parser.error("--fps 必须在 1 到 60 之间。")

    now = datetime.now()
    output = (
        Path(__file__).resolve().parents[1]
        / "artifacts"
        / now.strftime("game-capture-%Y-%m-%d")
        / "evidence"
        / now.strftime("%H%M%S_%f")
    )
    try:
        window = select_game_window(args.hwnd)
        capture_frames(window, output, args.fps, args.raw)
    except (RuntimeError, OSError, cv2.error) as exc:
        print(f"采集失败：{exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    sys.exit(main())
