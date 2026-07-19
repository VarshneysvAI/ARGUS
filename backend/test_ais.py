import asyncio
import websockets
import json
import os
from dotenv import load_dotenv

load_dotenv()
AIS_API_KEY = os.getenv("aistreamio_key")
HORMUZ_BBOX = [[24.0, 54.0], [27.5, 58.5]]

async def test():
    subscribe_message = {
        "APIKey": AIS_API_KEY,
        "BoundingBoxes": [[[54.0, 24.0], [58.5, 27.5]]]
    }
    print(f"Connecting with {AIS_API_KEY[:5]}...")
    try:
        async with websockets.connect("wss://stream.aisstream.io/v0/stream") as websocket:
            await websocket.send(json.dumps(subscribe_message))
            for _ in range(3):
                msg = await websocket.recv()
                print(msg)
    except Exception as e:
        print(e)

asyncio.run(test())
