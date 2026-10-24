"""Start the QQ Game Hall; the frontend owns process cleanup on failure/stop."""
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
                 if w.class_name.startswith("MainView_") and "火影忍者online" in w.window_name), None)

def prepare_window(hwnd):
    # 100% 缩放下该窗口外框与客户区一致，1920×1032 对应 Maa 截图 1340×720。
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
        raise RuntimeError("未找到 QQ 游戏大厅，请先安装并登录一次、保存登录状态。")
    if not uin:
        raise RuntimeError("需要填写自动登录 QQ 号才能启动游戏大厅。")
    # 必须在当前会话运行计划任务；普通 Run() 可能启动到主桌面。
    script = (
        "$s = New-Object -ComObject Schedule.Service; $s.Connect(); "
        "$sid = [Diagnostics.Process]::GetCurrentProcess().SessionId; "
        "$s.GetFolder('\\').GetTask('QQGame-SavedAccount').RunEx($env:MAANOP_UIN, 4, $sid, $null) | Out-Null"
    )
    subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                   env={**os.environ, "MAANOP_UIN": uin}, check=True)
    print("已启动游戏大厅，等待游戏窗口（最多 60 秒）。", flush=True)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        window = game_window(Toolkit.find_desktop_windows())
        if window:
            print("游戏窗口已出现。", flush=True)
            return window
        time.sleep(0.5)
    raise RuntimeError("60 秒内未出现游戏窗口。请检查大厅保存的登录状态、验证码或网络；本次停止，不自动重试。")

def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        if len(sys.argv) != 2:
            raise RuntimeError("需要前端提供一个选项 JSON 参数。")
        options = json.loads(sys.argv[1])
        uin = options["LoginAccount"]["uin"]
        if sys.platform != "win32":
            raise RuntimeError("QQ 游戏大厅仅支持 Windows。")
        executable = Path(options["GameHallPath"]["path"])
        window = launch(uin, executable)
        prepare_window(window.hwnd)
        return 0
    except (RuntimeError, OSError) as exc:
        print(f"启动游戏失败：{exc}", file=sys.stderr, flush=True)
        return 1

if __name__ == "__main__":
    sys.exit(main())
