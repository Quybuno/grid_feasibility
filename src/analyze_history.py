"""Phân tích lịch sử: C1, C3 (+dq_review.csv), C4, Q1–Q5 và bảng mart cho dashboard.
Chỉ dùng dữ liệu thật; không nội suy, không điền thiếu. Kết quả -> output/*.json, data/mart/*.parquet."""
from __future__ import annotations

import json
import sys
import time

import numpy as np
import pandas as pd
import psutil

from common import MART, OUT, PARQ, ROOT, load_json, load_yaml, log, run_state, save_json

LOGF = "analyze.log"
ST = run_state()
REG = load_yaml("regions.yml")["regions"]
AN = load_yaml("analysis.yml")
DQ = load_yaml("dq_rules.yml")
TZ = {k: v["tz"] for k, v in REG.items()}
CODES = json.loads((ROOT / "state" / "step0_codes.json").read_text())
REGIONS = [r for r in REG if CODES["region-data"].get(r)]
H0 = pd.Timestamp(ST["history_start"] + ":00", tz="UTC")
H1 = pd.Timestamp(ST["history_end"] + ":00", tz="UTC")
I0 = pd.Timestamp(ST["interchange_start"] + ":00", tz="UTC")
HOURS = pd.date_range(H0, H1, freq="h")
IHOURS = pd.date_range(I0, H1, freq="h")
POS_FUEL_EXCL = set()  # all fueltypes kept; positive part used for totals


def r4(x):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), 4)


# ------------------------------------------------------------------ load & dedup
def dedup(df, keys):
    n = len(df)
    dup_mask = df.duplicated(keys, keep="first")
    ndup = int(dup_mask.sum())
    conflict = 0
    if ndup:
        g = df[df.duplicated(keys, keep=False)].groupby(keys)["value"].nunique(dropna=False)
        conflict = int((g > 1).sum())
    return df[~dup_mask].copy(), ndup, n, conflict


def longest_gap(present_hours: pd.DatetimeIndex, idx: pd.DatetimeIndex) -> int:
    m = idx.isin(present_hours)
    if m.all():
        return 0
    miss = (~m).astype(np.int8)
    # run lengths of consecutive missing
    d = np.diff(np.concatenate([[0], miss, [0]]))
    starts, ends = np.where(d == 1)[0], np.where(d == -1)[0]
    return int((ends - starts).max())


def coverage_stats(df, keycol, keyval, idx):
    sub = df[df[keycol] == keyval] if keycol else df
    sub = sub[(sub.period_utc >= idx[0]) & (sub.period_utc <= idx[-1])]
    return sub


# ------------------------------------------------------------------ C1
def c1(region_raw, fuel_raw, ic_raw):
    res = {"region": [], "fuel_any": [], "fueltype": [], "interchange_pairs": [], "dedup": {}}
    reg = region_raw[(region_raw.period_utc >= H0) & (region_raw.period_utc <= H1)]
    for r in REGIONS:
        for t in ["D", "DF", "NG", "TI"]:
            s = reg[(reg.respondent == r) & (reg.type == t)]
            dd, ndup, n, conf = dedup(s, ["respondent", "type", "period"])
            present = pd.DatetimeIndex(dd.loc[dd.value.notna(), "period_utc"].unique())
            res["region"].append({"region": r, "type": t, "expected_hours": len(HOURS), "rows": n,
                                  "hours_present": int(len(present)),
                                  "share": r4(len(present) / len(HOURS)),
                                  "longest_gap_h": longest_gap(present, HOURS),
                                  "dup_share": r4(ndup / n) if n else None, "dup_conflicting_keys": conf,
                                  "null_share": r4(s.value.isna().mean()) if n else None,
                                  "first": str(dd.period_utc.min()) if n else None})
    fu = fuel_raw[(fuel_raw.period_utc >= H0) & (fuel_raw.period_utc <= H1)]
    for r in REGIONS:
        s = fu[fu.respondent == r]
        dd, ndup, n, conf = dedup(s, ["respondent", "fueltype", "period"])
        present = pd.DatetimeIndex(dd.loc[dd.value.notna(), "period_utc"].unique())
        res["fuel_any"].append({"region": r, "expected_hours": len(HOURS), "rows": n, "hours_present": int(len(present)),
                                "share": r4(len(present) / len(HOURS)), "longest_gap_h": longest_gap(present, HOURS),
                                "dup_share": r4(ndup / n) if n else None, "dup_conflicting_keys": conf,
                                "null_share": r4(s.value.isna().mean()) if n else None,
                                "fueltypes": sorted(dd.fueltype.unique().tolist())})
        for ft, g in dd.groupby("fueltype"):
            p = g.loc[g.value.notna(), "period_utc"].nunique()
            res["fueltype"].append({"region": r, "fueltype": ft, "hours_present": int(p), "share": r4(p / len(HOURS)),
                                    "first": str(g.period_utc.min()), "last": str(g.period_utc.max())})
    # interchange (fromba pass, locked fromba)
    ic = ic_raw[(ic_raw["pass"] == "fromba") & (ic_raw.period_utc >= I0) & (ic_raw.period_utc <= H1)]
    dd, ndup, n, conf = dedup(ic, ["fromba", "toba", "period"])
    res["dedup"]["interchange_fromba"] = {"rows": n, "dup_share": r4(ndup / n) if n else None, "conflicting": conf}
    for (a, b), g in dd.groupby(["fromba", "toba"]):
        present = pd.DatetimeIndex(g.loc[g.value.notna(), "period_utc"].unique())
        res["interchange_pairs"].append({"fromba": a, "toba": b, "expected_hours": len(IHOURS),
                                         "hours_present": int(len(present)), "share": r4(len(present) / len(IHOURS)),
                                         "longest_gap_h": longest_gap(present, IHOURS),
                                         "null_share": r4(g.value.isna().mean())})
    # criteria
    cr = AN["C1"]
    core = [x for x in res["region"] if x["type"] in cr["core_types"]]
    core_ok = all((x["share"] or 0) >= cr["core_min_hours_share"] for x in core)
    fuel_ok_regions = [x["region"] for x in res["fuel_any"] if (x["share"] or 0) >= cr["fuel_min_hours_share"]]
    gap_ok = all(x["longest_gap_h"] <= cr["demand_max_gap_hours"] for x in res["region"] if x["type"] == "D")
    dups = [x["dup_share"] or 0 for x in res["region"]] + [x["dup_share"] or 0 for x in res["fuel_any"]] + \
           [res["dedup"]["interchange_fromba"]["dup_share"] or 0]
    dup_ok = max(dups) <= cr["max_dup_key_share"]
    res["criteria"] = {
        "core_min_share": {"value": min(x["share"] or 0 for x in core), "threshold": ">= 0.98 mọi vùng", "pass": core_ok,
                           "failing": [f'{x["region"]}/{x["type"]}={x["share"]}' for x in core if (x["share"] or 0) < 0.98]},
        "fuel_regions_ge95": {"value": len(fuel_ok_regions), "regions": fuel_ok_regions, "threshold": ">= 5 vùng", "pass": len(fuel_ok_regions) >= 5},
        "demand_max_gap": {"value": max(x["longest_gap_h"] for x in res["region"] if x["type"] == "D"), "threshold": "<= 72h", "pass": gap_ok},
        "max_dup_share": {"value": max(dups), "threshold": "<= 0.001", "pass": dup_ok},
    }
    res["status"] = "PASS" if all(v["pass"] for v in res["criteria"].values()) else "FAIL"
    return res


