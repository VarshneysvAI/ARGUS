import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

load_dotenv()
AIS_API_KEY = os.getenv("aistreamio_key")
HORMUZ_BBOX = [[20.0, 48.0], [30.0, 60.0]]

async def test():
    subscribe_message = {
        "APIKey": AIS_API_KEY,
        "BoundingBoxes": [HORMUZ_BBOX]
    }
    print(f"Connecting with {AIS_API_KEY[:5]} to {HORMUZ_BBOX}...")
    try:
        async with websockets.connect("wss://stream.aisstream.io/v0/stream") as websocket:
            await websocket.send(json.dumps(subscribe_message))
            for _ in range(3):
                msg = await websocket.recv()
                print(msg[:200])
    except Exception as e:
        print(e)

asyncio.run(test())
