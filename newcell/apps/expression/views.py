import json
import os
import signal
import subprocess
import sys
import time
import uuid
from datetime import timedelta

import cv2
import numpy as np
from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.utils import timezone as dj_timezone
from django.views.decorators.csrf import csrf_exempt

from .models import ExpressionRecord, IdentityRecord, RegisteredFace


# ---------- payload 组装（SSE / snapshot / latest 共用） ----------

def _expression_payload(expr):
    if expr is None:
        return {"available": False, "reason": "no_record"}
    return {
        "available": True,
        "timestamp": expr.timestamp.isoformat(),
        "dominant_emotion": expr.dominant_emotion,
        "confidence": expr.confidence,
        "probabilities": expr.probability_dict(),
        "face_image": expr.face_image_path or None,
    }


def _identity_payload(ident, now=None):
    if ident is None:
        return {"available": False, "reason": "no_record"}
    now = now or dj_timezone.now()
    age = (now - ident.timestamp).total_seconds()
    return {
        "available": True,
        "person_name": ident.person_name,
        "confidence": ident.confidence,
        "is_unknown": ident.is_unknown,
        "timestamp": ident.timestamp.isoformat(),
        "age_seconds": round(age, 1),
    }


def _status_payload():
    from newcell.engine import stream_store
    hb = stream_store.read_heartbeat()
    if hb is None:
        return {
            "worker_running": False,
            "camera_ok": False,
            "last_update_seconds": None,
            "error": "no_heartbeat",
            "frame_url": "/api/video/stream",
        }
    mtime = stream_store.heartbeat_path().stat().st_mtime
    age = time.time() - mtime
    return {
        "worker_running": age < 20,
        "camera_ok": bool(hb.get("camera_ok")),
        "last_update_seconds": int(age),
        "error": hb.get("error"),
        "frame_url": "/api/video/stream",
    }


def _snapshot():
    expr = ExpressionRecord.objects.first()
    ident = IdentityRecord.objects.first()
    return {
        "server_time": dj_timezone.now().isoformat(),
        "expression": _expression_payload(expr),
        "identity": _identity_payload(ident),
        "status": _status_payload(),
    }


# ---------- 表情 / 身份 ----------

def expression_latest(request):
    return JsonResponse(_expression_payload(ExpressionRecord.objects.first()))


def expression_history(request):
    minutes = int(request.GET.get("minutes", 30))
    limit = int(request.GET.get("limit", 200))
    full = request.GET.get("full") == "1"
    since = dj_timezone.now() - timedelta(minutes=minutes)
    rows = []
    for r in ExpressionRecord.objects.filter(timestamp__gte=since)[:limit]:
        item = {
            "timestamp": r.timestamp.isoformat(),
            "dominant_emotion": r.dominant_emotion,
            "confidence": r.confidence,
        }
        if full:
            item["probabilities"] = r.probability_dict()
        rows.append(item)
    return JsonResponse({"rows": rows})


def identity_current(request):
    return JsonResponse(_identity_payload(IdentityRecord.objects.first()))


# ---------- 人脸库 CRUD ----------

@csrf_exempt
def face_list(request):
    return JsonResponse({"faces": [
        {
            "id": f.id,
            "person_name": f.person_name,
            "thumbnail": f.thumbnail_path or None,
            "created_at": f.created_at.isoformat(),
        }
        for f in RegisteredFace.objects.all()
    ]})


