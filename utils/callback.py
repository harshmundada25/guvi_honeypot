import threading
from typing import Dict, Optional

import requests

_sent_sessions: set[str] = set()


def _post_callback(url: str, payload: Dict) -> None:
    try:
        resp = requests.post(url, json=payload, timeout=5)
        print(f"[CALLBACK] Status {resp.status_code}")
    except Exception as exc:
        print(f"[CALLBACK] Failed: {exc}")


def send_callback_async(url: str, payload: Dict, session_id: Optional[str] = None) -> bool:
    """Send callback without blocking the main request."""
    sid = session_id or payload.get("sessionId")
    if sid and sid in _sent_sessions:
        return False
    if sid:
        _sent_sessions.add(sid)

    thread = threading.Thread(target=_post_callback, args=(url, payload), daemon=True)
    thread.start()
    return True

