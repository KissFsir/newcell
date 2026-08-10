import io
import json
import wave
from unittest import mock

import cv2
import numpy as np
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from newcell.apps.physio.models import PhysioRecord

from .models import RegisteredFace, LLMConfig, ExpressionRecord


def _jpeg_bytes(color=(120, 120, 120)):
    img = np.full((64, 64, 3), color, dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", img)
    return buf.tobytes()


def _wav_bytes(frames=None, sr=16000):
    frames = frames if frames is not None else np.zeros(sr, dtype=np.int16)
    bio = io.BytesIO()
    with wave.open(bio, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(frames.tobytes())
    return bio.getvalue()


class _NoFaceMTCNN:
    def detect(self, rgb, landmarks=False):
        return None, None


class _FaceMTCNN:
    def detect(self, rgb, landmarks=False):
        return np.array([[10.0, 10.0, 60.0, 60.0]]), np.array([0.99])


class _HappyPipe:
    def __call__(self, img):
        return [{"label": "happy", "score": 0.9}]


class _NoFaceApp:
    def get(self, bgr):
        return []


class _EmbedFace:
    # 单位向量 [1,0,...]，与同向量 RegisteredFace embedding 点积 = 1.0 > 阈值
    normed_embedding = np.eye(1, 512, dtype=np.float32)[0]


class _KnownFaceApp:
    def get(self, bgr):
        return [_EmbedFace()]


class _SilentVAD:
    def __call__(self, audio, model, sampling_rate=16000):
        return []


class _SpeechVAD:
    def __call__(self, audio, model, sampling_rate=16000):
        return [{"start": 0, "end": 8000}]


class _Whisper:
    def transcribe(self, audio, language="zh"):
        return {"text": "你好世界"}


class InferFrameTests(TestCase):
    @mock.patch("newcell.engine.model_loader.get_mtcnn", return_value=_NoFaceMTCNN())
    @mock.patch("newcell.engine.model_loader.get_expression_pipe", return_value=_HappyPipe())
    @mock.patch("newcell.engine.model_loader.get_insightface", return_value=_NoFaceApp())
    def test_no_face(self, *_):
        resp = self.client.post(
            reverse("expression:infer_frame"),
            {"file": SimpleUploadedFile("f.jpg", _jpeg_bytes())},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertFalse(body["available"])
        self.assertEqual(body["dominant_emotion"], "none")
        self.assertEqual(body["identity"]["person_name"], "unknown")

    @mock.patch("newcell.engine.model_loader.get_mtcnn", return_value=_FaceMTCNN())
    @mock.patch("newcell.engine.model_loader.get_expression_pipe", return_value=_HappyPipe())
    @mock.patch("newcell.engine.model_loader.get_insightface", return_value=_NoFaceApp())
    def test_with_face(self, *_):
        resp = self.client.post(
            reverse("expression:infer_frame"),
            {"file": SimpleUploadedFile("f.jpg", _jpeg_bytes())},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["available"])
        self.assertEqual(body["dominant_emotion"], "happy")

    def test_missing_file(self):
        resp = self.client.post(reverse("expression:infer_frame"), {})
        self.assertEqual(resp.status_code, 400)


class InferAudioTests(TestCase):
    def _post(self, wav):
        return self.client.post(
            reverse("expression:infer_audio"),
            {"file": SimpleUploadedFile("a.wav", wav, content_type="audio/wav")},
        )

    @mock.patch("newcell.engine.model_loader.get_vad", return_value=(object(), (_SilentVAD(),) * 5))
    def test_silent(self, *_):
        resp = self._post(_wav_bytes())
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"has_speech": False, "transcript": ""})

    @mock.patch("newcell.engine.model_loader.get_vad", return_value=(object(), (_SpeechVAD(),) * 5))
    @mock.patch("newcell.engine.model_loader.get_whisper", return_value=_Whisper())
    def test_speech(self, *_):
        resp = self._post(_wav_bytes(frames=np.zeros(16000, dtype=np.int16)))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"has_speech": True, "transcript": "你好世界"})

    def test_invalid_audio(self):
        resp = self._post(b"not a wav file")
        self.assertEqual(resp.status_code, 400)


class InferStatusTests(TestCase):
    def test_status_ok(self):
        resp = self.client.get(reverse("expression:infer_status"))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(resp.json()["state"], {"loading", "ready"})


class RemovedEndpointTests(TestCase):
    def test_old_streams_gone(self):
        for path in ("/api/stream", "/api/video/stream", "/api/camera/start", "/api/camera/stop"):
            self.assertEqual(self.client.get(path).status_code, 404, path)


