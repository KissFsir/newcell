"""生理串口读取器：进程内后台线程，双端口并行。

端口 A（温湿度+脉搏）：CSV `温度,脉搏,湿度`
端口 B（皮电）：单值 `gsr`
每收到一行 → 写 PhysioSample；每 5s 窗口 → 写 PhysioRecord 聚合。
端口断开自动重试；原始样本每 5 分钟清理一次（保留 1h）。
"""
import logging
import threading
import time

import serial

logger = logging.getLogger("newcell.engine.physio")

AGGREGATE_SECONDS = 5.0     # 聚合窗口
RETRY_DELAY = 3.0           # 端口断开重试间隔
CLEANUP_INTERVAL = 300      # 清理周期
RETAIN_SECONDS = 3600       # 原始样本保留时长

_status = {}  # kind -> {running, connected, last_ts, rate}


class _PortWorker(threading.Thread):
    """单个端口的读取线程。"""

    def __init__(self, port, kind, baudrate):
        super().__init__(daemon=True)
        self.port = port
        self.kind = kind
        self.baudrate = baudrate
        self._stop = threading.Event()
        self._window = []        # 本聚合窗口的样本
        self._window_start = None

    def stop(self):
        self._stop.set()

    @staticmethod
    def _parse_line(kind, line):
        if kind == "a":
            parts = line.split(",")
            if len(parts) < 3:
                return None
            try:
                return {"temp": float(parts[0]), "pulse": float(parts[1]), "humidity": float(parts[2])}
            except ValueError:
                return None
        try:
            return {"gsr": float(line)}
        except ValueError:
            return None

    def _write_sample(self, parsed):
        from newcell.apps.physio.models import PhysioSample
        PhysioSample.objects.create(
            port=self.kind,
            temp=parsed.get("temp", 0.0),
            humidity=parsed.get("humidity", 0.0),
            pulse=parsed.get("pulse", 0.0),
            gsr=parsed.get("gsr", 0.0),
        )

    def _flush_window(self):
        if not self._window:
            return
        n = len(self._window)
        hr = [s["pulse"] for s in self._window if "pulse" in s]
        temps = [s["temp"] for s in self._window if "temp" in s]
        hums = [s["humidity"] for s in self._window if "humidity" in s]
        gsrs = [s["gsr"] for s in self._window if "gsr" in s]

        from newcell.apps.physio.models import PhysioRecord
        PhysioRecord.objects.create(
            hr_avg=sum(hr) / n if hr else 0.0,
            hr_min=min(hr) if hr else 0.0,
            hr_max=max(hr) if hr else 0.0,
            temp_avg=sum(temps) / n if temps else 0.0,
            skin_humidity_avg=sum(hums) / n if hums else 0.0,
            gsr_avg=sum(gsrs) / n if gsrs else 0.0,
        )
        self._window = []

    def _cleanup(self):
        from datetime import timedelta
        from django.utils import timezone as dj_tz
        from newcell.apps.physio.models import PhysioSample
        PhysioSample.objects.filter(
            timestamp__lt=dj_tz.now() - timedelta(seconds=RETAIN_SECONDS)
        ).delete()

    def run(self):
        rate_count = 0
        rate_ts = time.time()
        last_cleanup = time.time()
        while not self._stop.is_set():
            ser = None
            try:
                ser = serial.Serial(self.port, self.baudrate, timeout=0.2)
            except Exception as e:
                logger.warning("physio open %s failed: %s", self.port, e)
                _status.setdefault(self.kind, {})["connected"] = False
                if self._stop.wait(RETRY_DELAY):
                    return
                continue

            _status[self.kind] = {"running": True, "connected": True, "last_ts": time.time(), "rate": 0.0}
            try:
                while not self._stop.is_set():
                    try:
                        raw = ser.readline()
                    except serial.SerialException:
                        break  # 端口断开
                    if not raw:
                        continue
                    line = raw.decode("utf-8", "ignore").strip()
                    if not line:
                        continue
                    parsed = self._parse_line(self.kind, line)
                    if parsed is None:
                        continue

                    now = time.time()
                    if self._window_start is None:
                        self._window_start = now
                    self._window.append(parsed)
                    if now - self._window_start >= AGGREGATE_SECONDS:
                        self._flush_window()
                        self._window_start = None

                    self._write_sample(parsed)

                    # 采样率统计（每秒更新）
                    rate_count += 1
                    if now - rate_ts >= 1.0:
                        _status[self.kind]["rate"] = rate_count
                        rate_count = 0
                        rate_ts = now
                    _status[self.kind]["last_ts"] = now

                    if now - last_cleanup >= CLEANUP_INTERVAL:
                        last_cleanup = now
                        try:
                            self._cleanup()
                        except Exception:
                            logger.exception("physio cleanup failed")

            finally:
                if ser is not None:
                    try:
                        ser.close()
                    except Exception:
                        pass
                if self._window:
                    self._flush_window()

            _status.setdefault(self.kind, {})["connected"] = False
            if self._stop.wait(RETRY_DELAY):
                return

        _status.setdefault(self.kind, {})["running"] = False
        _status.setdefault(self.kind, {})["connected"] = False


class PhysioReader:
    def __init__(self, port_a, port_b, baudrate):
        self.workers = []
        for kind, port in (("a", port_a), ("b", port_b)):
            if port and port.strip():
                self.workers.append(_PortWorker(port.strip(), kind, baudrate))

    def start(self):
        for w in self.workers:
            w.start()

    def stop(self):
        for w in self.workers:
            w.stop()

    def is_alive(self):
        return any(w.is_alive() for w in self.workers)


_reader = None
_reader_lock = threading.Lock()


def ensure_running():
    """配置 enabled 且未运行则（重）启动读取器。"""
    global _reader
    from newcell.apps.physio.models import SerialConfig
    cfg = SerialConfig.load()
    if not cfg.enabled:
        return False
    with _reader_lock:
        if _reader is not None and _reader.is_alive():
            return True
        try:
            if _reader is not None:
                _reader.stop()
        except Exception:
            pass
        _reader = PhysioReader(cfg.port_a, cfg.port_b, cfg.baudrate)
        _reader.start()
        return True


def stop_all():
    global _reader
    with _reader_lock:
        if _reader is not None:
            _reader.stop()
        _reader = None


def status():
    """触发懒启动并返回每端口状态 {a:{connected,running,rate}, b:{...}}。"""
    try:
        ensure_running()
    except Exception:
        logger.exception("physio ensure_running failed")
    out = {}
    for kind in ("a", "b"):
        st = _status.get(kind, {})
        last = st.get("last_ts")
        connected = bool(st.get("connected")) and last is not None and (time.time() - last < 3.0)
        out[kind] = {
            "connected": connected,
            "running": bool(st.get("running")),
            "rate": round(st.get("rate", 0.0), 1),
        }
    return out
