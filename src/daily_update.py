"""C5 — mô phỏng 1 lần cập nhật NGÀY: tải lại 7 ngày gần nhất (D-10..D-3) mọi route EIA + thời tiết 7 ngày,
rồi dựng lại Parquet và tính lại toàn bộ bảng mart. Đo thời gian từng phần. Raw lưu ở data/raw/daily/<D>/."""
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
import time

from common import EIA_BASE, RAW, STATE, STATS, http_get, load_yaml, log, run_state, save_json, write_json_gz

LOGF = "daily_update.log"
AGG13 = ["CAL", "CAR", "CENT", "FLA", "MIDA", "MIDW", "NE", "NY", "NW", "SE", "SW", "TEN", "TEX"]


def fetch_all(route, facets, start, end, tag):
    offset, page, n = 0, 0, 0
    while True:
        params = {"frequency": "hourly", "data[0]": "value", "start": start, "end": end, "offset": offset,
                  "length": 5000, "sort[0][column]": "period", "sort[0][direction]": "asc", **facets}
        r, _ = http_get(f"{EIA_BASE}/electricity/rto/{route}/data/", params, eia=True, logfile=LOGF)
        r.raise_for_status()
        j = r.json()
        data = j["response"]["data"]
        write_json_gz(RAW / "daily" / run_state()["D"] / f"{tag}_p{page:02d}.json.gz", j)
        n += len(data); offset += len(data); page += 1
        if not data or offset >= int(j["response"].get("total") or 0):
            return n


def main():
    st = run_state()
    regions = list(load_yaml("regions.yml")["regions"])
    ic = [r for r in regions if r != "US48"]
    end = dt.datetime.strptime(st["history_end"], "%Y-%m-%dT%H")
    start = end - dt.timedelta(days=7) + dt.timedelta(hours=1)
    s, e = start.strftime("%Y-%m-%dT%H"), end.strftime("%Y-%m-%dT%H")
    t0 = time.time()
    rows = {}
    f = {f"facets[respondent][{i}]": r for i, r in enumerate(regions)}
    rows["region"] = fetch_all("region-data", f, s, e, "region")
    rows["fuel"] = fetch_all("fuel-type-data", f, s, e, "fuel")
    rows["agg13"] = fetch_all("region-data", {"facets[type][]": "D", **{f"facets[respondent][{i}]": r for i, r in enumerate(AGG13)}}, s, e, "agg13")
    for d in ("fromba", "toba"):
        rows[f"ic_{d}"] = fetch_all("interchange-data", {f"facets[{d}][{i}]": r for i, r in enumerate(ic)}, s, e, f"ic_{d}")
    t_eia = time.time() - t0
    # weather 7 days, multi-location single request
    cfg = load_yaml("regions.yml")["regions"]
    cs = {}
    for v in cfg.values():
        for c in v["cities"]:
            cs[c["name"]] = (c["lat"], c["lon"])
    t1 = time.time()
    r, _ = http_get("https://archive-api.open-meteo.com/v1/archive", {
        "latitude": ",".join(str(v[0]) for v in cs.values()), "longitude": ",".join(str(v[1]) for v in cs.values()),
        "start_date": start.date().isoformat(), "end_date": end.date().isoformat(),
        "hourly": "temperature_2m", "timezone": "GMT"}, logfile=LOGF)
    write_json_gz(RAW / "daily" / st["D"] / "weather.json.gz", r.json() if r.status_code == 200 else {"status": r.status_code, "text": r.text[:500]})
    t_weather = time.time() - t1
    t2 = time.time()
    py = sys.executable
    subprocess.run([py, "step1b_build.py"], check=True)
    t_build = time.time() - t2
    t3 = time.time()
    subprocess.run([py, "analyze_history.py"], check=True)
    t_an = time.time() - t3
    res = {"window": [s, e], "rows": rows, "requests": STATS.count, "weather_status": r.status_code,
           "t_eia_s": round(t_eia, 1), "t_weather_s": round(t_weather, 1), "t_build_s": round(t_build, 1),
           "t_analyze_s": round(t_an, 1), "total_s": round(time.time() - t0, 1)}
    save_json("daily_update_timing.json", res)
    log(json.dumps(res), LOGF)


if __name__ == "__main__":
    sys.exit(main())

