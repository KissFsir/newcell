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


# ---------- 正式报告 ----------

REPORT_CONCLUSION_SYSTEM = (
    "你是多模态情绪状态监测系统的首席分析师。请根据一份监测会话的统计数据，"
    "撰写正式报告的「综合结论与建议」章节。要求：\n"
    "1. 客观、专业、克制，先总结主要情绪表现，再结合语音与生理数据给出解读。\n"
    "2. 分别指出观察到的事实与可能原因，用「推测」「可能」区分。\n"
    "3. 数据缺失时如实说明，不编造。\n"
    "4. 结尾给出 2-3 条具体、可执行的建议（如休息、调节情绪等，仅基于数据合理推断）。\n"
    "5. 输出 150~250 字，分点但用正式书面语，不要写落款署名。"
)

REPORT_FULL_SYSTEM = (
    "你是多模态情绪状态监测系统的首席分析师。请根据一份监测会话的统计数据，"
    "撰写一份完整、正式的中文监测报告。要求：\n"
    "1. 结构含：监测对象、监测时间、情绪状态分析、语音内容摘要、生理指标、综合结论与建议。\n"
    "2. 客观专业，引用数字准确，数据缺失如实说明。\n"
    "3. 综合结论给出 2-3 条可执行建议。\n"
    "4. 全文 400~600 字，正式书面语，可含小标题；"
    "使用纯文本，不要用 Markdown 标记（不要出现 #、*、- 等符号），段落间用空行分隔，不要写落款署名。"
)


def _identity_line(data):
    person = data.get("person") or "未知"
    extras = [x for x in (data.get("gender", ""), data.get("major", "")) if x]
    return f"【监测对象】{person}" + (f"（{'，'.join(extras)}）" if extras else "")


def build_conclusion_prompt(data):
    lines = [
        _identity_line(data),
        f"【主情绪分布】{data.get('emotion_counts') or '（无）'}",
        f"【情绪趋势】{data.get('trend') or '（无）'}",
        f"【语音内容】{data.get('transcript') or '（未采集到有效语音）'}",
        f"【生理指标】{data.get('physio') or '（未采集到生理数据）'}",
        "请撰写上述监测会话的正式报告「综合结论与建议」章节。",
    ]
    return "\n".join(lines)


def build_full_report_prompt(data):
    lines = [
        _identity_line(data),
    ]
    if data.get("time_range"):
        lines.append(f"【监测时间】{data['time_range']}")
    lines.append(f"【主情绪分布】{data.get('emotion_counts') or '（无）'}")
    lines.append(f"【情绪趋势】{data.get('trend') or '（无）'}")
    lines.append(f"【语音内容】{data.get('transcript') or '（未采集到有效语音）'}")
    lines.append(f"【生理指标】{data.get('physio') or '（未采集到生理数据）'}")
    lines.append("请撰写上述监测会话的完整正式报告。")
    return "\n".join(lines)
