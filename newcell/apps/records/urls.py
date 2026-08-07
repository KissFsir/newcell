from django.urls import path

from . import views

app_name = "records"

urlpatterns = [
    path("records/history", views.record_history, name="record_history"),
]
