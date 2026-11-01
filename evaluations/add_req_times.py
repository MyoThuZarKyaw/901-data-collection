#!/usr/bin/env python3
"""Add req_start / req_end UTC columns to a JMeter results CSV.

Usage:
    python3 add_req_times.py <input_csv>

Output:
    <input_basename>-extra.csv (suffix inserted before extension)
    with req_start, req_end prepended as the first two columns.

    req_start = human-readable UTC of `timeStamp` (epoch ms)
    req_end   = human-readable UTC of `timeStamp + elapsed` (epoch ms)
"""
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path


def to_utc_str(epoch_ms: int) -> str:
    dt = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


def output_path_for(input_path: Path) -> Path:
    if input_path.suffix:
        return input_path.with_name(f"{input_path.stem}-extra{input_path.suffix}")
    return input_path.with_name(f"{input_path.name}-extra")


def main() -> None:
    if len(sys.argv) != 2:
        print(f"Usage: {Path(sys.argv[0]).name} <input_csv>", file=sys.stderr)
        sys.exit(1)

    in_path = Path(sys.argv[1])
    if not in_path.is_file():
        print(f"Error: file not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    out_path = output_path_for(in_path)

    with in_path.open("r", newline="", encoding="utf-8-sig") as fin:
        reader = csv.DictReader(fin)
        if reader.fieldnames is None:
            print("Error: empty CSV / missing header.", file=sys.stderr)
            sys.exit(1)
        if "timeStamp" not in reader.fieldnames:
            print(f"Error: 'timeStamp' column not found. Found: {reader.fieldnames}", file=sys.stderr)
            sys.exit(1)
        if "elapsed" not in reader.fieldnames:
            print(f"Error: 'elapsed' column not found. Found: {reader.fieldnames}", file=sys.stderr)
            sys.exit(1)

        out_fieldnames = ["req_start", "req_end"] + reader.fieldnames

        with out_path.open("w", newline="", encoding="utf-8") as fout:
            writer = csv.DictWriter(fout, fieldnames=out_fieldnames)
            writer.writeheader()
            for row in reader:
                try:
                    ts = int(float(row["timeStamp"]))
                    el = int(float(row["elapsed"]))
                except (ValueError, TypeError):
                    row["req_start"] = ""
                    row["req_end"] = ""
                else:
                    row["req_start"] = to_utc_str(ts)
                    row["req_end"] = to_utc_str(ts + el)
                writer.writerow({k: row.get(k, "") for k in out_fieldnames})

    print(f"Wrote: {out_path}")


if __name__ == "__main__":
    main()