@csrf_exempt
def face_register(request):
    if request.method != "POST":
        return JsonResponse({"error": "method_not_allowed"}, status=405)
    name = request.POST.get("name", "").strip()
    file = request.FILES.get("file")
    if not name or not file:
        return JsonResponse({"error": "name_and_file_required"}, status=400)

    img = cv2.imdecode(np.frombuffer(file.read(), np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        return JsonResponse({"error": "invalid_image"}, status=400)

    from newcell.engine.model_loader import get_insightface, model_lock
    with model_lock:
        app = get_insightface()
        faces = app.get(img)
        if not faces:
            return JsonResponse({"error": "no_face_detected"}, status=400)
        emb = faces[0].normed_embedding.astype(np.float32)

    thumb_name = f"{uuid.uuid4().hex}.jpg"
    thumb_path = settings.MEDIA_ROOT / "thumb" / thumb_name
    os.makedirs(thumb_path.parent, exist_ok=True)
    cv2.imwrite(str(thumb_path), img)
    thumb_rel = f"/media/thumb/{thumb_name}"

    face, _ = RegisteredFace.objects.update_or_create(
        person_name=name,
        defaults={"embedding": emb.tobytes(), "thumbnail_path": thumb_rel},
    )
    return JsonResponse({
        "face": {
            "id": face.id,
            "person_name": face.person_name,
            "thumbnail": thumb_rel,
        }
    }, status=201)


@csrf_exempt
def face_delete(request, face_id):
    try:
        face = RegisteredFace.objects.get(id=face_id)
    except RegisteredFace.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)
    if face.thumbnail_path:
        p = settings.MEDIA_ROOT / face.thumbnail_path.lstrip("/media/")
        if p.exists():
            try:
                os.remove(p)
            except OSError:
                pass
    face.delete()
    return JsonResponse({"deleted": True})


# ---------- 实时流 ----------

def _frame_path():
    return settings.FACE_FRAME_DIR / "latest.jpg"


def mjpeg_stream(request):
    def gen():
        last_mtime = 0.0
        p = _frame_path()
        while True:
            try:
                if p.exists():
                    mtime = p.stat().st_mtime
                    if mtime != last_mtime:
                        last_mtime = mtime
                        data = p.read_bytes()
                        yield (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n\r\n" + data + b"\r\n"
                        )
            except Exception:
                pass
            time.sleep(0.1)

    resp = StreamingHttpResponse(
        gen(), content_type="multipart/x-mixed-replace; boundary=frame"
    )
    resp["Cache-Control"] = "no-store"
    return resp


def sse_stream(request):
    def gen():
        yield "retry: 3000\n\n"
        while True:
            data = json.dumps(_snapshot(), ensure_ascii=False)
            yield f"data: {data}\n\n"
            time.sleep(settings.SSE_INTERVAL)

    resp = StreamingHttpResponse(gen(), content_type="text/event-stream")
    resp["Cache-Control"] = "no-cache"
    resp["X-Accel-Buffering"] = "no"
    return resp


def snapshot(request):
    return JsonResponse(_snapshot())


# ---------- 实时采集 worker 启停（前端「开始采集」按钮） ----------

WORKER_PID_FILE = settings.MEDIA_ROOT / "state" / "worker.pid"


def _read_worker_pid():
    try:
        return int(WORKER_PID_FILE.read_text().strip())
    except (OSError, ValueError):
        return None


def _write_worker_pid(pid):
    WORKER_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    WORKER_PID_FILE.write_text(str(pid))


def _pid_alive(pid):
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


@csrf_exempt
def camera_start(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)
    pid = _read_worker_pid()
    if _pid_alive(pid):
        return JsonResponse({"ok": True, "already_running": True, "pid": pid})

    log_path = settings.MEDIA_ROOT / "state" / "camera_worker.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "ab")
    try:
        proc = subprocess.Popen(
            [sys.executable, "manage.py", "camera_worker"],
            cwd=settings.BASE_DIR,
            stdout=log,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        log.close()
        return JsonResponse({"ok": False, "error": str(e)}, status=500)
    _write_worker_pid(proc.pid)
    return JsonResponse({"ok": True, "already_running": False, "pid": proc.pid})


@csrf_exempt
def camera_stop(request):
    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "method_not_allowed"}, status=405)
    pid = _read_worker_pid()
    stopped = False
    if _pid_alive(pid):
        try:
            os.killpg(pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception:
                pass
        stopped = True
    _write_worker_pid(-1)
    return JsonResponse({"ok": True, "stopped": stopped})


def camera_status(request):
    from newcell.engine import stream_store
    pid = _read_worker_pid()
    alive = _pid_alive(pid)
    hb = stream_store.read_heartbeat()
    hb_age = None
    if hb is not None:
        p = stream_store.heartbeat_path()
        if p.exists():
            hb_age = time.time() - p.stat().st_mtime
    fresh = alive and hb_age is not None and hb_age < 20
    return JsonResponse({
        "running": alive,
        "pid": pid if alive else None,
        "camera_ok": bool(fresh and hb.get("camera_ok")),
        "loading": bool(alive and not fresh),
        "error": (hb or {}).get("error"),
        "last_update_seconds": round(hb_age, 1) if hb_age is not None else None,
    })
