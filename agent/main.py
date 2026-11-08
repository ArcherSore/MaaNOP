import sys

from maa.agent.agent_server import AgentServer
from maa.tasker import Tasker

from common import action_common, action_entry, reco_common
from login import action_login, reco_login, temp_account
from alt_accounts.shopping_festival import action_shopping, reco_shopping
from alt_accounts.task_merchant import core, navigation
from routine import action_survival, action_training, reco_auto_management, reco_escort, reco_ranked, reco_summon, reco_training
from events import action_mid_autumn, action_ninjutsu_training
from events.weekend import action_puzzle


def main():
    Tasker.set_log_dir("./debug")
    Tasker.set_save_on_error(True)

    if len(sys.argv) < 2:
        print("Usage: python main.py <socket_id>")
        print("socket_id is provided by AgentIdentifier.")
        sys.exit(1)
        
    socket_id = sys.argv[-1]

    AgentServer.start_up(socket_id)
    AgentServer.join()
    AgentServer.shut_down()


if __name__ == "__main__":
    main()
