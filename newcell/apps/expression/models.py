from django.db import models

EMOTION_LABELS = ["angry", "disgust", "fear", "happy", "neutral", "sad", "surprise"]


class ExpressionRecord(models.Model):
    """每 5 秒一条面部表情结果。"""
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    angry = models.FloatField(default=0.0)
    disgust = models.FloatField(default=0.0)
    fear = models.FloatField(default=0.0)
    happy = models.FloatField(default=0.0)
    neutral = models.FloatField(default=0.0)
    sad = models.FloatField(default=0.0)
    surprise = models.FloatField(default=0.0)
    dominant_emotion = models.CharField(max_length=16)
    confidence = models.FloatField(default=0.0)
    face_image_path = models.CharField(max_length=512, blank=True, default="")

    class Meta:
        ordering = ["-timestamp"]

    def probability_dict(self):
        return {k: getattr(self, k) for k in EMOTION_LABELS}


class IdentityRecord(models.Model):
    """每 5 秒一条身份识别结果。"""
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    person_name = models.CharField(max_length=128, default="unknown")
    confidence = models.FloatField(default=0.0)
    is_unknown = models.BooleanField(default=False)

    class Meta:
        ordering = ["-timestamp"]


class RegisteredFace(models.Model):
    """已注册人脸库：person_name 唯一，重注册 upsert 覆盖 embedding。"""
    person_name = models.CharField(max_length=128, unique=True)
    embedding = models.BinaryField()  # float32 normed_embedding(512).tobytes()
    thumbnail_path = models.CharField(max_length=512, blank=True, default="")
    gender = models.CharField(max_length=16, blank=True, default="")
    student_no = models.CharField(max_length=64, blank=True, default="")
    major = models.CharField(max_length=128, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]


class LLMConfig(models.Model):
    """AI 情感洞察的 LLM 配置（单例 id=1）。base_url/模型名代码写死。"""
    provider = models.CharField(max_length=16, default="ollama")  # ollama | deepseek
    ollama_model = models.CharField(max_length=128, default="qwen2.5:7b")
    deepseek_api_key = models.CharField(max_length=256, blank=True, default="")
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(id=1)
        return obj
