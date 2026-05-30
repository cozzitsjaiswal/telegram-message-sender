# hooks/hook-pytdbot.py
# Ensures pytdbot and all its runtime metadata deps are fully bundled.
from PyInstaller.utils.hooks import collect_all, copy_metadata, collect_submodules

datas, binaries, hiddenimports = collect_all('pytdbot')

# aio_pika checks importlib.metadata for its own version at startup
for pkg in ['aio-pika', 'aiormq', 'pamqp', 'yarl', 'multidict']:
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

hiddenimports += collect_submodules('aio_pika')
hiddenimports += collect_submodules('aiormq')
