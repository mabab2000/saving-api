import asyncio
import sys
import json
import websockets

async def main(user_id):
    uri = f"ws://127.0.0.1:8000/api/home/{user_id}"
    async with websockets.connect(uri) as ws:
        msg = await ws.recv()
        try:
            data = json.loads(msg)
        except Exception:
            data = msg
        print(data)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python test_ws_home.py <user_id>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))
