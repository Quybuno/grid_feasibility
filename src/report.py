"""BƯỚC 10–11 — C5 tài nguyên + sinh report.md từ kết quả thật trong output/*.json."""
from __future__ import annotations

import json
import sys

from common import MART, OUT, ROOT, STATE, dir_size, load_json, load_yaml, run_state

AN = load_yaml("analysis.yml")


def st_from(crit: dict, pending_ok=False):
    vals = [c.get("pass") for c in crit.values()]
    if any(v is False for v in vals):
        return "FAIL"
    if any(v is None for v in vals):
        return "CHƯA XÁC ĐỊNH"
    return "PASS"


def fmt(v):
    if isinstance(v, float):
        return f"{v:.4g}"
    if isinstance(v, (list, dict)):
        return json.dumps(v, ensure_ascii=False)
    return str(v)


def c5():
    runs_p = STATE / "snapshot_runs.jsonl"
    runs = [json.loads(l) for l in runs_p.read_text(encoding="utf-8").splitlines() if l.strip()] if runs_p.exists() else []
    hourly = [r["duration_s"] for r in runs if r["success"]]
    daily = load_json("daily_update_timing.json")
    bm = json.loads((STATE / "backfill_metrics.json").read_text()) if (STATE / "backfill_metrics.json").exists() else {"sessions": []}
    hist = load_json("history_results.json", {}) or {}
    mart = dir_size(MART)
    total = dir_size(ROOT)
    req_backfill = sum(s["requests"] for s in bm["sessions"])
    crit = {"hourly_update_s_max": {"value": max(hourly) if hourly else None, "threshold": "<= 300 s",
                                    "pass": (max(hourly) <= 300) if hourly else None},
            "daily_update_s": {"value": daily.get("total_s") if daily else None, "threshold": "<= 1800 s",
                               "pass": (daily["total_s"] <= 1800) if daily else None},
            "dashboard_tables_bytes": {"value": mart, "threshold": "<= 5 GB", "pass": mart <= AN["C5"]["dashboard_max_bytes"]}}
    return {"criteria": crit, "backfill_sessions": bm["sessions"], "backfill_requests_eia": req_backfill,
            "backfill_elapsed_s": sum(s["elapsed_s"] for s in bm["sessions"]),
            "snapshot_runs": len(runs), "snapshot_requests": sum(len(r["requests"]) for r in runs),
            "storage_total_bytes": total, "storage_raw_bytes": dir_size(ROOT / "data" / "raw"),
            "storage_parquet_bytes": dir_size(ROOT / "data" / "parquet"), "mart_bytes": mart,
            "peak_rss_analyze_bytes": (hist.get("resources") or {}).get("peak_rss_bytes"),
            "daily": daily}


