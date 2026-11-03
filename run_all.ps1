param (
    [switch]$ReportOnly
)

$Python = "C:\Users\Admin\AppData\Local\Programs\Python\Python312\python.exe"
$SrcDir = "d:\video\grid_feasibility\src"

if (-not $ReportOnly) {
    Write-Host "=== 1. Chạy snapshot C2 (nếu tới giờ) ==="
    & $Python "$SrcDir\snapshot.py"

    Write-Host "=== 2. Kiểm tra & tải backfill lịch sử EIA ==="
    & $Python "$SrcDir\step1_backfill.py"

    Write-Host "=== 3. Kiểm tra & tải dữ liệu thời tiết Open-Meteo ==="
    & $Python "$SrcDir\step4_weather.py"

    Write-Host "=== 4. Chuẩn hóa dữ liệu sang Parquet ==="
    & $Python "$SrcDir\step1b_build.py"

    Write-Host "=== 5. Phân tích lịch sử (C1, C3, C4, Q1-Q5) ==="
    & $Python "$SrcDir\analyze_history.py"

    Write-Host "=== 6. Đo thời gian cập nhật ngày (C5) ==="
    & $Python "$SrcDir\daily_update.py"
}

Write-Host "=== 7. Phân tích độ mới snapshot (C2) ==="
& $Python "$SrcDir\c2_analyze.py"

Write-Host "=== 8. Sinh báo cáo report.md ==="
& $Python "$SrcDir\report.py"

Write-Host "=== HOÀN TẤT ==="

