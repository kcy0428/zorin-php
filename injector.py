#!/usr/bin/env python3
"""
injector.py - 가상 IoT 센서 데이터 생성기
MySQL에 실시간 시뮬레이션 데이터를 주기적으로 삽입합니다.
"""

import subprocess
import time
import random
import math
import signal
import sys
from datetime import datetime

# ── DB 접속 설정 ────────────────────────────────────────────
DB_HOST   = "localhost"
DB_USER   = "shop_user"
DB_PASS   = "Shop@Pass1"
DB_NAME   = "zorinshop"
INTERVAL  = 2   # 삽입 주기 (초)

# ── 장치 목록 ────────────────────────────────────────────────
DEVICES = ["DEV-001", "DEV-002", "DEV-003", "DEV-004", "DEV-005"]

# ── 임계값 ──────────────────────────────────────────────────
THRESHOLDS = {
    "temperature": {"warning": 70.0,  "critical": 85.0},
    "humidity":    {"warning": 80.0,  "critical": 90.0},
    "cpu_usage":   {"warning": 75.0,  "critical": 90.0},
    "memory_usage":{"warning": 80.0,  "critical": 95.0},
}

# ── 장치 상태 (랜덤 워크용) ──────────────────────────────────
device_state = {
    dev: {
        "temp":    random.uniform(30, 60),
        "hum":     random.uniform(30, 60),
        "cpu":     random.uniform(10, 50),
        "mem":     random.uniform(20, 60),
        "net_in":  random.uniform(1, 50),
        "net_out": random.uniform(1, 20),
        "tick":    random.uniform(0, 2 * math.pi),
    }
    for dev in DEVICES
}

running = True


def signal_handler(sig, frame):
    global running
    print("\n[injector] 종료 신호 수신 — 정리 중...")
    running = False


signal.signal(signal.SIGINT,  signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def mysql_exec(sql: str) -> bool:
    """mysql CLI를 통해 SQL을 실행합니다."""
    result = subprocess.run(
        ["mysql", f"-u{DB_USER}", f"-p{DB_PASS}", DB_NAME, "-e", sql],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        err = result.stderr.replace(
            f"mysql: [Warning] Using a password on the command line interface can be insecure.\n", ""
        ).strip()
        if err:
            print(f"  [DB 오류] {err}")
        return False
    return True


def clamp(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def next_value(cur: float, lo: float, hi: float,
               drift: float = 2.0, spike_prob: float = 0.03) -> float:
    """현실적인 랜덤 워크 값을 생성합니다."""
    delta = random.gauss(0, drift)
    if random.random() < spike_prob:
        delta += random.choice([-1, 1]) * random.uniform(10, 20)
    return clamp(cur + delta, lo, hi)


def determine_status(temp, hum, cpu, mem) -> str:
    vals = {
        "temperature":  temp,
        "humidity":     hum,
        "cpu_usage":    cpu,
        "memory_usage": mem,
    }
    status = "normal"
    for key, val in vals.items():
        if val >= THRESHOLDS[key]["critical"]:
            return "critical"
        if val >= THRESHOLDS[key]["warning"]:
            status = "warning"
    return status


def generate_alerts(device_id: str, temp, hum, cpu, mem):
    """임계값 초과 시 alert_log에 기록합니다."""
    checks = [
        ("temperature",  temp, "온도"),
        ("humidity",     hum,  "습도"),
        ("cpu_usage",    cpu,  "CPU 사용률"),
        ("memory_usage", mem,  "메모리 사용률"),
    ]
    for key, val, label in checks:
        th = THRESHOLDS[key]
        if val >= th["critical"]:
            severity = "critical"
            msg = f"{label} 임계치 초과: {val:.1f} (임계값: {th['critical']})"
        elif val >= th["warning"]:
            severity = "warning"
            msg = f"{label} 경고 수준: {val:.1f} (경고값: {th['warning']})"
        else:
            continue

        sql = (
            f"INSERT INTO alert_log (device_id, alert_type, message, severity) VALUES ("
            f"'{device_id}', '{key}', '{msg}', '{severity}');"
        )
        mysql_exec(sql)


def insert_sensor_data(device_id: str, s: dict):
    """sensor_data 테이블에 행 삽입."""
    status = determine_status(s["temp"], s["hum"], s["cpu"], s["mem"])
    sql = (
        f"INSERT INTO sensor_data "
        f"(device_id, temperature, humidity, cpu_usage, memory_usage, "
        f"network_in, network_out, status) VALUES ("
        f"'{device_id}', "
        f"{s['temp']:.2f}, "
        f"{s['hum']:.2f}, "
        f"{s['cpu']:.2f}, "
        f"{s['mem']:.2f}, "
        f"{s['net_in']:.2f}, "
        f"{s['net_out']:.2f}, "
        f"'{status}');"
    )
    return mysql_exec(sql), status


def purge_old_data():
    """1시간 이상 된 레코드 삭제 (테이블 크기 관리)."""
    mysql_exec(
        "DELETE FROM sensor_data WHERE recorded_at < NOW() - INTERVAL 1 HOUR;"
    )
    mysql_exec(
        "DELETE FROM alert_log WHERE created_at < NOW() - INTERVAL 6 HOUR;"
    )


def main():
    print("=" * 60)
    print("  IoT 센서 데이터 인젝터 시작")
    print(f"  DB     : {DB_NAME}@{DB_HOST}")
    print(f"  장치   : {', '.join(DEVICES)}")
    print(f"  주기   : {INTERVAL}초")
    print(f"  종료   : Ctrl+C")
    print("=" * 60)

    tick = 0
    while running:
        now = datetime.now().strftime("%H:%M:%S")
        inserted = 0

        for dev in DEVICES:
            s = device_state[dev]
            s["tick"] += 0.1

            # 랜덤 워크 + 사인파 트렌드
            s["temp"]    = next_value(s["temp"]    + math.sin(s["tick"]) * 0.5, 20, 95)
            s["hum"]     = next_value(s["hum"]     + math.cos(s["tick"]) * 0.3, 10, 100)
            s["cpu"]     = next_value(s["cpu"],     5,  100, drift=3.0, spike_prob=0.05)
            s["mem"]     = next_value(s["mem"],     10, 100, drift=1.5)
            s["net_in"]  = next_value(s["net_in"],  0,  500, drift=10.0)
            s["net_out"] = next_value(s["net_out"], 0,  200, drift=5.0)

            ok, status = insert_sensor_data(dev, s)
            if ok:
                inserted += 1
                icon = {"normal": "✓", "warning": "⚠", "critical": "✗"}[status]
                print(
                    f"  [{now}] {dev} {icon} {status:8s} | "
                    f"T:{s['temp']:5.1f}°C  H:{s['hum']:5.1f}%  "
                    f"CPU:{s['cpu']:5.1f}%  MEM:{s['mem']:5.1f}%  "
                    f"NET↓{s['net_in']:5.1f} ↑{s['net_out']:5.1f} Mbps"
                )
                if status in ("warning", "critical"):
                    generate_alerts(dev, s["temp"], s["hum"], s["cpu"], s["mem"])

        # 10분마다 오래된 데이터 정리
        tick += 1
        if tick % (300 // INTERVAL) == 0:
            purge_old_data()
            print(f"  [{now}] [정리] 오래된 레코드 삭제 완료")

        print(f"  [{now}] → {inserted}/{len(DEVICES)}개 장치 삽입 완료")
        print()

        time.sleep(INTERVAL)

    print("[injector] 종료되었습니다.")


if __name__ == "__main__":
    main()
