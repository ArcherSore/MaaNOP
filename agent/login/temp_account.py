"""登录小号：多开对话框是大厅的另一个窗口，交给独立进程 temp_dialog.py 选号。"""
import subprocess
import sys
import time
from pathlib import Path

from maa.agent.agent_server import AgentServer
from maa.custom_action import CustomAction

from common.utils import send_focus_message


@AgentServer.custom_action("TempAccountSelect")
class TempAccountSelect(CustomAction):
    def run(self, context, argv):
        uin = context.get_node_data(argv.node_name)["attach"]["uin"]
        print(f"登录小号：在多开窗口选择 QQ {uin}")
        started = time.monotonic()
        process = subprocess.Popen(
            [sys.executable, str(Path(__file__).with_name("temp_dialog.py")), uin],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8",
        )
        while process.poll() is None:
            if context.tasker.stopping:
                process.kill()
                print("登录小号：收到停止，已结束选号进程")
                return False
            time.sleep(0.2)
        # 选号进程的输出同时包含它的失败原因和未捕获异常的堆栈。
        print(process.stdout.read().strip())
        print(f"登录小号：选号进程退出码 {process.returncode}（0 已点击，3 列表里没有，其他失败），用时 {time.monotonic() - started:.1f} 秒")
        if process.returncode == 3:
            send_focus_message(context, f"多开列表里没有 QQ {uin}")
        return process.returncode == 0
