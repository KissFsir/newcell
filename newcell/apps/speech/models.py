from django.db import models


class SpeechEmotionRecord(models.Model):
    """有语音时一条语音情绪结果。"""
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    emotion_label = models.CharField(max_length=32)
    confidence = models.FloatField(default=0.0)
    pitch_mean = models.FloatField(null=True, blank=True)
    rms_mean = models.FloatField(null=True, blank=True)
    speaking_rate = models.FloatField(null=True, blank=True)
    audio_path = models.CharField(max_length=512, blank=True, default="")

    class Meta:
        ordering = ["-timestamp"]


class TranscriptRecord(models.Model):
    """ASR 转录 + 文本情感。"""
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    text = models.TextField(default="")
    sentiment_label = models.CharField(max_length=32, default="")
    sentiment_confidence = models.FloatField(default=0.0)
    keywords = models.JSONField(default=list, blank=True)

    class Meta:
        ordering = ["-timestamp"]
