"""MQTT 服务消息解析测试（无需真实 Broker）。"""
from __future__ import annotations

from liniot.bus import EventBus
from liniot.config import MQTTConfig
from liniot.mqtt_service import MQTTService, parse_topic
from liniot.rules import RuleEngine
from liniot.service import DeviceService
from liniot.store import Store


def test_parse_topic():
    assert parse_topic("liniot/sensor-1/telemetry") == ("sensor-1", "telemetry")
    assert parse_topic("liniot/light-1/status") == ("light-1", "status")
    assert parse_topic("other/sensor-1/telemetry") is None
    assert parse_topic("liniot/sensor-1") is None


def make_service(tmp_path):
    store = Store(tmp_path / "m.db")
    service = DeviceService(store, EventBus(), RuleEngine(store, EventBus()))
    service.register("传感器", "sensor", device_id="sensor-1")
    return service


def make_mqtt(tmp_path):
    service = make_service(tmp_path)
    return MQTTService(MQTTConfig(host="localhost"), service), service


def test_handle_telemetry_payload_single_and_batch(tmp_path):
    mqtt, service = make_mqtt(tmp_path)

    assert mqtt.handle_telemetry_payload("sensor-1",
                                         {"metric": "temperature", "value": 25}) == 1
    assert mqtt.handle_telemetry_payload(
        "sensor-1", {"points": [{"metric": "humidity", "value": 55},
                                {"metric": "co2", "value": 420}]}) == 2

    metrics = set(service.store.metrics_of("sensor-1"))
    assert metrics == {"temperature", "humidity", "co2"}


def test_on_message_routes_status(tmp_path, monkeypatch):
    mqtt, service = make_mqtt(tmp_path)

    class Msg:
        topic = "liniot/sensor-1/status"
        payload = b'{"status":"online","properties":{"battery":88}}'

    mqtt._on_message(None, None, Msg())
    device = service.store.get_device("sensor-1")
    assert device["status"] == "online"
    assert device["properties"]["battery"] == 88


def test_on_message_ignores_bad_json(tmp_path):
    mqtt, _ = make_mqtt(tmp_path)

    class Msg:
        topic = "liniot/sensor-1/telemetry"
        payload = b"not-json{{"

    mqtt._on_message(None, None, Msg())  # 不应抛异常


def test_publish_command_without_client_is_safe(tmp_path):
    mqtt, _ = make_mqtt(tmp_path)
    mqtt.publish_command("sensor-1", {"property": "power", "value": True})  # client 未连接