# ------------------------------------------------------------------ wide hourly tables
def build_wide(region_raw, fuel_raw):
    reg, *_ = dedup(region_raw, ["respondent", "type", "period"])
    w = reg.pivot_table(index=["respondent", "period_utc"], columns="type", values="value", aggfunc="first")
    fu, *_ = dedup(fuel_raw, ["respondent", "fueltype", "period"])
    fw = fu.pivot_table(index=["respondent", "period_utc"], columns="fueltype", values="value", aggfunc="first")
    fueltypes = list(fw.columns)
    fw.columns = [f"F_{c}" for c in fw.columns]
    fcols = list(fw.columns)
    fw["FUEL_SUM"] = fw[fcols].sum(axis=1, min_count=1)
    fw["FUEL_POS"] = fw[fcols].clip(lower=0).sum(axis=1, min_count=1)
    fw["FUEL_N"] = fw[fcols].notna().sum(axis=1)
    wide = w.join(fw, how="outer").reset_index()
    wide = wide[(wide.period_utc >= H0) & (wide.period_utc <= H1)]
    # full hour grid per region (missing stays NaN; no fill)
    grid = pd.MultiIndex.from_product([REGIONS, HOURS], names=["respondent", "period_utc"]).to_frame(index=False)
    wide = grid.merge(wide, on=["respondent", "period_utc"], how="left")
    parts = []
    for r, g in wide.groupby("respondent", sort=False):
        loc = g.period_utc.dt.tz_convert(TZ[r])
        g = g.copy()
        g["period_local"] = loc.dt.strftime("%Y-%m-%dT%H:%M%z")
        g["local_date"] = loc.dt.tz_localize(None).dt.normalize()
        g["local_hour"] = loc.dt.hour
        g["local_dow"] = loc.dt.dayofweek
        g["local_month"] = loc.dt.month
        g["local_year"] = loc.dt.year
        parts.append(g)
    return pd.concat(parts, ignore_index=True), fueltypes


# ------------------------------------------------------------------ weekly-lag baseline (past only)
def lag_matrix(g: pd.DataFrame, col: str, weeks=8):
    """For each row: values of `col` at same local hour, local_date - 7k days (k=1..weeks).
    Also returns the UTC timestamps of those baseline points for the no-future check."""
    key = g[["local_date", "local_hour", col, "period_utc"]].drop_duplicates(["local_date", "local_hour"], keep="first")
    key = key.set_index(["local_date", "local_hour"])
    vals, ts = [], []
    for k in range(1, weeks + 1):
        idx = pd.MultiIndex.from_arrays([g.local_date - pd.Timedelta(days=7 * k), g.local_hour])
        sub = key.reindex(idx)
        vals.append(sub[col].to_numpy(dtype=float))
        ts.append(sub["period_utc"].to_numpy())
    return np.column_stack(vals), np.column_stack(ts)


