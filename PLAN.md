# 多模态情绪识别 Web 系统 — 功能与实施计划

## 约束
- 实时性：~5 秒间隔（准实时）
- 硬件：RTX 3060 及以上
- 场景：单人、中文
- 融合：暂不做融合模型，各模态独立预测，前端并列展示
- 后端：Django
- 已有硬件：Arduino（心率 + 体表温度 + 皮肤湿度）
- 跨平台：Mac (开发) → Windows 11 + CUDA (部署)

---

## 一、系统总体架构

```
Arduino --[串口]--> Python采集进程 --> SQLite/PostgreSQL
摄像头 --[OpenCV]--> Python推理进程 --> SQLite/PostgreSQL
麦克风 --[PyAudio]--> Python推理进程 --> SQLite/PostgreSQL
                                         |
                                    Django 后端
                                         |
                          Web前端 (模板 + Chart.js + WebSocket)
```

- 采集/推理以独立 Python 进程运行（非 Django 进程内），通过 DB 解耦
- 前端每 5 秒通过 WebSocket 或轮询刷新最新数据

---

## 二、模块与功能细化

### 模块 A：Arduino 生理信号采集

| 编号 | 功能 | 说明 |
|------|------|------|
| A1 | 串口数据读取 | Python pyserial 读取 Arduino 串口输出，解析 JSON/CSV 行 |
| A2 | 心率 (BPM) 采集与存储 | 存储原始 BPM 值 + 时间戳，每秒一条 |
| A3 | 体表温度采集与存储 | 摄氏度，每秒一条 |
| A4 | 皮肤湿度采集与存储 | 相对湿度/模拟值，每秒一条 |
| A5 | 5 秒窗口聚合 | 对最近 5 秒数据做 mean/max/min，生成一行聚合记录供前端消费 |
| A6 | 生理数据趋势 API | GET /api/physio/latest?seconds=60 返回最近 N 秒聚合数据 |

### 模块 B：摄像头 — 面部表情识别

| 编号 | 功能 | 说明 |
|------|------|------|
| B1 | 摄像头帧采集 | OpenCV 每 1 秒抓一帧，存为 numpy 数组 |
| B2 | 人脸检测 | MTCNN 或 RetinaFace 检出人脸 bounding box，单人场景只取面积最大的一张脸 |
| B3 | 人脸对齐与裁剪 | 根据关键点做仿射变换对齐，resize 到模型输入尺寸 |
| B4 | 表情分类推理 | 使用预训练模型（HSEmotion 或 ResNet-FER）输出 7 分类概率（怒厌恶惊悲喜中），每 5 秒跑一帧 |
| B5 | 表情结果 API | GET /api/expression/latest 返回最新一次表情分类结果（7 维概率 + 标签） |
| B6 | 表情历史 API | GET /api/expression/history?minutes=30 返回时间序列 |

### 模块 C：摄像头 — 人脸识别（身份）

| 编号 | 功能 | 说明 |
|------|------|------|
| C1 | 人脸注册页面 | 上传 3-5 张照片或通过摄像头抓拍，输入姓名，提取 face embedding 存入 DB |
| C2 | 人脸 embedding 提取 | InsightFace (ArcFace) 或 face_recognition 库提取 512 维向量 |
| C3 | 实时人脸识别 | 对当前帧提取 embedding，与注册库做余弦相似度匹配，阈值 > 0.6 认定身份 |
| C4 | 已注册人脸列表 | 页面展示已注册身份，支持删除/重新注册 |
| C5 | 身份识别 API | GET /api/identity/current 返回当前摄像头前的人的身份 + 置信度 |
| C6 | 未知人脸标记 | 当相似度低于阈值时标记为 "未知"，前端可提示注册 |

### 模块 D：麦克风 — 语音情绪识别 (SER)

