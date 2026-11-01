"""场景联动引擎测试。"""
from __future__ import annotations

from liniot.bus import EventBus
from liniot.rules import RuleEngine
from liniot.scene import SceneEngine
from liniot.service import DeviceService
from liniot.store import Store


def make(tmp_path):
    store = Store(tmp_path / "scene.db")
    service = DeviceService(store, EventBus(), RuleEngine(store, EventBus()))
    engine = SceneEngine(store, service)
    service.scene_engine = engine
    store.upsert_device("sensor-1", "传感器", "sensor", {})
    store.upsert_device("sensor-2", "传感器2", "sensor", {})
    store.upsert_device("light-1", "灯", "light", {})
    service.set_status("light-1", "online", {"power": False})
    return store, service, engine


def test_scene_triggers_and_queues_command(tmp_path):
    store, _, engine = make(tmp_path)
    store.create_scene("高温开灯", None, "temperature", ">", 28,
                       "light-1", "power", "true", 60)

    fired = engine.evaluate("sensor-1", [{"metric": "temperature", "value": 30}])
    assert len(fired) == 1
    assert fired[0]["action_device_id"] == "light-1"
    assert fired[0]["action_value"] is True
    commands = store.pending_commands("light-1")
    assert commands[0]["payload"] == {"property": "power", "value": True}

    # 冷却窗口内持续满足条件：不重复执行
    assert engine.evaluate("sensor-1", [{"metric": "temperature", "value": 31}]) == []
    assert store.pending_commands("light-1") == []


def test_scene_respects_source_device_scope(tmp_path):
    store, _, engine = make(tmp_path)
    store.create_scene("仅传感器1", "sensor-1", "temperature", ">", 28,
                       "light-1", "power", "true", 60)
    assert engine.evaluate("sensor-2", [{"metric": "temperature", "value": 35}]) == []
    assert store.pending_commands("light-1") == []


def test_scene_disabled_not_evaluated(tmp_path):
    store, _, engine = make(tmp_path)
    scene = store.create_scene("高温开灯", None, "temperature", ">", 28,
                               "light-1", "power", "true", 60)
    store.update_scene(scene["id"], enabled=False)
    assert engine.evaluate("sensor-1", [{"metric": "temperature", "value": 35}]) == []


def test_scene_missing_action_device_skips_safely(tmp_path):
    store, _, engine = make(tmp_path)
    store.create_scene("目标丢失", None, "temperature", ">", 28,
                       "ghost", "power", "true", 60)
    assert engine.evaluate("sensor-1", [{"metric": "temperature", "value": 35}]) == []


def test_scene_cooldown_expiry_and_crud(tmp_path):
    store, _, engine = make(tmp_path)
    scene = store.create_scene("高温开灯", None, "temperature", ">", 28,
                               "light-1", "power", "true", cooldown=1)
    assert engine.evaluate("sensor-1", [{"metric": "temperature", "value": 30}]) != []
    assert engine.evaluate("sensor-1", [{"metric": "temperature", "value": 30}]) == []
    assert store.get_scene(scene["id"])["last_fired"] > 0

    store.update_scene(scene["id"], threshold=100)
    assert store.get_scene(scene["id"])["threshold"] == 100
    store.delete_scene(scene["id"])
    assert store.list_scenes() == []
