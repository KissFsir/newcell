/*
 * 温湿度 + 脉搏板（原 COM6）
 * 输出固定 CSV：温度(°C), 脉搏波形, 湿度(%)，每行 \n 结尾，115200 波特率
 *
 * 相对原版优化：
 *  - 脉搏独立 20Hz 采样（50ms），脉搏波形需要较高采样率；
 *  - 温湿度 AHT20 按 5Hz 节拍读取（传感器本身转换率约 8Hz，不必每帧读），
 *    读取失败时沿用上次有效值，保证输出不断流；
 *  - 脉搏加一阶低通滤波，抑制传感器抖动；
 *  - I2C 提到 400kHz，缩短读取占用，降低对脉搏采样时序的影响。
 */
#include <Wire.h>
#include <AHT20.h>

AHT20 aht20;

const int PULSE_PIN = A3;        // 脉搏传感器接 A3
const unsigned long PULSE_MS = 50;   // 脉搏采样间隔 20Hz
const unsigned long AHT_MS = 200;    // 温湿度采样间隔 5Hz
const float ALPHA = 0.2;             // 脉搏滤波系数（越小越平滑，越小延迟越大）

float temperature = 0.0, humidity = 0.0;
float filteredPulse = 0.0;
bool ahtOk = false;
bool firstPulse = true;

unsigned long lastPulse = 0;
unsigned long lastAHT = 0;

void setup() {
  Serial.begin(115200);
  Wire.begin();
  Wire.setClock(400000);   // 400kHz I2C
  ahtOk = aht20.begin();
}

void loop() {
  unsigned long now = millis();

  // ---- 脉搏：20Hz ----
  if (now - lastPulse >= PULSE_MS) {
    lastPulse = now;

    int raw = analogRead(PULSE_PIN);
    if (firstPulse) {
      filteredPulse = (float)raw;
      firstPulse = false;
    } else {
      filteredPulse = ALPHA * raw + (1.0f - ALPHA) * filteredPulse;
    }

    // ---- 温湿度：5Hz 节拍，失败沿用旧值 ----
    if (now - lastAHT >= AHT_MS) {
      lastAHT = now;
      if (ahtOk && aht20.available()) {
        temperature = aht20.getTemperature();
        humidity = aht20.getHumidity();
      }
    }

    Serial.print(temperature, 1);
    Serial.print(',');
    Serial.print(filteredPulse / 10.0f, 1);
    Serial.print(',');
    Serial.println(humidity, 1);
  }
}