| 编号 | 功能 | 说明 |
|------|------|------|
| D1 | 音频流采集 | PyAudio 持续录音，每 5 秒切一片段，存为 WAV |
| D2 | 语音活动检测 (VAD) | Silero VAD 判断 5 秒片段是否有人说话，无人声则跳过不推理 |
| D3 | 语音情绪推理 | 使用 speechbrain/emotion-recognition 或中文 SER 模型，输出情绪分类（如 4 类：平静/开心/悲伤/愤怒） |
| D4 | 音频特征提取 | 基频 (F0)、响度 (RMS)、语速 (speaking rate) 作为辅助指标 |
| D5 | 语音情绪 API | GET /api/speech-emotion/latest 返回最新推理结果 |
| D6 | 无语音状态 | 当 VAD 判定无人声时返回 {status: "silent"}，前端对应留空 |

### 模块 E：ASR 语音转文字 + 文本情感分析

| 编号 | 功能 | 说明 |
|------|------|------|
| E1 | 语音转文字 (ASR) | 使用 FunASR 或 Whisper (medium) 中文模型，将 5 秒音频转为文本 |
| E2 | 文本情感分类 | 使用 `bert-base-chinese` 微调的情感模型（如 `uer/roberta-base-finetuned-jd-binary-chinese`）或 SnowNLP |
| E3 | 情感类别 | 正面/负面/中性，附带置信度 |
| E4 | 关键词提取 | jieba 分词 + TF-IDF / TextRank 提取说话中的关键词 |
| E5 | ASR 文本展示 | 前端实时字幕效果，展示最近一段识别文本 + 情感标签 |
| E6 | 转录历史 API | GET /api/transcript/history?minutes=30 返回文本时间线 |

### 模块 F：前端 — 实时监控面板

| 编号 | 功能 | 说明 |
|------|------|------|
| F1 | 核心 Dashboard | 单页布局，三栏网格，实时展示各模态结果 |
| F2 | 生理信号曲线 | Chart.js 折线图，心率/温度/湿度三条线，滚动最近 60 秒 |
| F3 | 面部表情展示 | 当前帧表情概率柱状图（7 类）+ 人脸识别身份标签 + 摄像头实时帧预览（JPEG 推流或 base64） |
| F4 | 语音模块展示 | 当前语音情绪标签 + 波形图 + ASR 转录文本 + 文本情感标签 |
| F5 | 综合情绪标签 | 页面顶部大标签：汇总当前主情绪（直接取面部表情的 top-1，不做融合），颜色编码（红=怒、蓝=悲等） |
| F6 | 5 秒自动刷新 | WebSocket 推送或 JS setInterval 轮询，每 5 秒拉一次全量最新数据 |
| F7 | 历史回放页面 | 选择日期/时间范围，查看过去的情绪变化曲线 |
| F8 | 系统状态指示 | 各模块连接状态指示灯（绿=正常/黄=无信号/红=错误），如 Arduino 串口断开、摄像头未检测到人脸、麦克风无声 |

### 模块 G：用户系统与数据管理

| 编号 | 功能 | 说明 |
|------|------|------|
| G1 | Django 用户系统 | 内置 auth，注册/登录/登出 |
| G2 | 情绪记录历史 | 列表页，分页展示所有历史情绪记录，按时间倒序 |
| G3 | 数据导出 | 导出选定时间范围的 CSV（含各模态结果 + 时间戳） |
| G4 | 每日情绪摘要 | 当日情绪分布饼图 + 主导情绪时长统计 |
| G5 | 后台管理 | Django Admin 注册所有模型，方便查看/管理原始数据 |

---

## 三、数据模型设计

```python
# 生理信号聚合记录 (每 5 秒一行)
class PhysioRecord:
    timestamp, hr_avg, hr_min, hr_max,
    temp_avg, skin_humidity_avg

# 面部表情记录 (每 5 秒一行)
class ExpressionRecord:
    timestamp, angry, disgust, fear, happy, sad, surprise, neutral
    dominant_emotion, confidence, face_image_path

# 人脸身份识别记录
class IdentityRecord:
    timestamp, person_name, confidence, is_unknown

# 注册人脸库
class RegisteredFace:
    person_name, embedding (BinaryField/npz), thumbnail_path, created_at

# 语音情绪记录 (有语音时)
class SpeechEmotionRecord:
    timestamp, emotion_label, confidence,
    pitch_mean, rms_mean, speaking_rate,
    audio_path

# ASR 转录记录
class TranscriptRecord:
    timestamp, text, sentiment_label, sentiment_confidence, keywords (JSON)

# 综合情绪快照 (从各模态 latest 拼装)
class EmotionSnapshot:
    timestamp, user, physio, expression, speech_emotion, transcript
```