# ------------------------------------------------------------------ C3
def c3(wide, agg13):
    rules = DQ["rules"]
    pc = DQ["pass_criteria"]
    per = []
    flags = []
    for r in REGIONS:
        g = wide[wide.respondent == r].sort_values("period_utc").reset_index(drop=True)
        D = g["D"]
        # R1
        hasD = D.notna()
        r1 = hasD & (D <= 0)
        # R2
        M, _ = lag_matrix(g, "D")
        cnt = np.sum(~np.isnan(M), axis=1)
        with np.errstate(all="ignore"):
            med = np.nanmedian(np.where(cnt[:, None] >= rules["R2"]["min_points"], M, np.nan), axis=1)
        evalR2 = hasD.to_numpy() & ~np.isnan(med)
        Dv = D.to_numpy(dtype=float)
        with np.errstate(all="ignore"):
            r2 = evalR2 & ((Dv > 3 * med) | (Dv < med / 3) | (Dv <= 0))
        # R3
        ok3 = g["NG"].notna() & (g["FUEL_N"] > 0) & (g["NG"] != 0)
        dev3 = (g["FUEL_SUM"] - g["NG"]).abs() / g["NG"].abs()
        r3 = ok3 & (dev3 > 0.05)
        # R4
        ok4 = g["D"].notna() & g["NG"].notna() & g["TI"].notna() & (g["D"] != 0)
        exp4 = g["NG"] - g["TI"]
        dev4 = (g["D"] - exp4).abs() / g["D"].abs()
        r4_ = ok4 & (dev4 > 0.10)
        per.append({"region": r,
                    "R1_eval_hours": int(hasD.sum()), "R1_flags": int(r1.sum()), "R1_share": r4(r1.sum() / max(hasD.sum(), 1)),
                    "R2_eval_hours": int(evalR2.sum()), "R2_flags": int(r2.sum()), "R2_share": r4(r2.sum() / max(evalR2.sum(), 1)),
                    "R3_eval_hours": int(ok3.sum()), "R3_flags": int(r3.sum()), "R3_pass_share": r4(1 - r3.sum() / max(ok3.sum(), 1)) if ok3.sum() else None,
                    "R4_eval_hours": int(ok4.sum()), "R4_flags": int(r4_.sum()), "R4_pass_share": r4(1 - r4_.sum() / max(ok4.sum(), 1)) if ok4.sum() else None})
        for rule, mask, val, exp, scol, ecol in (
                ("R1", r1.to_numpy(), Dv, np.zeros(len(g)), "D", None),
                ("R2", r2, Dv, med, "D", None),
                ("R3", r3.to_numpy(), g["FUEL_SUM"].to_numpy(float), g["NG"].to_numpy(float), "FUEL_SUM", "NG"),
                ("R4", r4_.to_numpy(), Dv, exp4.to_numpy(float), "D", "NG_minus_TI")):
            for i in np.where(mask)[0]:
                flags.append((r, g.period_utc.iat[i], rule, val[i], exp[i], scol, ecol))
    # R5 (informational, same-scope check with 13 EIA aggregates)
    r5 = {"applicable_to_locked_regions": False,
          "reason": "7 vùng khóa không phủ toàn bộ US48 => không cùng phạm vi (dq_rules.yml)"}
    if agg13 is not None and len(agg13):
        a, *_ = dedup(agg13, ["respondent", "type", "period"])
        a = a[(a.period_utc >= H0) & (a.period_utc <= H1) & a.value.notna()]
        s = a.groupby("period_utc").agg(sum13=("value", "sum"), n=("respondent", "nunique"))
        us = wide[wide.respondent == "US48"].set_index("period_utc")["D"]
        j = s.join(us.rename("US48"), how="inner")
        j = j[(j.n == 13) & j.US48.notna() & (j.US48 != 0)]
        dev = (j.sum13 - j.US48).abs() / j.US48.abs()
        r5.update({"aux_check_13_regions": {"hours_evaluated": int(len(j)), "flags": int((dev > 0.05).sum()),
                                            "flag_share": r4((dev > 0.05).mean()) if len(j) else None,
                                            "median_abs_dev": r4(dev.median()) if len(j) else None}})
    crit = {
        "R1_max_share": {"value": max(p["R1_share"] for p in per), "threshold": "<= 0.02 mọi vùng",
                         "pass": all(p["R1_share"] <= pc["R1_R2_max_flag_share"] for p in per)},
        "R2_max_share": {"value": max(p["R2_share"] for p in per), "threshold": "<= 0.02 mọi vùng",
                         "pass": all(p["R2_share"] <= pc["R1_R2_max_flag_share"] for p in per)},
        "R3_min_pass": {"value": min((p["R3_pass_share"] if p["R3_pass_share"] is not None else 0) for p in per),
                        "threshold": ">= 0.90 mọi vùng",
                        "pass": all((p["R3_pass_share"] or 0) >= pc["R3_min_pass_share"] for p in per),
                        "failing": [f'{p["region"]}={p["R3_pass_share"]}' for p in per if (p["R3_pass_share"] or 0) < 0.9]},
        "R4_min_pass": {"value": min((p["R4_pass_share"] if p["R4_pass_share"] is not None else 0) for p in per),
                        "threshold": ">= 0.90 mọi vùng",
                        "pass": all((p["R4_pass_share"] or 0) >= pc["R4_min_pass_share"] for p in per),
                        "failing": [f'{p["region"]}={p["R4_pass_share"]}' for p in per if (p["R4_pass_share"] or 0) < 0.9]},
    }
    return {"per_region": per, "R5": r5, "criteria": crit, "n_flags_total": len(flags)}, flags


