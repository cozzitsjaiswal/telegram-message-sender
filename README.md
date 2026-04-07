
# Telegram Promotion Bot

A Windows-friendly GUI application for automated Telegram promotion across multiple accounts. Built with [Telethon](https://docs.telethon.dev/) and [PyQt5](https://pypi.org/project/PyQt5/).

---

## Features

| Feature | Details |
|---|---|
| 👤 **Multi-account management** | Add unlimited Telegram user accounts; login via GUI OTP flow |
| 🔄 **Account rotation** | Round-robin rotation; auto-skips accounts in flood cooldown or banned |
| 📢 **10 message templates** | Rotating promotional messages, varied in tone and length |
| ⏱️ **Human-like delays** | Randomised delay between `MIN` and `MAX` seconds per message |
| 🛡️ **Error handling** | FloodWaitError → cooldown; banned errors → account marked inactive; auto-retry on network errors |
| 📋 **Live log tab** | Colour-coded, timestamped log (info / warning / error / success) |
| 📂 **Target file loading** | Load group usernames from a plain `.txt` file |
| 💾 **Session persistence** | Telethon session files keep accounts logged in across restarts |

---

## Project Structure

```
telegram-message-sender/
├── main.py                    # Entry point (qasync + PyQt5)
├── requirements.txt
├── .env.example
├── core/
│   ├── account.py             # Account dataclass & status
│   ├── account_manager.py     # Multi-account storage & rotation
│   ├── messages.py            # 10 message templates
│   ├── scraper.py             # Group target loader
│   └── promotion_engine.py    # Main promotion loop
└── gui/
    ├── styles.py              # Dark theme stylesheet
    ├── main_window.py         # Main window + tab layout
    ├── accounts_tab.py        # Accounts table + login flow
    ├── add_account_dialog.py  # Add account dialog
    ├── otp_dialog.py          # OTP / 2FA login dialog
    ├── promotion_tab.py       # Promotion controls
    └── log_tab.py             # Log display
```

---

## Installation

```bash
git clone https://github.com/yagizharman/telegram-message-sender.git
cd telegram-message-sender
pip install -r requirements.txt
```

---

## Usage

```bash
python main.py
```

### First-time setup (inside the GUI)

1. Go to the **Accounts** tab → click **Add Account**
2. Enter your phone number, API ID and API Hash from [my.telegram.org](https://my.telegram.org)
3. Click **Login** → enter the OTP Telegram sends to your phone
4. Repeat for all accounts you want to rotate
5. Go to the **Promotion** tab
6. Enter target group usernames (one per line) or load a `.txt` file
7. Set Min/Max delay in seconds
8. Click **▶ Start Promotion**

---

## Build as a standalone EXE

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "TelegramBot" main.py
```

The EXE is generated in `dist/`. Copy your `accounts.json` and `.session` files alongside it on deployment.

---

## Compliance

- This is a **userbot** (operates as a normal Telegram user, not a bot account).
- Never share your `.session` files or `accounts.json`.
- Comply with [Telegram's Terms of Service](https://telegram.org/tos) and local laws.
- Use responsibly — avoid spam and abuse.
