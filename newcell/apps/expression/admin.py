from django.contrib import admin

from .models import ExpressionRecord, IdentityRecord, RegisteredFace


@admin.register(ExpressionRecord)
class ExpressionRecordAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "dominant_emotion", "confidence", "happy", "sad")
    list_filter = ("dominant_emotion",)


@admin.register(IdentityRecord)
class IdentityRecordAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "person_name", "confidence", "is_unknown")
    list_filter = ("is_unknown",)


@admin.register(RegisteredFace)
class RegisteredFaceAdmin(admin.ModelAdmin):
    list_display = ("person_name", "created_at")