def dq_review(flags, wide):
    cfg = DQ["review_sample"]
    rng = np.random.default_rng(cfg["seed"])
    fl = pd.DataFrame(flags, columns=["region", "hour_utc", "rule", "value", "expected", "scol", "ecol"])
    fl = fl[fl.rule.isin(cfg["rules_sampled"])].sort_values(["region", "hour_utc", "rule"]).reset_index(drop=True)
    order = rng.permutation(len(fl))
    picked, cnt = [], {}
    for i in order:
        row = fl.iloc[i]
        k = (row.region, row.hour_utc.strftime("%Y-%m"))
        if cnt.get(k, 0) >= cfg["max_per_region_month"]:
            continue
        cnt[k] = cnt.get(k, 0) + 1
        picked.append(i)
        if len(picked) >= cfg["n"]:
            break
    out = []
    widx = wide.set_index(["respondent", "period_utc"])
    for i in picked:
        row = fl.iloc[i]
        g = wide[wide.respondent == row.region].set_index("period_utc")
        win = pd.date_range(row.hour_utc - pd.Timedelta(hours=36), row.hour_utc + pd.Timedelta(hours=35), freq="h")
        sub = g.reindex(win)
        if row.scol == "FUEL_SUM":
            sv, ev = sub["FUEL_SUM"], sub["NG"]
        elif row.ecol == "NG_minus_TI":
            sv, ev = sub["D"], sub["NG"] - sub["TI"]
        else:
            sv, ev = sub["D"], None
        tolist = lambda s: json.dumps([None if pd.isna(x) else round(float(x), 1) for x in s])
        out.append({"region": row.region, "hour_utc": row.hour_utc.strftime("%Y-%m-%dT%H:00Z"),
                    "hour_local": row.hour_utc.tz_convert(TZ[row.region]).strftime("%Y-%m-%dT%H:%M%z"),
                    "rule": row.rule, "value": r4(row.value), "expected": r4(row.expected),
                    "chuoi_72h_start_utc": win[0].strftime("%Y-%m-%dT%H:00Z"),
                    "chuoi_72h": tolist(sv),
                    "chuoi_72h_expected": tolist(ev) if ev is not None else "",
                    "is_real_issue": "", "ghi_chu": ""})
    df = pd.DataFrame(out)
    p = ROOT / "review" / "dq_review.csv"
    p.parent.mkdir(exist_ok=True)
    if p.exists():
        old = pd.read_csv(p, dtype=str, keep_default_na=False)
        if (old.get("is_real_issue", pd.Series(dtype=str)).str.strip() != "").any():
            df.to_csv(p.with_name("dq_review.regenerated.csv"), index=False, encoding="utf-8-sig")
            log("dq_review.csv đã có chấm tay -> không ghi đè; bản mới: dq_review.regenerated.csv", LOGF)
            return {"n": len(df), "path": str(p), "overwritten": False, "n_flags_pool": len(fl)}
    df.to_csv(p, index=False, encoding="utf-8-sig")
    return {"n": len(df), "path": str(p), "overwritten": True, "n_flags_pool": len(fl),
            "by_rule": df.rule.value_counts().to_dict() if len(df) else {}}


def manual_review_status():
    p = ROOT / "review" / "dq_review.csv"
    if not p.exists():
        return {"status": "CHƯA XÁC ĐỊNH", "reason": "không có file"}
    df = pd.read_csv(p, dtype=str, keep_default_na=False)
    v = df["is_real_issue"].str.strip().str.lower()
    filled = v[v != ""]
    if len(filled) < len(df) or len(df) == 0:
        return {"status": "CHƯA XÁC ĐỊNH", "reason": f"đã chấm {len(filled)}/{len(df)}"}
    yes = filled.isin(["1", "true", "yes", "y", "co", "có", "x"]).sum()
    share = yes / len(filled)
    return {"status": "PASS" if share >= DQ["pass_criteria"]["manual_min_valid_share"] else "FAIL",
            "valid_share": r4(share), "n": int(len(filled))}


# ------------------------------------------------------------------ C4
def c4(wide):
    w = pd.read_parquet(PARQ / "weather_city_hourly.parquet")
    checks = {}
    dupl = int(w.duplicated(["city", "time_utc"]).sum())
    offs = sorted(w.utc_offset_seconds.dropna().unique().tolist())
    tzs = sorted(w.timezone.dropna().unique().tolist())
    cont = {}
    for c, g in w.groupby("city"):
        d = g.time_utc.sort_values().diff().dropna().dt.total_seconds().unique().tolist()
        cont[c] = d == [3600.0]
    checks["weather_duplicates"] = dupl
    checks["weather_utc_offsets"] = offs
    checks["weather_timezones"] = tzs
    checks["weather_continuous_all_cities"] = all(cont.values())
    temps = []
    per = []
    for r in REGIONS:
        cs = REG[r]["cities"]
        tot = sum(c["pop2020"] for c in cs)
        mats = []
        for c in cs:
            key = c["name"].replace(" ", "_").replace(".", "")
            s = w[w.city == key].set_index("time_utc")["temperature_2m"].reindex(HOURS)
            mats.append(s.to_numpy(dtype=float) * c["pop2020"] / tot)
        M = np.column_stack(mats)
        t = np.where(np.isnan(M).any(axis=1), np.nan, M.sum(axis=1))  # no reweighting when a city missing
        df = pd.DataFrame({"respondent": r, "period_utc": HOURS, "temp_w": t})
        temps.append(df)
        loc = HOURS.tz_convert(TZ[r])
        tmp = pd.DataFrame({"t": t, "d": loc.tz_localize(None).normalize(), "h": loc.hour}).dropna()
        peak_h = tmp.loc[tmp.groupby("d")["t"].idxmax(), "h"]
        per.append({"region": r, "hours_with_temp": int(np.isfinite(t).sum()), "share": r4(np.isfinite(t).mean()),
                    "median_local_hour_of_daily_max": float(peak_h.median()),
                    "missing_last": str(HOURS[~np.isfinite(t)].max()) if (~np.isfinite(t)).any() else None})
    T = pd.concat(temps, ignore_index=True)
    j = wide[["respondent", "period_utc"]].merge(T, on=["respondent", "period_utc"], how="left", validate="one_to_one")
    checks["join_one_to_one"] = len(j) == len(wide)
    checks["diurnal_peak_in_12_18_all"] = all(12 <= p["median_local_hour_of_daily_max"] <= 18 for p in per)
    align_ok = (dupl == 0 and offs == [0] and checks["weather_continuous_all_cities"]
                and checks["join_one_to_one"] and checks["diurnal_peak_in_12_18_all"])
    crit = {"min_share": {"value": min(p["share"] for p in per), "threshold": ">= 0.99 mọi vùng",
                          "pass": all(p["share"] >= AN["C4"]["min_hours_share"] for p in per)},
            "utc_alignment": {"value": align_ok, "threshold": "không lệch", "pass": bool(align_ok)}}
    return {"per_region": per, "checks": checks, "criteria": crit}, T


