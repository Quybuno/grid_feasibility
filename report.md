# Báo cáo khả thi — Lưới điện Mỹ dưới áp lực nhu cầu và năng lượng tái tạo

- D (ngày chạy, UTC): **2026-11-03** · lịch sử: 2019-01-01T00 → 2026-10-31T23 UTC · trao đổi từ 2023-01-01T00
- C2 snapshot: 2/72 lần thành công, 2 khung giờ đã trôi qua kể từ 2026-11-03 16:08:08+00:00
- Mọi số liệu dưới đây được tính từ dữ liệu thật đã tải; không nội suy, không điền thiếu.

## 1. Bảng tiêu chí

| Mục | Trạng thái |
|---|---|
| C1 | **PASS** |
| C2 | **CHƯA ĐỦ DỮ LIỆU** |
| C3 | **FAIL** |
| C4 | **PASS** |
| C5 | **PASS** |
| Q1 | **PASS** |
| Q2 | **CHƯA XÁC ĐỊNH** |
| Q3 | **PASS** |
| Q4 | **FAIL** |
| Q5 | **FAIL** |

| Mục | Số đo | Giá trị | Ngưỡng | Kết quả |
|---|---|---|---|---|
| C1 | core_min_share | 0.9906 | >= 0.98 mọi vùng | PASS |
| C1 | fuel_regions_ge95 | 8 | >= 5 vùng | PASS |
| C1 | demand_max_gap | 25 | <= 72h | PASS |
| C1 | max_dup_share | 0 | <= 0.001 | PASS |
| C2 | success_share | 0.0278 | >= 0.95 | FAIL |
| C2 | demand_latency_median | None | <= 3h | FAIL |
| C2 | demand_latency_p95 | None | <= 12h | FAIL |
| C2 | fuel_latency_p95 | None | <= 48h | FAIL |
| C2 | revised_share | 0.0001 | <= 0.05 | PASS |
| C3 | R1_max_share | 0.0002 | <= 0.02 mọi vùng | PASS |
| C3 | R2_max_share | 0.0002 | <= 0.02 mọi vùng | PASS |
| C3 | R3_min_pass | 0.9489 | >= 0.90 mọi vùng | PASS |
| C3 | R4_min_pass | 0.857 | >= 0.90 mọi vùng | FAIL |
| C4 | min_share | 1 | >= 0.99 mọi vùng | PASS |
| C4 | utc_alignment | True | không lệch | PASS |
| C5 | hourly_update_s_max | 9.53 | <= 300 s | PASS |
| C5 | daily_update_s | 626 | <= 1800 s | PASS |
| C5 | dashboard_tables_bytes | 29664751 | <= 5 GB | PASS |
| Q1 | regions_ws_share_ge5pct_2025 | 8 | >= 5 | PASS |
| Q1 | full_years | 7 | >= 3 | PASS |
| Q1 | mean_median_consistency | 0.8108 | >= 0.80 | PASS |
| Q2 | forecast_meaning_C2 | CHƯA XÁC ĐỊNH | xác nhận | CHƯA XÁC ĐỊNH |
| Q2 | pooled_coverage | 0.9972 | >= 0.98 | PASS |
| Q2 | regions_ge98 | 8 | >= 5 | PASS |
| Q2 | mean_median_consistency | 0.9062 | >= 0.80 | PASS |
| Q3 | regions_ok | 8 | >= 5 vùng (phủ>=95% và OTH+UNK<=10%) | PASS |
| Q4 | pair_coverage | 0.9109 | >= 0.95 | FAIL |
| Q4 | symmetry_within_5pct | 0.6229 | >= 0.90 | FAIL |
| Q5 | max_flag_share | 0.244 | <= 0.05 mọi vùng | FAIL |
| Q5 | no_future_data | 0 | 0 vi phạm | PASS |
| C3 | chấm tay dq_review.csv | {'status': 'CHƯA XÁC ĐỊNH', 'reason': 'đã chấm 0/40'} | >= 70% hợp lý | CHƯA XÁC ĐỊNH |

## 2. Route thực tế, điều khoản, trích dẫn

| Route | Frequency | Facets (số giá trị) | Cột dữ liệu | startPeriod | endPeriod |
|---|---|---|---|---|---|
| electricity/rto/region-data | hourly, local-hourly | {"respondent": 83, "type": 4} | value | 2019-01-01T00 | 2026-11-04T08 |
| electricity/rto/fuel-type-data | hourly, local-hourly | {"respondent": 83, "fueltype": 20} | value | 2019-01-01T00 | 2026-11-03T07 |
| electricity/rto/region-sub-ba-data | hourly, local-hourly | {"subba": 90, "parent": 10} | value | 2019-01-01T00 | 2026-11-03T08 |
| electricity/rto/interchange-data | hourly, local-hourly | {"fromba": 83, "toba": 92} | value | 2019-01-01T00 | 2026-11-02T08 |
| electricity/rto/daily-region-data | daily | {"respondent": 83, "type": 4, "timezone": 5} | value | 2019-01-01 | 2026-11-03 |
| electricity/rto/daily-region-sub-ba-data | daily | {"subba": 90, "parent": 10, "timezone": 5} | value | 2019-01-01 | 2026-11-02 |
| electricity/rto/daily-fuel-type-data | daily | {"respondent": 83, "fueltype": 20, "timezone": 5} | value | 2019-01-01 | 2026-11-02 |
| electricity/rto/daily-interchange-data | daily | {"fromba": 83, "toba": 93, "timezone": 5} | value | 2019-01-01 | 2026-11-01 |

