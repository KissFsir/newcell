from django.urls import path

from . import views
from . import infer_views
from . import llm_views

app_name = "expression"

urlpatterns = [
    path("infer/frame", infer_views.infer_frame, name="infer_frame"),
    path("infer/audio", infer_views.infer_audio, name="infer_audio"),
    path("infer/status", infer_views.infer_status, name="infer_status"),
    path("infer/result", llm_views.infer_result, name="infer_result"),
    path("settings/llm", llm_views.llm_config, name="llm_config"),
    path("expression/latest", views.expression_latest, name="expression_latest"),
    path("expression/history", views.expression_history, name="expression_history"),
    path("identity/current", views.identity_current, name="identity_current"),
    path("faces", views.face_list, name="face_list"),
    path("faces/register", views.face_register, name="face_register"),
    path("faces/<int:face_id>", views.face_delete, name="face_delete"),
]
