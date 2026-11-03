#!/usr/bin/env python3
"""Nhập dữ liệu snapshot từ branch 'snapshots' (GitHub Actions) vào thư mục local pipeline."""
import argparse
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARQ = ROOT / "data" / "parquet" / "snapshots"
RAW = ROOT / "data" / "raw" / "snapshots"
STATE = ROOT / "state"


def main():
    parser = argparse.ArgumentParser(description="Import GitHub Actions snapshots")
    parser.add_argument("--src", type=Path, default=ROOT.parent / "snapshots-data" / "snapshots",
                        help="Thư mục snapshots tải về (mặc định: ../snapshots-data/snapshots)")
    args = parser.parse_args()
    src = args.src

    if not src.exists():
        # Thử tìm các vị trí phổ biến khác
        alt = [ROOT / "store" / "snapshots", Path("store/snapshots"), Path("../snapshots-data/snapshots")]
        for a in alt:
            if a.exists():
                src = a
                break

    if not src.exists():
        print(f"ERROR: Khong tim thay thu muc: {src}")
        return 1

    print(f"Dang dong bo tu: {src} -> {ROOT}")

    # 1. Đồng bộ Parquet
    src_parq = src / "parquet"
    if src_parq.exists():
        for route_dir in src_parq.iterdir():
            if route_dir.is_dir():
                dest_dir = PARQ / route_dir.name
                dest_dir.mkdir(parents=True, exist_ok=True)
                for f in route_dir.glob("*.parquet"):
                    shutil.copy2(f, dest_dir / f.name)
        print("  + Da dong bo cac file Parquet.")

    # 2. Đồng bộ Raw JSON
    src_raw = src / "raw"
    if src_raw.exists():
        for route_dir in src_raw.iterdir():
            if route_dir.is_dir():
                dest_dir = RAW / route_dir.name
                dest_dir.mkdir(parents=True, exist_ok=True)
                for f in route_dir.glob("*.json.gz"):
                    shutil.copy2(f, dest_dir / f.name)
        print("  + Da dong bo cac file Raw JSON.")

    # 3. Đồng bộ snapshot_runs.jsonl
    src_runs = src / "snapshot_runs.jsonl"
    dest_runs = STATE / "snapshot_runs.jsonl"
    if src_runs.exists():
        lines = [l.strip() for l in src_runs.read_text(encoding="utf-8").splitlines() if l.strip()]
        existing = set()
        if dest_runs.exists():
            for l in dest_runs.read_text(encoding="utf-8").splitlines():
                if l.strip():
                    try:
                        existing.add(json.loads(l).get("run_id"))
                    except Exception:
                        pass
        with open(dest_runs, "a", encoding="utf-8") as f:
            for l in lines:
                try:
                    rid = json.loads(l).get("run_id")
                    if rid not in existing:
                        f.write(l + "\n")
                        existing.add(rid)
                except Exception:
                    pass
        print(f"  + Da cap nhat state/snapshot_runs.jsonl ({len(existing)} runs ghi nhan).")

    print("Dong bo hoan tat! Chay lenh sau de cap nhat bao cao:")
    print("  .\\run_all.ps1 -ReportOnly")
    return 0


if __name__ == "__main__":
    main()

