#!/usr/bin/env python3
"""串口传输性能测量：统计行数/秒、字节/秒、采样间隔抖动。

给板子端的人测传输性能用（接真实 Arduino 板跑）：
    python serial_measure.py <端口> [波特率=115200] [时长秒=10]

例：
    python serial_measure.py COM6            # Windows
    python serial_measure.py /dev/cu.usbserial-XXX 115200 15
"""
import sys
import time

import serial


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    port = sys.argv[1]
    baud = int(sys.argv[2]) if len(sys.argv) > 2 else 115200
    duration = float(sys.argv[3]) if len(sys.argv) > 3 else 10.0

    ser = serial.Serial(port, baud, timeout=0.2)
    print(f"读取 {port} @ {baud} 波特，持续 {duration}s ...")
    lines = 0
    bytes_total = 0
    intervals = []
    prev = None
    start = time.time()
    while time.time() - start < duration:
        raw = ser.readline()
        if not raw:
            continue
        now = time.time()
        lines += 1
        bytes_total += len(raw)
        if prev is not None:
            intervals.append(now - prev)
        prev = now
    ser.close()

    elapsed = time.time() - start
    n = len(intervals)
    if n:
        avg_ms = sum(intervals) / n * 1000.0
        jitter_ms = (max(intervals) - min(intervals)) * 1000.0
    else:
        avg_ms = 0.0
        jitter_ms = 0.0

    print("-" * 56)
    print(f"时长        : {elapsed:.2f} s")
    print(f"行数        : {lines}")
    print(f"行速率      : {lines / elapsed:.1f} 行/s")
    print(f"字节速率    : {bytes_total / elapsed:.1f} B/s")
    print(f"行间隔均值  : {avg_ms:.2f} ms")
    print(f"行间隔抖动  : {jitter_ms:.2f} ms  (max-min)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
