import glob
import os
import re
import numpy as np
import pandas as pd

# ==============================================================================
# 1. LOAD AND CONCATENATE ALL CSV FILES
# ==============================================================================
DATA_DIR = "outputs"  # Adjust if files are in a different folder
csv_files = glob.glob(os.path.join(DATA_DIR, "*.csv"))

print(f"[*] Found {len(csv_files)} CSV files. Loading...")
assert len(csv_files) > 0, "No CSV files found! Check your folder path."

frames = []
for f in sorted(csv_files):
    df_temp = pd.read_csv(f)
    frames.append(df_temp)

df_master = pd.concat(frames, ignore_index=True)
print(
    f"[✓] Loaded {len(df_master)} total rows and {len(df_master.columns)} columns."
)

# ==============================================================================
# 2. AUDIT 1: MISSING (NaN) AND INFINITE (Inf) VALUES
# ==============================================================================
print("\n" + "=" * 50)
print("[*] AUDIT 1: Checking for NaNs and Infinite values...")
print("=" * 50)

# Replace +/- Inf with NaN for unified detection
df_master.replace([np.inf, -np.inf], np.nan, inplace=True)
nan_counts = df_master.isna().sum()
total_nans = nan_counts.sum()

if total_nans > 0:
    print(f"[!] Warning: Found {total_nans} NaN/Inf values:")
    print(nan_counts[nan_counts > 0])
    # Clean any lingering NaNs (e.g. from 0-variance windows)
    df_master.fillna(0.0, inplace=True)
    print("[✓] NaNs successfully imputed with 0.0.")
else:
    print("[✓] Clean: 0 NaNs and 0 Infs detected.")

# ==============================================================================
# 3. AUDIT 2: FEATURE VS METADATA SEPARATION
# ==============================================================================
print("\n" + "=" * 50)
print("[*] AUDIT 2: Defining Features and Preventing Data Leakage...")
print("=" * 50)

TARGET_COL = "proactive_state"

# Strictly metadata columns to exclude from training
METADATA_COLS = [
    "timestamp",
    "local_datetime",
    "service_name",
    "experiment_id",
    "raw_state",  # Direct leakage
    "proactive_label",  # Target duplicate string
]

FEATURE_COLS = [
    col
    for col in df_master.columns
    if col not in METADATA_COLS and col != TARGET_COL
]

print(f"Target Column (y): '{TARGET_COL}'")
print(f"Excluded Columns (Leakage prevention): {METADATA_COLS}")
print(f"\nFinal Feature Set (X) ({len(FEATURE_COLS)} features):")
for i, feat in enumerate(FEATURE_COLS, 1):
    print(f"  {i:2d}. {feat}")

# ==============================================================================
# 4. AUDIT 3: ZERO-VARIANCE (CONSTANT) FEATURES
# ==============================================================================
print("\n" + "=" * 50)
print("[*] AUDIT 3: Checking for constant (zero-variance) features...")
print("=" * 50)

zero_var_cols = [col for col in FEATURE_COLS if df_master[col].std() == 0]
if zero_var_cols:
    print(
        f"[!] Constant features detected (no predictive value): {zero_var_cols}"
    )
    print("    Recommendation: Drop these before training.")
else:
    print("[✓] All feature columns exhibit healthy numeric variance.")

# ==============================================================================
# 5. AUDIT 4: CLASS BALANCE & DISTRIBUTION
# ==============================================================================
print("\n" + "=" * 50)
print("[*] AUDIT 4: Target Class Distribution (y)...")
print("=" * 50)

dist = df_master[TARGET_COL].value_counts().sort_index()
dist_pct = df_master[TARGET_COL].value_counts(normalize=True).sort_index() * 100

summary_df = pd.DataFrame(
    {
        "Class Name": [
            "0: Healthy",
            "1: Degraded (Throttle)",
            "2: Failed (Trip)",
        ],
        "Count": dist.values,
        "Percentage": [f"{p:.2f}%" for p in dist_pct.values],
    }
)
print(summary_df.to_string(index=False))

print("\n--- Distribution Breakdown by Service ---")
print(
    pd.crosstab(
        df_master["service_name"],
        df_master[TARGET_COL],
        margins=True,
        margins_name="Total",
    ).rename(columns={0: "Healthy (0)", 1: "Degraded (1)", 2: "Failed (2)"})
)

# ==============================================================================
# 6. EXPORT CLEANED MASTER DATASET
# ==============================================================================
OUTPUT_CLEAN_FILE = "master_dataset_x002.csv"
df_master.to_csv(OUTPUT_CLEAN_FILE, index=False)
print("\n" + "=" * 50)
print(f"[✓] ETL Complete! Master dataset saved to: '{OUTPUT_CLEAN_FILE}'")
print("=" * 50)