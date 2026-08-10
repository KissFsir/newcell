"""AI 情感洞察：LLM 配置读写（settings/llm）+ 结果生成（infer/result）。"""
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from newcell.engine import llm
from .models import LLMConfig

_SYSTEM = (
    "你是多模态情绪识别系统的智能分析助手。请根据用户的表情、身份与最近语音，"
    "用 2-4 句中文简洁描述其当前状态与情绪，语气专业平和，不要编造语音内容。"
)


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


@csrf_exempt
def infer_result(request):
    """POST {emotion, confidence, person_name, transcript} → {result, provider, model}。"""
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

    prompt = (
        f"当前人物：{person}\n"
        f"主情绪：{emotion}（置信度 {confidence:.0%}）\n"
        f"最近语音：{transcript or '（无）'}"
    )

    cfg = LLMConfig.load()
    try:
        text = llm.generate_insight(cfg, _SYSTEM, prompt)
    except Exception as e:
        return JsonResponse({"error": f"AI 分析失败：{e}"})

    model = cfg.ollama_model if cfg.provider == "ollama" else llm.DEEPSEEK_MODEL
    return JsonResponse({"result": text, "provider": cfg.provider, "model": model})
