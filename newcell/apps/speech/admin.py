from django.contrib import admin

from .models import SpeechEmotionRecord, TranscriptRecord


@admin.register(SpeechEmotionRecord)
class SpeechEmotionRecordAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "emotion_label", "confidence")


@admin.register(TranscriptRecord)
class TranscriptRecordAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "sentiment_label", "sentiment_confidence", "text")
