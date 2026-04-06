import random
import asyncio
import logging
import os
import signal
import sys

from telethon import TelegramClient, events
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
load_dotenv()


def _require_env(key: str) -> str:
    """Return the value of an env variable or exit with a helpful message."""
    value = os.getenv(key, "").strip()
    if not value:
        logger.error(
            "Missing required environment variable: %s  "
            "Please add it to your .env file.",
            key,
        )
        sys.exit(1)
    return value


def _optional_env_list(key: str, cast=str) -> list:
    """Return a list parsed from a comma-separated env variable.  Returns []
    if the variable is absent or empty."""
    raw = os.getenv(key, "").strip()
    if not raw:
        return []
    items = []
    for part in raw.split(","):
        part = part.strip()
        if part:
            try:
                items.append(cast(part))
            except ValueError:
                logger.warning("Could not parse '%s' from %s – skipping.", part, key)
    return items


API_ID = _require_env("API_ID")
API_HASH = _require_env("API_HASH")
PHONE_NUMBER = _require_env("PHONE_NUMBER")

TARGET_GROUP_IDS: list[int] = _optional_env_list("TARGET_GROUP_IDS", int)
CHANNEL_USERNAMES: list[str] = _optional_env_list("CHANNEL_USERNAMES", str)

try:
    MIN_TIME = int(os.getenv("MIN_TIME", "30"))
    MAX_TIME = int(os.getenv("MAX_TIME", "60"))
    if MIN_TIME > MAX_TIME:
        raise ValueError("MIN_TIME must not be greater than MAX_TIME")
except ValueError as exc:
    logger.error("Invalid MIN_TIME / MAX_TIME configuration: %s", exc)
    sys.exit(1)

if not TARGET_GROUP_IDS:
    logger.warning(
        "TARGET_GROUP_IDS is empty – no groups will receive forwarded messages."
    )
if not CHANNEL_USERNAMES:
    logger.warning(
        "CHANNEL_USERNAMES is empty – no channels are being monitored."
    )

# ---------------------------------------------------------------------------
# Telegram client
# ---------------------------------------------------------------------------
client = TelegramClient("userbot_session", API_ID, API_HASH)

message_queue: asyncio.Queue = asyncio.Queue()


# ---------------------------------------------------------------------------
# Message processing
# ---------------------------------------------------------------------------
async def process_message() -> None:
    """Continuously dequeue messages and forward them to all target groups."""
    while True:
        channel_username, message = await message_queue.get()
        message_id = message.id

        for group_id in TARGET_GROUP_IDS:
            try:
                await client.forward_messages(group_id, message)
                logger.info(
                    "Message %s forwarded from %s → group %s",
                    message_id,
                    channel_username,
                    group_id,
                )
            except Exception as exc:
                logger.error(
                    "Error forwarding message %s from %s to group %s: %s",
                    message_id,
                    channel_username,
                    group_id,
                    exc,
                )

        # Mark the current task as done *before* re-enqueueing for the next round
        message_queue.task_done()

        delay = random.randint(MIN_TIME, MAX_TIME)
        logger.info(
            "Next forward from %s scheduled in %s seconds.", channel_username, delay
        )
        await asyncio.sleep(delay)

        # Re-enqueue for periodic forwarding
        await message_queue.put((channel_username, message))


# ---------------------------------------------------------------------------
# Event handlers – registered properly to avoid closure issues
# ---------------------------------------------------------------------------
def register_handlers() -> None:
    """Register a NewMessage handler for every monitored channel."""

    for channel in CHANNEL_USERNAMES:

        async def _handler(event, _channel=channel):
            message = event.message
            logger.info("New message detected in channel: %s", _channel)
            await message_queue.put((_channel, message))

        client.add_event_handler(_handler, events.NewMessage(chats=channel))
        logger.info("Registered handler for channel: %s", channel)


# ---------------------------------------------------------------------------
# Utility: dump group/channel IDs the account belongs to
# ---------------------------------------------------------------------------
async def save_group_ids() -> None:
    """Write all group IDs the account can see to group_ids.txt."""
    dialogs = await client.get_dialogs()
    output_path = "group_ids.txt"
    count = 0
    with open(output_path, "w", encoding="utf-8") as fh:
        for dialog in dialogs:
            if dialog.is_group or dialog.is_channel:
                fh.write(f"Name: {dialog.name!r}, ID: {dialog.id}\n")
                count += 1
    logger.info("Saved %d group/channel IDs to %s", count, output_path)


# ---------------------------------------------------------------------------
# Graceful shutdown
# ---------------------------------------------------------------------------
_shutdown_event: asyncio.Event | None = None


def _handle_signal(sig, frame):  # noqa: ANN001
    logger.info("Received signal %s – shutting down…", sig)
    if _shutdown_event:
        _shutdown_event.set()


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
async def main() -> None:
    global _shutdown_event
    _shutdown_event = asyncio.Event()

    # Register OS signals for graceful shutdown (Unix-like only; Windows uses Ctrl+C)
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle_signal)
        except (OSError, ValueError):
            pass

    await client.start(PHONE_NUMBER)
    logger.info("Telegram client started successfully.")

    await save_group_ids()
    register_handlers()

    # Launch the queue processor as a background task
    processor = asyncio.create_task(process_message())

    logger.info(
        "Bot running – monitoring %d channel(s), forwarding to %d group(s).",
        len(CHANNEL_USERNAMES),
        len(TARGET_GROUP_IDS),
    )

    try:
        # Run until disconnected *or* a shutdown signal is received
        await asyncio.wait(
            [
                asyncio.ensure_future(client.run_until_disconnected()),
                asyncio.ensure_future(_shutdown_event.wait()),
            ],
            return_when=asyncio.FIRST_COMPLETED,
        )
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Stopping bot…")
        processor.cancel()
        await client.disconnect()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
