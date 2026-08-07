from django.db import models
from django.conf import settings


class EmotionSnapshot(models.Model):
    """综合情绪快照（本轮仅建表，不落行；快照由 API 实时拼装）。"""
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    physio = models.ForeignKey(
        "physio.PhysioRecord", null=True, blank=True, on_delete=models.SET_NULL
    )
    expression = models.ForeignKey(
        "expression.ExpressionRecord", null=True, blank=True, on_delete=models.SET_NULL
    )
    speech_emotion = models.ForeignKey(
        "speech.SpeechEmotionRecord", null=True, blank=True, on_delete=models.SET_NULL
    )
    transcript = models.ForeignKey(
        "speech.TranscriptRecord", null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        ordering = ["-timestamp"]