# ------------------------------------------------------------------ Q1
def profile_metrics(p: pd.Series):
    """p indexed by local hour 0..23."""
    if p.reindex(range(24)).isna().any():
        return None
    p = p.reindex(range(24))
    return {"midday_depth": float(p.loc[6:9].max() - p.loc[10:15].min()),
            "afternoon_ramp": float(max((p.loc[h + 3] - p.loc[h]) / 3 for h in range(13, 18))),
            "evening_peak": float(p.loc[17:21].max())}


def q1(wide):
    cfg = AN["Q1"]
    w = wide.copy()
    for c in ("F_WND", "F_SUN"):
        if c not in w:
            w[c] = np.nan
    w["NL"] = w["D"] - w["F_WND"] - w["F_SUN"]
    w["complete"] = w[["D", "F_WND", "F_SUN"]].notna().all(axis=1)
    season = {m: s for s, ms in cfg["seasons"].items() for m in ms}
    w["season"] = w.local_month.map(season)
    share_year = 2025
    shares, cov = {}, {}
    for r in REGIONS:
        g = w[(w.respondent == r)]
        gy = g[g.local_year == share_year]
        tot = gy["FUEL_POS"].sum(min_count=1)
        ws = gy[["F_WND", "F_SUN"]].clip(lower=0).sum().sum()
        shares[r] = r4(ws / tot) if tot and tot > 0 else None
        cov[r] = {int(y): r4(gg.complete.mean()) for y, gg in g.groupby(g.period_utc.dt.year)}
    share_ok = [r for r in REGIONS if (shares[r] or 0) >= cfg["min_share"]]
    years = list(range(2019, 2026))
    full_years = [y for y in years if share_ok and all((cov[r].get(y) or 0) >= 0.98 for r in share_ok)]
    # profiles
    prof_rows, metrics = [], []
    c = w[w.complete]
    for (r, y, s), g in c.groupby(["respondent", "local_year", "season"]):
        med = g.groupby("local_hour")["NL"].median()
        mean = g.groupby("local_hour")["NL"].mean()
        for h in range(24):
            prof_rows.append({"region": r, "year": int(y), "season": s, "local_hour": h,
                              "nl_median": med.get(h, np.nan), "nl_mean": mean.get(h, np.nan),
                              "n_hours": int((g.local_hour == h).sum())})
        mm, ma = profile_metrics(med), profile_metrics(mean)
        if mm and ma:
            metrics.append({"region": r, "year": int(y), "season": s, **{f"med_{k}": v for k, v in mm.items()},
                            **{f"mean_{k}": v for k, v in ma.items()}, "n_hours": len(g)})
    M = pd.DataFrame(metrics)
    comps, same = 0, 0
    detail = []
    for r in share_ok:
        for y in full_years:
            if y + 1 not in full_years:
                continue
            for s in cfg["seasons"]:
                a = M[(M.region == r) & (M.year == y) & (M.season == s)]
                b = M[(M.region == r) & (M.year == y + 1) & (M.season == s)]
                if a.empty or b.empty:
                    continue
                for k in ("midday_depth", "afternoon_ramp", "evening_peak"):
                    dm = b[f"med_{k}"].iat[0] - a[f"med_{k}"].iat[0]
                    da = b[f"mean_{k}"].iat[0] - a[f"mean_{k}"].iat[0]
                    ok = np.sign(dm) == np.sign(da)
                    comps += 1
                    same += int(ok)
    cons = same / comps if comps else None
    pd.DataFrame(prof_rows).to_parquet(MART / "q1_netload_profiles.parquet", index=False)
    if len(M):
        M.to_parquet(MART / "q1_netload_metrics.parquet", index=False)
    latest = M[M.year == 2025].groupby("region")[["med_midday_depth", "med_afternoon_ramp", "med_evening_peak"]].median() if len(M) else pd.DataFrame()
    crit = {"regions_ws_share_ge5pct_2025": {"value": len(share_ok), "regions": share_ok, "threshold": ">= 5", "pass": len(share_ok) >= cfg["min_regions_share"]},
            "full_years": {"value": len(full_years), "years": full_years, "threshold": ">= 3", "pass": len(full_years) >= cfg["min_full_years"]},
            "mean_median_consistency": {"value": r4(cons), "n_comparisons": comps, "threshold": ">= 0.80",
                                        "pass": cons is not None and cons >= cfg["min_consistency"]}}
    return {"ws_share_2025": shares, "complete_coverage_by_year": cov, "criteria": crit,
            "latest_year_metrics_median_over_seasons": json.loads(latest.round(1).to_json(orient="index")) if len(latest) else {}}


