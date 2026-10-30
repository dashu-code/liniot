"""存储层测试。"""
from __future__ import annotations

from liniot.store import Store


def test_device_upsert_and_get(tmp_path):
    store = Store(tmp_path / "a.db")
    device, created = store.upsert_device("sensor-1", "温湿度传感器", "sensor", {"room": "客厅"})
    assert created is True
    assert device["id"] == "sensor-1"
    assert device["meta"] == {"room": "客厅"}
    assert device["status"] == "offline"

    _, created_again = store.upsert_device("sensor-1", "改名传感器", "sensor", {})
    assert created_again is False
    assert store.get_device("sensor-1")["name"] == "改名传感器"
    assert store.get_device("missing") is None


def test_status_merge_properties(tmp_path):
    store = Store(tmp_path / "a.db")
    store.upsert_device("light-1", "智能灯", "light", {})
    store.set_status("light-1", "online", {"power": False})
    store.set_status("light-1", "online", {"brightness": 80})  # 增量合并而非覆盖
    device = store.get_device("light-1")
    assert device["properties"] == {"power": False, "brightness": 80}
    assert device["status"] == "online"
    assert device["last_seen"] > 0


def test_telemetry_query_and_retention(tmp_path):
    store = Store(tmp_path / "a.db")
    store.upsert_device("sensor-1", "传感器", "sensor", {})
    points = [{"metric": "temperature", "value": 20 + i, "ts": 1000.0 + i}
              for i in range(30)]
    store.insert_telemetry("sensor-1", points)

    series = store.query_telemetry("sensor-1", "temperature", limit=200)
    assert len(series) == 30
    assert series[0]["value"] == 20  # 时间升序
    assert series[-1]["value"] == 49

    latest = store.latest_metrics()
    assert latest[("sensor-1", "temperature")]["value"] == 49

    store.prune(10)
    assert store.count_telemetry() == 10
    assert store.query_telemetry("sensor-1")[-1]["value"] == 49  # 保留最新


def test_commands_queue_and_deliver(tmp_path):
    store = Store(tmp_path / "a.db")
    store.upsert_device("light-1", "智能灯", "light", {})
    command = store.queue_command("light-1", {"property": "power", "value": True})
    assert command["payload"]["value"] is True

    pending = store.pending_commands("light-1")
    assert len(pending) == 1
    assert pending[0]["payload"] == {"property": "power", "value": True}
    assert store.pending_commands("light-1") == []  # 取走后不再返回
