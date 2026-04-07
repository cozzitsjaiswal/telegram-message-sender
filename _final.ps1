Copy-Item 'c:\Users\NazaraX\telegram-message-sender\dist\TelegramPromotionBot.exe' 'c:\Users\NazaraX\Desktop\TelegramPromotionBot.exe' -Force
$exeSize = [Math]::Round((Get-Item 'c:\Users\NazaraX\Desktop\TelegramPromotionBot.exe').Length / 1MB, 1)
Write-Host "EXE: $exeSize MB"

# Rebuild ZIP
$src = 'c:\Users\NazaraX\telegram-message-sender'
$out = 'c:\Users\NazaraX\Desktop\telegram-promotion-bot.zip'
$items = @(
    "$src\core",
    "$src\gui",
    "$src\main.py",
    "$src\requirements.txt",
    "$src\.env.example",
    "$src\.gitignore",
    "$src\README.md"
)
if (Test-Path $out) { Remove-Item $out }
Compress-Archive -Path $items -DestinationPath $out -Force
$zipSize = [Math]::Round((Get-Item $out).Length / 1KB, 1)
Write-Host "ZIP: $zipSize KB"
