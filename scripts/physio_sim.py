#!/usr/bin/env python3
"""生理数据模拟器（macOS/Linux）：用 pty 创建两个虚拟串口，持续输出两块板的数据格式。

本机没有真实 Arduino 板时，用它测后端读取链路：
  1. 运行本脚本，记下打印的两个虚拟端口路径（A / B）；
  2. 到「设置 → 生理数据采集」把端口 A/B 填成这两个路径，开启采集；
  3. 刷新监控面板，生理面板应出现脉搏波形 + 温度/湿度/皮电数值。

Ctrl+C 退出。
"""
import fcntl
import math
import os
import pty
import sys
import threading
import time


def make_virtual_port():
    master, slave = pty.openpty()
    flags = fcntl.fcntl(master, fcntl.F_GETFL)
    fcntl.fcntl(master, fcntl.F_SETFL, flags | os.O_NONBLOCK)
    return master, os.ttyname(slave)


def write_safe(master, data):
    try:
        os.write(master, data)
    except OSError:
        pass  # 无读取端 / 缓冲区满时丢弃，避免阻塞


def stream_port(master, kind):
    t = 0.0
    while True:
        if kind == "a":
            temp = 25.0 + 0.4 * math.sin(2 * math.pi * 0.02 * t)          # 25.0±0.4 缓变
            pulse = 42.0 + 9.0 * math.sin(2 * math.pi * 1.2 * t) + 1.5 * math.sin(2 * math.pi * 4.0 * t)  # 脉搏波形 ~1.2Hz
            humidity = 58.0 + 2.0 * math.sin(2 * math.pi * 0.05 * t)       # 58±2 缓变
            line = f"{temp:.1f},{pulse:.1f},{humidity:.1f}\n"
        else:
            gsr = 500.0 + 40.0 * math.sin(2 * math.pi * 0.25 * t)          # 皮电 500±40
            line = f"{int(gsr)}\n"
        write_safe(master, line.encode())
        t += 0.05
        time.sleep(0.05)  # 20Hz


if __name__ == "__main__":
    ma, pa = make_virtual_port()
    mb, pb = make_virtual_port()
    print("虚拟端口 A（温湿度+脉搏）:", pa)
    print("虚拟端口 B（皮电）:       ", pb)
    print("把这两个路径填到「设置 → 生理数据采集」并开启，再刷新监控面板。Ctrl+C 退出。")
    sys.stdout.flush()
    threading.Thread(target=stream_port, args=(ma, "a"), daemon=True).start()
    threading.Thread(target=stream_port, args=(mb, "b"), daemon=True).start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n退出。")
        try:
            os.close(ma)
            os.close(mb)
        except OSError:
            pass
