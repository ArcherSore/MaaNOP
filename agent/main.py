import sys

from maa.agent.agent_server import AgentServer
from maa.toolkit import Toolkit
from maa.tasker import Tasker

import my_action
import my_reco


def main():
    Toolkit.init_option("./")

    if len(sys.argv) < 2:
        print("Usage: python main.py <socket_id>")
        print("socket_id is provided by AgentIdentifier.")
        sys.exit(1)
        
    socket_id = sys.argv[-1]

    Tasker.set_reco_image_cache_limit(0) # 禁用缓存

    AgentServer.start_up(socket_id)
    AgentServer.join()
    AgentServer.shut_down()


if __name__ == "__main__":
    main()
