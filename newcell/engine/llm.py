"""AI 情感洞察的 LLM 调用（零第三方依赖，stdlib urllib）。

两种来源：
- ollama   —— 本地 `POST http://localhost:11434/api/generate`（必须 stream=false，默认是 true）
- deepseek —— OpenAI 兼容 `POST https://api.deepseek.com/chat/completions`，模型写死 deepseek-v4-flash
"""
import json
import urllib.error
import urllib.request

OLLAMA_HOST = "http://localhost:11434"
DEEPSEEK_BASE = "https://api.deepseek.com"
DEEPSEEK_MODEL = "deepseek-v4-flash"

_TIMEOUT = 90  # 秒；Ollama 冷启动加载模型可能要几十秒


def _post_json(url, payload, headers=None):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **(headers or {})},
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as r:
        return json.loads(r.read().decode("utf-8"))


def call_ollama(model, system, prompt, temperature=0.7):
    payload = {
        "model": model,
        "system": system,
        "prompt": prompt,
        "stream": False,  # Ollama 默认流式，必须显式关闭
        "options": {"temperature": temperature, "num_ctx": 4096},
    }
    data = _post_json(f"{OLLAMA_HOST}/api/generate", payload)
    return (data.get("response") or "").strip()


def call_deepseek(api_key, system, prompt, temperature=0.7):
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "temperature": temperature,
    }
    data = _post_json(
        f"{DEEPSEEK_BASE}/chat/completions",
        payload,
        headers={"Authorization": f"Bearer {api_key}"},
    )
    return data["choices"][0]["message"]["content"].strip()


def generate_insight(cfg, system, prompt):
    """按 LLMConfig 分发；异常统一向上抛，由视图转成友好错误。"""
    if cfg.provider == "deepseek":
        if not cfg.deepseek_api_key:
            raise ValueError("未配置 DeepSeek API key，请到「设置」填写")
        return call_deepseek(cfg.deepseek_api_key, system, prompt)
    return call_ollama(cfg.ollama_model or "qwen2.5:7b", system, prompt)
