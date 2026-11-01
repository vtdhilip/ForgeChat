import asyncio
import json
from typing import Set, Dict, Any

class EventBus:
    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        self._subscribers.discard(q)

    async def emit(self, event: str, data: Any):
        if not self._subscribers:
            return
        msg = f"event: {event}\ndata: {json.dumps(data)}\n\n"
        for q in list(self._subscribers):
            try:
                q.put_nowait(msg)
            except Exception:
                pass

bus = EventBus()
