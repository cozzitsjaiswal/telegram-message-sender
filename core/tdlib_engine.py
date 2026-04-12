"""
core/tdlib_engine.py
Production TDLib client with full async support for PyQt5 + qasync
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime

from pytdbot import Client, types
TDLibError = Exception

logger = logging.getLogger(__name__)


class TDLibEngine:
    """Single TDLib client with automatic state machine and Qt callbacks"""
    
    def __init__(
        self,
        phone_number: str,
        api_id: int,
        api_hash: str,
        database_dir: Path,
        tdlib_dll_path: Path,
        on_qr_code: Optional[Callable[[str], None]] = None,
        on_otp: Optional[Callable[[str], None]] = None,
        on_2fa: Optional[Callable[[str], None]] = None,
    ):
        self.phone_number = phone_number
        self.api_id = api_id
        self.api_hash = api_hash
        self.database_dir = database_dir
        self.tdlib_dll_path = tdlib_dll_path
        self.on_qr_code = on_qr_code      # will receive QR code URL
        self.on_otp = on_otp              # will request OTP
        self.on_2fa = on_2fa              # will request 2FA password
        
        self.client: Optional[Client] = None
        self._authorized = False
        self._otp_future: Optional[asyncio.Future] = None
        self._2fa_future: Optional[asyncio.Future] = None
        
    async def start(self) -> bool:
        """Initialize and start TDLib client"""
        self.database_dir.mkdir(parents=True, exist_ok=True)
        
        self.client = Client(
            api_id=self.api_id,
            api_hash=self.api_hash,
            database_encryption_key="your_secure_key",  # TODO: generate from env
            files_directory=str(self.database_dir / "files"),
            lib_path=str(self.tdlib_dll_path)
        )
        
        # Register authorization handler
        async def on_auth_state(client, update):
            # Parse state correctly whether it's a dict or pytdbot object
            if isinstance(update, dict):
                state = update.get("authorization_state", {})
            else:
                state = getattr(update, "authorization_state", update)
            
            if isinstance(state, dict):
                state_type = state.get("@type", "")
            else:
                state_type = getattr(state, "type", "") or getattr(state, "@type", "")
            
            if not state_type:
                state_type = type(state).__name__
            
            # Normalize to lower for easy comparison
            state_type_lower = state_type.lower()
            logger.info(f"Auth state triggered: {state_type_lower}")
            
            if "waitphonenumber" in state_type_lower:
                await self.client.set_phone_number(self.phone_number)
                
            elif "waitcode" in state_type_lower:
                if self.on_otp:
                    # Wait for GUI to provide code
                    self._otp_future = asyncio.Future()
                    self.on_otp(self.phone_number)
                    code = await self._otp_future
                    await self.client.set_auth_code(code)
                else:
                    logger.error("No OTP callback set")
                    
            elif "waitpassword" in state_type_lower:
                if self.on_2fa:
                    self._2fa_future = asyncio.Future()
                    self.on_2fa(self.phone_number)
                    pwd = await self._2fa_future
                    await self.client.set_auth_password(pwd)
                else:
                    logger.error("No 2FA callback set")
                    
            elif "ready" in state_type_lower:
                self._authorized = True
                logger.info(f"TDLib authorized for {self.phone_number}")
        
        if hasattr(self.client, "add_handler"):
            self.client.add_handler("updateAuthorizationState", on_auth_state)
            
        await self.client.start()
        return self._authorized
    
    def submit_otp(self, code: str):
        """Called from GUI to provide OTP"""
        if self._otp_future and not self._otp_future.done():
            self._otp_future.set_result(code)
    
    def submit_2fa(self, password: str):
        if self._2fa_future and not self._2fa_future.done():
            self._2fa_future.set_result(password)
    
    async def send_message(self, chat_id: int, text: str) -> Optional[Dict]:
        """Send a message – returns message info"""
        if not self.client or not self._authorized:
            logger.error("Client not ready")
            return None
        try:
            result = await self.client.send_message(
                chat_id=chat_id,
                input_message_content=types.InputMessageText(
                    text=types.FormattedText(text=text)
                )
            )
            return result.to_dict()
        except TDLibError as e:
            logger.error(f"Send failed: {e}")
            return None
    
    async def join_chat(self, identifier: str) -> bool:
        """Join by username or invite link"""
        try:
            # Try as invite link first
            if identifier.startswith("https://t.me/+"):
                result = await self.client.join_chat_by_invite_link(identifier)
            else:
                # Search public chat first
                search = await self.client.search_public_chat(identifier)
                if search and search.get("@type") == "chat":
                    result = await self.client.join_chat(chat_id=search.id)
                else:
                    logger.error(f"Chat {identifier} not found")
                    return False
            return True
        except TDLibError as e:
            logger.error(f"Join failed: {e}")
            return False
    
    async def get_chat_members(self, chat_id: int, limit: int = 500) -> List[Dict]:
        """Get members of a supergroup (requires supergroup ID)"""
        members = []
        offset = 0
        batch = 200
        while len(members) < limit:
            try:
                result = await self.client.get_supergroup_members(
                    supergroup_id=chat_id,
                    offset=offset,
                    limit=min(batch, limit - len(members))
                )
                if not result.members:
                    break
                for m in result.members:
                    members.append(m.to_dict())
                offset += len(result.members)
                await asyncio.sleep(0.3)
            except TDLibError as e:
                logger.error(f"Get members error: {e}")
                break
        return members
    
    async def search_public_chats(self, query: str, limit: int = 50) -> List[Dict]:
        """Search for public groups/channels"""
        try:
            result = await self.client.search_public_chats(query, limit=limit)
            return result.to_dict().get("chat_ids", [])
        except TDLibError as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def get_me(self) -> Optional[Dict]:
        """Get current user info"""
        try:
            me = await self.client.get_me()
            return me.to_dict()
        except TDLibError:
            return None
    
    async def stop(self):
        if self.client:
            await self.client.stop()
            self._authorized = False
