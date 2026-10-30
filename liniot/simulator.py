"""设备模拟器：无需任何硬件即可完整体验 LinIoT。

虚拟设备清单：
- 温湿度传感器：温度/湿度随机游走，按 interval 上报遥测；
- 智能灯：带 power 属性，周期回报状态，轮询拉取命令并执行（模拟真实控制回路）。
"""
from __future__ import annotations

import random
import time
from typing import Any

import httpx

SENSOR_RANGE = {"temperature": (16.0, 32.0), "humidity": (30.0, 80.0)}
SENSOR_STEP = {"temperature": 0.4, "humidity": 1.2}


def sensor_points(state: dict[str, float], rng: random.Random,
                  now: float) -> list[dict[str, Any]]:
    """随机游走一步并返回两个遥测点。"""
    points = []
    for metric, (low, high) in SENSOR_RANGE.items():
        value = state[metric] + rng.gauss(0, SENSOR_STEP[metric])
        state[metric] = min(high, max(low, value))
        points.append({"metric": metric, "value": round(state[metric], 2), "ts": now})
    return points


def apply_command(payload: dict[str, Any]) -> dict[str, Any]:
    """执行一条下发命令，返回需要回报的属性补丁。"""
    prop, value = payload.get("property"), payload.get("value")
    if prop in ("power", "on", "brightness"):
        return {prop: value}
    return {}


class Simulator:
    def __init__(self, base_url: str = "http://127.0.0.1:8000", sensors: int = 2,
                 lights: int = 2, interval: float = 5.0, seed: int = 42,
                 duration: float = 0.0) -> None:
        self.http = httpx.Client(base_url=base_url.rstrip("/"), timeout=5)
        self.interval = interval
        self.duration = duration
        self.rng = random.Random(seed)
        self.sensor_state: dict[str, dict[str, float]] = {}
        self.devices: list[dict[str, str]] = []
        for i in range(1, sensors + 1):
            self.devices.append({"id": f"sensor-{i}", "name": f"温湿度传感器-{i}",
                                 "type": "sensor"})
        for i in range(1, lights + 1):
            self.devices.append({"id": f"light-{i}", "name": f"智能灯-{i}", "type": "light"})

    # ------------------------------------------------------------------ 启动

    def ensure_devices(self) -> None:
        for spec in self.devices:
            resp = self.http.post("/api/devices", json={
                "id": spec["id"], "name": spec["name"], "type": spec["type"],
                "meta": {"simulated": "true"}})
            resp.raise_for_status()
            if spec["type"] == "sensor":
                self.sensor_state[spec["id"]] = {"temperature": 22.0, "humidity": 55.0}
                self.http.post(f"/api/devices/{spec['id']}/status",
                               json={"status": "online", "properties": {}})
            else:
                self.http.post(f"/api/devices/{spec['id']}/status",
                               json={"status": "online", "properties": {"power": False}})
            print(f"[sim] 注册设备 {spec['id']}（{spec['name']}）")

    # ------------------------------------------------------------------ 主循环

    def run(self) -> None:
        self.ensure_devices()
        print(f"[sim] 开始模拟：{len(self.devices)} 台设备，"
              f"遥测周期 {self.interval}s（Ctrl+C 退出）")
        started = time.time()
        next_telemetry = next_poll = next_heartbeat = 0.0
        try:
            while True:
                now = time.time()
                if self.duration and now - started >= self.duration:
                    print("[sim] 达到演示时长，退出")
                    return
                if now >= next_telemetry:
                    self._push_telemetry()
                    next_telemetry = now + self.interval
                if now >= next_poll:
                    self._poll_commands()
                    next_poll = now + 2.0
                if now >= next_heartbeat:
                    self._heartbeat()
                    next_heartbeat = now + 15.0
                time.sleep(0.5)
        except KeyboardInterrupt:
            print("\n[sim] 已停止")

    def _push_telemetry(self) -> None:
        for device_id, state in self.sensor_state.items():
            points = sensor_points(state, self.rng, time.time())
            self.http.post(f"/api/devices/{device_id}/telemetry", json={"points": points})

    def _poll_commands(self) -> None:
        for spec in self.devices:
            if spec["type"] != "light":
                continue
            commands = self.http.get(f"/api/devices/{spec['id']}/commands").json()
            for command in commands:
                patch = apply_command(command["payload"])
                if patch:
                    self.http.post(f"/api/devices/{spec['id']}/status",
                                   json={"status": "online", "properties": patch})
                    print(f"[sim] {spec['id']} 执行命令: {command['payload']}")

    def _heartbeat(self) -> None:
        for spec in self.devices:
            self.http.post(f"/api/devices/{spec['id']}/status",
                           json={"status": "online", "properties": {}})
