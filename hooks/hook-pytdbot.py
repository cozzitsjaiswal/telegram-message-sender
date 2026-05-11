# hook-pytdbot.py
# PyInstaller hook for pytdbot — ensures all runtime dependencies are collected.
from PyInstaller.utils.hooks import collect_all

# Collect everything from pytdbot itself
datas, binaries, hiddenimports = collect_all("pytdbot")

# Explicitly include aio_pika and its dependencies (pytdbot requires them at top-level)
_aio_datas, _aio_bins, _aio_hidden = collect_all("aio_pika")
_aiormq_datas, _aiormq_bins, _aiormq_hidden = collect_all("aiormq")
_pamqp_datas, _pamqp_bins, _pamqp_hidden = collect_all("pamqp")

datas.extend(_aio_datas)
datas.extend(_aiormq_datas)
datas.extend(_pamqp_datas)

binaries.extend(_aio_bins)
binaries.extend(_aiormq_bins)
binaries.extend(_pamqp_bins)

hiddenimports.extend(_aio_hidden)
hiddenimports.extend(_aiormq_hidden)
hiddenimports.extend(_pamqp_hidden)
