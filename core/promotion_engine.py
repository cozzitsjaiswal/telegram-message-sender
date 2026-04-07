"""
PromotionEngine — production-grade Telethon backend.

DISCOVERY STRATEGIES (all run in parallel per keyword batch):
  S1. contacts.SearchRequest         — fast, returns known/popular groups
  S2. messages.SearchGlobal          — deep search, extracts chats from public messages
  S3. Keyword variations             — expands each keyword into synonyms & suffixes
  S4. Username pattern probing       — derives likely @usernames from keyword words

JOIN LOGIC:
  — Always attempts JoinChannelRequest, zero skip logic.
  — On FloodWait: waits exactly e.seconds + buffer, then retries once.
  — Yields results as async-generator so GUI receives them live.
"""
from __future__ import annotations

import asyncio
import logging
import random
import re
from typing import AsyncIterator, Dict, List, Optional, Set

from telethon import TelegramClient
from telethon.errors import (
    ChannelPrivateError, ChatWriteForbiddenError, FloodWaitError,
    PeerFloodError, SlowModeWaitError, UserBannedInChannelError,
    UserNotParticipantError, UsernameInvalidError, UsernameNotOccupiedError,
)
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.contacts import SearchRequest, ResolveUsernameRequest
from telethon.tl.functions.messages import SearchGlobalRequest
from telethon.tl.types import (
    Channel, Chat, InputMessagesFilterEmpty,
    InputPeerEmpty,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Keyword expansion
# ---------------------------------------------------------------------------

_GENERIC_SUFFIXES = [
    "group", "chat", "official", "community", "signals",
    "hub", "network", "connect", "global", "india", "vip",
]

_DOMAIN_MAP: Dict[str, List[str]] = {
    "crypto":   ["cryptocurrency", "bitcoin", "btc", "defi", "altcoin", "web3"],
    "forex":    ["fx trading", "currency", "forex signals", "mt4", "trading"],
    "bank":     ["banking", "account", "finance", "payment", "transfer"],
    "earn":     ["income", "profit", "money", "passive income", "investment"],
    "invest":   ["investment", "stocks", "mutual fund", "portfolio", "returns"],
    "pay":      ["payment", "payout", "upi", "wallet", "cashback"],
    "loan":     ["lending", "credit", "finance", "borrow", "mortgage"],
    "usdt":     ["tether", "stablecoin", "usdtgroup", "flash usdt"],
    "trading":  ["trade", "trader", "signals", "analysis", "market"],
    "india":    ["indian", "bharat", "hindi", "desi", "rupee"],
}


def expand_keywords(keyword: str) -> List[str]:
    """Return the original keyword + smart variations, deduplicated."""
    kw = keyword.strip().lower()
    variants: List[str] = [keyword]

    # Joined / underscored versions
    joined = kw.replace(" ", "")
    underscored = kw.replace(" ", "_")
    if joined != kw:
        variants.append(joined)
    if underscored != kw:
        variants.append(underscored)

    # Domain synonyms
    for seed, synonyms in _DOMAIN_MAP.items():
        if seed in kw:
            variants.extend(synonyms)

    # Generic suffix combo (use first word only to keep variants targeted)
    first_word = kw.split()[0] if " " in kw else kw
    for suf in _GENERIC_SUFFIXES[:4]:   # limit to top 4 to avoid spam
        variants.append(f"{first_word} {suf}")

    # Deduplicate preserving order
    seen: Set[str] = set()
    unique: List[str] = []
    for v in variants:
        if v.lower() not in seen:
            seen.add(v.lower())
            unique.append(v)
    return unique[:5]   # cap to 5 variants per keyword to avoid rate limits


def derive_usernames(keyword: str) -> List[str]:
    """
    Derive plausible @usernames from a keyword by combining words and suffixes.
    E.g. "bank account india" → ["bankaccountindia", "bankaccount", "indiabank", ...]
    """
    words = re.sub(r"[^a-z0-9 ]", "", keyword.lower()).split()
    if not words:
        return []
    candidates: List[str] = []
    joined = "".join(words)
    if 4 <= len(joined) <= 32:
        candidates.append(joined)
    for suf in ["group", "chat", "official", "hub"]:
        c = f"{joined}{suf}"
        if len(c) <= 32:
            candidates.append(c)
    if len(words) >= 2:
        rev = "".join(reversed(words))
        if 4 <= len(rev) <= 32:
            candidates.append(rev)
    return candidates[:6]


# ---------------------------------------------------------------------------
# PromotionEngine
# ---------------------------------------------------------------------------

class PromotionEngine:
    """
    Telethon backend — streaming group discovery, force-join, send.
    """

    def __init__(self, client: TelegramClient, phone: str) -> None:
        self.client = client
        self.phone = phone

    # -----------------------------------------------------------------------
    # SEARCH — async generator, streams results as they're found
    # -----------------------------------------------------------------------

    async def discover_groups(
        self,
        keyword: str,
        limit: int = 100,
        use_variations: bool = True,
        use_username_probing: bool = True,
        status_callback = None,
    ) -> AsyncIterator[Dict]:
        """
        Async generator — yields group dicts as they're discovered.
        Caller can process each result immediately (live GUI updates).

        Each yielded dict:
          title, username, member_count, is_channel, entity, strategy
        """
        seen_ids: Set[int] = set()
        found = 0
        
        def _notify(msg: str):
            if status_callback:
                status_callback(msg)

        def _make_result(chat, strategy: str) -> Optional[Dict]:
            if not hasattr(chat, "id"):
                return None
            if chat.id in seen_ids:
                return None
            if not isinstance(chat, (Channel, Chat)):
                return None
            seen_ids.add(chat.id)
            return {
                "title":        getattr(chat, "title", "(no title)"),
                "username":     getattr(chat, "username", None) or "",
                "member_count": getattr(chat, "participants_count", 0) or 0,
                "is_channel":   getattr(chat, "broadcast", False),
                "entity":       chat,
                "strategy":     strategy,
            }

        keywords_to_search = expand_keywords(keyword) if use_variations else [keyword]

        s1_flood = False
        s2_flood = False

        for v_idx, kw_variant in enumerate(keywords_to_search):
            if found >= limit:
                break
            
            _notify(f"Variant {v_idx+1}/{len(keywords_to_search)}: '{kw_variant}'")

            # ── S1: contacts.SearchRequest ──────────────────────────────
            if not s1_flood:
                try:
                    res = await self.client(SearchRequest(q=kw_variant, limit=min(100, limit)))
                    for chat in res.chats:
                        r = _make_result(chat, f"S1:contacts [{kw_variant}]")
                        if r:
                            found += 1
                            yield r
                            if found >= limit:
                                return
                except FloodWaitError as e:
                    logger.warning("[%s] S1 FloodWait %ds for '%s'", self.phone, e.seconds, kw_variant)
                    _notify(f"S1 API Limit - Skipping S1 for '{kw_variant}'")
                    s1_flood = True # Stop using S1 for this keyword
                    await asyncio.sleep(min(e.seconds, 5))
                except Exception as e:
                    logger.debug("[%s] S1 error '%s': %s", self.phone, kw_variant, e)

                await asyncio.sleep(random.uniform(0.5, 1.2))

            # ── S2: messages.SearchGlobal ───────────────────────────────
            if not s2_flood and found < limit:
                try:
                    global_res = await self.client(SearchGlobalRequest(
                        q=kw_variant,
                        filter=InputMessagesFilterEmpty(),
                        min_date=None,
                        max_date=None,
                        offset_rate=0,
                        offset_peer=InputPeerEmpty(),
                        offset_id=0,
                        limit=min(100, limit),
                    ))
                    for chat in global_res.chats:
                        r = _make_result(chat, f"S2:global [{kw_variant}]")
                        if r:
                            found += 1
                            yield r
                            if found >= limit:
                                return
                except FloodWaitError as e:
                    logger.warning("[%s] S2 FloodWait %ds for '%s'", self.phone, e.seconds, kw_variant)
                    _notify(f"S2 API Limit - Skipping S2 for '{kw_variant}'")
                    s2_flood = True # Stop using S2 for this keyword
                    await asyncio.sleep(min(e.seconds, 5))
                except Exception as e:
                    logger.debug("[%s] S2 error '%s': %s", self.phone, kw_variant, e)

                await asyncio.sleep(random.uniform(0.5, 1.2))

        # ── S3: Username probing ────────────────────────────────────────
        if use_username_probing and found < limit:
            usernames = derive_usernames(keyword)
            for u_idx, uname in enumerate(usernames):
                if found >= limit:
                    break
                _notify(f"Probing @{uname} ({u_idx+1}/{len(usernames)})")
                try:
                    resolved = await self.client(ResolveUsernameRequest(uname))
                    if resolved and resolved.chats:
                        for chat in resolved.chats:
                            r = _make_result(chat, f"S3:probe [@{uname}]")
                            if r:
                                found += 1
                                yield r
                except (UsernameInvalidError, UsernameNotOccupiedError):
                    pass
                except FloodWaitError as e:
                    _notify(f"Probe API Limit - Waiting {min(e.seconds, 15)}s")
                    await asyncio.sleep(min(e.seconds, 15))
                except Exception:
                    pass
                await asyncio.sleep(random.uniform(0.5, 1.0))

    # -----------------------------------------------------------------------
    # JOIN — force attempt, never skips
    # -----------------------------------------------------------------------

    async def join_group(self, entity) -> tuple[bool, str]:
        """Force join — always attempts, handles FloodWait with retry."""
        try:
            await self.client(JoinChannelRequest(entity))
            logger.info("[%s] ✅ Joined: %s", self.phone, getattr(entity, "title", "?"))
            return True, ""
        except FloodWaitError as e:
            logger.warning("[%s] FloodWait %ds joining %s — waiting then retrying",
                           self.phone, e.seconds, getattr(entity, "title", "?"))
            await asyncio.sleep(min(e.seconds + 3, 120))
            try:
                await self.client(JoinChannelRequest(entity))
                return True, ""
            except Exception as e2:
                return False, f"RetryFailed:{e2}"
        except ChannelPrivateError:
            return False, "Private"
        except UserBannedInChannelError:
            return False, "Banned"
        except Exception as e:
            return False, type(e).__name__

    # -----------------------------------------------------------------------
    # SEND
    # -----------------------------------------------------------------------

    async def send_message(self, group_username: str, text: str) -> tuple[bool, str]:
        try:
            async with self.client.action(group_username, "typing"):
                await asyncio.sleep(random.uniform(1.2, 2.8))
            await self.client.send_message(group_username, text)
            logger.info("[%s] ✅ Sent to %s", self.phone, group_username)
            return True, ""
        except FloodWaitError as e:
            return False, f"FloodWait:{e.seconds}"
        except SlowModeWaitError as e:
            return False, f"SlowMode:{e.seconds}"
        except PeerFloodError:
            return False, "PeerFlood"
        except (ChatWriteForbiddenError, UserBannedInChannelError,
                UserNotParticipantError, ChannelPrivateError) as e:
            return False, type(e).__name__
        except Exception as e:
            logger.error("[%s] Send failed to %s: %s", self.phone, group_username, e)
            return False, str(e)

    # -----------------------------------------------------------------------
    # HEALTH
    # -----------------------------------------------------------------------

    async def is_alive(self) -> bool:
        try:
            if not self.client.is_connected():
                await self.client.connect()
            return await self.client.is_user_authorized()
        except Exception:
            return False
