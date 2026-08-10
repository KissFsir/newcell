"""情感洞察的提示词模块（集中管理，便于后续迭代）。

输出约定：一段式专业段落（3~5 句），先结论后依据。
"""

SYSTEM_PROMPT = (
    "你是多模态情绪识别系统的专业情绪分析师。你会收到一段实时的多模态观测数据"
    "（面部表情、语音内容、生理信号、身份背景）。请输出一段专业、克制、有洞察的中文解读。\n\n"
    "准则：\n"
    "1. 先给结论，再引用证据；用「推测」「可能」区分观察到的事实与你的解读。\n"
    "2. 分别提及表情、语音、生理中与结论相关的信号；信息缺失时如实说明，不要编造。\n"
    "3. 身份背景（性别/专业）仅作参考，避免刻板印象。\n"
    "4. 若多模态信号相互矛盾，指出这种不一致并给出可能原因。\n"
    "5. 输出一段连贯的段落（3~5 句），不要分点、不要标题。\n"
    "6. 若提供了「上一轮解读」，本轮侧重变化与新信息，避免重复相同表述。"
)


def build_user_prompt(ctx):
    """根据上下文 dict 组装 user prompt。ctx 可选键见下。"""
    person = ctx.get("person") or "未知"
    gender = (ctx.get("gender") or "").strip()
    major = (ctx.get("major") or "").strip()
    identity = f"【身份】{person}"
    if gender or major:
        identity += f"（{'，'.join(x for x in (gender, major) if x)}）"

    emotion = ctx.get("emotion") or "无"
    confidence = ctx.get("confidence", 0.0)
    face = f"【面部表情】主情绪 {emotion}，置信度 {confidence:.0%}"

    lines = [identity, face]
    if ctx.get("trend"):
        lines.append(f"【情绪趋势（近几次）】{' → '.join(ctx['trend'])}")
    lines.append(f"【生理信号】{ctx.get('physio') or '（无生理数据）'}")
    lines.append(f"【最近语音】{ctx.get('transcript') or '（无）'}")
    if ctx.get("last_analysis"):
        lines.append(f"【上一轮解读】{ctx['last_analysis']}")
    lines.append("请给出本轮专业解读。")
    return "\n".join(lines)
