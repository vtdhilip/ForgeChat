import time
import asyncio
from fastapi import APIRouter, Request, Depends
from fastapi.responses import StreamingResponse
from app.middleware.auth import get_current_user
from app.core.events import bus

router = APIRouter(prefix="/api", tags=["Events"])

@router.get("/events")
async def stream_events(request: Request, user: dict = Depends(get_current_user)):
    q = bus.subscribe()

    async def event_generator():
        try:
            now_ms = int(time.time() * 1000)
            yield f'event: hello\ndata: {{"ts":{now_ms},"userId":{user.get("id")}}}\n\n'
            while True:
                if await request.is_disconnected():
                    break
                try:
                    msg = await asyncio.wait_for(q.get(), timeout=25.0)
                    yield msg
                except asyncio.TimeoutError:
                    yield ": ka\n\n"
        finally:
            bus.unsubscribe(q)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
