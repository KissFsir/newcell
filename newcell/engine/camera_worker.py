"""摄像头采集 + 推理 worker（独立进程，由管理命令或 run_worker.py 启动）。

循环：读帧 → 写预览帧(~8fps) → 每 5s 推理一次（MTCNN 表情 + insightface 身份）→ 写心跳。
推理串行单线程；模型调用在 Django 请求路径由 model_lock 保护。
"""
import logging
import os
import time
from datetime import datetime

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger("newcell.engine.camera_worker")


def _load_models():
    from .model_loader import get_expression_pipe, get_insightface, get_mtcnn
    return get_mtcnn(), get_expression_pipe(), get_insightface()


def _open_camera():
    indices = [0, 1, 2, -1]
    for idx in indices:
        try:
            if os.name == "nt":
                cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            else:
                cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                logger.info("camera opened on index %s", idx)
                return cap
            cap.release()
        except Exception as e:
            logger.warning("camera index %s failed: %s", idx, e)
    return None


def _match_registered(emb, threshold):
    """与注册人脸库做余弦匹配，返回 (name, sim)。归一化向量点积即余弦。"""
    from ..apps.expression.models import RegisteredFace
    best_name, best_sim = "unknown", 0.0
    for face in RegisteredFace.objects.all():
        db_emb = np.frombuffer(face.embedding, dtype=np.float32)
        sim = float(np.dot(emb, db_emb))
        if sim > best_sim:
            best_sim = sim
            best_name = face.person_name
    if best_sim < threshold:
        return "unknown", best_sim
    return best_name, best_sim


def _save_face_thumb(bgr_face):
    """保存人脸缩略图，返回 media 相对路径。"""
    from django.conf import settings
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    name = f"{ts}.jpg"
    path = settings.MEDIA_ROOT / "faces" / name
    os.makedirs(path.parent, exist_ok=True)
    cv2.imwrite(str(path), bgr_face)
    return f"/media/faces/{name}"


def _run_inference(frame_bgr, mtcnn, pipe, face_app):
    from ..apps.expression.models import EMOTION_LABELS, ExpressionRecord, IdentityRecord
    from . import stream_store
    from .model_loader import model_lock

    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    h, w = frame_bgr.shape[:2]

    # ---- 模型推理（持有锁，防止请求路径并发）----
    with model_lock:
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
        faces = face_app.get(frame_bgr)
        if faces:
            emb = faces[0].normed_embedding
            person, id_conf = _match_registered(emb, threshold=_face_threshold())
            is_unknown = person == "unknown"

    # ---- 落库（锁外，串行单事务）----
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

    logger.info(
        "infer ok: expr=%s (%.2f) identity=%s (%.2f)",
        dominant, conf, person, id_conf,
    )


def _face_threshold():
    from django.conf import settings
    return settings.FACE_SIM_THRESHOLD


def _write_heartbeat(camera_ok, error=None):
    from . import stream_store
    stream_store.write_heartbeat({
        "running": True,
        "camera_ok": camera_ok,
        "error": error,
        "last_frame_ts": datetime.now().isoformat() if camera_ok else None,
    })


def main(interval=None):
    from django.conf import settings
    from . import stream_store
    interval = interval or settings.CAMERA_INTERVAL

    logger.info("loading models (first load may take ~1min)...")
    mtcnn, pipe, face_app = _load_models()
    logger.info("models loaded, starting capture loop (infer every %ss)", interval)

    cap = _open_camera()
    last_infer = 0.0
    last_beat = 0.0
    preview_skip = 0

    while True:
        if cap is None:
            cap = _open_camera()
            if cap is None:
                _write_heartbeat(camera_ok=False, error="no_camera")
                time.sleep(2)
                continue

        ret, frame = cap.read()
        if not ret:
            logger.warning("frame read failed, reopening camera")
            cap.release()
            cap = None
            _write_heartbeat(camera_ok=False, error="read_failed")
            time.sleep(1)
            continue

        # 预览 ~8fps（每 12 tick 写一次，tick 间隔 0.1s）
        preview_skip += 1
        if preview_skip % 12 == 0:
            try:
                stream_store.write_preview(frame)
            except Exception as e:
                logger.warning("preview write failed: %s", e)

        now = time.monotonic()
        if now - last_infer >= interval:
            last_infer = now
            try:
                _run_inference(frame, mtcnn, pipe, face_app)
            except Exception:
                logger.exception("inference failed")

        if now - last_beat >= 1.0:
            last_beat = now
            _write_heartbeat(camera_ok=True)

        time.sleep(0.1)
