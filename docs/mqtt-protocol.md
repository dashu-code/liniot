# MQTT 接入协议

LinIoT 服务端订阅上行主题并向设备下发命令。任何支持 MQTT 3.1.1/5.0 的客户端
（ESP32 PubSubClient、paho-mqtt、mosquitto_pub 等）均可直接接入。

## 主题约定

| 方向 | 主题 | 说明 |
|---|---|---|
| 设备 → 平台 | `liniot/{device_id}/telemetry` | 遥测上报 |
| 设备 → 平台 | `liniot/{device_id}/status` | 状态/属性回报、心跳 |
| 平台 → 设备 | `liniot/{device_id}/command` | 属性烧写命令 |

`device_id` 规则同 HTTP：`^[a-z0-9][a-z0-9_-]{0,63}$`。

## 遥测上报

单点：

```json
{"metric": "temperature", "value": 25.3}
```

批量（推荐，一次上报多个指标）：

```json
{"points": [
  {"metric": "temperature", "value": 25.3},
  {"metric": "humidity", "value": 61.0, "ts": 1793353000.1}
]}
```

- `value` 必须为数值；`ts` 为 Unix 秒，省略取服务器时间。
- 首次上报的 `device_id` 需已注册（HTTP `POST /api/devices` 或仿真器注册）；
  未注册的设备数据会被拒绝并记录日志。
- QoS 0/1 均可，建议 0（秒级遥测无需重传语义）。

## 状态与心跳

```json
{"status": "online", "properties": {"battery": 88}}
```

`properties` 为增量合并。定时（如 30 秒）发一次即可维持在线；超过
`LINIOT_ONLINE_TIMEOUT` 秒无任何上行，仪表盘显示离线。

**推荐用 MQTT 遗嘱消息实现秒级下线感知**：连接时设置

- Will Topic：`liniot/{device_id}/status`
- Will Payload：`{"status": "offline"}`

设备异常断开时 Broker 代发遗嘱，平台立即标记离线。

## 命令下发

平台向 `liniot/{device_id}/command` 发布（QoS 0）：

```json
{"property": "power", "value": true}
```

设备收到后执行，并**必须**向 `liniot/{device_id}/status` 回报新属性，
完成控制闭环（仪表盘与 AI 下发的命令都走此通道/或 HTTP 轮询）。
未启用 MQTT 时，设备可通过 `GET /api/devices/{id}/commands` 轮询拉取，二选一。

## 端到端示例（mosquitto 客户端）

```bash
# 注册设备
curl -X POST http://127.0.0.1:8000/api/devices \
  -H 'Content-Type: application/json' \
  -d '{"id":"plug-1","name":"智能插座","type":"switch"}'

# 上报遥测
mosquitto_pub -h localhost -t liniot/plug-1/telemetry \
  -m '{"points":[{"metric":"power","value":45.2},{"metric":"voltage","value":220.1}]}'

# 上线 + 属性
mosquitto_pub -h localhost -t liniot/plug-1/status \
  -m '{"status":"online","properties":{"relay":false}}'

# 下发命令（另开终端可观察）
mosquitto_pub -h localhost -t liniot/plug-1/command -m '{"property":"relay","value":true}'
```

## 服务端行为细节

- 非法 JSON、非法主题、未知设备：记 WARNING 日志并丢弃，不影响连接。
- 服务端断线自动重连（1s → 30s 退避），重连后自动重新订阅。
- 命令双写：下发命令同时入库（供 HTTP 轮询）与 MQTT 广播，两条通道互为备份；
  设备只需实现其一，注意避免重复执行（HTTP 拉取是一次性消费，天然幂等）。
