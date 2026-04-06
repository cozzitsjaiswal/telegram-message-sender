
# Telegram Message Forwarding Bot

A Telegram userbot that monitors source channels and automatically forwards new messages to target groups at randomised intervals. Built with [Telethon](https://docs.telethon.dev/).

## Features

- 📡 Monitor multiple source channels simultaneously
- 📨 Forward messages to multiple target groups
- ⏱️ Randomised delay between forwards (configurable `MIN_TIME` / `MAX_TIME`)
- 📝 Structured logging to both console and `bot.log`
- 🔄 Periodic re-forwarding: each new message is re-queued and forwarded again after the delay
- 🛡️ Start-up validation for all required environment variables
- 🗂️ Automatically writes discoverable group IDs to `group_ids.txt` on start
- 🛑 Graceful shutdown on `Ctrl+C` / `SIGTERM`

## Requirements

- Python 3.10+
- A Telegram account
- A Telegram **API ID** and **API Hash** – get them from [my.telegram.org](https://my.telegram.org)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yagizharman/telegram-message-sender.git
   cd telegram-message-sender
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Copy the example env file and fill it in:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your credentials (see [Configuration](#configuration) below).

## Configuration

All settings live in the `.env` file. Use `.env.example` as a template.

| Variable | Required | Description |
|---|---|---|
| `API_ID` | ✅ | Telegram API ID from my.telegram.org |
| `API_HASH` | ✅ | Telegram API Hash from my.telegram.org |
| `PHONE_NUMBER` | ✅ | Your phone number (international format, e.g. `+1234567890`) |
| `TARGET_GROUP_IDS` | ✅* | Comma-separated list of target group IDs |
| `CHANNEL_USERNAMES` | ✅* | Comma-separated channel usernames to monitor (without `@`) |
| `MIN_TIME` | ✅ | Minimum seconds between forwards (default `30`) |
| `MAX_TIME` | ✅ | Maximum seconds between forwards (default `60`) |

*Optional at startup, but the bot won't forward anything without them.

> **Tip**: If you don't know your group IDs, run the bot once – it will write all discoverable groups to **`group_ids.txt`** automatically.

## Usage

```bash
python main.py
```

On first run, Telethon will prompt you to authenticate with your phone number and a one-time code sent by Telegram. A `userbot_session.session` file is created so you only need to do this once.

## File Overview

```
telegram-message-sender/
├── main.py            # Main bot logic
├── requirements.txt   # Python dependencies
├── .env.example       # Environment variable template
├── .gitignore
└── README.md
```

## Notes

- This is a **userbot** (runs as a regular Telegram user, not a bot account). Make sure you comply with [Telegram's ToS](https://telegram.org/tos).
- Keep your `.env` file private – it contains sensitive credentials.
- The `userbot_session.session` file stores your login. Do not share it.
