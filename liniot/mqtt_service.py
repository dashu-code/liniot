"""MQTT 接入服务：订阅设备上行主题，转发到设备服务；命令经 MQTT 下发。

使用 paho-mqtt 2.x 回调 API，在独立线程中维护连接，断线自动重连。
未配置 Broker（LINIOT_MQTT_HOST 为空）时服务不启动，平台仍可通过
HTTP 通道完整工作。
"""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

import paho.mqtt.client as mqtt

from .config import MQTTConfig

logger = logging.getLogger("liniot.mqtt")

TOPIC_PREFIX = "liniot"
TELEMETRY_SUFFIX = "telemetry"
STATUS_SUFFIX = "status"
COMMAND_SUFFIX = "command"


def parse_topic(topic: str) -> tuple[str, str] | None:
    """解析 'liniot/{device_id}/{kind}'，返回 (device_id, kind)。"""
    parts = topic.split("/")
    if len(parts) == 3 and parts[0] == TOPIC_PREFIX:
        return parts[1], parts[2]
    return None


class MQTTService:
    def __init__(self, config: MQTTConfig, service) -> None:
        self.config = config
        self.service = service  # DeviceService
        self.client: mqtt.Client | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # ---------------------------------------------------------------- 生命周期

    def start(self) -> None:
        if not self.config.enabled or self._thread is not None:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="liniot-mqtt", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self.client is not None:
            try:
                self.client.disconnect()
            except Exception:
                pass

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._connect()
                return  # 连接成功后由 paho 网络线程接管并自动重连
            except Exception as exc:
                logger.warning("MQTT 连接失败(%s)，5 秒后重试: %s", self.config.host, exc)
                self._stop.wait(5)

    def _connect(self) -> None:
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="liniot-server")
        if self.config.username:
            client.username_pw_set(self.config.username, self.config.password)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        client.connect(self.config.host, self.config.port, keepalive=60)
        client.loop_start()
        self.client = client

    def _on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        logger.info("已连接 MQTT Broker %s:%s", self.config.host, self.config.port)
        client.subscribe([(f"{TOPIC_PREFIX}/+/{TELEMETRY_SUFFIX}", 0),
                          (f"{TOPIC_PREFIX}/+/{STATUS_SUFFIX}", 0)])

    def _on_message(self, client, userdata, msg) -> None:
        topic = parse_topic(msg.topic)
        if topic is None:
            return
        device_id, kind = topic
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            logger.warning("非法 MQTT 消息 %s: %r", msg.topic, msg.payload[:120])
            return
        try:
            if kind == TELEMETRY_SUFFIX:
                self.handle_telemetry_payload(device_id, payload)
            elif kind == STATUS_SUFFIX:
                self.service.set_status(device_id, payload.get("status", "online"),
                                        payload.get("properties"))
        except Exception:
            logger.exception("处理 MQTT 消息失败: %s", msg.topic)

    # ---------------------------------------------------------------- 消息解析

    def handle_telemetry_payload(self, device_id: str, payload: dict[str, Any]) -> int:
        """兼容两种上报格式：单点 {metric,value} 与批量 {points:[...]}。"""
        points = payload.get("points")
        if points is None:
            points = [{k: v for k, v in payload.items()
                       if k in ("metric", "value", "ts")}]
        return self.service.ingest(device_id, points, source="mqtt")

    def publish_command(self, device_id: str, payload: dict[str, Any]) -> None:
        if self.client is None:
            return
        self.client.publish(
            f"{TOPIC_PREFIX}/{device_id}/{COMMAND_SUFFIX}",
            json.dumps(payload, ensure_ascii=False), qos=0,
        )