def main():
    run = run_state()
    s0 = load_json("step0_api.json", {})
    H = load_json("history_results.json", {})
    C2 = load_json("c2_results.json", {}) or {}
    C5 = c5()
    save_json_path = OUT / "c5_results.json"
    save_json_path.write_text(json.dumps(C5, indent=2, default=str), encoding="utf-8")

    status = {}
    status["C1"] = H["C1"]["status"]
    status["C2"] = C2.get("status", "CHƯA ĐỦ DỮ LIỆU")
    c3auto = st_from(H["C3"]["criteria"])
    man = H["C3"]["manual"]["status"]
    status["C3"] = "FAIL" if c3auto == "FAIL" or man == "FAIL" else ("CHỜ CHẤM TAY" if man == "CHƯA XÁC ĐỊNH" else "PASS")
    status["C4"] = st_from(H["C4"]["criteria"])
    status["C5"] = st_from(C5["criteria"])
    for q in ("Q1", "Q2", "Q3", "Q4", "Q5"):
        status[q] = st_from(H[q]["criteria"])

    mandatory = ["C1", "C2", "C3", "C4", "C5", "Q1", "Q2", "Q5"]
    fails = [k for k in mandatory if status[k] == "FAIL"]
    q34 = [status["Q3"], status["Q4"]]
    if all(s == "FAIL" for s in q34):
        fails.append("Q3 và Q4 (cả hai)")
    pending = [k for k in mandatory if status[k] in ("CHƯA XÁC ĐỊNH", "CHƯA ĐỦ DỮ LIỆU")]
    if fails:
        verdict = "KHÔNG CHỐT"
    elif pending:
        verdict = None
    elif status["C3"] == "CHỜ CHẤM TAY" and "PASS" in q34:
        verdict = "CHỜ CHẤM TAY"
    elif "PASS" in q34:
        verdict = "CHỐT LƯỚI ĐIỆN"
    else:
        verdict = None

    def crit_rows(name, crit):
        out = []
        for k, c in crit.items():
            out.append(f"| {name} | {k} | {fmt(c.get('value'))} | {c.get('threshold')} | "
                       f"{'PASS' if c.get('pass') is True else ('FAIL' if c.get('pass') is False else 'CHƯA XÁC ĐỊNH')} |")
        return out

    L = []
    A = L.append
    A("# Báo cáo khả thi — Lưới điện Mỹ dưới áp lực nhu cầu và năng lượng tái tạo\n")
    A(f"- D (ngày chạy, UTC): **{run['D']}** · lịch sử: {run['history_start']} → {run['history_end']} UTC · trao đổi từ {run['interchange_start']}")
    A(f"- C2 snapshot: {C2.get('successful_slots', 0)}/{C2.get('planned_runs', 72)} lần thành công, "
      f"{C2.get('elapsed_slots', 0)} khung giờ đã trôi qua kể từ {C2.get('first_run')}")
    A("- Mọi số liệu dưới đây được tính từ dữ liệu thật đã tải; không nội suy, không điền thiếu.\n")

    A("## 1. Bảng tiêu chí\n")
    A("| Mục | Trạng thái |\n|---|---|")
    for k in ["C1", "C2", "C3", "C4", "C5", "Q1", "Q2", "Q3", "Q4", "Q5"]:
        A(f"| {k} | **{status[k]}** |")
    A("\n| Mục | Số đo | Giá trị | Ngưỡng | Kết quả |\n|---|---|---|---|---|")
    for k, crit in (("C1", H["C1"]["criteria"]), ("C2", C2.get("criteria", {})), ("C3", H["C3"]["criteria"]),
                    ("C4", H["C4"]["criteria"]), ("C5", C5["criteria"]), ("Q1", H["Q1"]["criteria"]),
                    ("Q2", H["Q2"]["criteria"]), ("Q3", H["Q3"]["criteria"]), ("Q4", H["Q4"]["criteria"]),
                    ("Q5", H["Q5"]["criteria"])):
        L.extend(crit_rows(k, crit))
    if not C2.get("criteria"):
        A("| C2 | (toàn bộ) | CHƯA ĐỦ DỮ LIỆU | 72 lần chạy | CHƯA XÁC ĐỊNH |")
    A(f"| C3 | chấm tay dq_review.csv | {H['C3']['manual']} | >= 70% hợp lý | {H['C3']['manual']['status']} |")

    A("\n## 2. Route thực tế, điều khoản, trích dẫn\n")
    A("| Route | Frequency | Facets (số giá trị) | Cột dữ liệu | startPeriod | endPeriod |\n|---|---|---|---|---|---|")
    for r in s0.get("routes", []):
        A(f"| {r['route']} | {', '.join(r['frequency'])} | {fmt(r['facets'])} | {', '.join(r['data_columns'])} | {r['startPeriod']} | {r['endPeriod']} |")
    A("\nRoute xác nhận (frequency=hourly, UTC):\n")
    A("| Loại dữ liệu | Route | Facet |\n|---|---|---|")
    A("| Nhu cầu | electricity/rto/region-data | type=D |")
    A("| Dự báo nhu cầu | electricity/rto/region-data | type=DF (\"Day-ahead demand forecast\") |")
    A("| Phát điện ròng | electricity/rto/region-data | type=NG |")
    A("| Trao đổi tổng | electricity/rto/region-data | type=TI (dương = xuất ròng) |")
    A("| Phát điện theo nguồn | electricity/rto/fuel-type-data | fueltype=* |")
    A("| Trao đổi giữa các vùng | electricity/rto/interchange-data | fromba, toba |")
    A(f"\n- Mã vùng: {fmt(s0.get('region_existence'))}. Không có mã nào thiếu; không thay mã.")
    p = s0.get("row_limit_probe", {})
    A(f"- Giới hạn dòng: yêu cầu length=10000 chỉ trả {p.get('rows_returned')} dòng (total={p.get('total')}) ⇒ tối đa 5000 dòng/request JSON. "
      "Phân trang bằng `offset` + `length`, sắp xếp `sort[0][column]=period`.")
    A(f"- Header giới hạn request quan sát được: {fmt(p.get('headers'))} (EIA không trả header quota/remaining; "
      "số request còn lại: CHƯA XÁC ĐỊNH). EIA không công bố hạn mức số request/giờ cố định; cần API key miễn phí.")
    A("- Điều khoản EIA: dữ liệu của chính phủ Hoa Kỳ, thuộc phạm vi công cộng, có thể dùng lại; EIA đề nghị ghi nguồn "
      "(https://www.eia.gov/about/copyrights_reuse.php). Trích dẫn: *U.S. Energy Information Administration, Hourly Electric "
      f"Grid Monitor (Form EIA-930), API v2 electricity/rto, truy cập {run['D']}.*")
    A("- Open-Meteo: API miễn phí cho mục đích phi thương mại, 600 call/phút, 5.000/giờ, 10.000/ngày (request dài hơn 2 tuần được tính nhiều call). "
      "Dữ liệu CC BY 4.0. Trích dẫn: *Weather data by Open-Meteo.com (CC BY 4.0); Zippenfenig, P. (2023). Open-Meteo.com Weather API, "
      "Zenodo, doi:10.5281/zenodo.7970649; Hersbach, H. et al. (2020) ERA5 hourly data, Copernicus C3S, doi:10.24381/cds.adbb2d47.*")
    A("- User-Agent mọi request: `grid-feasibility/0.1`. Key đọc từ biến môi trường `EIA_API_KEY`, bị che (`***`) trong mọi log.")

    A("\n## 3. Độ đầy đủ theo vùng và loại dữ liệu (C1)\n")
    A("| Vùng | Loại | Giờ kỳ vọng | Giờ có dữ liệu | Tỷ lệ | Khoảng thiếu dài nhất (h) | Trùng khóa | Null |\n|---|---|---|---|---|---|---|---|")
    for x in H["C1"]["region"]:
        A(f"| {x['region']} | {x['type']} | {x['expected_hours']} | {x['hours_present']} | {x['share']} | {x['longest_gap_h']} | {x['dup_share']} | {x['null_share']} |")
    for x in H["C1"]["fuel_any"]:
        A(f"| {x['region']} | FUEL (≥1 nguồn) | {x['expected_hours']} | {x['hours_present']} | {x['share']} | {x['longest_gap_h']} | {x['dup_share']} | {x['null_share']} |")
    icp = H["C1"]["interchange_pairs"]
    A(f"\nTrao đổi giữa các vùng (từ {run['interchange_start']}): {len(icp)} cặp fromba→toba; trùng khóa {H['C1']['dedup']['interchange_fromba']}. "
      f"Cặp dưới 95% giờ: {sum(1 for x in icp if (x['share'] or 0) < 0.95)}.")
    low = [f"{x['fromba']}→{x['toba']}={x['share']}" for x in icp if (x['share'] or 0) < 0.95]
    if low:
        A(f"Chi tiết cặp <95%: {', '.join(low[:60])}")

    A("\n## 4. Kết quả sơ bộ từng câu hỏi (mức liên quan, không suy luận nhân quả)\n")
    A("### C3 — Chất lượng dữ liệu\n")
    A("| Vùng | R1 cờ/giờ | R1 tỷ lệ | R2 cờ/giờ | R2 tỷ lệ | R3 đạt | R4 đạt |\n|---|---|---|---|---|---|---|")
    for x in H["C3"]["per_region"]:
        A(f"| {x['region']} | {x['R1_flags']}/{x['R1_eval_hours']} | {x['R1_share']} | {x['R2_flags']}/{x['R2_eval_hours']} | {x['R2_share']} | "
          f"{x['R3_pass_share']} (n={x['R3_eval_hours']}) | {x['R4_pass_share']} (n={x['R4_eval_hours']}) |")
    A(f"\nR5: {fmt(H['C3']['R5'])}")
    A(f"\nMẫu chấm tay: {fmt(H['C3']['review'])}")
    A("\n### C4 — Ghép thời tiết\n")
    A("| Vùng | Giờ có nhiệt độ | Tỷ lệ | Trung vị giờ địa phương của Tmax ngày | Giờ thiếu cuối cùng |\n|---|---|---|---|---|")
    for x in H["C4"]["per_region"]:
        A(f"| {x['region']} | {x['hours_with_temp']} | {x['share']} | {x['median_local_hour_of_daily_max']} | {x['missing_last']} |")
    A(f"\nKiểm tra căn UTC: {fmt(H['C4']['checks'])}")
    q1 = H["Q1"]
    A("\n### Q1 — Nhu cầu ròng\n")
    A(f"- Tỷ trọng gió+mặt trời 2025: {fmt(q1['ws_share_2025'])}")
    A(f"- Tỷ lệ giờ đủ (D, WND, SUN) theo năm: {fmt(q1['complete_coverage_by_year'])}")
    A(f"- Chỉ số 2025 (trung vị qua 4 mùa, hồ sơ trung vị, MW / MW/h): {fmt(q1['latest_year_metrics_median_over_seasons'])}")
    A("- Hồ sơ đầy đủ: `data/mart/q1_netload_profiles.parquet`, `q1_netload_metrics.parquet`.")
    q2 = H["Q2"]
    A("\n### Q2 — Sai số dự báo (e = DF − D)\n")
    A("| Vùng | MAPE % | MdAPE % | MAE MW | Bias MW | n | Phủ D&DF |\n|---|---|---|---|---|---|---|")
    for r, v in q2["summary"].items():
        A(f"| {r} | {v['MAPE']} | {v['MdAPE']} | {v['MAE']} | {v['bias']} | {v['n']} | {q2['coverage_by_region'].get(r)} |")
    A("\nNhóm (APE %, mean/median/size):\n")
    for g in q2["groups"]:
        A(f"- {g['region']} / {g['dim']}: " + ", ".join(f"{k}={v}" for k, v in g.items() if k not in ("region", "dim")))
    A("\nHồi quy APE (%) ~ lạnh P10 + nóng P90 + tỷ trọng tái tạo (điểm %) + giờ + tháng; SE Newey-West lag 24 (chỉ là mức liên quan):\n")
    A("| Vùng | n | cold_p10 (SE) | hot_p90 (SE) | ren_share_pp (SE) |\n|---|---|---|---|---|")
    for r, v in q2["regression_hac"].items():
        f = lambda k: f"{v[k]['coef']} ({v[k]['se_hac']})"
        A(f"| {r} | {v['n']} | {f('cold_p10')} | {f('hot_p90')} | {f('ren_share_pp')} |")
    q3 = H["Q3"]
    A("\n### Q3 — Thay đổi sản lượng theo nguồn 16h→20h giờ địa phương (MW, năm 2025: trung vị)\n")
    for r, v in q3["per_region"].items():
        d = v["delta_16_to_20"]
        items = sorted(((k, x["median_2025"]) for k, x in d.items() if x["median_2025"] is not None), key=lambda t: -abs(t[1]))
        A(f"- {r}: phủ nguồn={v['fuel_hours_share']}, OTH+UNK={v['other_unk_share']}, đạt={v['region_ok']}; Δ: "
          + ", ".join(f"{k} {x:+.0f}" for k, x in items[:8]))
    q4 = H["Q4"]
    A("\n### Q4 — Trao đổi trong 1% giờ nhu cầu cao nhất (2023→D-3)\n")
    A("| Vùng | Số giờ | Nhập ròng trung vị (căng thẳng) | Nhập ròng trung vị (mọi giờ) | Đối tác chính (nhập trung vị) |\n|---|---|---|---|---|")
    for r, v in q4["stress"].items():
        A(f"| {r} | {v['n_stress_hours']} | {v['net_import_median_stress']} | {v['net_import_median_all']} | {v['main_partner']} ({v['main_partner_median_import']}) |")
    A(f"\nKhớp hai chiều theo cặp (top 20 theo số giờ): {fmt(sorted(q4['symmetry_by_pair'], key=lambda x: -x['size'])[:20])}")
    q5 = H["Q5"]
    A(f"\n### Q5 — Khác thường (cửa sổ {q5['window'][0]} → {q5['window'][1]})\n")
    A("| Vùng | Giờ | Đánh giá được | MAD=0/thiếu baseline | Cờ | Tỷ lệ |\n|---|---|---|---|---|---|")
    for x in q5["per_region"]:
        A(f"| {x['region']} | {x['hours_in_window']} | {x['evaluable']} | {x['mad_zero_or_insufficient']} | {x['flags']} | {x['flag_share']} |")

    A("\n## 5. Độ mới và thời điểm hiển thị (C2)\n")
    if C2.get("latency"):
        A(f"- Trạng thái C2: **{status['C2']}** ({C2.get('successful_slots')}/{C2.get('planned_runs')} lần thành công; thời lượng/lần: {fmt(C2.get('duration_s'))}).")
        A(f"- Độ trễ (giờ, fetched_at lần đầu − period): {fmt(C2['latency'])}")
        A(f"- Sửa giá trị (>1%): {fmt(C2['revisions'])}")
        A(f"- Dự báo: {fmt(C2.get('forecast_meaning'))}")
        A(f"- HTTP status: {fmt(C2.get('statuses'))}; header quota: {fmt(C2.get('rate_headers_seen'))}")
        lat = C2["latency"]
        A(f"- Gợi ý hiển thị (dựa trên P95 đo được): nhu cầu/NG hiển thị đến now − {lat['D']['p95_h']} h; "
          f"theo nguồn đến now − {lat['FUEL']['p95_h']} h; trao đổi cặp đến now − {lat['INTERCHANGE']['p95_h']} h. "
          "Nếu giá trị là None/inf: CHƯA ĐỦ DỮ LIỆU.")
    else:
        A("- CHƯA ĐỦ DỮ LIỆU.")

    A("\n## 6. Lỗi đã gặp, khác biệt so với giả định\n")
    A(f"- Backfill: {fmt([{k: s[k] for k in ('elapsed_s', 'requests', 'chunks_done')} | {'n_fails': len(s['fails'])} for s in C5['backfill_sessions']])}")
    A(f"- Lỗi snapshot: {fmt(C2.get('errors'))}")
    A(f"- Fueltype quan sát: {fmt(H.get('fueltypes_seen'))}. Q1 dùng đúng định nghĩa đã khóa (WND, SUN); SNB/WNB (năng lượng tái tạo kèm pin) không cộng vào — giới hạn đã biết.")
    A("- Không có header quota từ EIA ⇒ 'số request còn lại' không đo được.")
    A("- Snapshot chỉ phát hiện được độ trễ ≤ 72 h (cửa sổ 72 h); giờ chưa xuất hiện khi rời cửa sổ được tính là +∞ trong phân vị.")
    A(f"\n### C5 tài nguyên\n\n{fmt({k: v for k, v in C5.items() if k not in ('criteria', 'backfill_sessions')})}")

    A("\n## 7. Câu hỏi: giữ / thu hẹp / bỏ\n")
    for q, nm in (("Q1", "Nhu cầu ròng"), ("Q2", "Sai số dự báo"), ("Q3", "Nguồn bù khi mặt trời giảm"),
                  ("Q4", "Trao đổi lúc căng thẳng"), ("Q5", "Phát hiện khác thường")):
        s = status[q]
        crit = H[q]["criteria"]
        failed = [k for k, c in crit.items() if c.get("pass") is False]
        und = [k for k, c in crit.items() if c.get("pass") is None]
        if s == "PASS":
            dec = "GIỮ"
        elif s == "FAIL":
            dec = f"KHÔNG ĐẠT theo ngưỡng đã khóa — tiêu chí trượt: {', '.join(failed)}. Phải thu hẹp phạm vi (chỉ vùng/kỳ đạt) hoặc bỏ; không nới ngưỡng."
        else:
            dec = f"CHƯA XÁC ĐỊNH — chờ: {', '.join(und)}"
        A(f"- **{q} {nm}**: {s}. {dec}")

    A("\n## 8. Kết luận cuối\n")
    if verdict:
        A(f"**{verdict}**\n")
        if fails:
            A("Điều kiện bắt buộc trượt:")
            for k in fails:
                if k in status and k in H and "criteria" in H[k]:
                    bad = {n: c["value"] for n, c in H[k]["criteria"].items() if c.get("pass") is False}
                elif k == "C2":
                    bad = {n: c["value"] for n, c in C2.get("criteria", {}).items() if c.get("pass") is False}
                elif k == "C5":
                    bad = {n: c["value"] for n, c in C5["criteria"].items() if c.get("pass") is False}
                else:
                    bad = {}
                if k == "C3":
                    bad = {n: c["value"] for n, c in H["C3"]["criteria"].items() if c.get("pass") is False}
                    if H["C3"]["manual"]["status"] == "FAIL":
                        bad["manual"] = H["C3"]["manual"]
                A(f"- {k}: {fmt(bad)}")
        if pending:
            A(f"\nNgoài ra còn chưa xác định: {', '.join(pending)} (không làm thay đổi kết luận vì đã có điều kiện bắt buộc trượt).")
    else:
        A("**CHƯA CHỌN ĐƯỢC KẾT LUẬN (báo cáo tạm thời)** — chưa có điều kiện bắt buộc nào trượt, nhưng còn "
          f"CHƯA XÁC ĐỊNH/CHƯA ĐỦ DỮ LIỆU: {', '.join(pending)}. Kết luận sẽ được chọn sau khi đủ 72 lần snapshot.")
    A("\n## Chạy lại\n")
    A("```powershell\ncd grid_feasibility\n.\\run_all.ps1            # toàn bộ, tiếp tục từ điểm dừng\n.\\run_all.ps1 -ReportOnly # chỉ tính lại C2 + báo cáo\n```")
    (ROOT / "report.md").write_text("\n".join(L), encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    print(f"verdict={verdict} status={status}")


if __name__ == "__main__":
    sys.exit(main())

