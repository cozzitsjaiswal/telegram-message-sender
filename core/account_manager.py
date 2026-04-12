"""
core/account_manager.py – Multi‑account management with TDLib backend
"""

import json
import asyncio
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
import logging

from core.tdlib_engine import TDLibEngine

logger = logging.getLogger(__name__)


class AccountManager:
    def __init__(self, data_path: Path, tdlib_dll_path: Path):
        self.data_path = data_path
        self.tdlib_dll_path = tdlib_dll_path
        self.accounts_file = data_path / "accounts.json"
        self.accounts: List[Dict] = []  # each: {phone, api_id, api_hash, engine}
        self.load_accounts()
    
    def load_accounts(self):
        if self.accounts_file.exists():
            with open(self.accounts_file, 'r') as f:
                data = json.load(f)
                if isinstance(data, list):
                    self.accounts = data
                else:
                    self.accounts = data.get('accounts', [])
                # Recreate engine objects? We'll lazy-init on login
                for acc in self.accounts:
                    acc['engine'] = None
                    acc['status'] = 'disconnected'
    
    def save_accounts(self):
        to_save = []
        for acc in self.accounts:
            to_save.append({
                'phone': acc['phone'],
                'api_id': acc['api_id'],
                'api_hash': acc['api_hash'],
                'status': acc.get('status', 'disconnected'),
                'added_at': acc.get('added_at', datetime.now().isoformat())
            })
        with open(self.accounts_file, 'w') as f:
            json.dump({'accounts': to_save}, f, indent=2)
    
    def add_account(self, phone: str, api_id: int, api_hash: str):
        # Check duplicate
        if any(a['phone'] == phone for a in self.accounts):
            return False
        self.accounts.append({
            'phone': phone,
            'api_id': api_id,
            'api_hash': api_hash,
            'engine': None,
            'status': 'pending',
            'added_at': datetime.now().isoformat()
        })
        self.save_accounts()
        return True
    
    async def login_account(self, index: int, on_otp, on_2fa) -> bool:
        acc = self.accounts[index]
        if acc.get('engine') and acc['status'] == 'connected':
            return True
        
        engine = TDLibEngine(
            phone_number=acc['phone'],
            api_id=acc['api_id'],
            api_hash=acc['api_hash'],
            database_dir=self.data_path / f"tdlib_{acc['phone'].replace('+','')}",
            tdlib_dll_path=self.tdlib_dll_path,
            on_otp=on_otp,
            on_2fa=on_2fa
        )
        success = await engine.start()
        if success:
            acc['engine'] = engine
            acc['status'] = 'connected'
        else:
            acc['status'] = 'failed'
        self.save_accounts()
        return success
    
    def get_engine(self, index: int) -> Optional[TDLibEngine]:
        if 0 <= index < len(self.accounts):
            return self.accounts[index].get('engine')
        return None
    
    def get_status(self, index: int) -> str:
        return self.accounts[index].get('status', 'unknown')
    
    @property
    def total_count(self) -> int:
        return len(self.accounts)
        
    def account_count(self) -> int:
        return self.total_count
        
    def get_all(self):
        return self.accounts

    def get_active(self):
        return [a for a in self.accounts if a.get('status') == 'connected']

    async def stop_all(self):
        for acc in self.accounts:
            if acc.get('engine'):
                await acc['engine'].stop()
