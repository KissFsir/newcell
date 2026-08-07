"""文件级共享：预览帧 + 心跳。

worker 与 Django 是不同进程，不能共享内存缓冲；
统一用「原子写文件」跨进程通信。
"""
import json
import os
import tempfile

import cv2
from django.conf import settings


def _atomic_write(path, data):
    d = os.path.dirname(str(path))
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, str(path))
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def write_preview(frame_bgr, quality=70):
    """压缩并原子写入最新预览帧。"""
    ok, buf = cv2.imencode(".jpg", frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if ok:
        _atomic_write(settings.FACE_FRAME_DIR / "latest.jpg", buf.tobytes())


def latest_frame_path():
    return settings.FACE_FRAME_DIR / "latest.jpg"


def write_heartbeat(payload):
    _atomic_write(settings.HEARTBEAT_PATH, json.dumps(payload).encode("utf-8"))


def heartbeat_path():
    return settings.HEARTBEAT_PATH


def read_heartbeat():
    p = heartbeat_path()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
