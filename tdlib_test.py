import logging
from telegram.client import Telegram

logging.basicConfig(level=logging.INFO)

# python-telegram wrapper handles downloading the correct libtdjson binary
tg = Telegram(
    api_id=1,        # dummy id
    api_hash='foo',  # dummy hash
    phone='+123456789',
    database_encryption_key='secret'
)

print("TDLib loaded successfully!")
