"""生理数据：串口配置 + 原始样本 / 聚合历史 / 端口探测。"""
import json

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from newcell.engine import physio as physio_engine


def _serial_payload(cfg):
    return {
        "enabled": cfg.enabled,
        "port_a": cfg.port_a,
        "port_b": cfg.port_b,
        "baudrate": cfg.baudrate,
    }


@csrf_exempt
def settings_serial(request):
    """GET 读取；PUT 更新（改 enabled/端口/波特率并重启读取器）。"""
    from .models import SerialConfig
    if request.method == "PUT":
        try:
            data = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            return JsonResponse({"error": "invalid_json"}, status=400)
        cfg = SerialConfig.load()
        if "enabled" in data:
            cfg.enabled = bool(data["enabled"])
        if "port_a" in data:
            cfg.port_a = str(data["port_a"]).strip() or "COM6"
        if "port_b" in data:
            cfg.port_b = str(data["port_b"]).strip() or "COM5"
        if "baudrate" in data:
            try:
                cfg.baudrate = int(data["baudrate"])
            except (TypeError, ValueError):
                pass
        cfg.save()
        # 重启读取器以应用新配置
        physio_engine.stop_all()
        if cfg.enabled:
            physio_engine.ensure_running()
        return JsonResponse(_serial_payload(cfg))
    return JsonResponse(_serial_payload(SerialConfig.load()))


def serial_ports(request):
    """列出系统可用串口，供设置页下拉选择。"""
    try:
        from serial.tools import list_ports
        ports = [{"device": p.device, "description": p.description} for p in list_ports.comports()]
    except Exception:
        ports = []
    return JsonResponse({"ports": ports})


def physio_latest(request):
    """最近原始样本 + 最新 5s 聚合 + 读取器状态（触发懒启动）。"""
    from .models import PhysioSample, PhysioRecord
    samples = list(PhysioSample.objects.order_by("-timestamp")[:200])
    samples.reverse()  # 时间升序，便于画波形
    latest = PhysioRecord.objects.first()
    return JsonResponse({
        "status": physio_engine.status(),
        "samples": [
            {
                "ts": s.timestamp.isoformat(),
                "port": s.port,
                "temp": s.temp,
                "humidity": s.humidity,
                "pulse": s.pulse,
                "gsr": s.gsr,
            }
            for s in samples
        ],
        "latest": (
            {
                "timestamp": latest.timestamp.isoformat(),
                "temp": latest.temp_avg,
                "humidity": latest.skin_humidity_avg,
                "pulse": latest.hr_avg,
                "gsr": latest.gsr_avg,
            }
            if latest
            else None
        ),
    })


def physio_history(request):
    limit = int(request.GET.get("limit", 200))
    from .models import PhysioRecord
    rows = [
        {
            "timestamp": r.timestamp.isoformat(),
            "temp": r.temp_avg,
            "humidity": r.skin_humidity_avg,
            "pulse": r.hr_avg,
            "gsr": r.gsr_avg,
        }
        for r in PhysioRecord.objects.all()[:limit]
    ]
    return JsonResponse({"rows": rows})
