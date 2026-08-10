from django.urls import path

from . import views

app_name = "physio"

urlpatterns = [
    path("settings/serial", views.settings_serial, name="settings_serial"),
    path("serial/ports", views.serial_ports, name="serial_ports"),
    path("physio/latest", views.physio_latest, name="physio_latest"),
    path("physio/history", views.physio_history, name="physio_history"),
]
