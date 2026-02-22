import asyncio
import httpx
import json

async def run():
    async with httpx.AsyncClient() as client:
        # We need the backend running, wait I can't run it and test it easily in one script unless I use subprocess or just test the internal method
        pass
