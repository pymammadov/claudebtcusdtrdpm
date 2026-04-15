# Export BTCUSD Trading Results to Windows
# PowerShell script to copy results from WSL to Windows and open in browser

param(
    [string]$SourcePath = "C:\home\user\claudebtcusdtrdpm\btcusd-trader\results",
    [string]$DestPath = "C:\Users\admin\claudebtcusdtrdpm\results",
    [switch]$OpenBrowser = $true
)

# Create destination folder if it doesn't exist
if (-not (Test-Path $DestPath)) {
    Write-Host "📁 Creating folder: $DestPath" -ForegroundColor Cyan
    New-Item -ItemType Directory -Path $DestPath -Force | Out-Null
}

# Copy all HTML and JSON files
Write-Host "📋 Copying files..." -ForegroundColor Cyan

$filePatterns = @("*.html", "*.json", "*.csv")
$fileCount = 0

foreach ($pattern in $filePatterns) {
    $files = Get-ChildItem -Path $SourcePath -Filter $pattern -ErrorAction SilentlyContinue

    foreach ($file in $files) {
        Copy-Item -Path $file.FullName -Destination $DestPath -Force
        Write-Host "  ✅ $($file.Name)" -ForegroundColor Green
        $fileCount++
    }
}

if ($fileCount -eq 0) {
    Write-Host "⚠️  No files found to copy" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ $fileCount files copied successfully!" -ForegroundColor Green

# Open report in browser if requested
if ($OpenBrowser) {
    $reportPath = Join-Path $DestPath "mt4_report.html"

    if (Test-Path $reportPath) {
        Write-Host "🌐 Opening report in browser..." -ForegroundColor Cyan
        Start-Process $reportPath
        Write-Host "✅ Report opened!" -ForegroundColor Green
    } else {
        Write-Host "⚠️  mt4_report.html not found" -ForegroundColor Yellow
    }
}

Write-Host "`n📊 Results available at: $DestPath" -ForegroundColor Cyan
