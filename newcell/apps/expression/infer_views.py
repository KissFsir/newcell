"""浏览器采集 → 推理接口（替代 worker/MJPEG/SSE 链路）。"""
import io
import json
import wave

import cv2
import numpy as np
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from newcell.engine import inference


@csrf_exempt
def infer_frame(request):
    """POST multipart，字段 file = JPEG 帧。返回表情 + 身份。"""
    if request.method != "POST":
        return JsonResponse({"error": "method_not_allowed"}, status=405)
    file = request.FILES.get("file")
    if not file:
        return JsonResponse({"error": "file_required"}, status=400)
    img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return JsonResponse({"error": "invalid_image"}, status=400)
    return JsonResponse(inference.infer_frame(img))


def _decode_wav(data):
    try:
        with wave.open(io.BytesIO(data), "rb") as w:
            sr = w.getframerate()
            ch = w.getnchannels()
            frames = w.readframes(w.getnframes())
    except (wave.Error, EOFError):
        return None, None
    if not frames:
        return None, None
    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    if ch > 1:
        audio = audio.reshape(-1, ch).mean(axis=1)
    return sr, audio


@csrf_exempt
def infer_audio(request):
    """POST multipart，字段 file = 16-bit PCM WAV。返回 VAD + 转录。"""
    if request.method != "POST":
        return JsonResponse({"error": "method_not_allowed"}, status=405)
    file = request.FILES.get("file")
    if not file:
        return JsonResponse({"error": "file_required"}, status=400)
    sr, audio = _decode_wav(file.read())
    if audio is None:
        return JsonResponse({"error": "invalid_audio"}, status=400)
    return JsonResponse(inference.infer_audio(audio, sr))


def infer_status(request):
    """GET。触发后台预热，返回模型加载状态 loading/ready。"""
    inference.start_warmup()
    return JsonResponse({"state": "ready" if inference.models_ready() else "loading"})


@csrf_exempt
def store_transcript(request):
    """POST {text}。供 Web Speech API 模式把浏览器识别结果落库，报告按时间窗可查。"""
    if request.method != "POST":
        return JsonResponse({"error": "method_not_allowed"}, status=405)
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)
    text = str(data.get("text", "")).strip()
    if not text:
        return JsonResponse({"error": "text_required"}, status=400)
    from newcell.apps.speech.models import TranscriptRecord
    TranscriptRecord.objects.create(text=text)
    return JsonResponse({"stored": True})
