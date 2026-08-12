"""正式报告：配置（settings/report）+ 生成（report/generate）+ 历史（reports）+ PDF。"""
import io
import json

from django.http import HttpResponse, JsonResponse
from django.utils import timezone as dj_tz
from django.views.decorators.csrf import csrf_exempt

from newcell.engine import llm, prompts
from .models import ReportConfig, ReportRecord, LLMConfig


def _payload(cfg):
    return {"mode": cfg.mode}


@csrf_exempt
def settings_report(request):
    """GET 读取；PUT 更新报告形式（structured | ai）。"""
    if request.method == "PUT":
        try:
            data = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid_json"}, status=400)
        cfg = ReportConfig.load()
        if "mode" in data:
            cfg.mode = "ai" if data["mode"] == "ai" else "structured"
        cfg.save()
        return JsonResponse(_payload(cfg))
    return JsonResponse(_payload(ReportConfig.load()))


def _parse_dt(s):
    if not s:
        return None
    try:
        return dj_tz.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except ValueError:
        return None


def _fmt_counts(counts):
    if not counts:
        return "（无）"
    items = sorted(counts.items(), key=lambda x: -x[1])
    return "，".join(f"{k} {v}次" for k, v in items)


def _fmt_physio(p):
    if not p:
        return ""
    parts = []
    if p.get("temp"):
        parts.append(f"体温均值{p['temp'][0]:.1f}°C（{p['temp'][1]:.1f}~{p['temp'][2]:.1f}）")
    if p.get("pulse"):
        parts.append(f"脉搏均值{p['pulse'][0]:.1f}（{p['pulse'][1]:.1f}~{p['pulse'][2]:.1f}）")
    if p.get("gsr"):
        parts.append(f"皮电均值{p['gsr'][0]:.0f}（{p['gsr'][1]:.0f}~{p['gsr'][2]:.0f}）")
    return "，".join(parts)


def _stats(start, end, person):
    """按时间窗统计会话数据，返回结构化 dict。"""
    from .models import ExpressionRecord, RegisteredFace
    from newcell.apps.physio.models import PhysioRecord
    from newcell.apps.speech.models import TranscriptRecord

    exprs = list(ExpressionRecord.objects.filter(timestamp__range=(start, end)))
    counts = {}
    trend = []
    for e in exprs:
        counts[e.dominant_emotion] = counts.get(e.dominant_emotion, 0) + 1
        trend.append(e.dominant_emotion)

    transcripts = [t.text for t in TranscriptRecord.objects.filter(timestamp__range=(start, end)) if t.text]
    transcript_text = "；".join(transcripts[-5:])

    physio = {}
    rows = list(PhysioRecord.objects.filter(timestamp__range=(start, end)))
    if rows:
        def agg(field):
            vals = [getattr(r, field) for r in rows if getattr(r, field)]
            return (sum(vals) / len(vals), min(vals), max(vals)) if vals else None
        physio = {
            "temp": agg("temp_avg"),
            "pulse": agg("hr_avg"),
            "gsr": agg("gsr_avg"),
        }

    face = RegisteredFace.objects.filter(person_name=person).first()
    return {
        "emotion_counts": counts,
        "trend": trend,
        "transcript": transcript_text,
        "physio": physio,
        "info": {"gender": face.gender if face else "", "major": face.major if face else ""},
    }


