"""BƯỚC 4 — Open-Meteo Historical Weather API, temperature_2m theo giờ, timezone=GMT, cho các thành phố đã khóa.
Chunk = (thành phố, năm) lưu JSON thô nén + .done (chạy lại không tải trùng). Không nội suy.
Open-Meteo: miễn phí cho mục đích phi thương mại; dữ liệu CC BY 4.0; giới hạn 600/phút, 5000/giờ, 10000/ngày."""
from __future__ import annotations

import datetime as dt
import json
import sys
import time

import pandas as pd

from common import PARQ, RAW, STATS, http_get, load_yaml, log, run_state, write_json_gz, read_json_gz

LOGF = "weather.log"
URL = "https://archive-api.open-meteo.com/v1/archive"


def cities():
    cfg = load_yaml("regions.yml")["regions"]
    out = {}
    for reg, v in cfg.items():
        for c in v["cities"]:
            key = c["name"].replace(" ", "_").replace(".", "")
            out[key] = (c["lat"], c["lon"])
    return out


def fetch(key, lat, lon, start, end):
    d = RAW / "weather" / key
    done = d / f"{start[:4]}.done"
    if done.exists():
        return "skip"
    params = {"latitude": lat, "longitude": lon, "start_date": start, "end_date": end,
              "hourly": "temperature_2m", "timezone": "GMT"}
    for attempt in range(30):
        r, el = http_get(URL, params, logfile=LOGF, max_tries=6)
        if r.status_code == 429 or (r.status_code == 400 and "limit" in r.text.lower()):
            log(f"open-meteo limit: {r.text[:150]}; sleep 600s", LOGF)
            time.sleep(600)
            continue
        if r.status_code != 200:
            raise RuntimeError(f"{key} {start} HTTP {r.status_code}: {r.text[:200]}")
        j = r.json()
        write_json_gz(d / f"{start[:4]}.json.gz", j)
        done.write_text(json.dumps({"at": dt.datetime.now(dt.timezone.utc).isoformat(), "end": end}))
        return "ok"
    raise RuntimeError("open-meteo limit persisted")


def build_parquet():
    rows = []
    for key in cities():
        for f in sorted((RAW / "weather" / key).glob("*.json.gz")):
            j = read_json_gz(f)
            h = j["hourly"]
            df = pd.DataFrame({"time": h["time"], "temperature_2m": h["temperature_2m"]})
            df["city"] = key
            df["utc_offset_seconds"] = j.get("utc_offset_seconds")
            df["timezone"] = j.get("timezone")
            df["grid_lat"] = j.get("latitude")
            df["grid_lon"] = j.get("longitude")
            rows.append(df)
    df = pd.concat(rows, ignore_index=True)
    df["time_utc"] = pd.to_datetime(df["time"], format="%Y-%m-%dT%H:%M").dt.tz_localize("UTC")
    df = df.drop(columns=["time"])
    out = PARQ / "weather_city_hourly.parquet"
    df.to_parquet(out, index=False)
    log(f"weather parquet rows={len(df)} -> {out}", LOGF)


def main():
    st = run_state()
    end = st["history_end"][:10]
    t0 = time.time()
    cs = cities()
    for key, (lat, lon) in cs.items():
        for y in range(2019, int(end[:4]) + 1):
            s = f"{y}-01-01"
            e = min(f"{y}-12-31", end)
            status = fetch(key, lat, lon, s, e)
            if status == "ok":
                log(f"{key} {y} ok (req={STATS.count})", LOGF)
                time.sleep(1.0)
    build_parquet()
    log(f"weather done in {time.time()-t0:.0f}s, requests={STATS.count}", LOGF)


if __name__ == "__main__":
    sys.exit(main())