Route xác nhận (frequency=hourly, UTC):

| Loại dữ liệu | Route | Facet |
|---|---|---|
| Nhu cầu | electricity/rto/region-data | type=D |
| Dự báo nhu cầu | electricity/rto/region-data | type=DF ("Day-ahead demand forecast") |
| Phát điện ròng | electricity/rto/region-data | type=NG |
| Trao đổi tổng | electricity/rto/region-data | type=TI (dương = xuất ròng) |
| Phát điện theo nguồn | electricity/rto/fuel-type-data | fueltype=* |
| Trao đổi giữa các vùng | electricity/rto/interchange-data | fromba, toba |

- Mã vùng: {"CISO": {"region-data": true, "fuel-type-data": true, "interchange-data": true}, "ERCO": {"region-data": true, "fuel-type-data": true, "interchange-data": true}, "PJM": {"region-data": true, "fuel-type-data": true, "interchange-data": true}, "MISO": {"region-data": true, "fuel-type-data": true, "interchange-data": true}, "NYIS": {"region-data": true, "fuel-type-data": true, "interchange-data": true}, "ISNE": {"region-data": true, "fuel-type-data": true, "interchange-data": true}, "SWPP": {"region-data": true, "fuel-type-data": true, "interchange-data": true}, "US48": {"region-data": true, "fuel-type-data": true, "interchange-data": true}}. Không có mã nào thiếu; không thay mã.
- Giới hạn dòng: yêu cầu length=10000 chỉ trả 5000 dòng (total=8691) ⇒ tối đa 5000 dòng/request JSON. Phân trang bằng `offset` + `length`, sắp xếp `sort[0][column]=period`.
- Header giới hạn request quan sát được: {} (EIA không trả header quota/remaining; số request còn lại: CHƯA XÁC ĐỊNH). EIA không công bố hạn mức số request/giờ cố định; cần API key miễn phí.
- Điều khoản EIA: dữ liệu của chính phủ Hoa Kỳ, thuộc phạm vi công cộng, có thể dùng lại; EIA đề nghị ghi nguồn (https://www.eia.gov/about/copyrights_reuse.php). Trích dẫn: *U.S. Energy Information Administration, Hourly Electric Grid Monitor (Form EIA-930), API v2 electricity/rto, truy cập 2026-11-03.*
- Open-Meteo: API miễn phí cho mục đích phi thương mại, 600 call/phút, 5.000/giờ, 10.000/ngày (request dài hơn 2 tuần được tính nhiều call). Dữ liệu CC BY 4.0. Trích dẫn: *Weather data by Open-Meteo.com (CC BY 4.0); Zippenfenig, P. (2023). Open-Meteo.com Weather API, Zenodo, doi:10.5281/zenodo.7970649; Hersbach, H. et al. (2020) ERA5 hourly data, Copernicus C3S, doi:10.24381/cds.adbb2d47.*
- User-Agent mọi request: `grid-feasibility/0.1`. Key đọc từ biến môi trường `EIA_API_KEY`, bị che (`***`) trong mọi log.

## 3. Độ đầy đủ theo vùng và loại dữ liệu (C1)

| Vùng | Loại | Giờ kỳ vọng | Giờ có dữ liệu | Tỷ lệ | Khoảng thiếu dài nhất (h) | Trùng khóa | Null |
|---|---|---|---|---|---|---|---|
| CISO | D | 68664 | 68640 | 0.9997 | 1 | 0.0 | 0.0003 |
| CISO | DF | 68664 | 68544 | 0.9983 | 49 | 0.0 | 0.0 |
| CISO | NG | 68664 | 68620 | 0.9994 | 24 | 0.0 | 0.0003 |
| CISO | TI | 68664 | 68142 | 0.9924 | 72 | 0.0 | 0.0 |
| ERCO | D | 68664 | 68663 | 1.0 | 1 | 0.0 | 0.0 |
| ERCO | DF | 68664 | 68520 | 0.9979 | 48 | 0.0 | 0.0 |
| ERCO | NG | 68664 | 68640 | 0.9997 | 24 | 0.0 | 0.0 |
| ERCO | TI | 68664 | 68509 | 0.9977 | 48 | 0.0 | 0.0 |
| PJM | D | 68664 | 68547 | 0.9983 | 25 | 0.0 | 0.0017 |
| PJM | DF | 68664 | 68426 | 0.9965 | 25 | 0.0 | 0.0 |
| PJM | NG | 68664 | 68544 | 0.9983 | 25 | 0.0 | 0.0017 |
| PJM | TI | 68664 | 68475 | 0.9972 | 25 | 0.0 | 0.0 |
| MISO | D | 68664 | 68629 | 0.9995 | 24 | 0.0 | 0.0005 |
| MISO | DF | 68664 | 68496 | 0.9976 | 24 | 0.0 | 0.0 |
| MISO | NG | 68664 | 68629 | 0.9995 | 24 | 0.0 | 0.0005 |
| MISO | TI | 68664 | 68539 | 0.9982 | 24 | 0.0 | 0.0 |
| NYIS | D | 68664 | 68662 | 1.0 | 2 | 0.0 | 0.0 |
| NYIS | DF | 68664 | 68568 | 0.9986 | 24 | 0.0 | 0.0 |
| NYIS | NG | 68664 | 68664 | 1.0 | 0 | 0.0 | 0.0 |
| NYIS | TI | 68664 | 68568 | 0.9986 | 24 | 0.0 | 0.0 |
| ISNE | D | 68664 | 68659 | 0.9999 | 2 | 0.0 | 0.0001 |
| ISNE | DF | 68664 | 68664 | 1.0 | 0 | 0.0 | 0.0 |
| ISNE | NG | 68664 | 68661 | 1.0 | 1 | 0.0 | 0.0 |
| ISNE | TI | 68664 | 68656 | 0.9999 | 2 | 0.0 | 0.0 |
| SWPP | D | 68664 | 68638 | 0.9996 | 24 | 0.0 | 0.0004 |
| SWPP | DF | 68664 | 68016 | 0.9906 | 384 | 0.0 | 0.0 |
| SWPP | NG | 68664 | 68639 | 0.9996 | 24 | 0.0 | 0.0004 |
| SWPP | TI | 68664 | 68472 | 0.9972 | 48 | 0.0 | 0.0014 |
| US48 | D | 68664 | 68664 | 1.0 | 0 | 0.0 | 0.0 |
| US48 | DF | 68664 | 68664 | 1.0 | 0 | 0.0 | 0.0 |
| US48 | NG | 68664 | 68664 | 1.0 | 0 | 0.0 | 0.0 |
| US48 | TI | 68664 | 68664 | 1.0 | 0 | 0.0 | 0.0 |
| CISO | FUEL (≥1 nguồn) | 68664 | 68620 | 0.9994 | 24 | 0.0 | 0.0003 |
| ERCO | FUEL (≥1 nguồn) | 68664 | 68640 | 0.9997 | 24 | 0.0 | 0.0 |
| PJM | FUEL (≥1 nguồn) | 68664 | 68544 | 0.9983 | 25 | 0.0 | 0.0017 |
| MISO | FUEL (≥1 nguồn) | 68664 | 68629 | 0.9995 | 24 | 0.0 | 0.0005 |
| NYIS | FUEL (≥1 nguồn) | 68664 | 68634 | 0.9996 | 11 | 0.0 | 0.0003 |
| ISNE | FUEL (≥1 nguồn) | 68664 | 68664 | 1.0 | 0 | 0.0 | 0.0 |
| SWPP | FUEL (≥1 nguồn) | 68664 | 68639 | 0.9996 | 24 | 0.0 | 0.0004 |
| US48 | FUEL (≥1 nguồn) | 68664 | 68664 | 1.0 | 0 | 0.0 | 0.0 |

Trao đổi giữa các vùng (từ 2023-01-01T00): 48 cặp fromba→toba; trùng khóa {'rows': 1469094, 'dup_share': 0.0, 'conflicting': 0}. Cặp dưới 95% giờ: 13.
Chi tiết cặp <95%: MISO→SIKE=0.182, PJM→CPLW=0.8876, SWPP→AECI=0.8892, SWPP→EPE=0.8892, SWPP→ERCO=0.8892, SWPP→MISO=0.8892, SWPP→PNM=0.7792, SWPP→PSCO=0.7792, SWPP→SIKE=0.0891, SWPP→SPA=0.6428, SWPP→SPC=0.6942, SWPP→WACM=0.6244, SWPP→WAUW=0.6278

## 4. Kết quả sơ bộ từng câu hỏi (mức liên quan, không suy luận nhân quả)

### C3 — Chất lượng dữ liệu

| Vùng | R1 cờ/giờ | R1 tỷ lệ | R2 cờ/giờ | R2 tỷ lệ | R3 đạt | R4 đạt |
|---|---|---|---|---|---|---|
| CISO | 0/68640 | 0.0 | 3/67968 | 0.0 | 0.9997 (n=68620) | 0.857 (n=68118) |
| ERCO | 0/68663 | 0.0 | 0/67991 | 0.0 | 0.9992 (n=68640) | 1.0 (n=68508) |
| PJM | 0/68547 | 0.0 | 4/67875 | 0.0001 | 0.9489 (n=68544) | 0.9889 (n=68474) |
| MISO | 0/68629 | 0.0 | 0/67957 | 0.0 | 1.0 (n=68629) | 1.0 (n=68529) |
| NYIS | 12/68662 | 0.0002 | 12/67990 | 0.0002 | 0.9997 (n=68634) | 1.0 (n=68554) |
| ISNE | 0/68659 | 0.0 | 0/67987 | 0.0 | 0.9995 (n=68661) | 1.0 (n=68654) |
| SWPP | 0/68638 | 0.0 | 1/67966 | 0.0 | 0.9968 (n=68639) | 0.9951 (n=68470) |
| US48 | 0/68664 | 0.0 | 0/67992 | 0.0 | 0.997 (n=68664) | 0.9997 (n=68664) |

R5: {"applicable_to_locked_regions": false, "reason": "7 vùng khóa không phủ toàn bộ US48 => không cùng phạm vi (dq_rules.yml)", "aux_check_13_regions": {"hours_evaluated": 68663, "flags": 0, "flag_share": 0.0, "median_abs_dev": 0.0}}

Mẫu chấm tay: {"n": 40, "path": "D:\\video\\grid_feasibility\\review\\dq_review.csv", "overwritten": true, "n_flags_pool": 14943, "by_rule": {"R4": 27, "R3": 13}}

### C4 — Ghép thời tiết

| Vùng | Giờ có nhiệt độ | Tỷ lệ | Trung vị giờ địa phương của Tmax ngày | Giờ thiếu cuối cùng |
|---|---|---|---|---|
| CISO | 68664 | 1.0 | 15.0 | None |
| ERCO | 68664 | 1.0 | 16.0 | None |
| PJM | 68664 | 1.0 | 15.0 | None |
| MISO | 68664 | 1.0 | 15.0 | None |
| NYIS | 68664 | 1.0 | 15.0 | None |
| ISNE | 68664 | 1.0 | 14.0 | None |
| SWPP | 68664 | 1.0 | 16.0 | None |
| US48 | 68664 | 1.0 | 16.0 | None |

Kiểm tra căn UTC: {"weather_duplicates": 0, "weather_utc_offsets": [0], "weather_timezones": ["GMT"], "weather_continuous_all_cities": true, "join_one_to_one": true, "diurnal_peak_in_12_18_all": true}

### Q1 — Nhu cầu ròng

- Tỷ trọng gió+mặt trời 2025: {"CISO": 0.3489, "ERCO": 0.3694, "PJM": 0.065, "MISO": 0.1952, "NYIS": 0.0532, "ISNE": 0.057, "SWPP": 0.3748, "US48": 0.1704}
- Tỷ lệ giờ đủ (D, WND, SUN) theo năm: {"CISO": {"2019": 0.997, "2020": 0.9995, "2021": 0.9993, "2022": 0.9997, "2023": 0.9998, "2024": 0.9973, "2025": 1.0, "2026": 1.0}, "ERCO": {"2019": 1.0, "2020": 1.0, "2021": 0.9999, "2022": 1.0, "2023": 1.0, "2024": 0.9995, "2025": 0.9973, "2026": 1.0}, "PJM": {"2019": 0.9998, "2020": 0.9948, "2021": 1.0, "2022": 0.9968, "2023": 0.9971, "2024": 0.9972, "2025": 0.9999, "2026": 1.0}, "MISO": {"2019": 0.9993, "2020": 1.0, "2021": 0.9998, "2022": 0.9997, "2023": 1.0, "2024": 0.9969, "2025": 1.0, "2026": 1.0}, "NYIS": {"2019": 0.9983, "2020": 0.9997, "2021": 0.9998, "2022": 1.0, "2023": 1.0, "2024": 0.9978, "2025": 0.9993, "2026": 1.0}, "ISNE": {"2019": 1.0, "2020": 1.0, "2021": 0.9998, "2022": 1.0, "2023": 1.0, "2024": 0.9997, "2025": 1.0, "2026": 1.0}, "SWPP": {"2019": 1.0, "2020": 1.0, "2021": 0.9999, "2022": 1.0, "2023": 1.0, "2024": 0.9969, "2025": 1.0, "2026": 1.0}, "US48": {"2019": 1.0, "2020": 1.0, "2021": 1.0, "2022": 1.0, "2023": 1.0, "2024": 1.0, "2025": 1.0, "2026": 1.0}}
- Chỉ số 2025 (trung vị qua 4 mùa, hồ sơ trung vị, MW / MW/h): {"CISO": {"med_midday_depth": 11329.8, "med_afternoon_ramp": 3859.6, "med_evening_peak": 25396.8}, "ERCO": {"med_midday_depth": 11361.2, "med_afternoon_ramp": 4284.4, "med_evening_peak": 46166.0}, "ISNE": {"med_midday_depth": 1710.0, "med_afternoon_ramp": 980.5, "med_evening_peak": 15277.2}, "MISO": {"med_midday_depth": 3159.5, "med_afternoon_ramp": 2787.9, "med_evening_peak": 68012.5}, "NYIS": {"med_midday_depth": 319.2, "med_afternoon_ramp": 631.8, "med_evening_peak": 18823.0}, "PJM": {"med_midday_depth": 4980.0, "med_afternoon_ramp": 3283.8, "med_evening_peak": 99864.2}, "SWPP": {"med_midday_depth": -1164.8, "med_afternoon_ramp": 343.4, "med_evening_peak": 24780.5}, "US48": {"med_midday_depth": 30243.2, "med_afternoon_ramp": 18184.1, "med_evening_peak": 452327.8}}
- Hồ sơ đầy đủ: `data/mart/q1_netload_profiles.parquet`, `q1_netload_metrics.parquet`.

### Q2 — Sai số dự báo (e = DF − D)

| Vùng | MAPE % | MdAPE % | MAE MW | Bias MW | n | Phủ D&DF |
|---|---|---|---|---|---|---|
| CISO | 8.599 | 3.043 | 1314.139 | -650.534 | 68520 | 0.9979 |
| ERCO | 2.419 | 1.767 | 1190.445 | 239.022 | 68519 | 0.9979 |
| ISNE | 2.539 | 1.644 | 313.791 | -195.0 | 68659 | 0.9999 |
| MISO | 2.791 | 2.507 | 2076.571 | 1809.217 | 68461 | 0.997 |
| NYIS | 2.923 | 2.428 | 510.149 | -423.155 | 68554 | 0.9986 |
| PJM | 3.611 | 3.096 | 63357.607 | -61182.319 | 68401 | 0.9962 |
| SWPP | 4.709 | 3.245 | 1582.104 | 1064.111 | 67990 | 0.9902 |
| US48 | 1.646 | 1.212 | 7787.855 | -4476.29 | 68664 | 1.0 |

Nhóm (APE %, mean/median/size):

- CISO / temp: cold_mean=3.5288, cold_median=2.7301, cold_size=6852.0, hot_mean=6.5179, hot_median=4.167, hot_size=6852.0, mid_mean=9.4927, mid_median=2.9792, mid_size=54816.0
- CISO / ren_share: high_mean=8.6781, high_median=5.2923, high_size=22834.0, low_mean=3.294, low_median=2.4644, low_size=22835.0, mid_mean=3.4982, mid_median=2.4629, mid_size=22834.0
- ERCO / temp: cold_mean=3.6974, cold_median=2.4698, cold_size=6852.0, hot_mean=1.8274, hot_median=1.3717, hot_size=6852.0, mid_mean=2.333, mid_median=1.7595, mid_size=54815.0
- ERCO / ren_share: high_mean=2.3118, high_median=1.7692, high_size=22838.0, low_mean=2.649, low_median=1.8417, low_size=22839.0, mid_mean=2.296, mid_median=1.6855, mid_size=22838.0
- PJM / temp: cold_mean=3.1092, cold_median=2.7567, cold_size=6841.0, hot_mean=3.5589, hot_median=3.0739, hot_size=6841.0, mid_mean=3.6798, mid_median=3.154, mid_size=54719.0
- PJM / ren_share: high_mean=3.1761, high_median=2.7656, high_size=22798.0, low_mean=4.0795, low_median=3.5598, low_size=22798.0, mid_mean=3.5754, mid_median=3.0513, mid_size=22798.0
- MISO / temp: cold_mean=2.3171, cold_median=1.988, cold_size=6847.0, hot_mean=3.2585, hot_median=2.9123, hot_size=6847.0, mid_mean=2.7917, mid_median=2.5346, mid_size=54767.0
- MISO / ren_share: high_mean=2.7108, high_median=2.4922, high_size=22819.0, low_mean=2.9732, low_median=2.6425, low_size=22820.0, mid_mean=2.6891, mid_median=2.3918, mid_size=22819.0
- NYIS / temp: cold_mean=3.4654, cold_median=3.3447, cold_size=6856.0, hot_mean=3.0029, hot_median=2.4599, hot_size=6856.0, mid_mean=2.8452, mid_median=2.3091, mid_size=54842.0
- NYIS / ren_share: high_mean=2.9958, high_median=2.5208, high_size=22838.0, low_mean=2.8464, low_median=2.35, low_size=22838.0, mid_mean=2.9272, mid_median=2.4138, mid_size=22837.0
- ISNE / temp: cold_mean=1.9466, cold_median=1.2888, cold_size=6866.0, hot_mean=1.7671, hot_median=1.1619, hot_size=6866.0, mid_mean=2.7098, mid_median=1.7682, mid_size=54927.0
- ISNE / ren_share: high_mean=2.9735, high_median=2.0676, high_size=22881.0, low_mean=2.3615, low_median=1.4774, low_size=22882.0, mid_mean=2.2819, mid_median=1.4651, mid_size=22881.0
- SWPP / temp: cold_mean=4.7212, cold_median=2.7703, cold_size=6799.0, hot_mean=4.6983, hot_median=3.3002, hot_size=6799.0, mid_mean=4.7092, mid_median=3.3233, mid_size=54392.0
- SWPP / ren_share: high_mean=4.5226, high_median=2.9187, high_size=22663.0, low_mean=4.8706, low_median=3.6372, low_size=22663.0, mid_mean=4.7349, mid_median=3.2, mid_size=22662.0
- US48 / temp: cold_mean=1.5533, cold_median=1.2133, cold_size=6867.0, hot_mean=1.5828, hot_median=1.007, hot_size=6867.0, mid_mean=1.6652, mid_median=1.2405, mid_size=54930.0
- US48 / ren_share: high_mean=1.8394, high_median=1.2964, high_size=22888.0, low_mean=1.5169, low_median=1.1668, low_size=22888.0, mid_mean=1.5811, mid_median=1.1693, mid_size=22888.0

Hồi quy APE (%) ~ lạnh P10 + nóng P90 + tỷ trọng tái tạo (điểm %) + giờ + tháng; SE Newey-West lag 24 (chỉ là mức liên quan):

| Vùng | n | cold_p10 (SE) | hot_p90 (SE) | ren_share_pp (SE) |
|---|---|---|---|---|
| CISO | 68503 | 0.6252 (0.1418) | -1.3541 (0.1864) | 0.0812 (0.0058) |
| ERCO | 68515 | 1.4343 (0.2452) | -0.9454 (0.0734) | -0.0096 (0.0029) |
| PJM | 68394 | -0.4578 (0.0602) | -0.089 (0.0663) | -0.0094 (0.0054) |
| MISO | 68458 | -0.6711 (0.0946) | 0.2491 (0.0735) | -0.0107 (0.0031) |
| NYIS | 68513 | 0.4056 (0.257) | 0.2519 (0.1638) | 0.0119 (0.0201) |
| ISNE | 68644 | -0.7715 (0.0544) | -0.8376 (0.0602) | 0.1263 (0.0071) |
| SWPP | 67988 | 0.0756 (0.3204) | -0.6353 (0.2002) | -0.0015 (0.0047) |
| US48 | 68664 | 0.0818 (0.0788) | -0.1826 (0.084) | 0.048 (0.0077) |

### Q3 — Thay đổi sản lượng theo nguồn 16h→20h giờ địa phương (MW, năm 2025: trung vị)

- CISO: phủ nguồn=0.9994, OTH+UNK=0.0288, đạt=True; Δ: SUN -10054, OTH +6709, WAT +2097, WND +538, NG -129, GEO +3, COL +0, NUC +0
- ERCO: phủ nguồn=0.9997, OTH+UNK=0.0023, đạt=True; Δ: SUN -17032, NG +7558, WND +3293, BAT +1967, COL +1018, UES +384, WAT +108, NUC -1
- PJM: phủ nguồn=0.9983, OTH+UNK=0.0148, đạt=True; Δ: SUN -5980, NG +4473, WAT +2244, COL +1066, WND +125, OIL +118, OTH +93, NUC +7
- MISO: phủ nguồn=0.9995, OTH+UNK=0.0086, đạt=True; Δ: SUN -7469, NG +3090, COL +1701, WAT +477, WND +275, BAT +44, OTH +22, NUC +3
- NYIS: phủ nguồn=0.9996, OTH+UNK=0.0279, đạt=True; Δ: NG +1205, WAT +613, OTH -219, NUC +15, WND -12, COL +0, OIL +0, SUN +0
- ISNE: phủ nguồn=1.0, OTH+UNK=0.0516, đạt=True; Δ: NG +1148, PS +476, SUN -386, WAT +136, WND +46, BAT +18, OTH +13, NUC +5
- SWPP: phủ nguồn=0.9996, OTH+UNK=0.0015, đạt=True; Δ: WND +1117, SUN -430, WAT -75, COL +0, NG +0, NUC +0, OIL +0, OTH +0
- US48: phủ nguồn=1.0, OTH+UNK=0.0169, đạt=True; Δ: SUN -44101, NG +27578, WAT +8564, COL +6438, WND +5914, OTH +4605, PS +2324, BAT +2132

### Q4 — Trao đổi trong 1% giờ nhu cầu cao nhất (2023→D-3)

| Vùng | Số giờ | Nhập ròng trung vị (căng thẳng) | Nhập ròng trung vị (mọi giờ) | Đối tác chính (nhập trung vị) |
|---|---|---|---|---|
| CISO | 336 | 2815.0 | 4298.0 | NEVP (836.5) |
| ERCO | 336 | -52.5 | 20.0 | CEN (-0.0) |
| PJM | 336 | -517.5 | -2358.0 | DUK (360.5) |
| MISO | 336 | 4850.0 | 2854.0 | PJM (4149.5) |
| NYIS | 336 | 2807.5 | 2279.0 | PJM (1434.0) |
| ISNE | 337 | 2627.0 | 1021.0 | HQT (1818.0) |
| SWPP | 336 | 258.5 | -399.0 | SPA (308.5) |

Khớp hai chiều theo cặp (top 20 theo số giờ): [{"fromba": "ISNE", "toba": "NYIS", "mean": 0.8549, "size": 33504}, {"fromba": "MISO", "toba": "SOCO", "mean": 0.0231, "size": 33464}, {"fromba": "CISO", "toba": "NEVP", "mean": 0.9988, "size": 33406}, {"fromba": "CISO", "toba": "PACW", "mean": 0.9396, "size": 33389}, {"fromba": "NYIS", "toba": "PJM", "mean": 0.1327, "size": 33356}, {"fromba": "MISO", "toba": "PJM", "mean": 0.0544, "size": 33340}, {"fromba": "MISO", "toba": "TVA", "mean": 0.5019, "size": 33269}, {"fromba": "PJM", "toba": "TVA", "mean": 0.0728, "size": 33233}, {"fromba": "CISO", "toba": "SRP", "mean": 0.4719, "size": 33142}, {"fromba": "MISO", "toba": "SPA", "mean": 0.8839, "size": 33134}, {"fromba": "CISO", "toba": "TIDC", "mean": 0.598, "size": 33013}, {"fromba": "CISO", "toba": "WALC", "mean": 0.6163, "size": 32950}, {"fromba": "CISO", "toba": "LDWP", "mean": 0.99, "size": 32635}, {"fromba": "CISO", "toba": "IID", "mean": 0.9767, "size": 32374}, {"fromba": "ERCO", "toba": "SWPP", "mean": 0.7464, "size": 29775}, {"fromba": "MISO", "toba": "SWPP", "mean": 0.5991, "size": 29766}, {"fromba": "SWPP", "toba": "WAUW", "mean": 0.9984, "size": 20972}, {"fromba": "SWPP", "toba": "WACM", "mean": 0.995, "size": 20909}, {"fromba": "MISO", "toba": "SIKE", "mean": 0.9744, "size": 6019}]

### Q5 — Khác thường (cửa sổ 2026-08-02 23:00:00+00:00 → 2026-10-31 23:00:00+00:00)

| Vùng | Giờ | Đánh giá được | MAD=0/thiếu baseline | Cờ | Tỷ lệ |
|---|---|---|---|---|---|
| CISO | 2160 | 2160 | 0 | 226 | 0.1046 |
| ERCO | 2160 | 2160 | 0 | 527 | 0.244 |
| PJM | 2160 | 2160 | 0 | 314 | 0.1454 |
| MISO | 2160 | 2160 | 0 | 164 | 0.0759 |
| NYIS | 2160 | 2160 | 0 | 180 | 0.0833 |
| ISNE | 2160 | 2160 | 0 | 143 | 0.0662 |
| SWPP | 2160 | 2160 | 0 | 240 | 0.1111 |
| US48 | 2160 | 2160 | 0 | 397 | 0.1838 |

## 5. Độ mới và thời điểm hiển thị (C2)

- Trạng thái C2: **CHƯA ĐỦ DỮ LIỆU** (2/72 lần thành công; thời lượng/lần: {"median": 7.83, "max": 9.53}).
- Độ trễ (giờ, fetched_at lần đầu − period): {"D": {"n": 0, "censored_gt_window": 0, "median_h": null, "p95_h": null, "per_region_median_h": {"CISO": null, "ERCO": null, "ISNE": null, "MISO": null, "NYIS": null, "PJM": null, "SWPP": null, "US48": null}}, "NG": {"n": 0, "censored_gt_window": 0, "median_h": null, "p95_h": null, "per_region_median_h": {"CISO": null, "ERCO": null, "ISNE": null, "MISO": null, "NYIS": null, "PJM": null, "SWPP": null, "US48": null}}, "TI": {"n": 0, "censored_gt_window": 0, "median_h": null, "p95_h": null, "per_region_median_h": {"CISO": null, "ERCO": null, "ISNE": null, "MISO": null, "NYIS": null, "PJM": null, "SWPP": null, "US48": null}}, "FUEL": {"n": 0, "censored_gt_window": 0, "median_h": null, "p95_h": null}, "INTERCHANGE": {"n": 0, "censored_gt_window": 0, "median_h": null, "p95_h": null}, "DF_lead_hours": {"n": 0, "median_h": null, "min_h": null}}
- Sửa giá trị (>1%): {"D": {"keys_seen_2plus": 568, "revised_gt1pct": 1, "share": 0.0018, "median_rel_change_revised": 0.0234, "max_rel_change": 0.0234, "any_change_share": 0.0123}, "DF": {"keys_seen_2plus": 638, "revised_gt1pct": 0, "share": 0.0, "median_rel_change_revised": null, "max_rel_change": 0.0, "any_change_share": 0.0}, "NG": {"keys_seen_2plus": 484, "revised_gt1pct": 0, "share": 0.0, "median_rel_change_revised": null, "max_rel_change": 0.0, "any_change_share": 0.0}, "TI": {"keys_seen_2plus": 445, "revised_gt1pct": 0, "share": 0.0, "median_rel_change_revised": null, "max_rel_change": 0.0, "any_change_share": 0.0}, "FUEL": {"keys_seen_2plus": 4571, "revised_gt1pct": 0, "share": 0.0, "median_rel_change_revised": null, "max_rel_change": 0.0, "any_change_share": 0.0}, "INTERCHANGE": {"keys_seen_2plus": 1347, "revised_gt1pct": 0, "share": 0.0, "median_rel_change_revised": null, "max_rel_change": 0.0, "any_change_share": 0.0}, "pooled_actuals": {"keys": 7415, "revised": 1, "share": 0.0001}}
- Dự báo: {"status": "CHƯA XÁC ĐỊNH", "type_name_api": "Day-ahead demand forecast", "values_per_key_per_snapshot_max": 1, "api_versions": "một phiên bản (không có facet thời điểm phát hành; 1 giá trị/khóa)", "DF_revised_share": 0.0}
- HTTP status: {"200": 6}; header quota: []
- Gợi ý hiển thị (dựa trên P95 đo được): nhu cầu/NG hiển thị đến now − None h; theo nguồn đến now − None h; trao đổi cặp đến now − None h. Nếu giá trị là None/inf: CHƯA ĐỦ DỮ LIỆU.

## 6. Lỗi đã gặp, khác biệt so với giả định

- Backfill: [{"elapsed_s": 1158.0, "requests": 3027, "chunks_done": 1690, "n_fails": 0}]
- Lỗi snapshot: []
- Fueltype quan sát: ["BAT", "COL", "GEO", "NG", "NUC", "OES", "OIL", "OTH", "PS", "SNB", "SUN", "UES", "UNK", "WAT", "WNB", "WND"]. Q1 dùng đúng định nghĩa đã khóa (WND, SUN); SNB/WNB (năng lượng tái tạo kèm pin) không cộng vào — giới hạn đã biết.
- Không có header quota từ EIA ⇒ 'số request còn lại' không đo được.
- Snapshot chỉ phát hiện được độ trễ ≤ 72 h (cửa sổ 72 h); giờ chưa xuất hiện khi rời cửa sổ được tính là +∞ trong phân vị.

### C5 tài nguyên

{"backfill_requests_eia": 3027, "backfill_elapsed_s": 1158.0, "snapshot_runs": 2, "snapshot_requests": 6, "storage_total_bytes": 367670132, "storage_raw_bytes": 74414084, "storage_parquet_bytes": 114841838, "mart_bytes": 29664751, "peak_rss_analyze_bytes": 3313360896, "daily": {"window": ["2026-10-25T00", "2026-10-31T23"], "rows": {"region": 5360, "fuel": 12720, "agg13": 2184, "ic_fromba": 7527, "ic_toba": 6265}, "requests": 11, "weather_status": 200, "t_eia_s": 16.8, "t_weather_s": 1.6, "t_build_s": 513.2, "t_analyze_s": 94.4, "total_s": 626.0}}

## 7. Câu hỏi: giữ / thu hẹp / bỏ

- **Q1 Nhu cầu ròng**: PASS. GIỮ
- **Q2 Sai số dự báo**: CHƯA XÁC ĐỊNH. CHƯA XÁC ĐỊNH — chờ: forecast_meaning_C2
- **Q3 Nguồn bù khi mặt trời giảm**: PASS. GIỮ
- **Q4 Trao đổi lúc căng thẳng**: FAIL. KHÔNG ĐẠT theo ngưỡng đã khóa — tiêu chí trượt: pair_coverage, symmetry_within_5pct. Phải thu hẹp phạm vi (chỉ vùng/kỳ đạt) hoặc bỏ; không nới ngưỡng.
- **Q5 Phát hiện khác thường**: FAIL. KHÔNG ĐẠT theo ngưỡng đã khóa — tiêu chí trượt: max_flag_share. Phải thu hẹp phạm vi (chỉ vùng/kỳ đạt) hoặc bỏ; không nới ngưỡng.

## 8. Kết luận cuối

**KHÔNG CHỐT**

Điều kiện bắt buộc trượt:
- C3: {"R4_min_pass": 0.857}
- Q5: {"max_flag_share": 0.244}

Ngoài ra còn chưa xác định: C2, Q2 (không làm thay đổi kết luận vì đã có điều kiện bắt buộc trượt).

## Chạy lại

```powershell
cd grid_feasibility
.\run_all.ps1            # toàn bộ, tiếp tục từ điểm dừng
.\run_all.ps1 -ReportOnly # chỉ tính lại C2 + báo cáo
```