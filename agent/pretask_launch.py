"""Start the official microclient; the frontend owns process cleanup on failure/stop."""
import json
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys
import time

def game_window(windows):
    return next((w for w in windows
                 if w.class_name.startswith("MainView_") and "火影忍者Online" in w.window_name), None)

def prepare_window(hwnd):
    # 100% 缩放下该微端外框与客户区一致，1920×1032 对应 Maa 截图 1340×720。
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetWindowPos.argtypes = [
        wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
        ctypes.c_int, ctypes.c_int, wintypes.UINT,
    ]
    user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.ShowWindow(hwnd, 9)  # SW_RESTORE：退出最大化/最小化。
    # SWP_NOZORDER | SWP_NOACTIVATE。
    if not user32.SetWindowPos(hwnd, None, 0, 0, 1920, 1032, 0x14):
        raise ctypes.WinError(ctypes.get_last_error())
    client = wintypes.RECT()
    if not user32.GetClientRect(hwnd, ctypes.byref(client)):
        raise ctypes.WinError(ctypes.get_last_error())
    actual = (client.right - client.left, client.bottom - client.top)
    if actual != (1920, 1032):
        raise RuntimeError(f"窗口尺寸设置未生效，实际客户区为 {actual[0]}×{actual[1]}。")
    print("游戏客户区已设置为 1920×1032。", flush=True)

def launch(uin, executable):
    from maa.toolkit import Toolkit

    # Toolkit enumerates the caller's desktop, so the main desktop's game is not reused.
    window = game_window(Toolkit.find_desktop_windows())
    if window:
        print("游戏窗口已存在，复用当前窗口。", flush=True)
        return window
    if not executable.is_file():
        raise RuntimeError("未找到官方微端，请先安装并手动登录一次、勾选记住密码。")
    args = [str(executable), "-/appid:1103286479"]
    if uin:
        args.append(f"-loginuin:{uin}")
    subprocess.Popen(args, cwd=str(executable.parent))
    print("已启动微端，等待游戏窗口（最多 60 秒）。", flush=True)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        window = game_window(Toolkit.find_desktop_windows())
        if window:
            print("游戏窗口已出现。", flush=True)
            return window
        time.sleep(0.5)
    raise RuntimeError("60 秒内未出现游戏窗口。请检查保存密码、验证码或网络；本次停止，不自动重试。")

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        if len(sys.argv) != 2:
            raise RuntimeError("需要前端提供一个选项 JSON 参数。")
        uin = json.loads(sys.argv[1])["LoginAccount"]["uin"]
        if sys.platform != "win32":
            raise RuntimeError("官方微端仅支持 Windows。")
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise RuntimeError("无法获取当前用户的 APPDATA 目录。")
        executable = Path(appdata) / "Tencent" / "QQMicroGameBox" / "Launch.exe"
        window = launch(uin, executable)
        prepare_window(window.hwnd)
        return 0
    except (RuntimeError, OSError) as exc:
        print(f"启动游戏失败：{exc}", file=sys.stderr, flush=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
