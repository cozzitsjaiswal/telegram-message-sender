# Package the final Furaya Promo Engine installer bundle

$dist   = 'c:\Users\NazaraX\telegram-message-sender\dist\FurayaPromoEngine.exe'
$inst   = 'c:\Users\NazaraX\telegram-message-sender\installer.ps1'
$out    = 'c:\Users\NazaraX\Desktop\FurayaPromoEngine_Setup.zip'

# Also copy EXE individually to Desktop for quick access
Copy-Item $dist 'c:\Users\NazaraX\Desktop\FurayaPromoEngine.exe' -Force

# Create installer README
$readme = @"
============================================
  FURAYA PROMO ENGINE — Installation Guide
============================================

WHAT IS INCLUDED:
  FurayaPromoEngine.exe  - The application
  installer.ps1          - Automated installer

OPTION A — Quick Install (Recommended):
  1. Right-click installer.ps1
  2. Select "Run with PowerShell"
  3. If prompted, click "Yes" (UAC)
  
  This will:
  - Install to C:\FurayaPromoEngine\
  - Create C:\FurayaPromoEngine\data\ for your data
  - Add a Desktop shortcut
  - Add to Start Menu
  - Launch the app automatically

OPTION B — Manual:
  Just double-click FurayaPromoEngine.exe from anywhere.
  All data is always stored in C:\FurayaPromoEngine\data\

DATA FILES LOCATION:
  C:\FurayaPromoEngine\data\
    accounts.json       - Your Telegram accounts
    messages.json       - Your message templates
    *.session           - Login sessions
    bot.log             - Activity log
    performance.json    - Campaign statistics
    campaign_memory.json - Rotation state

FIRST USE:
  1. Go to Accounts tab → Add Account (need API ID + API Hash from my.telegram.org)
  2. Click Login → enter the OTP from Telegram
  3. Go to Campaign tab → enter target groups
  4. Select mode (SAFE/NORMAL/AGGRESSIVE)
  5. Click Start Campaign

============================================
"@
$readme | Out-File -FilePath 'c:\Users\NazaraX\Desktop\README_Furaya.txt' -Encoding UTF8

# Build zip with EXE + installer + readme
if (Test-Path $out) { Remove-Item $out }
Compress-Archive -Path $dist, $inst, 'c:\Users\NazaraX\Desktop\README_Furaya.txt' -DestinationPath $out -Force

$exeMB  = [Math]::Round((Get-Item $dist).Length / 1MB, 1)
$zipKB  = [Math]::Round((Get-Item $out).Length / 1MB, 1)
Write-Host "EXE:     $exeMB MB"
Write-Host "ZIP:     $zipKB MB -> $out"
Write-Host "Desktop: FurayaPromoEngine.exe + FurayaPromoEngine_Setup.zip + README"