@csrf_exempt
def report_generate(request):
    """POST {start, end, person_name} → 生成并落库，返回报告。"""
    if request.method != "POST":
        return JsonResponse({"error": "method_not_allowed"}, status=405)
    try:
        data = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "invalid_json"}, status=400)

    start = _parse_dt(data.get("start"))
    end = _parse_dt(data.get("end"))
    person = str(data.get("person_name", "unknown"))
    if start is None or end is None or start > end:
        return JsonResponse({"error": "invalid_time_range"}, status=400)

    stats = _stats(start, end, person)
    info = stats["info"]

    # 模板：本次请求 mode 优先，未传则用全局默认
    requested = str(data.get("mode", ""))
    mode = ("ai" if requested == "ai" else "structured") if requested else ReportConfig.load().mode
    cfg_llm = LLMConfig.load()

    content = {
        "mode": mode,
        "person": person,
        "gender": info["gender"],
        "major": info["major"],
        "start": start.isoformat(),
        "end": end.isoformat(),
        "emotion_counts": stats["emotion_counts"],
        "trend": stats["trend"],
        "transcript": stats["transcript"],
        "physio": stats["physio"],
    }

    data_for_prompt = {
        "person": person,
        "gender": info["gender"],
        "major": info["major"],
        "emotion_counts": _fmt_counts(stats["emotion_counts"]),
        "trend": " → ".join(stats["trend"]) if stats["trend"] else "（无）",
        "transcript": stats["transcript"] or "（未采集到有效语音）",
        "physio": _fmt_physio(stats["physio"]) or "（未采集到生理数据）",
        "time_range": (
            f"{start.strftime('%Y-%m-%d %H:%M:%S')} ~ {end.strftime('%Y-%m-%d %H:%M:%S')}"
        ),
    }

    try:
        if mode == "ai":
            content["text"] = llm.generate_insight(
                cfg_llm, prompts.REPORT_FULL_SYSTEM, prompts.build_full_report_prompt(data_for_prompt)
            )
        else:
            content["conclusion"] = llm.generate_insight(
                cfg_llm, prompts.REPORT_CONCLUSION_SYSTEM, prompts.build_conclusion_prompt(data_for_prompt)
            )
    except Exception as e:
        return JsonResponse({"error": f"报告生成失败：{e}"})

    record = ReportRecord.objects.create(
        person_name=person, mode=mode, start_time=start, end_time=end, content=content
    )
    return JsonResponse(_record_payload(record))


def _record_payload(r):
    return {
        "id": r.id,
        "person_name": r.person_name,
        "mode": r.mode,
        "created_at": r.created_at.isoformat(),
        "start_time": r.start_time.isoformat() if r.start_time else None,
        "end_time": r.end_time.isoformat() if r.end_time else None,
        "content": r.content,
    }


def report_list(request):
    """历史报告列表，支持按 person / start / end（created_at 范围）过滤。"""
    limit = int(request.GET.get("limit", 200))
    qs = ReportRecord.objects.all()

    person = request.GET.get("person", "").strip()
    if person:
        qs = qs.filter(person_name=person)
    start = _parse_dt(request.GET.get("start"))
    end = _parse_dt(request.GET.get("end"))
    if start:
        qs = qs.filter(created_at__gte=start)
    if end:
        qs = qs.filter(created_at__lte=end)

    persons = list(
        ReportRecord.objects.values_list("person_name", flat=True).distinct().order_by("person_name")
    )
    return JsonResponse({
        "reports": [_record_payload(r) for r in qs[:limit]],
        "persons": persons,
    })


@csrf_exempt
def report_detail(request, report_id):
    try:
        r = ReportRecord.objects.get(id=report_id)
    except ReportRecord.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)
    if request.method == "DELETE":
        r.delete()
        return JsonResponse({"deleted": True})
    return JsonResponse(_record_payload(r))


def report_pdf(request, report_id):
    """把报告渲染成可下载的 PDF（reportlab + STSong-Light 中文字体）。"""
    try:
        r = ReportRecord.objects.get(id=report_id)
    except ReportRecord.DoesNotExist:
        return JsonResponse({"error": "not_found"}, status=404)
    buf = io.BytesIO()
    _build_pdf(buf, r)
    resp = HttpResponse(buf.getvalue(), content_type="application/pdf")
    resp["Content-Disposition"] = f'attachment; filename="report-{r.id}.pdf"'
    return resp


def _fmt_pdf_counts(counts):
    if not counts:
        return "（未采集到有效表情数据）"
    items = sorted(counts.items(), key=lambda x: -x[1])
    return "；".join(f"{k} {v} 次" for k, v in items)


