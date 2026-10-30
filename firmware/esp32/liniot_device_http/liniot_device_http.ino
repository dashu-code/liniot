/* LinIoT ESP32 固件示例 — HTTP 通道
 *
 * 功能：每 10 秒上报一次温湿度（DHT22），每 3 秒轮询一次下发命令。
 * 无需 MQTT Broker，只需要 LinIoT 平台可达。
 *
 * 依赖（Arduino Library Manager）：
 *   - DHT sensor library (Adafruit)
 *   - ArduinoJson (可选；本例用手写 JSON 避免依赖)
 *
 * 使用：修改 WIFI_SSID/WIFI_PASSWORD/PLATFORM_URL 后烧录。
 * 首次上电会自动在平台注册设备（幂等）。
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>

const char* WIFI_SSID     = "你的WiFi名称";
const char* WIFI_PASSWORD = "你的WiFi密码";

// 平台地址；ESP32 与平台需在同一局域网，或使用公网地址
const char* PLATFORM_URL = "http://192.168.1.100:8000";
const char* DEVICE_ID    = "esp32-dht-1";
const char* DEVICE_NAME  = "ESP32 温湿度节点";

const int DHT_PIN  = 4;       // DHT22 数据脚
const int LED_PIN  = 2;       // 板载 LED，演示 power 属性控制

DHT dht(DHT_PIN, DHT22);
unsigned long lastTelemetry = 0;
unsigned long lastPoll      = 0;

void registerDevice() {
  HTTPClient http;
  http.begin(String(PLATFORM_URL) + "/api/devices");
  http.addHeader("Content-Type", "application/json");
  String body = String("{\"id\":\"") + DEVICE_ID + "\",\"name\":\"" + DEVICE_NAME +
                "\",\"type\":\"sensor\",\"meta\":{\"fw\":\"esp32-http-example\"}}";
  int code = http.POST(body);          // 幂等：重复注册返回 200
  Serial.printf("[reg] %d\n", code);
  http.end();
}

void reportStatus(const char* status, bool power) {
  HTTPClient http;
  http.begin(String(PLATFORM_URL) + "/api/devices/" + DEVICE_ID + "/status");
  http.addHeader("Content-Type", "application/json");
  String body = String("{\"status\":\"") + status + "\",\"properties\":{\"power\":";
  body += power ? "true" : "false";
  body += "}}";
  http.POST(body);
  http.end();
}

void sendTelemetry(float t, float h) {
  if (isnan(t) || isnan(h)) return;
  HTTPClient http;
  http.begin(String(PLATFORM_URL) + "/api/devices/" + DEVICE_ID + "/telemetry");
  http.addHeader("Content-Type", "application/json");
  String body = String("{\"points\":[") +
                "{\"metric\":\"temperature\",\"value\":" + String(t, 1) + "}," +
                "{\"metric\":\"humidity\",\"value\":" + String(h, 1) + "}]}";
  int code = http.POST(body);
  Serial.printf("[tel] %s -> %d\n", body.c_str(), code);
  http.end();
}

void pollCommands() {
  HTTPClient http;
  http.begin(String(PLATFORM_URL) + "/api/devices/" + DEVICE_ID + "/commands");
  int code = http.GET();
  if (code != 200) { http.end(); return; }

  String resp = http.getString();
  http.end();
  if (resp.indexOf("\"property\"") < 0) return;   // 空队列

  // 极简解析：找到 power 命令的 value（生产环境建议用 ArduinoJson）
  int p = resp.indexOf("\"property\":\"power\"");
  if (p >= 0) {
    bool on = resp.substring(resp.indexOf("\"value\"", p)).indexOf("true") >= 0 &&
              resp.indexOf("\"value\"", p) < resp.indexOf("}", p);
    digitalWrite(LED_PIN, on ? HIGH : LOW);
    Serial.printf("[cmd] power = %s\n", on ? "ON" : "OFF");
    reportStatus("online", on);     // 回报新状态，完成控制闭环
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  dht.begin();

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("连接 WiFi");
  while (WiFi.status() != WL_CONNECTED) { delay(400); Serial.print("."); }
  Serial.printf("\n已连接，IP: %s\n", WiFi.localIP().toString().c_str());

  registerDevice();
  reportStatus("online", false);
}

void loop() {
  unsigned long now = millis();
  if (now - lastTelemetry >= 10000) {          // 每 10 秒上报
    lastTelemetry = now;
    sendTelemetry(dht.readTemperature(), dht.readHumidity());
    reportStatus("online", digitalRead(LED_PIN) == HIGH);   // 心跳
  }
  if (now - lastPoll >= 3000) {                // 每 3 秒拉取命令
    lastPoll = now;
    pollCommands();
  }
}
