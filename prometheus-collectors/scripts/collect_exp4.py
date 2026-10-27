import os
import requests
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================
PROMETHEUS_URL = "http://localhost:9090/api/v1/query_range"

def get_quries(service_name):
    return  {
        # CPU
        "target_cpu": f'otel_process_cpu_usage{{application="{service_name}"}} * 100',

        # Memory (used / committed avoids the 3-pool heap split issue)
        "target_mem": f'sum(otel_jvm_memory_used_bytes{{area="heap", application="{service_name}"}}) / sum(otel_jvm_memory_max_bytes{{area="heap", application="{service_name}"}} > 0)',

        # Throughput, Latency, and Error Rate (using 1m rate window)
        "target_throughput": f'sum(rate(otel_http_server_requests_milliseconds_count{{application="{service_name}"}}[1m]))',
        "target_latency": f'sum(rate(otel_http_server_requests_milliseconds_sum{{application="{service_name}"}}[1m])) / sum(rate(otel_http_server_requests_milliseconds_count{{application="{service_name}"}}[1m]))',
        "target_error_rate": f'sum(rate(otel_http_server_requests_milliseconds_count{{application="{service_name}", status=~"5.."}}[1m])) / sum(rate(otel_http_server_requests_milliseconds_count{{application="{service_name}"}}[1m]))',

        # Threads & Active requests
        "target_live_threads": f'otel_jvm_threads_live{{application="{service_name}"}}',
        "target_active_requests": f'sum(otel_http_server_requests_active_milliseconds_count{{application="{service_name}"}})'
    }

def get_output_filepath(service_name, start_ms):
    output_path = Path(f"outputs/Exp004_{service_name}_{ms_to_utc_compact(start_ms)}.csv")
    # Create parent directories if they don't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    return output_path

def timestamp_utc(ms: int) -> str:
    # Convert milliseconds to seconds and create a datetime object in UTC
    dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    # Format to 'YYYY-MM-DD HH:MM:SS'
    return dt.strftime("%Y-%m-%d %H:%M:%S")
    # Example usage:
    # ts = 1793003135039
    # print(format_timestamp_utc(ts))
    # Output: 2026-10-26 08:25:35

def ms_to_utc_compact(ms: int) -> str:
    """Convert timestamp in milliseconds to UTC format:

    YYYYMMDD_HHMMSS (e.g., 20261027_033546)
    """
    dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    return dt.strftime("%Y%m%d_%H%M%S")
    # Example usage:
    # # A timestamp around Oct 27, 2026 at 03:35:46 UTC
    # ts_ms = 1793072146000
    # formatted_date = ms_to_utc_compact(ts_ms)

    # print(formatted_date)
    # # Output: 20261027_033546

# ==============================================================================
# 4. EXTRACTION LOGIC
# ==============================================================================
def fetch_series(query_name, query_str, start_ms, end_ms, step = '2s'):
    params = {
        "query": query_str,
        "start":  start_ms / 1000.0,
        "end": end_ms / 1000.0,
        "step": step
    }
    try:
        res = requests.get(PROMETHEUS_URL, params=params, timeout=15)
        res.raise_for_status()
        data = res.json().get("data", {}).get("result", [])
        
        if query_name == "target_error_rate":
            print(res.json())
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


def assign_status(row):
    """Assigns ground-truth state based on latency and error rate thresholds."""
    if row["target_latency"] > 1000.0 or row["target_error_rate"] > 0.1:
        return "Failed"
    elif row["target_latency"] > 300.0:
        return "Degraded"
    else:
        return "Healthy"


def collect_data(service_name, start_ms, end_ms):
    print(f"[*] Fetching metrics from {timestamp_utc(start_ms)} to {timestamp_utc(end_ms)}...")
    print(f"[*] Start Epoch: {start_ms / 1000.0} | End Epoch: {end_ms / 1000.0}\n")

    # Fetch each query and merge automatically on timestamp index
    df = pd.DataFrame({name: fetch_series(name, q, start_ms, end_ms) for name, q in get_quries(service_name).items()})

    if df.empty:
        print("\n[!] No data could be collected. Exiting.")
        return

    # Clean gaps
    df = df.ffill().bfill().fillna(0.0)
    df.reset_index(inplace=True)

    if "index" in df.columns:
        df.rename(columns={"index": "timestamp"}, inplace=True)

    # Add human-readable timestamps
    df["local_datetime"] = df["timestamp"].apply(
        lambda ts: datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
    )

    df["status"] = df.apply(assign_status, axis=1)

    # Save
    output_path = get_output_filepath(service_name, start_ms)
    df.to_csv(output_path, index=False)
    print(f"\n[✓] Successfully saved {len(df)} rows to '{output_path.name}'")
    print(df.head())

    # Print label distribution to verify all 3 states were captured
    print("\n--- Status Distribution ---")
    print(df["status"].value_counts())
    print("\n--- Summary Statistics by Status ---")
    print(df.groupby("status")[["target_latency", "target_active_requests", "target_cpu"]].mean())

if __name__ == "__main__":
    start_ms = 1793009874068
    end_ms = 1793010474055
    collect_data("inventory_service", start_ms, end_ms)
    collect_data("payment_service", start_ms, end_ms)
    collect_data("order_service", start_ms, end_ms)