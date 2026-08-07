from django.urls import path

from . import views

app_name = "expression"

urlpatterns = [
    path("stream", views.sse_stream, name="sse_stream"),
    path("video/stream", views.mjpeg_stream, name="video_stream"),
    path("expression/latest", views.expression_latest, name="expression_latest"),
    path("expression/history", views.expression_history, name="expression_history"),
    path("identity/current", views.identity_current, name="identity_current"),
    path("faces", views.face_list, name="face_list"),
    path("faces/register", views.face_register, name="face_register"),
    path("faces/<int:face_id>", views.face_delete, name="face_delete"),
    path("snapshot", views.snapshot, name="snapshot"),
    path("camera/start", views.camera_start, name="camera_start"),
    path("camera/stop", views.camera_stop, name="camera_stop"),
    path("camera/status", views.camera_status, name="camera_status"),
]
