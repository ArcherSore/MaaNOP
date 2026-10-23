"""Start the official microclient; the frontend owns process cleanup on failure/stop."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


class LaunchError(Exception):
    pass


def parse_uin(argument):
    try:
        uin = json.loads(argument)["LoginAccount"]["uin"]
    except (ValueError, KeyError, TypeError) as exc:
        raise LaunchError("缺少 LoginAccount.uin 参数。") from exc
    if not isinstance(uin, str) or (uin and not re.fullmatch(r"[1-9][0-9]{4,11}", uin)):
        raise LaunchError("QQ 号必须是 5～12 位数字，或留空使用手动登录。")
    return uin


def game_window(windows):
    return any(w.class_name.startswith("MainView_") and "火影忍者Online" in w.window_name
               for w in windows)


def launch(uin, executable):
    from maa.toolkit import Toolkit

    # Toolkit enumerates the caller's desktop, so the main desktop's game is not reused.
    if game_window(Toolkit.find_desktop_windows()):
        if uin:
            raise LaunchError("游戏已运行，无法确认当前 QQ 账号。请先关闭分身中的微端，再指定 QQ 号启动。")
        print("游戏窗口已存在，沿用当前账号。", flush=True)
        return
    if not executable.is_file():
        raise LaunchError("未找到官方微端，请先安装并手动登录一次、勾选记住密码。")
    args = [str(executable), "-/appid:1103286479"]
    if uin:
        args.append(f"-loginuin:{uin}")
    subprocess.Popen(args, cwd=str(executable.parent))
    print("已启动微端，等待游戏窗口（最多 60 秒）。", flush=True)
    deadline = time.monotonic() + 60
    while time.monotonic() < deadline:
        if game_window(Toolkit.find_desktop_windows()):
            print("游戏窗口已出现；网页内二次登录仍需手动完成。", flush=True)
            return
        time.sleep(0.5)
    raise LaunchError("60 秒内未出现游戏窗口。请检查保存密码、验证码或网络；本次停止，不自动重试。")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        if len(sys.argv) != 2:
            raise LaunchError("需要前端提供一个选项 JSON 参数。")
        uin = parse_uin(sys.argv[1])
        if sys.platform != "win32":
            raise LaunchError("官方微端仅支持 Windows。")
        appdata = os.environ.get("APPDATA")
        if not appdata:
            raise LaunchError("无法获取当前用户的 APPDATA 目录。")
        executable = Path(appdata) / "Tencent" / "QQMicroGameBox" / "Launch.exe"
        launch(uin, executable)
        return 0
    except (LaunchError, OSError) as exc:
        print(f"启动游戏失败：{exc}", file=sys.stderr, flush=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
