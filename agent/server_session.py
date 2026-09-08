from dataclasses import dataclass
from threading import Lock
from typing import Optional


def parse_server_range_string(server_range_str: str) -> list[int]:
    server_list: list[int] = []
    for range_part in (server_range_str or "").split(","):
        range_part = range_part.strip().strip('"')
        if not range_part:
            continue
        if "-" in range_part:
            start, end = map(int, range_part.split("-", 1))
            server_list.extend(range(start, end + 1))
        else:
            server_list.append(int(range_part))
    return server_list


@dataclass
class ServerSession:
    server_list: list[int]
    region_type: str = "public"
    next_index: int = 0
    finished: bool = False


_sessions: dict[int, ServerSession] = {}
_lock = Lock()


def initialize_server_session(
    task_id: int,
    server_list: list[int],
    region_type: str = "public",
) -> ServerSession:
    with _lock:
        session = ServerSession(server_list=list(server_list), region_type=region_type)
        _sessions[int(task_id)] = session
        return session


def get_server_session(task_id: int) -> Optional[ServerSession]:
    with _lock:
        return _sessions.get(int(task_id))


def take_next_server(task_id: int) -> Optional[dict]:
    with _lock:
        session = _sessions.get(int(task_id))
        if session is None:
            return None
        server_list = list(session.server_list)
        server_cnt = len(server_list)
        if session.next_index >= server_cnt:
            session.finished = True
            return {
                "server_list": server_list,
                "region_type": session.region_type,
                "server_index": session.next_index,
                "server_cnt": server_cnt,
                "finished": True,
            }
        server_id = server_list[session.next_index]
        session.next_index += 1
        session.finished = False
        return {
            "server_list": server_list,
            "region_type": session.region_type,
            "server_id": server_id,
            "server_index": session.next_index,
            "server_cnt": server_cnt,
            "finished": False,
        }


def is_server_session_finished(task_id: int) -> bool:
    with _lock:
        session = _sessions.get(int(task_id))
        if session is None:
            return False
        return session.finished


def clear_server_session(task_id: int) -> None:
    with _lock:
        _sessions.pop(int(task_id), None)
