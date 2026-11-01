"""API 集成测试：REST 端点 + WebSocket。"""
from __future__ import annotations


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_device_crud_and_telemetry_flow(client):
    resp = client.post("/api/devices", json={"id": "sensor-1", "name": "客厅传感器",
                                             "type": "sensor"})
    assert resp.status_code == 201

    # 幂等注册返回 200
    again = client.post("/api/devices", json={"id": "sensor-1", "name": "客厅传感器",
                                              "type": "sensor"})
    assert again.status_code == 200

    batch = {"points": [{"metric": "temperature", "value": 25.5},
                        {"metric": "humidity", "value": 60}]}
    assert client.post("/api/devices/sensor-1/telemetry", json=batch).json()["accepted"] == 2

    series = client.get("/api/devices/sensor-1/telemetry",
                        params={"metric": "temperature"}).json()
    assert len(series) == 1 and series[0]["value"] == 25.5

    detail = client.get("/api/devices/sensor-1").json()
    assert detail["online"] is True  # 刚上报过数据

    assert client.delete("/api/devices/sensor-1").status_code == 200
    assert client.get("/api/devices/sensor-1").status_code == 404


def test_telemetry_single_point_compat(client):
    client.post("/api/devices", json={"id": "sensor-1", "name": "s", "type": "sensor"})
    resp = client.post("/api/devices/sensor-1/telemetry",
                       json={"metric": "temperature", "value": 21})
    assert resp.json()["accepted"] == 1


def test_rules_crud_and_alert_via_api(client):
    client.post("/api/devices", json={"id": "sensor-1", "name": "s", "type": "sensor"})
    rule = client.post("/api/rules", json={"device_id": "sensor-1", "metric": "temperature",
                                           "op": ">", "threshold": 30}).json()
    assert rule["id"] > 0

    client.post("/api/devices/sensor-1/telemetry",
                json={"metric": "temperature", "value": 35})
    alerts = client.get("/api/alerts").json()
    assert len(alerts) == 1 and "35" in alerts[0]["message"]

    assert client.patch(f"/api/rules/{rule['id']}", json={"enabled": False}).json()["enabled"] == 0
    assert client.delete(f"/api/rules/{rule['id']}").status_code == 200


def test_properties_command_flow(client):
    client.post("/api/devices", json={"id": "light-1", "name": "灯", "type": "light"})
    client.post("/api/devices/light-1/status",
                json={"status": "online", "properties": {"power": False}})

    queued = client.post("/api/devices/light-1/properties",
                         json={"properties": {"power": True}}).json()["queued"]
    assert queued[0]["payload"] == {"property": "power", "value": True}

    commands = client.get("/api/devices/light-1/commands").json()
    assert commands[0]["payload"]["value"] is True
    assert client.get("/api/devices/light-1/commands").json() == []


def test_websocket_hello(client):
    with client.websocket_connect("/ws") as ws:
        hello = ws.receive_json()
    assert hello["type"] == "hello"
    assert hello["data"]["overview"]["devices"] == 0


def test_overview(client):
    client.post("/api/devices", json={"id": "sensor-1", "name": "s", "type": "sensor"})
    client.post("/api/devices/sensor-1/telemetry",
                json={"metric": "temperature", "value": 20})
    overview = client.get("/api/overview").json()
    assert overview == {"devices": 1, "online": 1, "telemetry_points": 1,
                        "alerts_24h": 0, "rules": 0}


def test_ai_chat_endpoint_local_mode(client):
    client.post("/api/devices", json={"id": "light-1", "name": "智能灯", "type": "light"})
    client.post("/api/devices/light-1/status",
                json={"status": "online", "properties": {"power": False}})

    result = client.post("/api/ai/chat", json={"message": "打开所有的灯"}).json()
    assert result["mode"] == "local"
    assert "智能灯" in result["reply"]
    assert client.get("/api/devices/light-1/commands").json()[0]["payload"]["value"] is True


def test_scenes_crud_and_trigger(client):
    client.post("/api/devices", json={"id": "sensor-1", "name": "s", "type": "sensor"})
    client.post("/api/devices", json={"id": "light-1", "name": "灯", "type": "light"})
    client.post("/api/devices/light-1/status",
                json={"status": "online", "properties": {"power": False}})

    scene = client.post("/api/scenes", json={
        "name": "高温开灯", "metric": "temperature", "op": ">", "threshold": 28,
        "action_device_id": "light-1", "action_property": "power",
        "action_value": True, "cooldown": 60}).json()
    assert scene["id"] > 0 and scene["enabled"] == 1

    client.post("/api/devices/sensor-1/telemetry",
                json={"metric": "temperature", "value": 30})
    commands = client.get("/api/devices/light-1/commands").json()
    assert commands[0]["payload"] == {"property": "power", "value": True}

    # 冷却窗口内不重复下发
    client.post("/api/devices/sensor-1/telemetry",
                json={"metric": "temperature", "value": 31})
    assert client.get("/api/devices/light-1/commands").json() == []

    assert client.patch(f"/api/scenes/{scene['id']}",
                        json={"enabled": False}).json()["enabled"] == 0
    assert client.delete(f"/api/scenes/{scene['id']}").status_code == 200
    assert client.get("/api/scenes").json() == []


def test_scene_rejects_unknown_devices(client):
    resp = client.post("/api/scenes", json={
        "name": "x", "metric": "temperature", "op": ">", "threshold": 1,
        "action_device_id": "ghost", "action_property": "power", "action_value": True})
    assert resp.status_code == 404


def test_validation_errors(client):
    assert client.post("/api/devices", json={"name": "", "type": "x"}).status_code == 422
    assert client.post("/api/devices", json={"id": "非法ID", "name": "x"}).status_code == 422
    assert client.get("/api/devices/ghost/telemetry").status_code == 404
