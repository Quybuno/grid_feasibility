"""BƯỚC 2 — phân tích snapshot: tỷ lệ chạy thành công, độ trễ xuất hiện, tỷ lệ sửa, hành vi dự báo DF."""
from __future__ import annotations

import json
import sys

import numpy as np
import pandas as pd

from common import PARQ, STATE, load_yaml, save_json

AN = load_yaml("analysis.yml")["C2"]


def r4(x):
    return None if x is None or (isinstance(x, float) and (np.isnan(x) or np.isinf(x))) else round(float(x), 4)


def pct(a, q):
    a = np.asarray(a, dtype=float)
    return float(np.percentile(a, q)) if len(a) else None


def load_route(route):
    fs = sorted((PARQ / "snapshots" / route).glob("*.parquet"))
    if not fs:
        return pd.DataFrame()
    df = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["period_utc"] = pd.to_datetime(df["period"], format="%Y-%m-%dT%H").dt.tz_localize("UTC")
    df["fetched_at"] = pd.to_datetime(df["fetched_at"], utc=True)
    return df


def latency(df, keys, fetch_times, window_h):
    """first non-null appearance; censored (+inf) if never seen while inside the 72h window."""
    first_fetch, last_fetch = fetch_times.min(), fetch_times.max()
    nn = df[df.value.notna()]
    first = nn.groupby(keys + ["period_utc"]).fetched_at.min().reset_index()
    # expected universe: series seen at least once x hours after first fetch
    series = nn[keys].drop_duplicates()
    hours = pd.date_range(first_fetch.ceil("h"), last_fetch.floor("h"), freq="h")
    if len(hours) == 0 or series.empty:
        return np.array([]), 0, 0
    uni = series.merge(pd.DataFrame({"period_utc": hours}), how="cross")
    m = uni.merge(first, on=keys + ["period_utc"], how="left")
    lat = (m.fetched_at - m.period_utc).dt.total_seconds() / 3600
    fully_observed = (m.period_utc + pd.Timedelta(hours=window_h)) <= last_fetch
    lat = np.where(m.fetched_at.isna() & fully_observed, np.inf, lat)
    keep = ~np.isnan(lat)
    return lat[keep], int(np.isinf(lat[keep]).sum()), int(keep.sum())


def revisions(df, keys):
    nn = df[df.value.notna()].sort_values("fetched_at")
    g = nn.groupby(keys + ["period_utc"])
    v0 = g.value.transform("first")
    n = g.value.transform("size")
    rel = (nn.value - v0).abs() / np.maximum(v0.abs(), 1.0)
    nn = nn.assign(rel=rel, n=n)
    multi = nn[nn.n >= 2]
    per_key = multi.groupby(keys + ["period_utc"]).rel.max()
    revised = per_key[per_key > AN["revision_threshold"]]
    return {"keys_seen_2plus": int(len(per_key)), "revised_gt1pct": int(len(revised)),
            "share": r4(len(revised) / len(per_key)) if len(per_key) else None,
            "median_rel_change_revised": r4(revised.median()) if len(revised) else None,
            "max_rel_change": r4(per_key.max()) if len(per_key) else None,
            "any_change_share": r4((per_key > 0).mean()) if len(per_key) else None}


