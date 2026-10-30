/* LinIoT ESP32 固件示例 — MQTT 通道
 *
 * 功能：订阅 liniot/esp32-mqtt-1/command 接收命令；
 *       每 10 秒向 .../telemetry 上报模拟温湿度；遗嘱消息实现秒级下线感知。
 *
 * 依赖（Arduino Library Manager）：
 *   - PubSubClient (Nick O'Leary)
 *
 * 使用：修改 WiFi / Broker 地址后烧录。Broker 可用 docker-compose.yml 里的
 * mosquitto，或 broker.emqx.io 等公共 Broker（仅测试用）。
 */

#include <WiFi.h>
#include <PubSubClient.h>

const char* WIFI_SSID     = "你的WiFi名称";
const char* WIFI_PASSWORD = "你的WiFi密码";

const char* MQTT_HOST = "192.168.1.100";   // Broker 地址
const int   MQTT_PORT = 1883;
const char* DEVICE_ID = "esp32-mqtt-1";
const char* DEVICE_NAME = "ESP32 MQTT 节点";

WiFiClient wifi;
PubSubClient mqtt(wifi);

const int LED_PIN = 2;
bool power = false;
unsigned long lastTelemetry = 0;

String topic(const char* suffix) {
  return String("liniot/") + DEVICE_ID + "/" + suffix;
}

void publishStatus(const char* status, bool* powerPtr) {
  String body = String("{\"status\":\"") + status + "\"";
  if (powerPtr) {
    body += ",\"properties\":{\"power\":";
    body += *powerPtr ? "true" : "false";
    body += "}";
  }
  body += "}";
  mqtt.publish(topic("status").c_str(), body.c_str());
}

void onCommand(char* topicStr, byte* payload, unsigned int length) {
  String msg;
  for (unsigned int i = 0; i < length; i++) msg += (char)payload[i];
  Serial.printf("[cmd] %s %s\n", topicStr, msg.c_str());

  // 极简解析（生产环境建议用 ArduinoJson）
  if (msg.indexOf("\"property\":\"power\"") >= 0) {
    power = msg.indexOf("\"value\":true") >= 0;
    digitalWrite(LED_PIN, power ? HIGH : LOW);
    publishStatus("online", &power);        // 回报，完成闭环
  }
}

void connectMqtt() {
  while (!mqtt.connected()) {
    String clientId = String("liniot-") + DEVICE_ID;
    // 遗嘱：异常掉线时 Broker 代发 offline，平台立即标记离线
    bool ok = mqtt.connect(clientId.c_str(),
                           nullptr, nullptr,
                           topic("status").c_str(), 0, true,
                           "{\"status\":\"offline\"}");
    if (ok) {
      Serial.println("[mqtt] 已连接");
      mqtt.subscribe(topic("command").c_str());
      publishStatus("online", &power);
    } else {
      Serial.printf("[mqtt] 连接失败 rc=%d，2 秒后重试\n", mqtt.state());
      delay(2000);
    }
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) { delay(400); Serial.print("."); }
  Serial.printf("\nWiFi 已连接: %s\n", WiFi.localIP().toString().c_str());

  mqtt.setServer(MQTT_HOST, MQTT_PORT);
  mqtt.setCallback(onCommand);
  mqtt.setKeepAlive(30);
}

void loop() {
  if (!mqtt.connected()) connectMqtt();
  mqtt.loop();

  unsigned long now = millis();
  if (now - lastTelemetry >= 10000) {
    lastTelemetry = now;
    // 示例用模拟值；接真实传感器时替换为 DHT/SHT 读取结果
    float t = 22.0 + (random(0, 40) / 10.0);
    float h = 55.0 + (random(0, 60) / 10.0);
    String body = String("{\"points\":[") +
                  "{\"metric\":\"temperature\",\"value\":" + String(t, 1) + "}," +
                  "{\"metric\":\"humidity\",\"value\":" + String(h, 1) + "}]}";
    mqtt.publish(topic("telemetry").c_str(), body.c_str());
    Serial.printf("[tel] %s\n", body.c_str());
  }
}
