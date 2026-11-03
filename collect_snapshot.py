#!/usr/bin/env python3
"""Thu thập một snapshot (72 giờ gần nhất) từ EIA API v2.
Thiết kế cho GitHub Actions: chạy đúng một lần rồi thoát, không lặp, không in API key."""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import json
import os
import random
import sys
import time
from pathlib import Path

import pandas as pd
import requests
import yaml

USER_AGENT = "grid-feasibility/0.1"
EIA_BASE = "https://api.eia.gov/v2"

# 8 Balancing Authorities đã khóa trong đề tài
LOCKED_REGIONS = ["CISO", "ERCO", "PJM", "MISO", "NYIS", "ISNE", "SWPP", "US48"]
LOCKED_IC_REGIONS = ["CISO", "ERCO", "PJM", "MISO", "NYIS", "ISNE", "SWPP"]


def get_api_key() -> str:
    key = os.environ.get("EIA_API_KEY", "").strip()
    if not key and sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                key = winreg.QueryValueEx(k, "EIA_API_KEY")[0]
        except OSError:
            pass
    if not key:
        print("ERROR: Bien moi truong EIA_API_KEY chua duoc thiet lap.", file=sys.stderr)
        sys.exit(1)
    return key


def scrub(text: str, key: str) -> str:
    if not key:
        return str(text)
    return str(text).replace(key, "***")


def http_get(url: str, params: dict, key: str, max_tries: int = 6, timeout: int = 60):
    params = dict(params)
    params["api_key"] = key
    delay = 2.0
    for attempt in range(1, max_tries + 1):
        t0 = time.time()
        try:
            r = requests.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=timeout)
            el = time.time() - t0
            if r.status_code == 429 or 500 <= r.status_code < 600:
                ra = r.headers.get("Retry-After")
                wait = None
                if ra:
                    try:
                        wait = float(ra)
                    except ValueError:
                        wait = None
                if wait is None:
                    wait = delay + random.uniform(0.5, 1.5)
                    delay = min(delay * 2, 120.0)
                print(f"[RETRY] HTTP {r.status_code} attempt {attempt}/{max_tries}; sleeping {wait:.1f}s...")
                time.sleep(wait)
                continue
            return r, el
        except requests.RequestException as e:
            msg = scrub(str(e), key)
            print(f"[NETERR] attempt {attempt}/{max_tries}: {type(e).__name__}: {msg[:200]}")
            time.sleep(delay)
            delay = min(delay * 2, 120.0)
    raise RuntimeError(f"Gave up on {url} after {max_tries} attempts")


def write_json_gz(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with gzip.open(tmp, "wt", encoding="utf-8") as f:
        json.dump(obj, f)
    os.replace(tmp, path)


def fetch_route(route: str, facet_key: str, codes: list[str], start: str, run_id: str,
                fetched_at: str, key: str, out_dir: Path, reqlog: list[dict]) -> pd.DataFrame:
    rows, offset, page = [], 0, 0
    while True:
        params = {
            "frequency": "hourly",
            "data[0]": "value",
            "start": start,
            "offset": offset,
            "length": 5000,
            "sort[0][column]": "period",
            "sort[0][direction]": "asc",
        }
        for i, c in enumerate(codes):
            params[f"facets[{facet_key}][{i}]"] = c

        r, el = http_get(f"{EIA_BASE}/electricity/rto/{route}/data/", params, key)
        hdr = {k: v for k, v in r.headers.items() if any(s in k.lower() for s in ("limit", "remaining", "retry"))}
        entry = {"route": route, "page": page, "status": r.status_code, "elapsed_s": round(el, 3), "headers": hdr}
        if r.status_code != 200:
            entry["rows"] = 0
            reqlog.append(entry)
            raise RuntimeError(f"{route} HTTP {r.status_code}")

        j = r.json()
        data = j.get("response", {}).get("data", [])
        total = int(j.get("response", {}).get("total") or 0)
        entry.update(rows=len(data), total=total)
        reqlog.append(entry)

        # Lưu raw JSON nén
        raw_path = out_dir / "raw" / route / f"{run_id}_p{page:02d}.json.gz"
        write_json_gz(raw_path, j)

        rows.extend(data)
        offset += len(data)
        page += 1
        if not data or offset >= total:
            break

    df = pd.DataFrame(rows)
    df["fetched_at"] = fetched_at
    df["run_id"] = run_id
    return df


def main():
    parser = argparse.ArgumentParser(description="EIA hourly snapshot collector")
    parser.add_argument("--out", type=Path, default=Path("store/snapshots"),
                        help="Thư mục lưu trữ snapshot (mặc định: store/snapshots)")
    args = parser.parse_args()

    api_key = get_api_key()
    out_dir = args.out
    out_dir.mkdir(parents=True, exist_ok=True)

    now_utc = dt.datetime.now(dt.timezone.utc)
    run_id = now_utc.strftime("%Y%m%dT%H")
    fetched_at = now_utc.isoformat(timespec="seconds")
    start = (now_utc.replace(minute=0, second=0, microsecond=0) - dt.timedelta(hours=72)).strftime("%Y-%m-%dT%H")

    print(f"=== Bat dau snapshot {run_id} ===")
    print(f"Thoi diem fetched_at (UTC): {fetched_at}")
    print(f"Cua so start: {start}")
    print(f"Thu muc dau ra: {out_dir}")

    t0 = time.time()
    reqlog = []
    nrows = {}
    success = True
    error_msg = None

    try:
        tasks = [
            ("region-data", "respondent", LOCKED_REGIONS),
            ("fuel-type-data", "respondent", LOCKED_REGIONS),
            ("interchange-data", "fromba", LOCKED_IC_REGIONS),
        ]
        for route, fk, cs in tasks:
            t_route = time.time()
            df = fetch_route(route, fk, cs, start, run_id, fetched_at, api_key, out_dir, reqlog)
            # Lưu parquet
            parq_dir = out_dir / "parquet" / route
            parq_dir.mkdir(parents=True, exist_ok=True)
            # Ép kiểu an toàn trước khi lưu
            for col in df.columns:
                if df[col].dtype == object:
                    df[col] = df[col].astype("string")
            df.to_parquet(parq_dir / f"{run_id}.parquet", index=False)
            nrows[route] = len(df)
            print(f"  + {route}: {len(df)} dong trong {time.time()-t_route:.2f}s")

    except Exception as e:
        success = False
        error_msg = scrub(f"{type(e).__name__}: {e}", api_key)
        print(f"ERROR: {error_msg}", file=sys.stderr)

    duration_s = round(time.time() - t0, 2)
    manifest = {
        "run_id": run_id,
        "fetched_at": fetched_at,
        "window_start": start,
        "success": success,
        "error": error_msg,
        "duration_s": duration_s,
        "rows": nrows,
        "requests": reqlog,
    }

    # 1. Ghi manifest riêng cho lần chạy này
    manifest_dir = out_dir / "manifests"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    (manifest_dir / f"{run_id}.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    # 2. Append vào snapshot_runs.jsonl để tiện phân tích
    runs_file = out_dir / "snapshot_runs.jsonl"
    with open(runs_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(manifest) + "\n")

    print(f"=== Snapshot {run_id} ket thuc: success={success}, {duration_s}s, rows={nrows} ===")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
