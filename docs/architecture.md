# 系统架构

## 总览

```
                        ┌────────────────────────────────────────────────────┐
                        │                    LinIoT 进程                     │
                        │                                                    │
 ESP32/树莓派/模拟器 ────┼──▶ MQTTService ──┐          ┌── WebSocket /ws ──▶ 仪表盘
 （MQTT 客户端）         │   (paho 线程)     │          │                    （浏览器）
                        │                   ▼          │
 任意 HTTP 客户端 ──────┼──▶ FastAPI /api/* ──▶ DeviceService ──▶ EventBus（进程内广播）
                        │   (线程池)            │    │
                        │                      ▼    ▼
                        │                 RuleEngine  事件: telemetry/device/
                        │                   │         alert/command
                        │                   ▼
                        │              SQLite Store ◀── AI 助手（读快照/写命令）
                        │            devices/telemetry/      │
                        │            rules/alerts/commands   ▼
                        │                          OpenAI 兼容 /chat/completions
                        └────────────────────────────────────────────────────┘
```

## 模块职责

| 模块 | 文件 | 职责 |
|---|---|---|
| 存储 | `liniot/store.py` | SQLite 全部读写；单连接 + `RLock`，WAL 模式；遥测按设备环形保留 |
| 设备服务 | `liniot/service.py` | 用例编排：注册、遥测入库、状态维护、命令下发；HTTP/MQTT 两通道汇聚于此 |
| 规则引擎 | `liniot/rules.py` | 遥测到达时同步判定；按「(规则, 设备)」记录上升沿状态，避免重复告警 |
| 事件总线 | `liniot/bus.py` | 进程内发布/订阅；`call_soon_threadsafe` 把 MQTT 线程的事件安全投递到 asyncio |
| MQTT 接入 | `liniot/mqtt_service.py` | 订阅 `liniot/+/#` 上行主题；命令经 `liniot/{id}/command` 下发；断线自动重连 |
| HTTP API | `liniot/api.py` | REST + WebSocket；`/api/*` 语义与 MQTT 通道一致 |
| AI 助手 | `liniot/ai.py` | 组装设备快照 → LLM 结构化输出 → 白名单校验 → 命令落库；无 Key 走本地意图 |
| 仪表盘 | `web/` | 原生 JS 单页，hash 路由；Canvas 图表零依赖 |
| 模拟器 | `liniot/simulator.py` | 虚拟传感器（随机游走）与智能灯（轮询命令并回报），无需硬件 |

## 关键设计

### 双通道一致语义

HTTP 与 MQTT 上报最终都调用 `DeviceService.ingest()` / `set_status()`，因此规则判定、
在线状态、实时推送的行为与接入方式无关。命令下发同时写库（HTTP 轮询拉取）并经 MQTT
广播（在线订阅），设备任选其一。

### 线程模型

- paho-mqtt 回调运行在独立网络线程；FastAPI 同步端点运行在 anyio 线程池。
- 两者都通过 `EventBus.publish()` → `loop.call_soon_threadsafe()` 把事件投递到
  asyncio 事件循环，再广播给 WebSocket 订阅者，避免跨线程直接操作连接。
- SQLite 共享单连接 + 线程锁，写入串行化；WAL 允许读写并发。单机台内设备规模
  （< 1000 台、点间隔秒级）完全够用，这是「轻量级」的取舍。

### 上升沿告警

规则在数据到达时同步判定。触发态以 `(rule_id, device_id)` 为键保存在内存：
条件持续为真只告警一次，恢复后再次越限才重新告警。全局规则（`device_id` 为空）
对每台设备独立做边沿判定，互不干扰（tests/test_rules.py 有专门回归用例）。

### 数据保留

每设备保留最近 `LINIOT_RETENTION`（默认 20000）条遥测。写入路径每 200 条批量
执行一次窗口函数清理，避免表无限增长；索引 `(device_id, metric, ts)` 保证曲线
查询为 O(log n + limit)。

### AI 安全边界

AI 只能调用 `set_property` 一个动作，且属性名必须已存在于设备 `properties` 中，
值必须是标量；LLM 输出按 JSON 解析，非法动作被逐条拒绝并保留在响应的 `results`
里可审计。所有下发命令写入 `commands` 表，设备确认后属性才变更。

## 扩展点

- **新协议接入**：实现一个把报文转成 `DeviceService` 调用的服务类即可（参考
  `MQTTService.handle_telemetry_payload`）。
- **新规则类型**：在 `rules.py` 增加判定函数与持久化字段；引擎与 API 结构已分离。
- **替换存储**：`Store` 的接口即契约（devices/telemetry/rules/alerts/commands 五域），
  可换 PostgreSQL/TimescaleDB 实现同接口。
