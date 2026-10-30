"""模拟器纯逻辑测试。"""
from __future__ import annotations

import random

from liniot.simulator import apply_command, sensor_points


def test_sensor_points_random_walk_within_bounds():
    rng = random.Random(7)
    state = {"temperature": 22.0, "humidity": 55.0}
    metrics = set()
    for _ in range(200):
        points = sensor_points(state, rng, 0.0)
        assert len(points) == 2
        for point in points:
            metrics.add(point["metric"])
    assert metrics == {"temperature", "humidity"}
    assert 16 <= state["temperature"] <= 32
    assert 30 <= state["humidity"] <= 80


def test_apply_command_supported_properties():
    assert apply_command({"property": "power", "value": True}) == {"power": True}
    assert apply_command({"property": "brightness", "value": 80}) == {"brightness": 80}
    assert apply_command({"property": "reboot", "value": 1}) == {}  # 未知属性忽略
    assert apply_command({}) == {}
