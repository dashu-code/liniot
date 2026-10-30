"""设备服务与命令回路测试。"""
from __future__ import annotations

import pytest

from liniot.bus import EventBus
from liniot.rules import RuleEngine
from liniot.service import DeviceService, UnknownDevice
from liniot.store import Store


@pytest.fixture()
def service(tmp_path):
    store = Store(tmp_path / "s.db")
    return DeviceService(store, EventBus(), RuleEngine(store, EventBus()))


def test_register_generates_id_and_is_idempotent(service):
    device, created = service.register("客厅温湿度传感器", "sensor")
    assert created is True
    assert device["id"].startswith("device-")  # 中文无法转 slug 时的兜底前缀

    same, created_again = service.register("改名", "sensor", device_id=device["id"])
    assert created_again is False


def test_ingest_unknown_device(service):
    with pytest.raises(UnknownDevice):
        service.ingest("ghost", [{"metric": "temperature", "value": 1}])


def test_ingest_filters_invalid_points(service):
    service.register("传感器", "sensor", device_id="sensor-1")
    count = service.ingest("sensor-1", [
        {"metric": "temperature", "value": 25},
        {"metric": "bad metric!", "value": 1},   # 非法 metric 被过滤
        {"metric": "humidity", "value": None},   # 缺 value 被过滤
    ])
    assert count == 1
    assert service.store.metrics_of("sensor-1") == ["temperature"]


def test_command_roundtrip(service):
    service.register("智能灯", "light", device_id="light-1")
    service.set_status("light-1", "online", {"power": False})

    commands = service.set_properties("light-1", {"power": True})
    assert len(commands) == 1
    assert commands[0]["payload"] == {"property": "power", "value": True}

    # 设备轮询取走命令并回报状态（模拟真实控制回路）
    pending = service.poll_commands("light-1")
    assert pending[0]["payload"]["value"] is True
    assert service.poll_commands("light-1") == []
    service.set_status("light-1", "online", {"power": True})
    assert service.store.get_device("light-1")["properties"]["power"] is True


def test_view_online_status(service):
    service.register("传感器", "sensor", device_id="sensor-1")
    device = service.store.get_device("sensor-1")
    assert service.view(device)["online"] is False  # 从未上报
    service.set_status("sensor-1", "online")
    assert service.view(service.store.get_device("sensor-1"))["online"] is True


def test_overview(service):
    service.register("传感器", "sensor", device_id="sensor-1")
    service.ingest("sensor-1", [{"metric": "temperature", "value": 25}])
    overview = service.overview()
    assert overview["devices"] == 1
    assert overview["online"] == 1
    assert overview["telemetry_points"] == 1
