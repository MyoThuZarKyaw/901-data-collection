import pandas as pd
import json
import sys
import os

# ==============================================================================
# 1. CONFIGURATION (Match your FastAPI schema exactly)
# ==============================================================================
# These are the 21 fields the Brain expects
REQUIRED_FIELDS = [
    "service_name",
    "target_cpu",
    "target_mem",
    "target_throughput",
    "target_latency",
    "target_error_rate",
    "target_live_threads",
    "target_active_requests",
    "latency_delta_30s",
    "latency_delta_60s",
    "mem_delta_60s",
    "cpu_delta_30s",
    "throughput_delta_30s",
    "latency_accel_30s",
    "latency_rolling_mean_1m",
    "latency_std_1m",
    "throughput_rolling_mean_1m",
    "active_req_rolling_mean_1m",
    "latency_surge_ratio",
    "thread_pressure_ratio",
    "latency_zscore"
]

def extract_payload(file_path, target_timestamp):
    if not os.path.exists(file_path):
        print(f"[!] Error: File '{file_path}' not found.")
        return

    # 1. Load the CSV
    df = pd.read_csv(file_path)
    
    # Ensure timestamp is integer for comparison
    df['timestamp'] = df['timestamp'].astype(int)
    
    # 2. Find the closest row to the user's timestamp
    idx = (df['timestamp'] - int(target_timestamp)).abs().idxmin()
    row = df.loc[idx]
    
    actual_ts = row['timestamp']
    print(f"[*] Closest match found at timestamp: {actual_ts}")
    print(f"[*] Delta from requested: {abs(actual_ts - int(target_timestamp))} seconds")
    print("-" * 30)

    # 3. Build the payload
    payload = {}
    for field in REQUIRED_FIELDS:
        if field in df.columns:
            val = row[field]
            # Use .item() to convert numpy/pandas types to standard Python types
            # This prevents the 'json.dumps' error and the TypeError you saw.
            try:
                if hasattr(val, 'item'):
                    payload[field] = val.item()
                else:
                    payload[field] = val
            except Exception:
                payload[field] = val
        else:
            payload[field] = 0.0

    # 4. Output the JSON
    print(json.dumps(payload, indent=2))

if __name__ == "__main__":
    file_path = "outputs/ExpTest01_inventory_service.csv"
    timestamp = 1793260724
    extract_payload(file_path, timestamp)