---

## 四、项目目录结构

```
newcell/
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── config/                 # Django 项目配置
│   ├── settings.py
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py             # Channels (WebSocket)
├── apps/
│   ├── accounts/           # 用户系统
│   ├── dashboard/          # 前端面板视图
│   ├── physio/             # 生理信号
│   ├── expression/         # 面部表情 + 人脸识别
│   ├── speech/             # 语音情绪 + ASR
│   └── records/            # 历史记录 + 导出
├── engine/                 # 推理进程（独立于 Django）
│   ├── arduino_reader.py   # 串口读取
│   ├── camera_worker.py    # 摄像头采集 + 表情 + 人脸识别
│   ├── mic_worker.py       # 麦克风采集 + VAD + SER + ASR
│   └── model_loader.py     # 模型加载/缓存
├── models/                 # 预训练模型存放（.gitignore）
├── static/
├── templates/
└── media/                  # 采集帧/音频文件存放
```

---

## 五、模型选型（全部中文适配或语言无关）

| 任务 | 推荐模型 | 理由 |
|------|----------|------|
| 人脸检测 | MTCNN (facenet-pytorch) | 轻量，PyTorch 原生，CPU 可跑 |
| 表情分类 | HSEmotion (hse-neutral) | 7 类包括中性，PyTorch，ImageNet 预训练泛化好 |
| 人脸识别 | InsightFace (buffalo_l) | ArcFace，中文人脸效果好，有 Python SDK |
| VAD | Silero VAD | 轻量，PyTorch，准确率高 |
| 语音情绪 | speechbrain/emotion-recognition-wav2vec2 | 开源 SER，4 类，英文预训但 emotion cues 跨语言可用 |
| ASR | FunASR (Paraformer-zh) 或 Whisper medium | 中文 ASR 效果好，HuggingFace 可下载 |
| 文本情感 | uer/roberta-base-finetuned-jd-binary-chinese | 中文情感二分类，HuggingFace |
| 关键词 | jieba + TF-IDF | 中文分词标配 |

---

## 六、开发顺序（5 个 Phase）

### Phase 1 — Django 骨架 + 数据模型
- 初始化 Django 项目，配置 settings/database/static
- 创建所有 app + 模型 + 迁移
- 用户系统（注册/登录/登出）
- Django Admin 注册
- 空的 Dashboard 页面框架

### Phase 2 — 摄像头模块（表情 + 人脸识别）
- 实现 camera_worker.py：抓帧 → 人脸检测 → 对齐 → 表情推理 → embedding 提取
- 实现人脸注册/识别功能
- 表情 API + 身份 API
- 前端 Dashboard 集成表情区和人脸身份区

### Phase 3 — 麦克风模块（语音情绪 + ASR）
- 实现 mic_worker.py：录音 → VAD → SER → ASR → 文本情感 → 关键词
- 对应 API
- 前端 Dashboard 集成语音区

### Phase 4 — Arduino 生理信号
- 实现 arduino_reader.py：串口读取 → 解析 → 5 秒聚合写库
- 生理数据 API
- 前端 Chart.js 生理曲线

### Phase 5 — 历史回放 + 数据导出 + 打磨
- 历史回放页面
- CSV 导出
- 每日摘要
- 系统状态指示灯
- 整体联调测试

---

## 七、验证方式

1. **Phase 1**：Django runserver 正常启动，注册/登录可用，Admin 可看到空表
2. **Phase 2**：启动 camera_worker，前端 5 秒刷新能看到表情柱状图 + 身份标签；注册人脸后可识别
3. **Phase 3**：对着麦克风说话，前端出现 ASR 文字 + 文本情感 + 语音情绪标签；不说话时显示 silent
4. **Phase 4**：Arduino 连接电脑，前端能看到心率/温度/湿度曲线
5. **Phase 5**：选历史时间范围，看到过去的完整情绪时间线；导出 CSV 数据正确
