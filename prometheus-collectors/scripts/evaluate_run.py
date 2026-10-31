#!/usr/bin/env python3
"""evaluate_run.py.

Automated Comparative Evaluator for Master Thesis
Calculates: MTTD, JMeter Client Metrics, Upstream Thread Pressure, Overhead.
"""

from datetime import datetime
import json
import sys
import numpy as np
import pandas as pd
import requests

PROMETHEUS_URL = "http://localhost:9090"


def query_prometheus(query: str, time_sec: float):
    try:
        r = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query",
            params={"query": query, "time": time_sec},
            timeout=5,
        )
        data = r.json()
        if (
            data["status"] == "success"
            and len(data["data"]["result"]) > 0
            and "value" in data["data"]["result"][0]
        ):
            return float(data["data"]["result"][0]["value"][1])
    except Exception:
        pass
    return None


def query_prometheus_range(
    query: str, start_sec: float, end_sec: float, step: int = 1
):
    try:
        r = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query_range",
            params={
                "query": query,
                "start": start_sec,
                "end": end_sec,
                "step": f"{step}s",
            },
            timeout=10,
        )
        data = r.json()
        if data["status"] == "success" and len(data["data"]["result"]) > 0:
            values = data["data"]["result"][0]["values"]
            return [float(v[1]) for v in values if v[1] is not None]
    except Exception:
        pass
    return []


def analyze_jmeter(jtl_file: str, start_epoch_ms: int, end_epoch_ms: int):
    print(f"[*] Parsing JMeter file: {jtl_file}...")
    df = pd.read_csv(jtl_file)

    # Filter to test window
    if "timeStamp" in df.columns:
        df = df[
            (df["timeStamp"] >= start_epoch_ms)
            & (df["timeStamp"] <= end_epoch_ms)
        ]

    total_requests = len(df)
    if total_requests == 0:
        return {}

    # JMeter success column is usually boolean True/False
    failed_df = df[df["success"] == False]
    error_count = len(failed_df)
    error_rate = (error_count / total_requests) * 100.0

    # Latency distribution (elapsed time in ms)
    latencies = df["elapsed"]
    mean_lat = latencies.mean()
    p95_lat = np.percentile(latencies, 95)
    max_lat = latencies.max()

    # Response codes breakdown
    code_counts = (
        failed_df["responseCode"].value_counts().to_dict()
        if error_count > 0
        else {}
    )

    return {
        "total_requests": total_requests,
        "error_count": error_count,
        "error_rate": error_rate,
        "mean_latency": mean_lat,
        "p95_latency": p95_lat,
        "max_latency": max_lat,
        "error_breakdown": code_counts,
    }


def find_cb_trip_time(
    service_name: str, start_sec: float, end_sec: float, step: int = 1
):
    """Finds exact timestamp Resilience4j transitioned to state 1 (OPEN)."""
    # Resilience4j state: 0 = CLOSED, 1 = OPEN, 2 = HALF_OPEN
    query = f'resilience4j_circuitbreaker_state{{application="{service_name}", state="open"}}'
    try:
        r = requests.get(
            f"{PROMETHEUS_URL}/api/v1/query_range",
            params={
                "query": query,
                "start": start_sec,
                "end": end_sec,
                "step": f"{step}s",
            },
            timeout=10,
        )
        data = r.json()
        if data["status"] == "success" and len(data["data"]["result"]) > 0:
            for v in data["data"]["result"][0]["values"]:
                timestamp, val = float(v[0]), float(v[1])
                if val == 1.0:
                    return timestamp
    except Exception:
        pass
    return None


def main():
    if len(sys.argv) < 5:
        print(
            "Usage: python evaluate_run.py <mode: reactive|proactive> <inject_time_str: 'YYYY-MM-DD HH:MM:SS'> <duration_sec> <jmeter_jtl_file>"
        )
        print(
            "Example: python evaluate_run.py proactive '2026-10-31 10:15:00' 120 results.csv"
        )
        sys.exit(1)


    mode = "reactive"
    inject_str = "2026-10-31 10:15:00"
    duration_sec = 120
    jtl_file = "results.csv"

    # Convert injection time
    t_inject_dt = datetime.strptime(inject_str, "%Y-%m-%d %H:%M:%S")
    t_inject_sec = t_inject_dt.timestamp()
    t_end_sec = t_inject_sec + duration_sec

    print(f"\n=======================================================")
    print(f"   EVALUATING {mode.upper()} EXPERIMENT RUN")
    print(f"=======================================================")
    print(f"Fault Injected At : {inject_str} ({int(t_inject_sec)})")
    print(f"Evaluation Window : {duration_sec}s (until {int(t_end_sec)})")

    # 1. Detection Speed (MTTD)
    cb_trip_time = find_cb_trip_time(
        "order_service", t_inject_sec, t_end_sec, step=1
    )
    if cb_trip_time:
        mttd = cb_trip_time - t_inject_sec
        trip_str = datetime.fromtimestamp(cb_trip_time).strftime(
            "%Y-%m-%d %H:%M:%S"
        )
        print(f"\n[Q2: Detection Speed]")
        print(f" - Circuit Breaker OPEN at: {trip_str}")
        print(f" - MTTD (Mean Time to Detect / Trip): {mttd:.2f} seconds")
    else:
        mttd = None
        print(f"\n[Q2: Detection Speed]")
        print(f" - Circuit Breaker: Did NOT trip to OPEN in window")

    # 2. Client Metrics (JMeter)
    jmeter_res = analyze_jmeter(
        jtl_file, int(t_inject_sec * 1000), int(t_end_sec * 1000)
    )
    print(f"\n[Q1: Client Failure Impact]")
    if jmeter_res:
        print(f" - Total Requests Sent   : {jmeter_res['total_requests']}")
        print(
            f" - Failed Requests        : {jmeter_res['error_count']} ({jmeter_res['error_rate']:.2f}%)"
        )
        print(f" - Mean Client Latency   : {jmeter_res['mean_latency']:.2f} ms")
        print(f" - P95 Client Latency    : {jmeter_res['p95_latency']:.2f} ms")
        print(f" - Max Client Latency    : {jmeter_res['max_latency']:.2f} ms")
        print(f" - Error Code Breakdown  : {jmeter_res['error_breakdown']}")

    # 3. Upstream Thread & Cascading Pressure (Order Service & Gateway)
    order_active = query_prometheus_range(
        'sum(otel_http_server_requests_active_milliseconds_count{application="order_service"})',
        t_inject_sec,
        t_end_sec,
    )
    order_threads = query_prometheus_range(
        'sum(otel_jvm_threads_live{application="order_service"})',
        t_inject_sec,
        t_end_sec,
    )
    gw_active = query_prometheus_range(
        'sum(otel_http_server_requests_active_milliseconds_count{application="gateway"})',
        t_inject_sec,
        t_end_sec,
    )

    peak_order_active = max(order_active) if order_active else 0
    peak_order_threads = max(order_threads) if order_threads else 0
    peak_gw_active = max(gw_active) if gw_active else 0

    print(f"\n[Q3: Cascading Failure Prevention]")
    print(
        f" - Order Service Peak Active Requests : {peak_order_active} concurrent"
    )
    print(f" - Order Service Peak Live Threads     : {peak_order_threads}")
    print(
        f" - Gateway Peak Active Requests        : {peak_gw_active} concurrent"
    )

    print(f"\n=======================================================\n")


if __name__ == "__main__":
    main()