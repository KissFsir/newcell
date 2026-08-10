/*
 * 皮电板（GSR，原 COM5）
 * 输出单值 CSV：皮电原始值，每行 \n 结尾，115200 波特率
 *
 * 相对原版优化：
 *  - 20Hz 采样 + 一阶低通滤波，抑制手指接触抖动；
 *  - 指示灯改为 500ms 周期闪烁（不再每个采样帧 toggle），
 *    避免 digitalWrite 干扰 analogRead 的采样时序；
 *  - 固定 50ms 节拍，用 millis() 非阻塞计时。
 */
const int GSR_PIN = A0;              // GSR 模块接 A0
const unsigned long SAMPLE_MS = 50;  // 采样间隔 20Hz
const float ALPHA = 0.15;            // 滤波系数（越小越平滑）

float filtered = 0.0;
bool firstSample = true;
unsigned long lastSample = 0;

void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
}

void loop() {
  unsigned long now = millis();
  if (now - lastSample < SAMPLE_MS) return;
  lastSample = now;

  int raw = analogRead(GSR_PIN);
  if (firstSample) {
    filtered = (float)raw;
    firstSample = false;
  } else {
    filtered = ALPHA * raw + (1.0f - ALPHA) * filtered;
  }

  // 指示灯 500ms 周期闪烁（0.5s 亮 / 0.5s 灭）
  digitalWrite(LED_BUILTIN, ((now / 500UL) & 1UL) ? HIGH : LOW);

  Serial.println((int)filtered);
}