def _fmt_pdf_physio(p):
    if not p:
        return "（未采集到生理数据）"
    parts = []
    if p.get("temp"):
        parts.append(f"体温均值 {p['temp'][0]:.1f}°C（{p['temp'][1]:.1f}~{p['temp'][2]:.1f}）")
    if p.get("pulse"):
        parts.append(f"脉搏均值 {p['pulse'][0]:.1f}（{p['pulse'][1]:.1f}~{p['pulse'][2]:.1f}）")
    if p.get("gsr"):
        parts.append(f"皮电均值 {p['gsr'][0]:.0f}（{p['gsr'][1]:.0f}~{p['gsr'][2]:.0f}）")
    return "；".join(parts) if parts else "（未采集到生理数据）"


def _fmt_pdf_trend(trend):
    if not trend:
        return "（无）"
    compressed = []
    for e in trend:
        if not compressed or compressed[-1] != e:
            compressed.append(e)
    return "、".join(compressed[:8]) + ("等" if len(compressed) > 8 else "")


def _build_pdf(buf, r):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

    base = getSampleStyleSheet()["Normal"]
    title = ParagraphStyle("title", parent=base, fontName="STSong-Light", fontSize=18, leading=24, alignment=1, spaceAfter=4)
    meta = ParagraphStyle("meta", parent=base, fontName="STSong-Light", fontSize=9, leading=14, alignment=1, textColor=colors.grey)
    heading = ParagraphStyle("heading", parent=base, fontName="STSong-Light", fontSize=12, leading=17, spaceBefore=12, spaceAfter=5)
    body = ParagraphStyle("body", parent=base, fontName="STSong-Light", fontSize=10.5, leading=17)
    foot = ParagraphStyle("foot", parent=base, fontName="STSong-Light", fontSize=9, leading=14, alignment=2, textColor=colors.grey)

    c = r.content or {}
    story = []
    story.append(Paragraph("情绪状态监测报告", title))
    story.append(Paragraph(f"报告编号 NC-{str(r.id).zfill(4)} · 生成时间 {r.created_at.strftime('%Y-%m-%d %H:%M')}", meta))
    story.append(Spacer(1, 6))

    def fmt_dt(s):
        if not s:
            return "—"
        try:
            return dj_tz.datetime.fromisoformat(str(s).replace("Z", "+00:00")).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "—"

    if r.mode == "ai":
        for para in (c.get("text") or "").split("\n"):
            para = para.strip()
            if para:
                story.append(Paragraph(para, body))
    else:
        extras = [x for x in (c.get("gender", ""), c.get("major", "")) if x]
        identity = c.get("person", "未知") + (f"（{'，'.join(extras)}）" if extras else "")
        story.append(Paragraph("一、监测对象", heading))
        story.append(Paragraph(f"姓名：{identity}", body))
        story.append(Paragraph(f"监测时间：{fmt_dt(c.get('start'))} ~ {fmt_dt(c.get('end'))}", body))

        story.append(Paragraph("二、情绪状态分析", heading))
        story.append(Paragraph(f"主情绪分布：{_fmt_pdf_counts(c.get('emotion_counts'))}", body))
        story.append(Paragraph(f"情绪变化：{_fmt_pdf_trend(c.get('trend'))}", body))

        story.append(Paragraph("三、语音内容摘要", heading))
        story.append(Paragraph(c.get("transcript") or "（未采集到有效语音）", body))

        story.append(Paragraph("四、生理指标", heading))
        story.append(Paragraph(_fmt_pdf_physio(c.get("physio")), body))

        story.append(Paragraph("五、综合结论与建议", heading))
        story.append(Paragraph(c.get("conclusion") or "（结论生成中）", body))

    story.append(Spacer(1, 18))
    story.append(Paragraph("新元多模态情绪识别系统", foot))
    story.append(Paragraph(dj_tz.now().strftime("%Y-%m-%d"), foot))

    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=24 * mm, bottomMargin=20 * mm,
                            leftMargin=22 * mm, rightMargin=22 * mm, title="情绪状态监测报告")
    doc.build(story)
