# API 协议（浏览器采集 → 推理）

浏览器 `getUserMedia` 采集视频+音频，节流上行到以下推理接口；HTTP 请求/响应，无 SSE/WebSocket。
全部挂载在 `/api/` 下，推理接口 `csrf_exempt`。

## 推理接口

### POST /api/infer/frame
- Content-Type: `multipart/form-data`，字段 `file` = JPEG 帧（前端 canvas.toBlob 0.8 质量）。
- 内部：解码 BGR → MTCNN 检测人脸 → 表情 pipeline（7 类）→ insightface embedding → 与注册人脸比对。
- 每次调用写 `ExpressionRecord` + `IdentityRecord`。
- 200 响应：
```json
{
  "available": true,
  "dominant_emotion": "neutral",
  "confidence": 0.68,
  "face_image": "/media/thumb/xxxx.jpg",
  "identity": {
    "person_name": "曾逸韩",
    "confidence": 0.75,
    "is_unknown": false
  }
}
```
- 无脸：`available=false, dominant_emotion="none", identity.person_name="unknown", is_unknown=true`。
- 400：`{"error": "file_required" | "invalid_image"}`。

### POST /api/infer/audio
- Content-Type: `multipart/form-data`，字段 `file` = 16-bit PCM 单/双声道 WAV（前端 ScriptProcessor 采集 → WAV 编码）。
- 内部：重采样 16k → Silero VAD；有语音才跑 whisper tiny（`language="zh"`）；写 `TranscriptRecord`。
- 200 响应：
```json
{ "has_speech": true, "transcript": "你好世界" }
```
- 静音：`{"has_speech": false, "transcript": ""}`。
- 400：`{"error": "file_required" | "invalid_audio"}`。

### GET /api/infer/status
- 触发后台模型预热（`inference.start_warmup()`，首载 ~1min 只触发一次）。
- 200 响应：`{"state": "loading" | "ready"}`。前端轮询至 `ready` 后启动帧/音频循环。

## 保留的查询接口（History / FaceRegister 仍用）
- `GET /api/expression/latest`、`GET /api/expression/history`
- `GET /api/identity/current`
- `GET /api/faces`、`POST /api/faces/register`、`DELETE /api/faces/<id>`

## 已删除（旧架构）
`/api/stream`(SSE)、`/api/video/stream`(MJPEG)、`/api/camera/start|stop|status`、`/api/snapshot` 均返回 404（`RemovedEndpointTests` 断言）。
