"""BƯỚC 2 — snapshot hằng giờ (72 lần). Mỗi lần: 72 giờ gần nhất (start=now-72h, không end) cho
region-data, fuel-type-data, interchange-data. Lưu JSON thô nén + Parquet kèm fetched_at.
Idempotent theo giờ: run_id = giờ UTC hiện tại; nếu đã thành công thì bỏ qua (không tải trùng)."""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
import traceback

import pandas as pd

from common import (EIA_BASE, PARQ, RAW, STATE, BudgetExceeded, check_budget, http_get, load_yaml, log,
                    utcnow, write_json_gz)

LOGF = "snapshot.log"
RUNS = STATE / "snapshot_runs.jsonl"
MAX_RUNS = 72


def done_runs() -> list[dict]:
    if not RUNS.exists():
        return []
    return [json.loads(l) for l in RUNS.read_text(encoding="utf-8").splitlines() if l.strip()]


def fetch_route(route, facet_key, codes, start, run_id, fetched_at, reqlog):
    rows, offset, page = [], 0, 0
    while True:
        params = {"frequency": "hourly", "data[0]": "value", "start": start, "offset": offset, "length": 5000,
                  "sort[0][column]": "period", "sort[0][direction]": "asc"}
        for i, c in enumerate(codes):
            params[f"facets[{facet_key}][{i}]"] = c
        r, el = http_get(f"{EIA_BASE}/electricity/rto/{route}/data/", params, eia=True, logfile=LOGF)
        hdr = {k: v for k, v in r.headers.items() if any(s in k.lower() for s in ("limit", "remaining", "retry"))}
        entry = {"route": route, "page": page, "status": r.status_code, "elapsed_s": round(el, 3), "headers": hdr}
        if r.status_code != 200:
            entry["rows"] = 0
            reqlog.append(entry)
            raise RuntimeError(f"{route} HTTP {r.status_code}")
        j = r.json()
        data = j["response"]["data"]
        total = int(j["response"].get("total") or 0)
        entry.update(rows=len(data), total=total)
        reqlog.append(entry)
        write_json_gz(RAW / "snapshots" / route / f"{run_id}_p{page:02d}.json.gz", j)
        rows.extend(data)
        offset += len(data)
        page += 1
        if not data or offset >= total:
            break
    df = pd.DataFrame(rows)
    df["fetched_at"] = fetched_at
    df["run_id"] = run_id
    return df


def main(force=False):
    regions = load_yaml("regions.yml")["regions"]
    st0 = json.loads((STATE / "step0_codes.json").read_text()) if (STATE / "step0_codes.json").exists() else None
    codes = list(regions)
    ic_codes = [c for c in codes if c != "US48"]
    if st0:  # only codes confirmed by metadata
        codes = [c for c in codes if st0["region-data"].get(c)]
        ic_codes = [c for c in ic_codes if st0["interchange-data"].get(c)]
    runs = done_runs()
    ok = [r for r in runs if r.get("success")]
    if len(runs) >= MAX_RUNS and not force:
        log(f"already {len(runs)} runs; nothing to do", LOGF)
        return 0
    now = utcnow()
    run_id = now.strftime("%Y%m%dT%H")
    if any(r["run_id"] == run_id and r.get("success") for r in runs) and not force:
        log(f"run {run_id} already successful; skip", LOGF)
        return 0
    start = (now.replace(minute=0, second=0, microsecond=0) - dt.timedelta(hours=72)).strftime("%Y-%m-%dT%H")
    t0 = time.time()
    reqlog, success, err = [], True, None
    fetched_at = now.isoformat(timespec="seconds")
    nrows = {}
    try:
        check_budget(force=True)
        for route, fk, cs in (("region-data", "respondent", codes), ("fuel-type-data", "respondent", codes),
                              ("interchange-data", "fromba", ic_codes)):
            df = fetch_route(route, fk, cs, start, run_id, fetched_at, reqlog)
            out = PARQ / "snapshots" / route
            out.mkdir(parents=True, exist_ok=True)
            df.astype({c: "string" for c in df.columns if df[c].dtype == object}).to_parquet(out / f"{run_id}.parquet", index=False)
            nrows[route] = len(df)
    except BudgetExceeded as e:
        success, err = False, str(e)
    except Exception as e:  # noqa
        success, err = False, f"{type(e).__name__}: {e}"
        log(traceback.format_exc(), LOGF)
    rec = {"run_id": run_id, "fetched_at": fetched_at, "window_start": start, "success": success, "error": err,
           "duration_s": round(time.time() - t0, 2), "rows": nrows, "requests": reqlog,
           "run_index": len(runs) + 1}
    with open(RUNS, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    log(f"snapshot {run_id} success={success} rows={nrows} {rec['duration_s']}s err={err}", LOGF)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main(force="--force" in sys.argv))

