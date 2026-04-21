# check-hook-test-results.ps1
# Quick verification script for hook test results

Write-Host "`n=== SOLAR-Ralph Hook Test Results ===" -ForegroundColor Cyan

$logDir = ".github\solar-system\logs\hook-tests"

if (-not (Test-Path $logDir)) {
    Write-Host "❌ Test log directory not found: $logDir" -ForegroundColor Red
    exit 1
}

Write-Host "`n📁 Log Directory: $logDir" -ForegroundColor White

# Check for summary
$summaryPath = Join-Path $logDir "TEST-SUMMARY.txt"
if (Test-Path $summaryPath) {
    Write-Host "`n✅ TEST-SUMMARY.txt found - displaying contents:" -ForegroundColor Green
    Write-Host "================================================`n" -ForegroundColor Gray
    Get-Content $summaryPath
    Write-Host "`n================================================" -ForegroundColor Gray
}
else {
    Write-Host "`n⚠️  TEST-SUMMARY.txt not found (test may not have completed)" -ForegroundColor Yellow
}

# Count logs
$logFiles = Get-ChildItem $logDir -Filter "*.log"
$counterFiles = Get-ChildItem $logDir -Filter "*-counter.txt" -ErrorAction SilentlyContinue
$markerFiles = Get-ChildItem $logDir -Filter "*.marker" -ErrorAction SilentlyContinue
$jsonFiles = Get-ChildItem $logDir -Filter "*.json" -ErrorAction SilentlyContinue

Write-Host "`n📊 File Counts:" -ForegroundColor Cyan
Write-Host "   Log files: $($logFiles.Count)" -ForegroundColor White
Write-Host "   Counter files: $($counterFiles.Count)" -ForegroundColor White
Write-Host "   Marker files: $($markerFiles.Count)" -ForegroundColor White
Write-Host "   JSON files: $($jsonFiles.Count)" -ForegroundColor White

# Show recent activity
Write-Host "`n⏰ Recent Activity (last 5 minutes):" -ForegroundColor Cyan
$recentFiles = Get-ChildItem $logDir | Where-Object { 
    $_.LastWriteTime -gt (Get-Date).AddMinutes(-5) 
} | Sort-Object LastWriteTime -Descending | Select-Object -First 10

if ($recentFiles) {
    $recentFiles | Format-Table Name, LastWriteTime -AutoSize
}
else {
    Write-Host "   No recent activity" -ForegroundColor Yellow
}

# Check specific test files
Write-Host "`n🔍 Test File Verification:" -ForegroundColor Cyan

$checkFiles = @(
    "hooksystemanalysis.log",
    "prompt-counter.txt",
    "tool-execution-counter.txt",
    "active-subagents.json"
)

foreach ($file in $checkFiles) {
    $filePath = Join-Path $logDir $file
    if (Test-Path $filePath) {
        $size = (Get-Item $filePath).Length
        Write-Host "   ✅ $file ($size bytes)" -ForegroundColor Green
        
        # Show counter values
        if ($file -like "*-counter.txt") {
            $value = Get-Content $filePath -Raw
            Write-Host "      Current count: $value" -ForegroundColor Gray
        }
    }
    else {
        Write-Host "   ❌ $file (not found)" -ForegroundColor Red
    }
}

# Check for errors
$errorLog = Join-Path $logDir "errors.log"
if (Test-Path $errorLog) {
    Write-Host "`n⚠️  ERRORS DETECTED:" -ForegroundColor Red
    Write-Host "================================================" -ForegroundColor Red
    Get-Content $errorLog | Select-Object -Last 20
    Write-Host "================================================`n" -ForegroundColor Red
}
else {
    Write-Host "`n✅ No errors detected (errors.log doesn't exist)" -ForegroundColor Green
}

# Final verdict
Write-Host "`n=== Final Verdict ===" -ForegroundColor Cyan

$hasAnalysis = Test-Path (Join-Path $logDir "hooksystemanalysis.log")
$hasCounters = Test-Path (Join-Path $logDir "prompt-counter.txt")
$hasSummary = Test-Path $summaryPath
$hasErrors = Test-Path $errorLog

if ($hasAnalysis -and $hasCounters -and $hasSummary -and -not $hasErrors) {
    Write-Host "✅ PASS - Hook system validated and working!" -ForegroundColor Green
    Write-Host "`nReady to proceed with v4.1 P0 implementation:" -ForegroundColor White
    Write-Host "  1. Edit pre-tool-use.cjs for inquiry gate" -ForegroundColor Gray
    Write-Host "  2. Edit session-start.cjs for learning capture" -ForegroundColor Gray
    Write-Host "  3. Edit post-tool-use.cjs for session logging" -ForegroundColor Gray
}
else {
    Write-Host "⚠️  PARTIAL - Review findings before proceeding" -ForegroundColor Yellow
    if (-not $hasAnalysis) { Write-Host "   Missing: hooksystemanalysis.log" -ForegroundColor Red }
    if (-not $hasCounters) { Write-Host "   Missing: counter files" -ForegroundColor Red }
    if (-not $hasSummary) { Write-Host "   Missing: TEST-SUMMARY.txt" -ForegroundColor Red }
    if ($hasErrors) { Write-Host "   Errors detected in errors.log" -ForegroundColor Red }
}

Write-Host ""