# ------------------------------------------------------------------ Q2
def newey_west_ols(y, X, lag=24):
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ y
    u = y - X @ beta
    Z = X * u[:, None]
    S = Z.T @ Z
    for l in range(1, lag + 1):
        wl = 1 - l / (lag + 1)
        G = Z[l:].T @ Z[:-l]
        S += wl * (G + G.T)
    V = XtX_inv @ S @ XtX_inv
    se = np.sqrt(np.diag(V))
    return beta, se, len(y)


def q2(wide, temps):
    cfg = AN["Q2"]
    w = wide.merge(temps, on=["respondent", "period_utc"], how="left")
    w["both"] = w.D.notna() & w.DF.notna()
    cov_region = {r: r4(w[w.respondent == r].both.mean()) for r in REGIONS}
    pooled = r4(w.both.mean())
    ok_regions = [r for r, v in cov_region.items() if (v or 0) >= cfg["min_coverage"]]
    e = w[w.both & (w.D > 0)].copy()
    e["err"] = e.DF - e.D
    e["abs"] = e.err.abs()
    e["ape"] = e["abs"] / e.D * 100
    e["ren_share"] = e[["F_WND", "F_SUN"]].clip(lower=0).sum(axis=1, min_count=2) / e.FUEL_POS
    summ = e.groupby("respondent").agg(MAPE=("ape", "mean"), MdAPE=("ape", "median"), MAE=("abs", "mean"),
                                       bias=("err", "mean"), n=("ape", "size")).round(3)
    by_month = e.groupby(["respondent", "local_month"]).agg(MAPE=("ape", "mean"), MAE=("abs", "mean"), bias=("err", "mean"), n=("ape", "size")).reset_index()
    by_hour = e.groupby(["respondent", "local_hour"]).agg(MAPE=("ape", "mean"), MAE=("abs", "mean"), bias=("err", "mean"), n=("ape", "size")).reset_index()
    by_month.to_parquet(MART / "q2_err_by_month.parquet", index=False)
    by_hour.to_parquet(MART / "q2_err_by_hour.parquet", index=False)
    comps, same, groups, reg_out = 0, 0, [], {}
    for r in REGIONS:
        g = e[e.respondent == r].sort_values("period_utc")
        gt = g[g.temp_w.notna()]
        if len(gt) > 100:
            p10, p90 = gt.temp_w.quantile([0.1, 0.9])
            tg = np.where(gt.temp_w <= p10, "cold", np.where(gt.temp_w >= p90, "hot", "mid"))
            st = gt.groupby(tg)["ape"].agg(["mean", "median", "size"])
            groups.append({"region": r, "dim": "temp", **{f"{k}_{m}": r4(st.loc[k, m]) for k in st.index for m in ("mean", "median", "size")}})
            for a in ("cold", "hot"):
                if a in st.index and "mid" in st.index:
                    comps += 1
                    same += int(np.sign(st.loc[a, "mean"] - st.loc["mid", "mean"]) == np.sign(st.loc[a, "median"] - st.loc["mid", "median"]))
        gr = g[g.ren_share.notna()]
        if len(gr) > 100:
            q = gr.ren_share.quantile([1 / 3, 2 / 3])
            rg = np.where(gr.ren_share <= q.iloc[0], "low", np.where(gr.ren_share <= q.iloc[1], "mid", "high"))
            st = gr.groupby(rg)["ape"].agg(["mean", "median", "size"])
            groups.append({"region": r, "dim": "ren_share", **{f"{k}_{m}": r4(st.loc[k, m]) for k in st.index for m in ("mean", "median", "size")}})
            for a in ("high", "mid"):
                if a in st.index and "low" in st.index:
                    comps += 1
                    same += int(np.sign(st.loc[a, "mean"] - st.loc["low", "mean"]) == np.sign(st.loc[a, "median"] - st.loc["low", "median"]))
        # regression
        gg = g[g.temp_w.notna() & g.ren_share.notna()]
        if len(gg) > 1000:
            p10, p90 = gg.temp_w.quantile([0.1, 0.9])
            X = [np.ones(len(gg)), (gg.temp_w <= p10).astype(float), (gg.temp_w >= p90).astype(float), gg.ren_share.to_numpy() * 100]
            names = ["const", "cold_p10", "hot_p90", "ren_share_pp"]
            for h in range(1, 24):
                X.append((gg.local_hour == h).astype(float).to_numpy())
            for m in range(2, 13):
                X.append((gg.local_month == m).astype(float).to_numpy())
            X = np.column_stack(X)
            b, se, n = newey_west_ols(gg.ape.to_numpy(float), X, lag=24)
            reg_out[r] = {nm: {"coef": r4(b[i]), "se_hac": r4(se[i]), "t": r4(b[i] / se[i]) if se[i] > 0 else None}
                          for i, nm in enumerate(names)}
            reg_out[r]["n"] = int(n)
    cons = same / comps if comps else None
    c2 = load_json("c2_results.json", {}) or {}
    fm = c2.get("forecast_meaning", {}).get("status", "CHƯA XÁC ĐỊNH")
    crit = {"forecast_meaning_C2": {"value": fm, "threshold": "xác nhận", "pass": fm == "XÁC NHẬN" if fm != "CHƯA XÁC ĐỊNH" else None},
            "pooled_coverage": {"value": pooled, "threshold": ">= 0.98", "pass": (pooled or 0) >= cfg["min_coverage"]},
            "regions_ge98": {"value": len(ok_regions), "regions": ok_regions, "threshold": ">= 5", "pass": len(ok_regions) >= cfg["min_regions"]},
            "mean_median_consistency": {"value": r4(cons), "n_comparisons": comps, "threshold": ">= 0.80",
                                        "pass": cons is not None and cons >= cfg["min_consistency"]}}
    return {"coverage_by_region": cov_region, "summary": json.loads(summ.to_json(orient="index")), "groups": groups,
            "regression_hac": reg_out, "criteria": crit}


