# Changelog

## 0.1.0 (2026-10-30)

首个公开版本。

- 设备接入：HTTP 与 MQTT 双通道，语义一致；遗嘱消息下线检测
- 存储：SQLite（WAL），遥测按设备环形保留，批量窗口清理
- 规则引擎：阈值规则，按「规则 × 设备」上升沿去重，全局规则，Webhook 通知
- 实时仪表盘：原生 JS 零构建，WebSocket 推送 + 轮询降级，Canvas 实时图表，
  属性控制，规则管理，告警中心
- AI 助手：OpenAI 兼容 API（可配 DeepSeek/Ollama 等），无 Key 本地意图回退，
  动作白名单校验与命令审计
- 工具链：设备模拟器、`liniot run/simulate` CLI、40 个 pytest 用例、
  GitHub Actions CI、Docker Compose（含 mosquitto）、ESP32 固件示例（HTTP/MQTT）
