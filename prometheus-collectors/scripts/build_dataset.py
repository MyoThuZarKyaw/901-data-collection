import os
import glob
import re
import pandas as pd
import numpy as np

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================
DATA_DIR = "./raw_data"  # Folder containing your 20 CSV files
OUTPUT_FILE = "master_dataset.csv"

# Step size is 2 seconds
STEP_30S = 15  # 15 rows = 30 seconds
STEP_60S = 30  # 30 rows = 60 seconds

# Proactive look-ahead window: Predict 30 to 50 seconds into the future
LOOK_AHEAD_STEPS = 20  # 40 seconds lead-time runway


def get_sort_key(filepath):
    """Sorts files naturally: exp1 -> exp10, with inventory before payment."""
    filename = os.path.basename(filepath)
    match = re.search(r'exp(\d+)', filename, re.IGNORECASE)
    exp_num = int(match.group(1)) if match else 999
    svc_priority = 0 if "inventory" in filename.lower() else 1
    return (exp_num, svc_priority)


def compute_raw_state(df):
    """
    Classifies the instantaneous state of the service:
    2 = Failed   (Latency > 1000ms OR Errors > 15% OR Container Dead)
    1 = Degraded (Latency > 300ms OR Errors > 3% OR Memory > 85% with positive slope OR CPU > 70%)
    0 = Healthy  (Normal operating parameters)
    """
    conditions = [
        # State 2: Failed
        (df["target_latency"] > 1000.0) |
        (df["target_error_rate"] > 0.15) |
        (df["target_live_threads"] == 0),

        # State 1: Degraded (Note: Memory only triggers if >85% AND actively climbing!)
        (df["target_latency"] > 300.0) |
        (df["target_error_rate"] > 0.03) |
        ((df["target_mem"] > 0.85) & (df["mem_delta_60s"] > 0.02)) |
        (df["target_cpu"] > 70.0)
    ]
    choices = [2, 1]
    return np.select(conditions, choices, default=0)


def process_single_experiment(filepath):
    """Processes a single experiment CSV with temporal features and 3-state target."""
    filename = os.path.basename(filepath)
    df = pd.read_csv(filepath)

    if df.empty or len(df) < STEP_60S:
        print(f"  [!] Skipping {filename} (insufficient rows: {len(df)})")
        return None

    df["timestamp"] = df["timestamp"].astype(int)
    df = df.sort_values(by="timestamp").reset_index(drop=True)

    # Metadata
    match = re.search(r'exp(\d+)', filename, re.IGNORECASE)
    df["experiment_id"] = int(match.group(1)) if match else 0
    df["service_name"] = "payment_service" if "payment" in filename.lower() else "inventory_service"
    df["source_file"] = filename

    # ==========================================================================
    # 2. FEATURE ENGINEERING (Deltas, Rolling Stats, Volatility)
    # ==========================================================================
    df["latency_delta_30s"] = df["target_latency"] - df["target_latency"].shift(STEP_30S)
    df["latency_delta_60s"] = df["target_latency"] - df["target_latency"].shift(STEP_60S)
    df["mem_delta_60s"] = df["target_mem"] - df["target_mem"].shift(STEP_60S)
    df["cpu_delta_30s"] = df["target_cpu"] - df["target_cpu"].shift(STEP_30S)
    df["throughput_delta_30s"] = df["target_throughput"] - df["target_throughput"].shift(STEP_30S)

    df["latency_rolling_mean_1m"] = df["target_latency"].rolling(window=STEP_60S).mean()
    df["latency_std_1m"] = df["target_latency"].rolling(window=STEP_60S).std().fillna(0)
    df["throughput_rolling_mean_1m"] = df["target_throughput"].rolling(window=STEP_60S).mean()
    df["active_req_rolling_mean_1m"] = df["target_active_requests"].rolling(window=STEP_60S).mean()
    df["latency_accel_30s"] = df["latency_delta_30s"] - df["latency_delta_30s"].shift(STEP_30S)

    # ==========================================================================
    # 3. PROACTIVE 3-STATE LOOKAHEAD TARGET (y)
    # ==========================================================================
    # Compute instantaneous state: 0, 1, or 2
    raw_state = compute_raw_state(df)

    # Mathematical rolling max on reversed array finds the worst-case future state
    # (Since 2 > 1 > 0, max automatically picks Failed over Degraded over Healthy)
    future_state = pd.Series(raw_state).iloc[::-1].rolling(window=LOOK_AHEAD_STEPS, min_periods=1).max().iloc[::-1]

    # Shift forward by 5 steps (10 seconds minimum lead-time warning)
    df["proactive_state"] = future_state.shift(-5).fillna(0).astype(int)

    # Drop initial NaNs from 60s lag window
    df = df.dropna().reset_index(drop=True)
    return df


def main():
    raw_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))
    csv_files = sorted(raw_files, key=get_sort_key)

    print(f"[*] Found {len(csv_files)} CSV files. Processing (Exp 1 -> 10):\n")

    processed_frames = []
    for f in csv_files:
        print(f"  Processing: {os.path.basename(f)} ...", end=" ")
        df_clean = process_single_experiment(f)
        if df_clean is not None:
            processed_frames.append(df_clean)
            print(f"Done ({len(df_clean)} rows)")

    if not processed_frames:
        print("[!] No data processed.")
        return

    master_df = pd.concat(processed_frames, ignore_index=True)
    master_df.to_csv(OUTPUT_FILE, index=False)

    print(
        f"\n[✓] Successfully created '{OUTPUT_FILE}' with {len(master_df)} rows and {len(master_df.columns)} columns.")

    print("\n--- Rows per Experiment ---")
    print(pd.crosstab(master_df["experiment_id"], master_df["service_name"]))

    print("\n--- Proactive 3-State Target Distribution (y) ---")
    print(master_df["proactive_state"].value_counts(normalize=True).rename(
        index={0: "0 (Healthy)", 1: "1 (Degraded / Throttle)", 2: "2 (Failed / Trip)"}
    ))

    print("\n--- State Breakdown by Service ---")
    print(pd.crosstab(
        master_df["service_name"],
        master_df["proactive_state"]
    ).rename(columns={0: "Healthy (0)", 1: "Degraded (1)", 2: "Failed (2)"}))


if __name__ == "__main__":
    main()