from django.http import JsonResponse


def record_history(request):
    """统一记录列表：本轮返回 expression + identity，按时间倒序。"""
    limit = int(request.GET.get("limit", 100))
    from newcell.apps.expression.models import ExpressionRecord, IdentityRecord

    combined = []
    for e in ExpressionRecord.objects.all()[:limit]:
        combined.append({
            "_ts": e.timestamp,
            "timestamp": e.timestamp.isoformat(),
            "type": "expression",
            "dominant_emotion": e.dominant_emotion,
            "confidence": e.confidence,
        })
    for i in IdentityRecord.objects.all()[:limit]:
        combined.append({
            "_ts": i.timestamp,
            "timestamp": i.timestamp.isoformat(),
            "type": "identity",
            "person_name": i.person_name,
            "confidence": i.confidence,
        })
    combined.sort(key=lambda r: r["_ts"], reverse=True)
    return JsonResponse({"rows": [
        {k: v for k, v in r.items() if k != "_ts"} for r in combined[:limit]
    ]})
