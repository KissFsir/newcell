"""生产/集成入口：服务 Vite 构建产物 static/dist/index.html。"""
from pathlib import Path

from django.conf import settings
from django.http import Http404, HttpResponse


def index_view(request):
    p = Path(settings.STATICFILES_DIRS[0]) / "dist" / "index.html"
    if not p.exists():
        raise Http404("frontend 未构建：先 cd frontend && npm run build")
    return HttpResponse(p.read_text(encoding="utf-8"))
