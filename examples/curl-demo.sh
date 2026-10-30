#!/usr/bin/env bash
# LinIoT 纯 API 演示：注册 → 上报 → 规则 → 告警 → AI → 命令闭环
# 用法：先启动平台（liniot run），再运行本脚本。BASE 指向平台地址。
set -e
BASE="${BASE:-http://127.0.0.1:8000}"

echo "== 1. 注册设备 =="
curl -s -X POST "$BASE/api/devices" -H 'Content-Type: application/json' \
  -d '{"id":"sensor-1","name":"客厅温湿度传感器","type":"sensor"}' ; echo
curl -s -X POST "$BASE/api/devices" -H 'Content-Type: application/json' \
  -d '{"id":"light-1","name":"智能灯","type":"light"}' ; echo

echo "== 2. 设备上线并上报遥测 =="
curl -s -X POST "$BASE/api/devices/light-1/status" -H 'Content-Type: application/json' \
  -d '{"status":"online","properties":{"power":false}}' ; echo
curl -s -X POST "$BASE/api/devices/sensor-1/telemetry" -H 'Content-Type: application/json' \
  -d '{"points":[{"metric":"temperature","value":31.5},{"metric":"humidity","value":58.0}]}' ; echo

echo "== 3. 配置阈值规则（温度 > 30）=="
curl -s -X POST "$BASE/api/rules" -H 'Content-Type: application/json' \
  -d '{"device_id":"sensor-1","metric":"temperature","op":">","threshold":30,"note":"高温告警"}' ; echo

echo "== 4. 再上报一次，触发告警 =="
curl -s -X POST "$BASE/api/devices/sensor-1/telemetry" -H 'Content-Type: application/json' \
  -d '{"points":[{"metric":"temperature","value":32.0}]}' > /dev/null
sleep 0.3
curl -s "$BASE/api/alerts?limit=3" ; echo

echo "== 5. AI 助手：自然语言开灯（本地规则模式）=="
curl -s -X POST "$BASE/api/ai/chat" -H 'Content-Type: application/json' \
  -d '{"message":"打开所有的灯"}' ; echo

echo "== 6. 设备拉取并执行命令（控制闭环）=="
curl -s "$BASE/api/devices/light-1/commands" ; echo
curl -s -X POST "$BASE/api/devices/light-1/status" -H 'Content-Type: application/json' \
  -d '{"status":"online","properties":{"power":true}}' ; echo

echo "== 7. 概览 =="
curl -s "$BASE/api/overview" ; echo
echo "演示完成：打开 $BASE 查看仪表盘"
