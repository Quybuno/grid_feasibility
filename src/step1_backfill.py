"""BƯỚC 1 — backfill lịch sử 2019-01-01 .. D-3 (interchange từ 2023-01-01). Chunk = (dataset, nhóm, tháng).
Mỗi chunk lưu JSON thô nén theo trang + file .done => chạy lại tiếp từ điểm dừng, không tải trùng."""
from __future__ import annotations

import datetime as dt
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from common import (EIA_BASE, RAW, STATE, STATS, BudgetExceeded, check_budget, http_get, load_yaml, log,
                    run_state, save_json, write_json_gz)

LOGF = "backfill.log"
AGG13 = ["CAL", "CAR", "CENT", "FLA", "MIDA", "MIDW", "NE", "NY", "NW", "SE", "SW", "TEN", "TEX"]


def months(start: str, end: str):
    s = dt.datetime.strptime(start[:7], "%Y-%m")
    e = dt.datetime.strptime(end[:7], "%Y-%m")
    while s <= e:
        nxt = (s.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
        yield s, nxt
        s = nxt


def build_chunks(st):
    codes = json.loads((STATE / "step0_codes.json").read_text())
    regions = [r for r in load_yaml("regions.yml")["regions"] if codes["region-data"].get(r)]
    fuel_regions = [r for r in regions if codes["fuel-type-data"].get(r)]
    ic_regions = [r for r in regions if r != "US48" and codes["interchange-data"].get(r)]
    end = dt.datetime.strptime(st["history_end"], "%Y-%m-%dT%H")
    chunks = []

    def window(ms, me, start_floor):
        s = max(ms, start_floor)
        e = min(me - dt.timedelta(hours=1), end)
        return s.strftime("%Y-%m-%dT%H"), e.strftime("%Y-%m-%dT%H")

    h0 = dt.datetime(2019, 1, 1)
    for ms, me in months(st["history_start"], st["history_end"]):
        s, e = window(ms, me, h0)
        tag = ms.strftime("%Y-%m")
        for r in regions:
            chunks.append(("region-data", r, tag, {"facets[respondent][]": r, "start": s, "end": e}))
        for r in fuel_regions:
            chunks.append(("fuel-type-data", r, tag, {"facets[respondent][]": r, "start": s, "end": e}))
        if all(codes.get("agg13", {}).get(a) for a in AGG13):
            p = {"start": s, "end": e, "facets[type][]": "D"}
            for i, a in enumerate(AGG13):
                p[f"facets[respondent][{i}]"] = a
            chunks.append(("region-data-agg13", "AGG13", tag, p))
    i0 = dt.datetime.strptime(st["interchange_start"], "%Y-%m-%dT%H")
    for ms, me in months(st["interchange_start"], st["history_end"]):
        s, e = window(ms, me, i0)
        tag = ms.strftime("%Y-%m")
        for direction in ("fromba", "toba"):
            p = {"start": s, "end": e}
            for i, r in enumerate(ic_regions):
                p[f"facets[{direction}][{i}]"] = r
            chunks.append((f"interchange-data-{direction}", "LOCKED", tag, p))
    return chunks


def route_of(ds):
    return {"region-data": "region-data", "region-data-agg13": "region-data", "fuel-type-data": "fuel-type-data",
            "interchange-data-fromba": "interchange-data", "interchange-data-toba": "interchange-data"}[ds]


def run_chunk(ch):
    ds, key, tag, p = ch
    d = RAW / "backfill" / ds / key
    done = d / f"{tag}.done"
    if done.exists():
        return ds, key, tag, "skip", 0
    offset, page, n = 0, 0, 0
    while True:
        params = {"frequency": "hourly", "data[0]": "value", "offset": offset, "length": 5000,
                  "sort[0][column]": "period", "sort[0][direction]": "asc", **p}
        r, el = http_get(f"{EIA_BASE}/electricity/rto/{route_of(ds)}/data/", params, eia=True, logfile=LOGF)
        if r.status_code != 200:
            raise RuntimeError(f"{ds}/{key}/{tag} HTTP {r.status_code}: {r.text[:200]}")
        j = r.json()
        data = j["response"]["data"]
        total = int(j["response"].get("total") or 0)
        write_json_gz(d / f"{tag}_p{page:02d}.json.gz", j)
        n += len(data)
        offset += len(data)
        page += 1
        if not data or offset >= total:
            break
    done.write_text(json.dumps({"rows": n, "pages": page, "total": total,
                                "at": dt.datetime.now(dt.timezone.utc).isoformat()}))
    return ds, key, tag, "ok", n


def main(workers=4):
    st = run_state()
    chunks = build_chunks(st)
    todo = [c for c in chunks if not (RAW / "backfill" / c[0] / c[1] / f"{c[2]}.done").exists()]
    log(f"backfill: {len(chunks)} chunks, {len(todo)} to do, D={st['D']}", LOGF)
    t0 = time.time()
    fails = []
    with ThreadPoolExecutor(workers) as ex:
        futs = {ex.submit(run_chunk, c): c for c in todo}
        for k, f in enumerate(as_completed(futs), 1):
            c = futs[f]
            try:
                ds, key, tag, status, n = f.result()
                if k % 25 == 0 or status != "ok":
                    log(f"[{k}/{len(todo)}] {ds}/{key}/{tag} {status} rows={n} req={STATS.count} "
                        f"size={check_budget()/1e6:.0f}MB", LOGF)
            except BudgetExceeded as e:
                log(f"STOP: {e}", LOGF)
                ex.shutdown(cancel_futures=True)
                raise
            except Exception as e:  # noqa
                fails.append((c[0], c[1], c[2], str(e)[:200]))
                log(f"FAIL {c[0]}/{c[1]}/{c[2]}: {e}", LOGF)
    el = time.time() - t0
    prev = json.loads((STATE / "backfill_metrics.json").read_text()) if (STATE / "backfill_metrics.json").exists() else {"sessions": []}
    prev["sessions"].append({"started": dt.datetime.fromtimestamp(t0, dt.timezone.utc).isoformat(), "elapsed_s": round(el, 1),
                             "chunks_done": len(todo) - len(fails), "requests": STATS.count, "fails": fails})
    (STATE / "backfill_metrics.json").write_text(json.dumps(prev, indent=1))
    log(f"backfill finished in {el:.0f}s, requests={STATS.count}, fails={len(fails)}", LOGF)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())

