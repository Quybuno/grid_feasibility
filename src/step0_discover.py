"""BƯỚC 0 — khám phá EIA API v2 nhánh electricity/rto: route, facet, data column, frequency, period."""
from __future__ import annotations

import json
import sys

from common import EIA_BASE, http_get, load_yaml, log, run_state, save_json, write_json_gz, RAW, STATS


def meta(route: str):
    r, el = http_get(f"{EIA_BASE}/{route}", eia=True)
    log(f"meta {route} -> {r.status_code} in {el:.2f}s")
    r.raise_for_status()
    return r.json()


def facet_values(route: str, facet: str):
    r, el = http_get(f"{EIA_BASE}/{route}/facet/{facet}", eia=True)
    r.raise_for_status()
    return r.json().get("response", {}).get("facets", [])


def main():
    st = run_state()
    regions = load_yaml("regions.yml")["regions"]
    root = meta("electricity/rto")
    write_json_gz(RAW / "meta" / "electricity_rto.json.gz", root)
    routes = root["response"].get("routes", [])
    table = []
    detail = {}
    for rt in routes:
        rid = rt["id"]
        m = meta(f"electricity/rto/{rid}")
        write_json_gz(RAW / "meta" / f"{rid}.json.gz", m)
        resp = m["response"]
        facets = {}
        for fc in resp.get("facets", []):
            try:
                vals = facet_values(f"electricity/rto/{rid}", fc["id"])
            except Exception as e:  # noqa
                vals = [{"error": str(e)[:200]}]
            facets[fc["id"]] = vals
        write_json_gz(RAW / "meta" / f"{rid}_facets.json.gz", facets)
        row = {
            "route": f"electricity/rto/{rid}",
            "name": resp.get("name"),
            "frequency": [f["id"] for f in resp.get("frequency", [])],
            "facets": {k: len(v) for k, v in facets.items()},
            "data_columns": list((resp.get("data") or {}).keys()),
            "startPeriod": resp.get("startPeriod"),
            "endPeriod": resp.get("endPeriod"),
            "defaultFrequency": resp.get("defaultFrequency"),
        }
        table.append(row)
        detail[rid] = {"facets": facets, "frequency": resp.get("frequency"), "data": resp.get("data")}

    # region-code existence check against respondent facet of region-data
    resp_codes = {}
    for rid in ("region-data", "fuel-type-data"):
        f = detail.get(rid, {}).get("facets", {}).get("respondent", [])
        resp_codes[rid] = {x.get("id"): x.get("name") for x in f if isinstance(x, dict)}
    ic = detail.get("interchange-data", {}).get("facets", {})
    resp_codes["interchange-data"] = {x.get("id"): x.get("name") for x in ic.get("fromba", []) if isinstance(x, dict)}
    existence = {code: {rid: (code in codes) for rid, codes in resp_codes.items()} for code in regions}

    agg13 = ["CAL", "CAR", "CENT", "FLA", "MIDA", "MIDW", "NE", "NY", "NW", "SE", "SW", "TEN", "TEX"]
    agg13_exist = {c: c in resp_codes.get("region-data", {}) for c in agg13}

    # row limit probe: request length=10000 JSON and see what is returned / warnings
    r, el = http_get(f"{EIA_BASE}/electricity/rto/region-data/data/", {
        "frequency": "hourly", "data[0]": "value", "facets[respondent][]": "PJM",
        "start": "2024-01-01T00", "end": "2024-03-31T23", "length": 10000}, eia=True)
    j = r.json()
    probe = {"status": r.status_code, "rows_returned": len(j.get("response", {}).get("data", [])),
             "total": j.get("response", {}).get("total"), "warnings": j.get("response", {}).get("warnings"),
             "headers": {k: v for k, v in r.headers.items() if "limit" in k.lower() or "retry" in k.lower()}}
    sample = j.get("response", {}).get("data", [])[:3]

    out = {"run": st, "routes": table, "region_existence": existence, "agg13_exist": agg13_exist,
           "row_limit_probe": probe, "sample_rows": sample,
           "fueltypes": detail.get("fuel-type-data", {}).get("facets", {}).get("fueltype"),
           "region_types": detail.get("region-data", {}).get("facets", {}).get("type"),
           "requests": STATS.count}
    save_json("step0_api.json", out)
    print(json.dumps({k: out[k] for k in ("routes", "region_existence", "agg13_exist", "row_limit_probe",
                                          "sample_rows", "fueltypes", "region_types")}, indent=1)[:12000])


if __name__ == "__main__":
    sys.exit(main())

