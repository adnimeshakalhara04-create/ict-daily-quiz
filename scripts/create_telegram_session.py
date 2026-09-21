from __future__ import annotations

import asyncio
import getpass

from telethon import TelegramClient
from telethon.sessions import StringSession


async def main() -> None:
    print("Create a Telegram StringSession for ICT Daily Quiz automation.")
    print("Nothing is saved to this repository. The generated session must be stored as a GitHub secret.")
    api_id = int(input("Telegram API ID: ").strip())
    api_hash = getpass.getpass("Telegram API hash: ").strip()

    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.start()
    try:
        session = client.session.save()
        print("\nTELEGRAM_SESSION (copy this directly into a GitHub Actions secret):\n")
        print(session)
        print("\nDo not commit or share this value.")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