# ------------------------------------------------------------------ Q3
def q3(wide, c1res):
    cfg = AN["Q3"]
    fuel_share = {x["region"]: x["share"] for x in c1res["fuel_any"]}
    fcols = [c for c in wide.columns if c.startswith("F_")]
    out, ok = {}, []
    for r in REGIONS:
        g = wide[wide.respondent == r]
        pos = g["FUEL_POS"].sum()
        oth = sum(g[c].clip(lower=0).sum() for c in ("F_OTH", "F_UNK") if c in g)
        oshare = oth / pos if pos else None
        h16 = g[g.local_hour == 16].drop_duplicates("local_date").set_index("local_date")[fcols]
        h20 = g[g.local_hour == 20].drop_duplicates("local_date").set_index("local_date")[fcols]
        d = (h20 - h16)
        d_last = d[d.index.year == 2025]
        stats = {}
        for c in fcols:
            s, sl = d[c].dropna(), d_last[c].dropna()
            if len(s):
                stats[c[2:]] = {"mean_all": r4(s.mean()), "median_all": r4(s.median()), "n_days_all": int(len(s)),
                                "mean_2025": r4(sl.mean()) if len(sl) else None,
                                "median_2025": r4(sl.median()) if len(sl) else None, "n_days_2025": int(len(sl))}
        good = (fuel_share.get(r) or 0) >= 0.95 and oshare is not None and oshare <= 0.10
        if good:
            ok.append(r)
        out[r] = {"fuel_hours_share": fuel_share.get(r), "other_unk_share": r4(oshare), "region_ok": good, "delta_16_to_20": stats}
    crit = {"regions_ok": {"value": len(ok), "regions": ok, "threshold": ">= 5 vùng (phủ>=95% và OTH+UNK<=10%)",
                           "pass": len(ok) >= cfg["min_regions"]}}
    return {"per_region": out, "criteria": crit}


# ------------------------------------------------------------------ Q4
def q4(wide, ic_raw):
    cfg = AN["Q4"]
    ic = ic_raw[(ic_raw.period_utc >= I0) & (ic_raw.period_utc <= H1)]
    ic, *_ = dedup(ic.sort_values("pass"), ["fromba", "toba", "period"])
    locked = [r for r in REGIONS if r != "US48"]
    fb = ic[ic.fromba.isin(locked)]
    pairs = fb.groupby(["fromba", "toba"])
    tot_exp = len(IHOURS) * pairs.ngroups
    tot_have = int(fb[fb.value.notna()].groupby(["fromba", "toba"]).period_utc.nunique().sum())
    coverage = tot_have / tot_exp if tot_exp else None
    # symmetry
    a = ic[ic.value.notna()][["fromba", "toba", "period_utc", "value"]]
    b = a.rename(columns={"fromba": "toba", "toba": "fromba", "value": "rev"})
    j = a.merge(b, on=["fromba", "toba", "period_utc"], how="inner")
    j = j[j.fromba.isin(locked)]
    j = j[j.fromba < j.toba]  # each unordered pair once
    den = np.maximum(j.value.abs(), j.rev.abs())
    match = np.where(den == 0, True, (j.value + j.rev).abs() / den.replace(0, np.nan) <= 0.05)
    sym = float(np.mean(match)) if len(j) else None
    sym_pairs = j.assign(m=match).groupby(["fromba", "toba"]).m.agg(["mean", "size"]).round(4).reset_index()
    stress = {}
    w = wide[(wide.period_utc >= I0)]
    for r in locked:
        g = w[(w.respondent == r) & w.D.notna()]
        thr = g.D.quantile(0.99)
        sh = g[g.D >= thr]
        f = fb[(fb.fromba == r) & fb.period_utc.isin(sh.period_utc)]
        partner = (-f.groupby("toba").value.median()).sort_values(ascending=False)
        stress[r] = {"n_stress_hours": int(len(sh)), "D_threshold": r4(thr),
                     "net_import_median_stress": r4((-sh.TI).median()), "net_import_mean_stress": r4((-sh.TI).mean()),
                     "net_import_median_all": r4((-g.TI).median()),
                     "main_partner": partner.index[0] if len(partner) else None,
                     "main_partner_median_import": r4(partner.iloc[0]) if len(partner) else None,
                     "top3_partners": {k: r4(v) for k, v in partner.head(3).items()}}
    crit = {"pair_coverage": {"value": r4(coverage), "n_pairs": int(pairs.ngroups), "threshold": ">= 0.95", "pass": (coverage or 0) >= cfg["min_coverage"]},
            "symmetry_within_5pct": {"value": r4(sym), "n_hours": int(len(j)), "threshold": ">= 0.90", "pass": (sym or 0) >= cfg["min_symmetry_share"]}}
    return {"stress": stress, "symmetry_by_pair": sym_pairs.to_dict(orient="records"), "criteria": crit}


