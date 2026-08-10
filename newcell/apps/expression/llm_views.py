"""AI 情感洞察：LLM 配置读写（settings/llm）+ 结果生成（infer/result）。"""
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from newcell.engine import llm
from newcell.engine import prompts
from .models import LLMConfig


def _payload(cfg):
    return {
        "provider": cfg.provider,
        "ollama_model": cfg.ollama_model,
        "deepseek_api_key": cfg.deepseek_api_key,
    }


@csrf_exempt
def llm_config(request):
    """GET 读取；PUT 更新（JSON body，字段可选）。"""
    if request.method == "PUT":
        try:
            data = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid_json"}, status=400)
        cfg = LLMConfig.load()
        if "provider" in data:
            cfg.provider = "deepseek" if data["provider"] == "deepseek" else "ollama"
        if "ollama_model" in data:
            cfg.ollama_model = str(data["ollama_model"]).strip() or "qwen2.5:7b"
        if "deepseek_api_key" in data:
            cfg.deepseek_api_key = str(data["deepseek_api_key"]).strip()
        cfg.save()
        return JsonResponse(_payload(cfg))
    return JsonResponse(_payload(LLMConfig.load()))


def _build_context(emotion, confidence, person, transcript, last_analysis=""):
    """用 DB 补充身份/情绪趋势/生理上下文，返回 prompts.build_user_prompt 用的 ctx。"""
    from .models import RegisteredFace, ExpressionRecord
    from newcell.apps.physio.models import PhysioRecord

    ctx = {
        "emotion": emotion,
        "confidence": confidence,
        "person": person,
        "transcript": transcript,
        "last_analysis": last_analysis,
    }

    face = RegisteredFace.objects.filter(person_name=person).first()
    if face is not None:
        ctx["gender"] = face.gender
        ctx["major"] = face.major

    records = list(ExpressionRecord.objects.all()[:5])
    records.reverse()  # 时间正序
    if records:
        ctx["trend"] = [r.dominant_emotion for r in records]

    p = PhysioRecord.objects.first()
    if p is not None:
        ctx["physio"] = (
            f"体温 {p.temp_avg:.1f}°C，脉搏波形均值 {p.hr_avg:.1f}，皮电 {p.gsr_avg:.0f}"
        )
    return ctx


@csrf_exempt
def infer_result(request):
    """POST {emotion, confidence, person_name, transcript, last_analysis} → {result, provider, model}。"""
    if request.method != "POST":
        return JsonResponse({"error": "method_not_allowed"}, status=405)
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    emotion = str(data.get("emotion", "none"))
    confidence = float(data.get("confidence", 0) or 0)
    person = str(data.get("person_name", "unknown"))
    transcript = str(data.get("transcript", "")).strip()[:300]
    last_analysis = str(data.get("last_analysis", "")).strip()[:500]

    ctx = _build_context(emotion, confidence, person, transcript, last_analysis)
    user_prompt = prompts.build_user_prompt(ctx)

    cfg = LLMConfig.load()
    try:
        text = llm.generate_insight(cfg, prompts.SYSTEM_PROMPT, user_prompt)
    except Exception as e:
        return JsonResponse({"error": f"AI 分析失败：{e}"})

    model = cfg.ollama_model if cfg.provider == "ollama" else llm.DEEPSEEK_MODEL
    return JsonResponse({"result": text, "provider": cfg.provider, "model": model})
