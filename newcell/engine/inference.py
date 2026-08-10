"""浏览器采集 → 后端推理（Django 进程内，懒加载模型）。

替代原 camera_worker：不再由 worker 开摄像头采集，而是接收浏览器上传的
帧/音频，跑模型返回结果。模型复用 engine/model_loader 的懒加载单例 + RLock。
"""
import logging
import os
import threading
from datetime import datetime

import numpy as np

from . import model_loader

logger = logging.getLogger("newcell.engine.inference")

# 全局"模型就绪"标志 + 首次 status 轮询触发后台预热
_models_ready = False
_warmup_started = False
_warmup_lock = threading.Lock()


def _load_all():
    model_loader.get_mtcnn()
    model_loader.get_expression_pipe()
    model_loader.get_insightface()
    model_loader.get_vad()
    model_loader.get_whisper()


def start_warmup():
    """首次轮询 status 触发后台加载，避免首个推理请求阻塞 ~1min。"""
    global _warmup_started
    with _warmup_lock:
        if _warmup_started:
            return
        _warmup_started = True

    def run():
        global _models_ready
        try:
            _load_all()
        except Exception:
            logger.exception("model warmup failed")
        finally:
            _models_ready = True

    threading.Thread(target=run, daemon=True).start()


def models_ready():
    return _models_ready


def _save_face_thumb(bgr_face):
    from django.conf import settings
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{ts}.jpg"
    path = settings.MEDIA_ROOT / "faces" / name
    os.makedirs(path.parent, exist_ok=True)
    import cv2
    cv2.imwrite(str(path), bgr_face)
    return f"/media/faces/{name}"


def _match_registered(emb, threshold):
    """返回 (命中 RegisteredFace 对象 | None, 最高相似度)。"""
    from ..apps.expression.models import RegisteredFace
    best_face, best_sim = None, 0.0
    for face in RegisteredFace.objects.all():
        db_emb = np.frombuffer(face.embedding, dtype=np.float32)
        sim = float(np.dot(emb, db_emb))
        if sim > best_sim:
            best_sim = sim
            best_face = face
    if best_face is None or best_sim < threshold:
        return None, best_sim
    return best_face, best_sim


def _face_threshold():
    from django.conf import settings
    return settings.FACE_SIM_THRESHOLD


def infer_frame(frame_bgr):
    """对一帧 BGR 做表情 + 身份推理，写库并返回结果 dict。

    返回:
        {available, dominant_emotion, confidence, face_image,
         identity: {person_name, confidence, is_unknown}}
    """
    from ..apps.expression.models import EMOTION_LABELS, ExpressionRecord, IdentityRecord

    import cv2
    from PIL import Image

    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    h, w = frame_bgr.shape[:2]

    with model_loader.model_lock:
        mtcnn = model_loader.get_mtcnn()
        pipe = model_loader.get_expression_pipe()
        face_app = model_loader.get_insightface()

        boxes, _ = mtcnn.detect(rgb, landmarks=False)
        face_rgb = None
        face_rect = None
        if boxes is not None and len(boxes):
            areas = [(b[2] - b[0]) * (b[3] - b[1]) for b in boxes]
            x1, y1, x2, y2 = boxes[int(np.argmax(areas))]
            pad = int(0.1 * (x2 - x1))
            x1 = max(0, int(x1) - pad)
            y1 = max(0, int(y1) - pad)
            x2 = min(w, int(x2) + pad)
            y2 = min(h, int(y2) + pad)
            face_rect = (x1, y1, x2, y2)
            face_rgb = rgb[y1:y2, x1:x2]

        probs = {k: 0.0 for k in EMOTION_LABELS}
        dominant, conf = "none", 0.0
        if face_rgb is not None:
            results = pipe(Image.fromarray(face_rgb))
            for r in results:
                label = str(r["label"]).lower()
                if label in probs:
                    probs[label] = float(r["score"])
            dominant = max(probs, key=probs.get)
            conf = probs[dominant]

        person, is_unknown, id_conf = "unknown", True, 0.0
        identity_info = {}
        faces = face_app.get(frame_bgr)
        if faces:
            emb = faces[0].normed_embedding
            matched, id_conf = _match_registered(emb, threshold=_face_threshold())
            if matched is not None:
                person = matched.person_name
                is_unknown = False
                identity_info = {
                    "gender": matched.gender,
                    "student_no": matched.student_no,
                    "major": matched.major,
                }

    face_path = ""
    if face_rect is not None:
        face_path = _save_face_thumb(frame_bgr[face_rect[1]:face_rect[3], face_rect[0]:face_rect[2]])

    from django.db import transaction
    with transaction.atomic():
        ExpressionRecord.objects.create(
            **probs, dominant_emotion=dominant, confidence=conf, face_image_path=face_path
        )
        IdentityRecord.objects.create(
            person_name=person, confidence=id_conf, is_unknown=is_unknown
        )

    logger.info("infer_frame ok: expr=%s (%.2f) identity=%s (%.2f)", dominant, conf, person, id_conf)
    return {
        "available": face_rect is not None,
        "dominant_emotion": dominant,
        "confidence": conf,
        "face_image": face_path or None,
        "identity": {
            "person_name": person,
            "confidence": id_conf,
            "is_unknown": is_unknown,
            "gender": identity_info.get("gender", ""),
            "student_no": identity_info.get("student_no", ""),
            "major": identity_info.get("major", ""),
        },
    }


def _resample(audio, src_sr, dst_sr=16000):
    if src_sr == dst_sr:
        return audio
    n = int(len(audio) * dst_sr / src_sr)
    x = np.linspace(0, len(audio) - 1, n)
    return np.interp(x, np.arange(len(audio)), audio).astype(np.float32)


def infer_audio(audio_f32, sample_rate):
    """对一段音频做 VAD，有语音则 whisper 中文转录，写库并返回结果。

    返回: {has_speech, transcript}
    """
    from ..apps.speech.models import TranscriptRecord

    audio = _resample(np.asarray(audio_f32, dtype=np.float32), int(sample_rate))
    if audio.size == 0:
        return {"has_speech": False, "transcript": ""}

    import torch
    with model_loader.model_lock:
        model, utils = model_loader.get_vad()
        get_speech_ts, *_ = utils
        ts = get_speech_ts(torch.from_numpy(audio).float(), model, sampling_rate=16000)
        has_speech = len(ts) > 0
        transcript = ""
        if has_speech:
            whisper = model_loader.get_whisper()
            result = whisper.transcribe(audio, language="zh")
            transcript = (result.get("text") or "").strip()

    if has_speech:
        from django.db import transaction
        with transaction.atomic():
            TranscriptRecord.objects.create(text=transcript)

    logger.info("infer_audio ok: has_speech=%s transcript=%r", has_speech, transcript)
    return {"has_speech": has_speech, "transcript": transcript}
