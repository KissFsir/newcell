# 模型下载与调用指南

## 环境

```bash
conda activate newcell
```

## 一键下载所有模型

```bash
python models/download.py
```

模型缓存目录: `models/cache/`（已加入 .gitignore）

---

## 模型清单

| 编号 | 模型 | 用途 | 大小 | 文件 |
|------|------|------|------|------|
| 1 | MTCNN | 人脸检测 | ~2MB | `demo_face_detect.py` |
| 2 | Silero VAD | 语音活动检测 | ~1.5MB | `demo_vad.py` |
| 3 | ViT-Expression | 面部表情 7 分类 | ~80MB | `demo_expression.py` |
| 4 | InsightFace buffalo_sc | 人脸识别 (512维embedding) | ~130MB | `demo_face_id.py` |
| 5 | Whisper tiny | 中文语音转文字 | ~150MB | `demo_asr.py` |
| 6 | DistilBERT-multilingual | 文本情感 3 分类 | ~200MB | `demo_sentiment.py` |
| 7 | Wav2Vec2 SUPERB-ER | 语音情绪 4 分类 | ~380MB | `demo_ser.py` |

**总计约 940MB。**

---

## 各模型调用示例

### 1. 人脸检测 (MTCNN)

```python
from facenet_pytorch import MTCNN
import cv2

mtcnn = MTCNN(keep_all=True, device="cpu")

img = cv2.cvtColor(cv2.imread("photo.jpg"), cv2.COLOR_BGR2RGB)
boxes, probs, points = mtcnn.detect(img, landmarks=True)
# boxes: [(x1,y1,x2,y2), ...], probs: [0.99, ...], points: 5 个关键点
```

### 2. 面部表情 (ViT)

```python
from transformers import pipeline

pipe = pipeline("image-classification",
    model="dima806/facial_emotions_image_detection")

results = pipe("face.jpg")
# [{"label": "happy", "score": 0.87}, {"label": "neutral", "score": 0.08}, ...]
```

### 3. 人脸识别 (InsightFace)

```python
import insightface

app = insightface.app.FaceAnalysis(name="buffalo_sc", download=True)
app.prepare(ctx_id=-1)  # CPU

faces = app.get(img_bgr)       # 检测 + embedding
emb = faces[0].normed_embedding  # 512 维向量
# 与注册库做余弦相似度匹配确认身份
```

### 4. 语音活动检测 (Silero VAD)

```python
import torch

model, utils = torch.hub.load("snakers4/silero-vad", "silero_vad")
get_speech_ts, *_ = utils

audio = torch.randn(16000)  # 1 秒 16kHz 音频
ts = get_speech_ts(audio, model, sampling_rate=16000)
# ts 为空 → 无人声，非空 → 有人声
```

### 5. 语音转文字 (Whisper tiny)

```python
import whisper

model = whisper.load_model("tiny")
result = model.transcribe("audio.wav", language="zh")
print(result["text"])  # "今天天气真好"
```

### 6. 文本情感 (DistilBERT)

```python
from transformers import pipeline

pipe = pipeline("text-classification",
    model="lxyuan/distilbert-base-multilingual-cased-sentiments-student")

result = pipe("今天很开心！")
# [{"label": "positive", "score": 0.96}]
```

### 7. 语音情绪 (SUPERB Wav2Vec2)

```python
from transformers import pipeline

clf = pipeline("audio-classification",
    model="superb/wav2vec2-base-superb-er")

results = clf("speech.wav")
# [{label: "hap", score: 0.85}, ...]
# 标签: neu(平静) / hap(开心) / sad(悲伤) / ang(愤怒)
```

---

## 实时采集管线 (组合调用)

5 秒一个周期的完整流程：

```python
# 1. 摄像头 → 表情
cap = cv2.VideoCapture(0)
frame = cap.read()[1]
# 人脸检测 + 表情分类 (demo_face_detect.py + demo_expression.py)
# 人脸识别 (demo_face_id.py)

# 2. 麦克风 → 语音情绪 + ASR
audio = record_5s()  # PyAudio 采集
if has_speech(audio):           # demo_vad.py
    emotion = predict_emotion()  # demo_ser.py
    text = transcribe()          # demo_asr.py
    sentiment = analyze_sentiment(text)  # demo_sentiment.py

# 3. Arduino → 生理数据
# pyserial 读取串口 → 心率/温度/湿度 → 5s 聚合

# 4. 所有结果写入数据库 → 前端轮询展示
```

---

## 切换到 CUDA (Windows + NVIDIA)

每个脚本中的设备参数改为:

```python
# MTCNN
mtcnn = MTCNN(device="cuda")

# InsightFace
app.prepare(ctx_id=0)  # 0 = GPU

# transformers pipeline
pipe = pipeline(..., device=0)

# Whisper
# 自动使用 CUDA，无需改动
```
