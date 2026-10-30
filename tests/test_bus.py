"""事件总线测试。"""
from __future__ import annotations

import asyncio

from liniot.bus import EventBus


def test_publish_without_loop_is_noop():
    bus = EventBus()
    bus.publish({"type": "test"})  # 不应抛异常


def test_subscribe_receive_and_unsubscribe():
    bus = EventBus()
    received = []

    async def main():
        bus.attach_loop(asyncio.get_running_loop())
        queue = bus.subscribe()
        bus.publish({"type": "telemetry", "data": [1, 2]})
        message = await asyncio.wait_for(queue.get(), timeout=1)
        received.append(message)
        bus.unsubscribe(queue)
        bus.publish({"type": "after"})  # 已取消订阅，不会收到

    asyncio.run(main())
    assert received == [{"type": "telemetry", "data": [1, 2]}]


def test_slow_subscriber_drops_oldest():
    bus = EventBus()

    async def main():
        bus.attach_loop(asyncio.get_running_loop())
        queue = bus.subscribe()
        for i in range(600):  # 超过 maxsize=500
            bus.publish({"i": i})
        await asyncio.sleep(0.1)
        assert not queue.empty()
        # 队列应保留最新的一部分消息而非阻塞发布方
        last = None
        while not queue.empty():
            last = queue.get_nowait()
        assert last is not None and last["i"] >= 500

    asyncio.run(main())
