"""
core/advanced_scraper.py

Production-grade Telegram scraping engine for Furaya Campaign System.
- Scrapes channel messages, group members, and global messages.
- Obeys strict API rate limits (100 msgs/min per account).
- Handles FloodWaitError with automatic pause and single retry.
- Dumps data to Path.home() / "FurayaPromoEngine" / "scraped".
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Dict, List, Any

from telethon import TelegramClient
from telethon.errors import FloodWaitError
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import InputMessagesFilterEmpty, InputPeerEmpty, User, Channel

logger = logging.getLogger(__name__)


class AdvancedScraper:
    """
    Handles robust scraping operations across Telegram channels/groups.
    """

    def __init__(self, client: TelegramClient, phone: str):
        self.client = client
        self.phone = phone
        self.data_dir = Path.home() / "FurayaPromoEngine" / "scraped"
        self.data_dir.mkdir(parents=True, exist_ok=True)

    # -------------------------------------------------------------------------
    # 1. Scrape Channel Messages
    # -------------------------------------------------------------------------
    async def scrape_channel_messages(
        self,
        channel_id: str | int,
        limit: int = 1000,
        since_date: Optional[datetime] = None,
        on_progress: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrape messages from a specific channel/chat, respecting 100 msg/min limits.
        """
        output_file = self.data_dir / f"{self.phone}_msgs_{channel_id}.json"
        results = []
        fetched = 0
        retried = False
        last_id = 0

        if on_progress:
            on_progress(0, limit, f"Starting message scrape for {channel_id}...")

        while fetched < limit:
            try:
                # Add human-like random jitter before requesting chunks
                await asyncio.sleep(random.uniform(1.2, 3.5))
                
                # Fetch chunk
                # Telethon naturally paginates, we use offset_id for manual pagination
                # to safely resume after a FloodWaitError.
                chunk = await self.client.get_messages(
                    channel_id,
                    limit=min(100, limit - fetched),
                    offset_id=last_id,
                    offset_date=since_date
                )
                
                if not chunk:
                    break   # No more messages available

                for msg in chunk:
                    results.append({
                        "id": msg.id,
                        "date": msg.date.isoformat() if msg.date else None,
                        "text": msg.message,
                        "views": getattr(msg, 'views', 0),
                        "forwards": getattr(msg, 'forwards', 0)
                    })
                    fetched += 1
                    last_id = msg.id

                retried = False  # Reset retry flag on success
                self._save_json(output_file, results)

                if on_progress:
                    on_progress(fetched, limit, f"Scraped {fetched} messages...")

                # 100 msgs/min limit enforcement
                if fetched < limit and len(chunk) > 0:
                    logger.info(f"[{self.phone}] Yielding 60 seconds to respect 100msgs/min limit.")
                    if on_progress:
                        on_progress(fetched, limit, "Sleeping 60s for rate limit...")
                    await asyncio.sleep(60)

            except FloodWaitError as e:
                if retried:
                    logger.error(f"[{self.phone}] Double FloodWait! Aborting message scrape.")
                    break
                
                wait_time = e.seconds + 5
                logger.warning(f"[{self.phone}] FloodWait {e.seconds}s. Sleeping {wait_time}s.")
                if on_progress:
                    on_progress(fetched, limit, f"API Rate Limit. Waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                retried = True
                
            except Exception as e:
                logger.error(f"[{self.phone}] Error scraping messages: {e}")
                break

        if on_progress:
            on_progress(fetched, limit, f"✅ Scrape complete. Saved to {output_file.name}")
            
        return results

    # -------------------------------------------------------------------------
    # 2. Scrape Group Members
    # -------------------------------------------------------------------------
    async def scrape_group_members(
        self,
        group_id: str | int,
        max_members: int = 5000,
        on_progress: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Scrapes a list of users from a Telegram group. Requires Admin/visibility rights
        depending on group privacy settings.
        """
        output_file = self.data_dir / f"{self.phone}_members_{group_id}.json"
        members = []
        fetched = 0
        retried = False
        
        if on_progress:
            on_progress(0, max_members, f"Scraping members from {group_id}...")

        try:
            # We use iter_participants. To handle FloodWaits cleanly without losing state,
            # we run it until completion or error. It fetches roughly 200 per chunk anyway.
            # Telethon abstracts the offset hashes.
            iterator = self.client.iter_participants(group_id, limit=max_members)
            
            while fetched < max_members:
                await asyncio.sleep(random.uniform(1.0, 3.0))
                
                try:
                    # Fetch one user. Telethon caches chunks, so this doesn't ping API 5000 times
                    user = await iterator.__anext__()
                    data = {
                        "id": user.id,
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "is_premium": user.premium,
                        "bot": user.bot
                    }
                    members.append(data)
                    fetched += 1
                    
                    if fetched % 100 == 0:
                        self._save_json(output_file, members)
                        if on_progress:
                            on_progress(fetched, max_members, f"Fetched {fetched} members...")
                            
                except StopAsyncIteration:
                    break   # End of list
                
                except FloodWaitError as e:
                    if retried:
                        break
                    wait_time = e.seconds + 5
                    logger.warning(f"[{self.phone}] FloodWait {e.seconds}s fetching members.")
                    if on_progress:
                        on_progress(fetched, max_members, f"FloodWait. Sleeping {wait_time}s...")
                    await asyncio.sleep(wait_time)
                    retried = True

        except Exception as e:
            logger.error(f"[{self.phone}] Member scrape error: {e}")
            
        self._save_json(output_file, members)
        
        if on_progress:
            on_progress(fetched, max_members, f"✅ Member scrape complete. ({fetched} users)")
            
        return members

    # -------------------------------------------------------------------------
    # 3. Global Message Search
    # -------------------------------------------------------------------------
    async def search_global(
        self,
        query: str,
        limit: int = 500,
        on_progress: Optional[Callable[[int, int, str], None]] = None
    ) -> List[Dict[str, Any]]:
        """
        Searches ALL of public Telegram indexed messages for a particular keyword.
        Respects the 100/min cap strictly by batching.
        """
        safe_query = "".join(c for c in query if c.isalnum() or c == " ").strip()
        output_file = self.data_dir / f"{self.phone}_global_{safe_query.replace(' ', '_')}.json"
        
        results = []
        fetched = 0
        retried = False
        offset_id = 0
        
        if on_progress:
            on_progress(0, limit, f"Global search for '{query}'...")

        while fetched < limit:
            try:
                await asyncio.sleep(random.uniform(2.0, 4.0))

                req = SearchGlobalRequest(
                    q=query,
                    filter=InputMessagesFilterEmpty(),
                    min_date=None,
                    max_date=None,
                    offset_rate=0,
                    offset_peer=InputPeerEmpty(),
                    offset_id=offset_id,
                    limit=min(100, limit - fetched)
                )
                
                res = await self.client(req)
                if not res.messages:
                    break

                for msg in res.messages:
                    # Extract channel info if available
                    chat_uname = None
                    if hasattr(msg, "peer_id"):
                        for chat in res.chats:
                            if hasattr(chat, "id") and chat.id == getattr(msg.peer_id, "channel_id", 0):
                                chat_uname = getattr(chat, "username", None)
                                break
                    
                    results.append({
                        "id": msg.id,
                        "date": msg.date.isoformat() if msg.date else None,
                        "text": msg.message,
                        "source_username": chat_uname
                    })
                    fetched += 1
                    offset_id = msg.id

                retried = False
                self._save_json(output_file, results)
                
                if on_progress:
                    on_progress(fetched, limit, f"Found {fetched} global hits...")

                # 100 msgs/min limit
                if fetched < limit and len(res.messages) > 0:
                    logger.info(f"[{self.phone}] Sleeping 60s to respect global search limits.")
                    if on_progress:
                        on_progress(fetched, limit, "Sleeping 60s for rate limit...")
                    await asyncio.sleep(60)

            except FloodWaitError as e:
                if retried:
                    break
                wait_time = e.seconds + 5
                logger.warning(f"[{self.phone}] Global Search FloodWait! Sleeping {wait_time}s.")
                if on_progress:
                    on_progress(fetched, limit, f"Rate Limit. Paused for {wait_time}s...")
                await asyncio.sleep(wait_time)
                retried = True
            
            except Exception as e:
                logger.error(f"[{self.phone}] Global search error: {e}")
                break

        if on_progress:
            on_progress(fetched, limit, f"✅ Global search complete. ({fetched} found)")

        return results

    # -------------------------------------------------------------------------
    # Helper
    # -------------------------------------------------------------------------
    def _save_json(self, path: Path, data: Any) -> None:
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to write JSON {path}: {e}")

# =========================================================================
# Example Usage:
# =========================================================================
# async def main():
#     client = ... # Authorized TelegramClient mapping to account_manager
#     scraper = AdvancedScraper(client, "+1234567890")
#
#     def gui_cb(curr, total, msg):
#         print(f"[{curr}/{total}] {msg}")
#
#     # Target 1000 messages from a group, enforcing a 60s sleep every 100 msgs
#     await scraper.scrape_channel_messages("my_favorite_group", limit=1000, on_progress=gui_cb)
#
#     # Pull 5000 users from a local group
#     await scraper.scrape_group_members("local_networking", max_members=5000, on_progress=gui_cb)
#
#     # Search index globally
#     await scraper.search_global("crypto signals", limit=500, on_progress=gui_cb)
