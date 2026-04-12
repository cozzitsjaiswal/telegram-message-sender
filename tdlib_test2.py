import logging
from pytdbot import Client

logging.basicConfig(level=logging.INFO)

try:
    app = Client(
        api_id=1,
        api_hash="foo",
        database_encryption_key="secret",
        files_directory="./tdlib_files"
    )
    print("pytdbot initialized successfully! library=", app.lib_path)
    app.start()
except Exception as e:
    import traceback
    traceback.print_exc()