class FaceInfoTests(TestCase):
    @mock.patch("newcell.engine.model_loader.get_insightface", return_value=_KnownFaceApp())
    def test_register_with_info(self, *_):
        resp = self.client.post(
            reverse("expression:face_register"),
            {
                "name": "李四",
                "gender": "女",
                "student_no": "20240002",
                "major": "心理学",
                "file": SimpleUploadedFile("f.jpg", _jpeg_bytes()),
            },
        )
        self.assertEqual(resp.status_code, 201)
        face = RegisteredFace.objects.get(person_name="李四")
        self.assertEqual(face.gender, "女")
        self.assertEqual(face.student_no, "20240002")
        self.assertEqual(face.major, "心理学")

    def test_face_list_includes_info(self):
        RegisteredFace.objects.create(
            person_name="王五",
            embedding=b"\x00" * 2048,
            gender="男",
            student_no="20240003",
            major="数学",
        )
        resp = self.client.get(reverse("expression:face_list"))
        face = resp.json()["faces"][0]
        self.assertEqual(face["gender"], "男")
        self.assertEqual(face["student_no"], "20240003")
        self.assertEqual(face["major"], "数学")

    @mock.patch("newcell.engine.model_loader.get_mtcnn", return_value=_FaceMTCNN())
    @mock.patch("newcell.engine.model_loader.get_expression_pipe", return_value=_HappyPipe())
    @mock.patch("newcell.engine.model_loader.get_insightface", return_value=_KnownFaceApp())
    def test_infer_frame_known_face_identity_info(self, *_):
        RegisteredFace.objects.create(
            person_name="张三",
            embedding=np.eye(1, 512, dtype=np.float32)[0].tobytes(),
            gender="男",
            student_no="20240001",
            major="计算机科学",
        )
        resp = self.client.post(
            reverse("expression:infer_frame"),
            {"file": SimpleUploadedFile("f.jpg", _jpeg_bytes())},
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertTrue(body["available"])
        identity = body["identity"]
        self.assertEqual(identity["person_name"], "张三")
        self.assertFalse(identity["is_unknown"])
        self.assertEqual(identity["gender"], "男")
        self.assertEqual(identity["student_no"], "20240001")
        self.assertEqual(identity["major"], "计算机科学")


class LLMConfigTests(TestCase):
    def test_get_default(self):
        resp = self.client.get(reverse("expression:llm_config"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["provider"], "ollama")

    def test_put(self):
        resp = self.client.put(
            reverse("expression:llm_config"),
            data=json.dumps({
                "provider": "deepseek",
                "deepseek_api_key": "sk-test",
                "ollama_model": "qwen2.5:7b",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["provider"], "deepseek")
        self.assertEqual(body["deepseek_api_key"], "sk-test")
        cfg = LLMConfig.load()
        self.assertEqual(cfg.provider, "deepseek")
        self.assertEqual(cfg.ollama_model, "qwen2.5:7b")


class InferResultTests(TestCase):
    @mock.patch("newcell.engine.llm.generate_insight", return_value="张三目前情绪平静。")
    def test_result_ok(self, *_):
        resp = self.client.post(
            reverse("expression:infer_result"),
            data=json.dumps({
                "emotion": "neutral",
                "confidence": 0.68,
                "person_name": "张三",
                "transcript": "你好",
            }),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["result"], "张三目前情绪平静。")
        self.assertEqual(body["provider"], "ollama")

    @mock.patch("newcell.engine.llm.generate_insight", side_effect=ConnectionError("refused"))
    def test_result_error(self, *_):
        resp = self.client.post(
            reverse("expression:infer_result"),
            data=json.dumps({"emotion": "neutral"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("error", resp.json())

    @mock.patch("newcell.engine.llm.generate_insight", return_value="张三目前情绪平静。")
    def test_result_context_enriched(self, mock_gen):
        PhysioRecord.objects.create(temp_avg=36.5, hr_avg=42.0, gsr_avg=505.0)
        ExpressionRecord.objects.create(dominant_emotion="neutral", neutral=0.9)
        ExpressionRecord.objects.create(dominant_emotion="happy", happy=0.8)
        resp = self.client.post(
            reverse("expression:infer_result"),
            data=json.dumps({"emotion": "happy", "person_name": "张三", "last_analysis": "上一句"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        system, user_prompt = mock_gen.call_args[0][1], mock_gen.call_args[0][2]
        self.assertIn("专业情绪分析师", system)
        self.assertIn("【生理信号】体温 36.5", user_prompt)
        self.assertIn("【情绪趋势（近几次）】", user_prompt)
        self.assertIn("【上一轮解读】上一句", user_prompt)


class PromptTests(TestCase):
    def test_build_user_prompt_structure(self):
        from newcell.engine import prompts
        p = prompts.build_user_prompt({
            "person": "张三",
            "gender": "男",
            "major": "计算机科学",
            "emotion": "neutral",
            "confidence": 0.68,
            "trend": ["neutral", "neutral", "happy"],
            "physio": "体温 36.5°C，脉搏波形均值 42.0，皮电 505",
            "transcript": "你好",
            "last_analysis": "上一句",
        })
        self.assertIn("【身份】张三（男，计算机科学）", p)
        self.assertIn("【面部表情】主情绪 neutral，置信度 68%", p)
        self.assertIn("【情绪趋势（近几次）】neutral → neutral → happy", p)
        self.assertIn("【生理信号】体温 36.5°C", p)
        self.assertIn("【上一轮解读】上一句", p)
        self.assertIn("请给出本轮专业解读。", p)