def main():
    runs_p = STATE / "snapshot_runs.jsonl"
    runs = [json.loads(l) for l in runs_p.read_text(encoding="utf-8").splitlines() if l.strip()] if runs_p.exists() else []
    res = {"n_runs_recorded": len(runs)}
    if not runs:
        res["status"] = "CHƯA ĐỦ DỮ LIỆU"
        save_json("c2_results.json", res)
        return
    first = pd.Timestamp(runs[0]["fetched_at"])
    slots = pd.date_range(first.floor("h"), periods=AN["runs"], freq="h")
    now = pd.Timestamp.now(tz="UTC")
    elapsed_slots = int((slots <= now).sum())
    ok_slots = {pd.Timestamp(r["fetched_at"]).floor("h") for r in runs if r["success"]}
    n_success = sum(1 for s in slots if s in ok_slots)
    durations = [r["duration_s"] for r in runs if r["success"]]
    res.update({"first_run": str(first), "planned_runs": AN["runs"], "elapsed_slots": elapsed_slots,
                "successful_slots": n_success,
                "success_share_of_planned": r4(n_success / AN["runs"]),
                "success_share_so_far": r4(n_success / max(elapsed_slots, 1)),
                "complete": elapsed_slots >= AN["runs"],
                "duration_s": {"median": pct(durations, 50), "max": max(durations) if durations else None},
                "requests_per_run_median": float(np.median([len(r["requests"]) for r in runs])),
                "statuses": pd.Series([q["status"] for r in runs for q in r["requests"]]).value_counts().to_dict(),
                "rate_headers_seen": sorted({k for r in runs for q in r["requests"] for k in q.get("headers", {})}),
                "errors": [r["error"] for r in runs if not r["success"]]})
    reg = load_route("region-data")
    fuel = load_route("fuel-type-data")
    ic = load_route("interchange-data")
    fetch_times = pd.to_datetime(pd.Series([r["fetched_at"] for r in runs if r["success"]]), utc=True)
    W = AN["window_hours"]
    lat = {}
    for t in ["D", "NG", "TI"]:
        a, cens, n = latency(reg[reg.type == t], ["respondent", "type"], fetch_times, W)
        lat[t] = {"n": n, "censored_gt_window": cens, "median_h": r4(pct(a, 50)), "p95_h": r4(pct(a, 95))}
        lat[t]["per_region_median_h"] = {}
        for rgn, g in reg[reg.type == t].groupby("respondent"):
            b, _, _ = latency(g, ["respondent", "type"], fetch_times, W)
            lat[t]["per_region_median_h"][rgn] = r4(pct(b, 50))
    a, cens, n = latency(fuel, ["respondent", "fueltype"], fetch_times, W)
    lat["FUEL"] = {"n": n, "censored_gt_window": cens, "median_h": r4(pct(a, 50)), "p95_h": r4(pct(a, 95))}
    a, cens, n = latency(ic, ["fromba", "toba"], fetch_times, W)
    lat["INTERCHANGE"] = {"n": n, "censored_gt_window": cens, "median_h": r4(pct(a, 50)), "p95_h": r4(pct(a, 95))}
    # DF lead: how far ahead of the period the forecast first appears (negative latency = ahead)
    df_ = reg[(reg.type == "DF") & reg.value.notna()]
    lead = (df_.groupby(["respondent", "period_utc"]).fetched_at.min().reset_index())
    lead = lead[lead.period_utc > first + pd.Timedelta(hours=48)]
    leadh = (lead.period_utc - lead.fetched_at).dt.total_seconds() / 3600
    lat["DF_lead_hours"] = {"n": int(len(leadh)), "median_h": r4(leadh.median()) if len(leadh) else None,
                            "min_h": r4(leadh.min()) if len(leadh) else None}
    res["latency"] = lat
    rev = {t: revisions(reg[reg.type == t], ["respondent", "type"]) for t in ["D", "DF", "NG", "TI"]}
    rev["FUEL"] = revisions(fuel, ["respondent", "fueltype"])
    rev["INTERCHANGE"] = revisions(ic, ["fromba", "toba"])
    # pooled over actuals (D, NG, TI, FUEL, INTERCHANGE) — DF handled separately
    tot = sum(rev[k]["keys_seen_2plus"] for k in ["D", "NG", "TI", "FUEL", "INTERCHANGE"])
    rv = sum(rev[k]["revised_gt1pct"] for k in ["D", "NG", "TI", "FUEL", "INTERCHANGE"])
    rev["pooled_actuals"] = {"keys": tot, "revised": rv, "share": r4(rv / tot) if tot else None}
    res["revisions"] = rev
    multi_val = reg[reg.type == "DF"].groupby(["respondent", "period_utc", "run_id"]).size().max() if len(reg) else None
    df_rev = rev["DF"]["share"]
    if not res["complete"] or (res["success_share_of_planned"] or 0) < AN["min_success_share"]:
        fm = "CHƯA XÁC ĐỊNH"
    elif df_rev is not None and df_rev <= AN["max_revised_share"] and multi_val == 1:
        fm = "XÁC NHẬN"
    else:
        fm = "KHÔNG XÁC NHẬN"
    res["forecast_meaning"] = {"status": fm, "type_name_api": "Day-ahead demand forecast",
                               "values_per_key_per_snapshot_max": int(multi_val) if multi_val is not None else None,
                               "api_versions": "một phiên bản (không có facet thời điểm phát hành; 1 giá trị/khóa)",
                               "DF_revised_share": df_rev}
    crit = {
        "success_share": {"value": res["success_share_of_planned"], "threshold": ">= 0.95", "pass": (res["success_share_of_planned"] or 0) >= AN["min_success_share"]},
        "demand_latency_median": {"value": lat["D"]["median_h"], "threshold": "<= 3h", "pass": lat["D"]["median_h"] is not None and lat["D"]["median_h"] <= AN["demand_latency_median_max_h"]},
        "demand_latency_p95": {"value": lat["D"]["p95_h"], "threshold": "<= 12h", "pass": lat["D"]["p95_h"] is not None and lat["D"]["p95_h"] <= AN["demand_latency_p95_max_h"]},
        "fuel_latency_p95": {"value": lat["FUEL"]["p95_h"], "threshold": "<= 48h", "pass": lat["FUEL"]["p95_h"] is not None and lat["FUEL"]["p95_h"] <= AN["fuel_latency_p95_max_h"]},
        "revised_share": {"value": rev["pooled_actuals"]["share"], "threshold": "<= 0.05", "pass": rev["pooled_actuals"]["share"] is not None and rev["pooled_actuals"]["share"] <= AN["max_revised_share"]},
    }
    res["criteria"] = crit
    if not res["complete"]:
        res["status"] = "CHƯA ĐỦ DỮ LIỆU"
    else:
        res["status"] = "PASS" if all(c["pass"] for c in crit.values()) else "FAIL"
    save_json("c2_results.json", res)
    print(json.dumps({k: res[k] for k in ("status", "n_runs_recorded", "elapsed_slots", "successful_slots")}, indent=1))


if __name__ == "__main__":
    sys.exit(main())

