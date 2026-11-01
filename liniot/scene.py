"""场景联动引擎：当 [设备指标满足条件] 则 [对另一设备执行属性动作]。

与规则引擎共用上升沿判定思路，但动作不是告警而是控制命令；
通过 cooldown 冷却窗口防止传感器抖动导致命令来回震荡
（例如「温度>28 开灯 / 温度<28 关灯」被同一批数据反复触发）。
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from .rules import OPS

logger = logging.getLogger("liniot.scene")


class SceneEngine:
    def __init__(self, store, service) -> None:
        self.store = store
        self.service = service  # DeviceService，由 create_app 装配
        # 冷却期内不重复评估的记录：scene_id -> 处于触发态
        self._active: dict[int, bool] = {}
    def evaluate(self, device_id: str, points: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """处理一批遥测点，执行被触发的场景动作，返回触发记录。"""
        fired: list[dict[str, Any]] = []
        scenes = self.store.list_scenes(only_enabled=True)
        if not scenes:
            return fired
        now = time.time()
        for scene in scenes:
            if scene["source_device_id"] and scene["source_device_id"] != device_id:
                continue
            judge = OPS.get(scene["op"])
            if judge is None:
                continue
            matched = [p for p in points if p["metric"] == scene["metric"]]
            if not matched:
                continue
            triggered = judge(matched[-1]["value"], scene["threshold"])
            was_active = self._active.get(scene["id"], False)
            if not triggered:
                self._active[scene["id"]] = False
                continue
            # 条件持续满足时受冷却窗口限制，不重复执行动作
            if was_active or now - scene["last_fired"] < scene["cooldown"]:
                self._active[scene["id"]] = True
                continue
            record = self._fire(scene, matched[-1]["value"], now)
            if record is not None:
                fired.append(record)
        return fired

    def _fire(self, scene: dict[str, Any], value: float, now: float) -> dict[str, Any] | None:
        # 目标设备可能已被删除：跳过执行但置触发态，避免每批数据重复报错
        if self.service.store.get_device(scene["action_device_id"]) is None:
            logger.warning("场景 %s 的目标设备 %s 不存在，跳过执行",
                           scene["name"], scene["action_device_id"])
            self._active[scene["id"]] = True
            return None
        try:
            action_value = json.loads(scene["action_value"])
        except json.JSONDecodeError:
            action_value = scene["action_value"]
        self.store.touch_scene(scene["id"], now)
        self._active[scene["id"]] = True
        commands = self.service.set_properties(
            scene["action_device_id"], {scene["action_property"]: action_value})
        record = {
            "scene_id": scene["id"], "name": scene["name"],
            "source_device_id": scene["source_device_id"],
            "metric": scene["metric"], "value": value,
            "action_device_id": scene["action_device_id"],
            "action_property": scene["action_property"],
            "action_value": action_value,
            "commands": commands, "ts": now,
        }
        self.service.bus.publish({"type": "scene_fired", "data": record})
        logger.info("场景触发: %s（%s=%s）", scene["name"], scene["metric"], value)
        return record

    def forget(self, device_id: str) -> None:
        for key in [k for k in self._active]:
            scene = self.store.get_scene(key)
            if scene and (scene["source_device_id"] == device_id
                          or scene["action_device_id"] == device_id):
                self._active.pop(key, None)