# ------------------------------------------------------------------ Q5
def q5(wide):
    cfg = AN["Q5"]
    start = H1 - pd.Timedelta(days=90)
    per, all_flags, future_violations = [], [], 0
    for r in REGIONS:
        g = wide[wide.respondent == r].sort_values("period_utc").reset_index(drop=True)
        M, T = lag_matrix(g, "D")
        ev = (g.period_utc > start).to_numpy() & g.D.notna().to_numpy()
        Mi, Ti, gi = M[ev], T[ev], g[ev]
        # no-future check: every baseline timestamp strictly earlier than evaluated hour
        tsv = pd.DataFrame(Ti).apply(pd.to_datetime, utc=True)
        later = (tsv.to_numpy() >= gi.period_utc.to_numpy()[:, None]) & tsv.notna().to_numpy()
        future_violations += int(later.sum())
        cnt = np.sum(~np.isnan(Mi), axis=1)
        Mi = np.where(cnt[:, None] >= cfg["min_points"], Mi, np.nan)
        with np.errstate(all="ignore"):
            med = np.nanmedian(Mi, axis=1)
            mad = 1.4826 * np.nanmedian(np.abs(Mi - med[:, None]), axis=1)
        x = gi.D.to_numpy(float)
        evaluable = ~np.isnan(med) & (mad > 0)
        flag = evaluable & (np.abs(x - med) > 3 * mad)
        per.append({"region": r, "hours_in_window": int(ev.sum()), "evaluable": int(evaluable.sum()),
                    "mad_zero_or_insufficient": int((~evaluable).sum()), "flags": int(flag.sum()),
                    "flag_share": r4(flag.sum() / evaluable.sum()) if evaluable.sum() else None})
        all_flags.append(pd.DataFrame({"region": r, "period_utc": gi.period_utc.to_numpy(), "D": x, "median": med,
                                       "madn": mad, "flag": flag}))
    pd.concat(all_flags).to_parquet(MART / "q5_anomaly_last90d.parquet", index=False)
    crit = {"max_flag_share": {"value": max((p["flag_share"] or 0) for p in per), "threshold": "<= 0.05 mọi vùng",
                               "pass": all(p["flag_share"] is not None and p["flag_share"] <= cfg["max_flag_share"] for p in per)},
            "no_future_data": {"value": future_violations, "threshold": "0 vi phạm", "pass": future_violations == 0}}
    return {"window": [str(start), str(H1)], "per_region": per, "criteria": crit}


def main():
    t0 = time.time()
    proc = psutil.Process()
    region_raw = pd.read_parquet(PARQ / "region_raw.parquet")
    fuel_raw = pd.read_parquet(PARQ / "fuel_raw.parquet")
    ic_raw = pd.read_parquet(PARQ / "interchange_raw.parquet")
    agg13 = pd.read_parquet(PARQ / "agg13_raw.parquet") if (PARQ / "agg13_raw.parquet").exists() else None
    res = {"run": ST}
    res["C1"] = c1(region_raw, fuel_raw, ic_raw); log("C1 done", LOGF)
    wide, fueltypes = build_wide(region_raw, fuel_raw)
    res["fueltypes_seen"] = fueltypes
    c3res, flags = c3(wide, agg13)
    c3res["review"] = dq_review(flags, wide)
    c3res["manual"] = manual_review_status()
    res["C3"] = c3res; log("C3 done", LOGF)
    res["C4"], temps = c4(wide); log("C4 done", LOGF)
    mart = wide.merge(temps, on=["respondent", "period_utc"], how="left")
    mart.to_parquet(MART / "hourly_region_wide.parquet", index=False)
    daily = mart.groupby(["respondent", "local_date"]).agg(
        D_sum=("D", "sum"), D_max=("D", "max"), NG_sum=("NG", "sum"), DF_sum=("DF", "sum"),
        WND_sum=("F_WND", "sum"), SUN_sum=("F_SUN", "sum"), temp_mean=("temp_w", "mean"), hours=("D", "count")).reset_index()
    daily.to_parquet(MART / "daily_region.parquet", index=False)
    res["Q1"] = q1(wide); log("Q1 done", LOGF)
    res["Q2"] = q2(wide, temps); log("Q2 done", LOGF)
    res["Q3"] = q3(wide, res["C1"]); log("Q3 done", LOGF)
    res["Q4"] = q4(wide, ic_raw); log("Q4 done", LOGF)
    res["Q5"] = q5(wide); log("Q5 done", LOGF)
    mi = proc.memory_info()
    res["resources"] = {"analyze_elapsed_s": round(time.time() - t0, 1),
                        "peak_rss_bytes": int(getattr(mi, "peak_wset", mi.rss))}
    save_json("history_results.json", res)
    log(f"analyze done in {time.time()-t0:.0f}s", LOGF)


if __name__ == "__main__":
    sys.exit(main())

