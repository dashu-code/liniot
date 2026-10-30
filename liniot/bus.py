"""进程内事件总线：把后端事件（遥测/告警/设备状态）实时推给 WebSocket 订阅者。

MQTT 线程、FastAPI 线程池都可能调用 publish()，因此通过
loop.call_soon_threadsafe 把消息安全地投递到 asyncio 事件循环。
"""
from __future__ import annotations

import asyncio
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subscribers: set[asyncio.Queue] = set()

    def attach_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    def publish(self, message: dict[str, Any]) -> None:
        """线程安全地广播一条消息；无事件循环（如测试环境）时静默丢弃。"""
        loop = self._loop
        if loop is None:
            return

        def _emit() -> None:
            for queue in list(self._subscribers):
                try:
                    queue.put_nowait(message)
                except asyncio.QueueFull:
                    # 订阅者消费过慢则丢弃最旧消息，保证发布方不阻塞
                    try:
                        queue.get_nowait()
                        queue.put_nowait(message)
                    except Exception:
                        pass

        loop.call_soon_threadsafe(_emit)
