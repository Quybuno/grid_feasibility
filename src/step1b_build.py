"""Chuẩn hóa JSON thô backfill -> Parquet (giữ nguyên mọi dòng, kể cả trùng; dedup ở bước phân tích).
Mọi thời gian: period_utc (UTC) + period_local/local_date/local_hour/local_dow theo múi giờ IANA của vùng (DST đúng)."""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from common import PARQ, RAW, load_yaml, log, read_json_gz

TZ = {k: v["tz"] for k, v in load_yaml("regions.yml")["regions"].items()}


def add_time(df: pd.DataFrame, region_col: str) -> pd.DataFrame:
    df["period_utc"] = pd.to_datetime(df["period"], format="%Y-%m-%dT%H").dt.tz_localize("UTC")
    df["period_local"] = pd.NA
    df["local_date"] = pd.NaT
    df["local_hour"] = pd.array([pd.NA] * len(df), dtype="Int8")
    df["local_dow"] = pd.array([pd.NA] * len(df), dtype="Int8")
    df["utc_offset_h"] = pd.array([pd.NA] * len(df), dtype="Float32")
    parts = []
    for reg, g in df.groupby(region_col, sort=False):
        tz = TZ.get(reg)
        g = g.copy()
        if tz:
            loc = g["period_utc"].dt.tz_convert(tz)
            g["period_local"] = loc.dt.strftime("%Y-%m-%dT%H:%M%z")
            g["local_date"] = loc.dt.tz_localize(None).dt.normalize()
            g["local_hour"] = loc.dt.hour.astype("Int8")
            g["local_dow"] = loc.dt.dayofweek.astype("Int8")
            g["utc_offset_h"] = ((loc.dt.tz_localize(None) - g["period_utc"].dt.tz_localize(None))
                                 .dt.total_seconds() / 3600).astype("Float32")
        parts.append(g)
    return pd.concat(parts, ignore_index=True)


def load_pages(ds: str) -> pd.DataFrame:
    frames = []
    for f in sorted((RAW / "backfill" / ds).rglob("*.json.gz")):
        data = read_json_gz(f)["response"]["data"]
        if data:
            d = pd.DataFrame(data)
            d["chunk"] = f.parent.name + "/" + f.name.split("_p")[0]
            frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    df["value_raw"] = df["value"].astype("string")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df


def main():
    for ds, regcol, out in (("region-data", "respondent", "region_raw"),
                            ("fuel-type-data", "respondent", "fuel_raw"),
                            ("region-data-agg13", "respondent", "agg13_raw")):
        df = load_pages(ds)
        keep = [c for c in ["period", "respondent", "type", "fueltype", "value", "value_raw", "value-units", "chunk"] if c in df]
        df = add_time(df[keep], regcol)
        df.to_parquet(PARQ / f"{out}.parquet", index=False)
        log(f"{out}: {len(df)} rows")
    frames = []
    for direction in ("fromba", "toba"):
        d = load_pages(f"interchange-data-{direction}")
        d["pass"] = direction
        frames.append(d)
    ic = pd.concat(frames, ignore_index=True)
    ic = ic[["period", "fromba", "toba", "value", "value_raw", "value-units", "chunk", "pass"]]
    ic = add_time(ic, "fromba")
    ic.to_parquet(PARQ / "interchange_raw.parquet", index=False)
    log(f"interchange_raw: {len(ic)} rows")


if __name__ == "__main__":
    sys.exit(main())
