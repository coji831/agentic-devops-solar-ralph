# hook-test-runner.ps1
# Quick manual test runner for hook system validation
# Runs test-hook.cjs for each event type to verify functionality

Write-Host "`n=== SOLAR-Ralph Hook System Test Runner ===" -ForegroundColor Cyan
Write-Host "Testing all 8 hook events...`n" -ForegroundColor White

$rootDir = Split-Path -Parent $PSScriptRoot
$testHook = Join-Path $rootDir ".github\hooks\test-hook.cjs"
$logDir = Join-Path $rootDir ".github\solar-system\logs\hook-tests"

# Verify test hook exists
if (-not (Test-Path $testHook)) {
    Write-Host "ERROR: test-hook.cjs not found at $testHook" -ForegroundColor Red
    exit 1
}

Write-Host "Test hook: $testHook" -ForegroundColor Gray
Write-Host "Log directory: $logDir`n" -ForegroundColor Gray

# Test events
$events = @(
    "SessionStart",
    "UserPromptSubmit",
    "PreToolUse",
    "PostToolUse",
    "SubagentStart",
    "SubagentStop",
    "PreCompact",
    "Stop"
)

$passed = 0
$failed = 0

foreach ($event in $events) {
    Write-Host "Testing $event..." -NoNewline
    
    # Set environment variable for event
    $env:GITHUB_COPILOT_HOOK_EVENT = $event
    
    # Run hook
    $result = node $testHook 2>&1
    $exitCode = $LASTEXITCODE
    
    if ($exitCode -eq 0) {
        Write-Host " PASS" -ForegroundColor Green
        $passed++
    }
    else {
        Write-Host " FAIL (exit code: $exitCode)" -ForegroundColor Red
        Write-Host "  Output: $result" -ForegroundColor Yellow
        $failed++
    }
}

Write-Host "`n=== Test Results ===" -ForegroundColor Cyan
Write-Host "Passed: $passed/$($events.Count)" -ForegroundColor Green
Write-Host "Failed: $failed/$($events.Count)" -ForegroundColor $(if ($failed -gt 0) { "Red" } else { "Green" })

# Check log directory
Write-Host "`n=== Log Files Created ===" -ForegroundColor Cyan
if (Test-Path $logDir) {
    $logFiles = Get-ChildItem $logDir | Select-Object Name, Length, LastWriteTime
    $logFiles | Format-Table -AutoSize
    
    Write-Host "Total log files: $($logFiles.Count)" -ForegroundColor White
}
else {
    Write-Host "WARNING: Log directory not created at $logDir" -ForegroundColor Yellow
}

# Summary
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
if ($failed -eq 0) {
    Write-Host "✅ All hooks working! System ready for v4.1 implementation." -ForegroundColor Green
}
else {
    Write-Host "❌ Some hooks failed. Review errors before proceeding." -ForegroundColor Red
    Write-Host "Check: $logDir\errors.log for details" -ForegroundColor Yellow
}

Write-Host ""
