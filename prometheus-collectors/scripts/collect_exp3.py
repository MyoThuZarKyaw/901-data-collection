import os
import requests
import pandas as pd
from datetime import datetime, timezone

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================
PROMETHEUS_URL = "http://localhost:9090/api/v1/query_range"
TARGET_SERVICE = "payment_service" #  inventory_service or payment_service
STEP = "2s"  # Set to "1s" or "2s"

# Your exact experiment window (in your local Mac time)
START_TIME_STR = "2026-09-18 11:19:52"
END_TIME_STR = "2026-09-18 11:29:52"

OUTPUT_FILE = f"raw_data/exp3_burst_healthy_payment.csv"  # exp3_burst_healthy_inventory or exp3_burst_healthy_payment

# ==============================================================================
# 2. FIXED TIMESTAMP CONVERSION (Uses Local Mac Timezone)
# ==============================================================================
start_dt = datetime.strptime(START_TIME_STR, "%Y-%m-%d %H:%M:%S")
end_dt = datetime.strptime(END_TIME_STR, "%Y-%m-%d %H:%M:%S")

START_TS = int(start_dt.timestamp())
END_TS = int(end_dt.timestamp())

# ==============================================================================
# 3. QUERIES (Matching your Prometheus metrics)
# ==============================================================================
QUERIES = {
    # CPU
    "target_cpu": f'otel_process_cpu_usage{{application="{TARGET_SERVICE}"}} * 100',

    # Memory (used / committed avoids the 3-pool heap split issue)
    "target_mem": f'sum(otel_jvm_memory_used_bytes{{area="heap", application="{TARGET_SERVICE}"}}) / sum(otel_jvm_memory_max_bytes{{area="heap", application="{TARGET_SERVICE}"}} > 0)',


    # Throughput, Latency, and Error Rate (using 1m rate window)
    "target_throughput": f'sum(rate(otel_http_server_requests_milliseconds_count{{application="{TARGET_SERVICE}"}}[1m]))',
    "target_latency": f'sum(rate(otel_http_server_requests_milliseconds_sum{{application="{TARGET_SERVICE}"}}[1m])) / sum(rate(otel_http_server_requests_milliseconds_count{{application="{TARGET_SERVICE}"}}[1m]))',
    "target_error_rate": f'sum(rate(otel_http_server_requests_milliseconds_count{{application="{TARGET_SERVICE}", status=~"5.."}}[1m])) / sum(rate(otel_http_server_requests_milliseconds_count{{application="{TARGET_SERVICE}"}}[1m]))',

    # Threads & Active requests
    "target_live_threads": f'otel_jvm_threads_live{{application="{TARGET_SERVICE}"}}',
    "target_active_requests": f'sum(otel_http_server_requests_active_milliseconds_count{{application="{TARGET_SERVICE}"}})'
}


# ==============================================================================
# 4. EXTRACTION LOGIC
# ==============================================================================
def fetch_series(query_name, query_str):
    params = {
        "query": query_str,
        "start": START_TS,
        "end": END_TS,
        "step": STEP
    }
    try:
        res = requests.get(PROMETHEUS_URL, params=params, timeout=15)
        res.raise_for_status()
        data = res.json().get("data", {}).get("result", [])

        if not data:
            print(f"  [WARN] No data for: {query_name}")
            return pd.Series(dtype=float)

        values = data[0]["values"]
        df_temp = pd.DataFrame(values, columns=["timestamp", query_name])
        df_temp["timestamp"] = df_temp["timestamp"].astype(int)
        df_temp[query_name] = pd.to_numeric(df_temp[query_name], errors="coerce")

        print(f"  [OK] {query_name}: {len(df_temp)} points")
        return df_temp.set_index("timestamp")[query_name]

    except Exception as e:
        print(f"  [ERROR] {query_name}: {e}")
        return pd.Series(dtype=float)


def main():
    print(f"[*] Fetching metrics from {START_TIME_STR} to {END_TIME_STR}...")
    print(f"[*] Start Epoch: {START_TS} | End Epoch: {END_TS}\n")

    # Fetch each query and merge automatically on timestamp index
    df = pd.DataFrame({name: fetch_series(name, q) for name, q in QUERIES.items()})

    if df.empty:
        print("\n[!] No data could be collected. Exiting.")
        return

    # Clean gaps
    df = df.ffill().bfill().fillna(0.0)
    df.reset_index(inplace=True)

    if "index" in df.columns:
        df.rename(columns={"index": "timestamp"}, inplace=True)

    # Add human-readable timestamps
    df["Local Datetime"] = df["timestamp"].apply(
        lambda ts: datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    )
    df["status"] = "Healthy"

    # Save
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n[✓] Successfully saved {len(df)} rows to '{OUTPUT_FILE}'")
    print(df.head())


if __name__ == "__main__":
    main()