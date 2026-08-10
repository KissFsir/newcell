import os
import uuid
from datetime import timedelta

import cv2
import numpy as np
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone as dj_timezone
from django.views.decorators.csrf import csrf_exempt

from .models import ExpressionRecord, IdentityRecord, RegisteredFace


# ---------- payload 组装（latest / history 共用） ----------

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
            "gender": f.gender,
            "student_no": f.student_no,
            "major": f.major,
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
        defaults={
            "embedding": emb.tobytes(),
            "thumbnail_path": thumb_rel,
            "gender": request.POST.get("gender", "").strip(),
            "student_no": request.POST.get("student_no", "").strip(),
            "major": request.POST.get("major", "").strip(),
        },
    )
    return JsonResponse({
        "face": {
            "id": face.id,
            "person_name": face.person_name,
            "thumbnail": thumb_rel,
            "gender": face.gender,
            "student_no": face.student_no,
            "major": face.major,
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
