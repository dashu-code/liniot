"""告警 Webhook 演示接收器。

用法：
  python examples/webhook_server.py          # 监听 9000
  LINIOT_WEBHOOK_URL=http://127.0.0.1:9000/alert liniot run
之后每当规则触发，这里会打印一条平台推送的告警 JSON。
"""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:  # noqa: N802（http.server 命名约定）
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            alert = json.loads(body)
            print(f"\n[webhook] 收到告警: {alert.get('message')} "
                  f"(device={alert.get('device_id')}, ts={alert.get('ts')})")
        except json.JSONDecodeError:
            print(f"[webhook] 非 JSON 请求: {body[:120]!r}")
        self.send_response(204)
        self.end_headers()

    def log_message(self, *args) -> None:  # 静默默认访问日志
        pass


if __name__ == "__main__":
    print("Webhook 演示接收器监听 http://0.0.0.0:9000/alert （Ctrl+C 退出）")
    HTTPServer(("0.0.0.0", 9000), Handler).serve_forever()
