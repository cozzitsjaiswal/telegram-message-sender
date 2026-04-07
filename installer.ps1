# Furaya Promo Engine — Windows Installer
# Run this script as Administrator for best results.
# It will:
#   1. Create C:\FurayaPromoEngine\ (install dir)
#   2. Create C:\FurayaPromoEngine\data\  (runtime data)
#   3. Copy FurayaPromoEngine.exe there
#   4. Create a Desktop shortcut
#   5. Create a Start Menu shortcut
#   6. Open the app

$ErrorActionPreference = 'Stop'
$AppName    = "Furaya Promo Engine"
$InstallDir = "C:\FurayaPromoEngine"
$DataDir    = "$InstallDir\data"
$ExeName    = "FurayaPromoEngine.exe"
$ExeSrc     = Join-Path $PSScriptRoot $ExeName

# ── 1. Create directories ──────────────────────────────────────────────────────
Write-Host "`n[1/5] Creating installation directory..."
New-Item -ItemType Directory -Path $InstallDir -Force | Out-Null
New-Item -ItemType Directory -Path $DataDir    -Force | Out-Null
Write-Host "      $InstallDir  OK"
Write-Host "      $DataDir  OK"

# ── 2. Copy EXE ────────────────────────────────────────────────────────────────
Write-Host "[2/5] Copying application..."
if (-not (Test-Path $ExeSrc)) {
    Write-Host "ERROR: Cannot find $ExeName next to this installer." -ForegroundColor Red
    Write-Host "       Make sure installer.ps1 and $ExeName are in the same folder."
    pause; exit 1
}
Copy-Item $ExeSrc "$InstallDir\$ExeName" -Force
$sizeMB = [Math]::Round((Get-Item "$InstallDir\$ExeName").Length / 1MB, 1)
Write-Host "      Installed ($sizeMB MB)  OK"

# ── 3. Desktop shortcut ────────────────────────────────────────────────────────
Write-Host "[3/5] Creating Desktop shortcut..."
$WShell   = New-Object -ComObject WScript.Shell
$Shortcut = $WShell.CreateShortcut("$env:USERPROFILE\Desktop\$AppName.lnk")
$Shortcut.TargetPath       = "$InstallDir\$ExeName"
$Shortcut.WorkingDirectory = $InstallDir
$Shortcut.Description      = $AppName
$Shortcut.Save()
Write-Host "      Desktop shortcut  OK"

# ── 4. Start Menu shortcut ────────────────────────────────────────────────────
Write-Host "[4/5] Creating Start Menu entry..."
$StartMenuDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Furaya"
New-Item -ItemType Directory -Path $StartMenuDir -Force | Out-Null
$SM = $WShell.CreateShortcut("$StartMenuDir\$AppName.lnk")
$SM.TargetPath       = "$InstallDir\$ExeName"
$SM.WorkingDirectory = $InstallDir
$SM.Description      = $AppName
$SM.Save()
Write-Host "      Start Menu  OK"

# ── 5. Launch ──────────────────────────────────────────────────────────────────
Write-Host "[5/5] Launching $AppName..."
Start-Process "$InstallDir\$ExeName"

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host " $AppName installed successfully!" -ForegroundColor Green
Write-Host " Location : $InstallDir"           -ForegroundColor White
Write-Host " Data     : $DataDir"              -ForegroundColor White
Write-Host " Shortcut : Desktop + Start Menu"  -ForegroundColor White
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
pause
