"""
core/tdlib_engine.py — Furaya v5.5
Fixed TDLib auth state machine using correct pytdbot API.
"""

import asyncio
import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable

logger = logging.getLogger(__name__)

# ─── DLL loader (Windows) ─────────────────────────────────────────────────────

def _load_tdjson_dll(dll_path: Path) -> Optional[str]:
    """Add DLL directory to Windows search path. Returns path string or None."""
    if sys.platform != "win32":
        return None
    dll_path = Path(dll_path)
    if not dll_path.exists():
        logger.warning(f"tdjson.dll not found at {dll_path}")
        return None
    try:
        os.add_dll_directory(str(dll_path.parent))
    except Exception as e:
        logger.warning(f"add_dll_directory failed: {e}")
    return str(dll_path)


# ─── TDLibEngine ──────────────────────────────────────────────────────────────

class TDLibEngine:
    """
    Single Telegram account client using pytdbot.
    Handles the full auth state machine: PhoneNumber → OTP → 2FA → Ready.
    """

    def __init__(
        self,
        phone_number: str,
        api_id: int,
        api_hash: str,
        database_dir: Path,
        tdlib_dll_path: Path,
        on_otp: Optional[Callable] = None,
        on_2fa: Optional[Callable] = None,
        log_cb: Optional[Callable] = None,
    ):
        self.phone_number = phone_number
        self.api_id = int(api_id)
        self.api_hash = str(api_hash)
        self.database_dir = Path(database_dir)
        self.tdlib_dll_path = Path(tdlib_dll_path)
        self.on_otp = on_otp
        self.on_2fa = on_2fa
        self.log_cb = log_cb or (lambda level, msg: logger.info(msg))

        self.client = None
        self._authorized = False
        self._auth_event = asyncio.Event()
        self._otp_future: Optional[asyncio.Future] = None
        self._2fa_future: Optional[asyncio.Future] = None
        self._connection_state = "unknown"
        self._failed = False
        self._fail_reason = ""

    def _log(self, level: str, msg: str):
        self.log_cb(level, f"[{self.phone_number}] {msg}")
        getattr(logger, level.lower(), logger.info)(msg)

    async def start(self) -> bool:
        """Start TDLib client and drive auth to completion. Returns True if authorized."""
        self.database_dir.mkdir(parents=True, exist_ok=True)

        # ── Placeholder credential guard ───────────────────────────────
        if str(self.api_id) == "12345678" or "abcdef" in self.api_hash.lower():
            self._log("ERROR", "❌ Placeholder API credentials detected! Get real ones from https://my.telegram.org/apps")
            return False

        dll_path_str = _load_tdjson_dll(self.tdlib_dll_path)

        try:
            from pytdbot import Client
        except ImportError as e:
            import traceback
            self._log("ERROR", f"pytdbot failed to load inside EXE: {e}\n{traceback.format_exc()}")
            return False

        # ── Derive database path (no colons on Windows) ───────────────
        safe_phone = self.phone_number.replace("+", "").replace(" ", "")
        db_dir = self.database_dir / f"tdlib_{safe_phone}"
        db_dir.mkdir(parents=True, exist_ok=True)

        client_kwargs = dict(
            api_id=self.api_id,
            api_hash=self.api_hash,
            database_encryption_key="furaya_v55",
            files_directory=str(db_dir / "files"),
        )
        if dll_path_str:
            client_kwargs["lib_path"] = dll_path_str

        try:
            self.client = Client(**client_kwargs)
        except Exception as e:
            self._log("ERROR", f"Failed to create TDLib client: {e}")
            return False

        # ── Auth handler ───────────────────────────────────────────────
        @self.client.on_updateAuthorizationState()
        async def _on_auth(client, update):
            try:
                state = update.get("authorization_state", {})
                state_type = state.get("@type", "").lower()
                self._log("INFO", f"Auth state: {state_type}")

                if "waittdlibparameters" in state_type:
                    # pytdbot handles this automatically
                    pass

                elif "waitphonenumber" in state_type:
                    self._log("INFO", f"Sending phone number: {self.phone_number}")
                    result = await client.setAuthenticationPhoneNumber(
                        phone_number=self.phone_number
                    )
                    if isinstance(result, dict) and result.get("@type", "").lower() == "error":
                        err = result.get("message", "Unknown error")
                        self._log("ERROR", f"Phone number rejected: {err}")
                        self._failed = True
                        self._fail_reason = err
                        self._auth_event.set()

                elif "waitcode" in state_type:
                    self._log("INFO", "Waiting for OTP code...")
                    if self.on_otp:
                        self._otp_future = asyncio.get_event_loop().create_future()
                        await self.on_otp(self.phone_number)
                        try:
                            code = await asyncio.wait_for(self._otp_future, timeout=300.0)
                            result = await client.checkAuthenticationCode(code=str(code))
                            if isinstance(result, dict) and result.get("@type", "").lower() == "error":
                                err = result.get("message", "Unknown error")
                                self._log("ERROR", f"OTP rejected: {err}")
                                self._failed = True
                                self._fail_reason = err
                                self._auth_event.set()
                        except asyncio.TimeoutError:
                            self._log("ERROR", "OTP timed out (5 min)")
                            self._failed = True
                            self._fail_reason = "OTP timeout"
                            self._auth_event.set()
                    else:
                        self._log("ERROR", "No OTP callback set")
                        self._failed = True
                        self._auth_event.set()

                elif "waitpassword" in state_type:
                    self._log("INFO", "Waiting for 2FA password...")
                    if self.on_2fa:
                        self._2fa_future = asyncio.get_event_loop().create_future()
                        await self.on_2fa(self.phone_number)
                        try:
                            pwd = await asyncio.wait_for(self._2fa_future, timeout=300.0)
                            result = await client.checkAuthenticationPassword(password=str(pwd))
                            if isinstance(result, dict) and result.get("@type", "").lower() == "error":
                                err = result.get("message", "Unknown error")
                                self._log("ERROR", f"2FA rejected: {err}")
                                self._failed = True
                                self._fail_reason = err
                                self._auth_event.set()
                        except asyncio.TimeoutError:
                            self._log("ERROR", "2FA timed out (5 min)")
                            self._failed = True
                            self._fail_reason = "2FA timeout"
                            self._auth_event.set()
                    else:
                        self._log("ERROR", "No 2FA callback set")
                        self._failed = True
                        self._auth_event.set()

                elif "ready" in state_type:
                    self._authorized = True
                    self._log("INFO", "✅ Authorized successfully!")
                    self._auth_event.set()

                elif "closed" in state_type or "closepending" in state_type:
                    if not self._authorized:
                        self._log("WARN", "TDLib closed before authorization")
                        self._failed = True
                        self._auth_event.set()

            except Exception as ex:
                self._log("ERROR", f"Auth handler exception: {ex}\n{traceback.format_exc()}")
                self._failed = True
                self._auth_event.set()

        # ── Connection state tracking ──────────────────────────────────
        @self.client.on_updateConnectionState()
        async def _on_conn(client, update):
            try:
                state = update.get("state", {}).get("@type", "Unknown")
                self._connection_state = state
                self._log("INFO", f"Connection: {state}")
            except Exception:
                pass

        # ── Start client (non-blocking) ────────────────────────────────
        try:
            self._log("INFO", "Starting TDLib client...")
            await self.client.start(wait_login=False)
        except Exception as e:
            self._log("ERROR", f"client.start() failed: {e}\n{traceback.format_exc()}")
            return False

        # ── Wait for auth with connection heartbeat ────────────────────
        start_time = asyncio.get_event_loop().time()
        timeout = 120.0

        while not self._auth_event.is_set():
            try:
                await asyncio.wait_for(
                    asyncio.shield(self._auth_event.wait()),
                    timeout=15.0
                )
            except asyncio.TimeoutError:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    self._log("ERROR", f"Login timeout after {timeout}s")
                    break
                if "Connecting" in self._connection_state:
                    self._log("WARN", f"⏳ Still connecting... ({elapsed:.0f}s elapsed)")
                elif "WaitingForNetwork" in self._connection_state:
                    self._log("ERROR", "❌ No network — check your internet connection")
                    break
                else:
                    self._log("INFO", f"⏳ Waiting for Telegram... ({elapsed:.0f}s)")

        return self._authorized

    # ── Public helpers for GUI submissions ─────────────────────────────

    def submit_otp(self, code: str):
        """Called by GUI when user enters OTP."""
        if self._otp_future and not self._otp_future.done():
            self._otp_future.set_result(code.strip())

    def submit_2fa(self, password: str):
        """Called by GUI when user enters 2FA password."""
        if self._2fa_future and not self._2fa_future.done():
            self._2fa_future.set_result(password)

    # ── Messaging ─────────────────────────────────────────────────────

    async def send_message(self, chat_id: int, text: str) -> bool:
        """Send plain text message to a chat. Returns True on success."""
        if not self.client or not self._authorized:
            return False
        try:
            from pytdbot import types as td_types
            result = await self.client.sendMessage(
                chat_id=chat_id,
                input_message_content=td_types.InputMessageText(
                    text=td_types.FormattedText(text=text, entities=[])
                )
            )
            return not (hasattr(result, "error") and result.error)
        except Exception as e:
            self._log("ERROR", f"send_message failed: {e}")
            return False

    # ── Group discovery & joining ──────────────────────────────────────

    async def search_groups(self, keyword: str, limit: int = 30) -> List[Dict]:
        """Search public Telegram groups/channels by keyword."""
        if not self.client or not self._authorized:
            return []
        try:
            result = await self.client.searchPublicChats(query=keyword)
            chats = []
            if hasattr(result, "chat_ids"):
                for cid in result.chat_ids[:limit]:
                    info = await self.get_chat_info(cid)
                    if info:
                        chats.append(info)
            return chats
        except Exception as e:
            self._log("ERROR", f"search_groups failed: {e}")
            return []

    async def get_chat_info(self, chat_id: int) -> Optional[Dict]:
        """Get basic info about a chat."""
        try:
            result = await self.client.getChat(chat_id=chat_id)
            if hasattr(result, "error") and result.error:
                return None
            return {
                "id": result.id,
                "title": getattr(result, "title", ""),
                "type": type(result.type).__name__ if hasattr(result, "type") else "",
                "member_count": getattr(result, "member_count", 0),
                "username": getattr(getattr(result, "usernames", None), "editable_username", ""),
            }
        except Exception:
            return None

    async def join_chat(self, identifier: str) -> bool:
        """Join a public chat by username or invite link."""
        if not self.client or not self._authorized:
            return False
        try:
            if identifier.startswith("https://t.me/+") or identifier.startswith("https://t.me/joinchat"):
                result = await self.client.joinChatByInviteLink(invite_link=identifier)
            else:
                username = identifier.lstrip("@")
                chat = await self.client.searchPublicChat(username=username)
                if hasattr(chat, "error") and chat.error:
                    return False
                result = await self.client.joinChat(chat_id=chat.id)
            return not (hasattr(result, "error") and result.error)
        except Exception as e:
            self._log("ERROR", f"join_chat({identifier}) failed: {e}")
            return False

    async def get_me(self) -> Optional[Dict]:
        """Get the current user info."""
        if not self.client:
            return None
        try:
            me = await self.client.getMe()
            if hasattr(me, "error") and me.error:
                return None
            return {
                "id": me.id,
                "first_name": getattr(me, "first_name", ""),
                "username": getattr(getattr(me, "usernames", None), "editable_username", ""),
                "phone": getattr(me, "phone_number", self.phone_number),
            }
        except Exception:
            return None

    async def stop(self):
        """Gracefully close the TDLib client."""
        if self.client:
            try:
                await self.client.stop()
            except Exception:
                pass
            self.client = None
        self._authorized = False
