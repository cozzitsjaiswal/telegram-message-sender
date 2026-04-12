import asyncio
from pathlib import Path
from core.tdlib_engine import TDLibEngine
import logging

logging.basicConfig(level=logging.INFO)

async def test():
    engine = TDLibEngine(
        phone_number="+1234567890",  # We will test without a real phone, it should just prompt and wait
        api_id=1,
        api_hash="hash",
        database_dir=Path("./tdlib_test_db"),
        tdlib_dll_path=Path("tdjson.dll"),
        on_otp=lambda phone: print(f"Enter OTP for {phone}: "),
        on_2fa=lambda phone: print(f"Enter 2FA: ")
    )
    
    # Run the start as a task to see if it initializes
    task = asyncio.create_task(engine.start())
    await asyncio.sleep(2)
    # Give it time to hit the fake auth state
    print("Test finished initializing!")
    await engine.stop()

if __name__ == '__main__':
    asyncio.run(test())
