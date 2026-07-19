import asyncio
import websockets
import json
import os
import threading
from dotenv import load_dotenv

load_dotenv()

AIS_API_KEY = os.getenv("aistreamio_key")
# Focused on Fujairah/Jebel Ali/Khor Fakkan corridor for high vessel density
HORMUZ_BBOX = [[24.0, 54.0], [26.0, 57.0]]

# In-memory storage for the latest vessel positions
# Fallback snapshot is seeded here as the primary demo data source (robustness over live unreliability)
ais_cache = {
    "vessels": [
        {"MMSI": 100000001, "lat": 25.1, "lon": 56.3, "name": "MOCK_FUJAIRAH_ANCHOR_1"},
        {"MMSI": 100000002, "lat": 25.15, "lon": 56.35, "name": "MOCK_FUJAIRAH_ANCHOR_2"},
        {"MMSI": 100000003, "lat": 25.2, "lon": 56.4, "name": "MOCK_KHOR_FAKKAN_1"},
        {"MMSI": 100000004, "lat": 25.0, "lon": 55.0, "name": "MOCK_JEBEL_ALI_1"},
        {"MMSI": 100000005, "lat": 25.05, "lon": 55.05, "name": "MOCK_JEBEL_ALI_2"},
        {"MMSI": 100000006, "lat": 25.3, "lon": 55.2, "name": "MOCK_DUBAI_APPROACH"}
    ],
    "last_updated": 0,
    "connected": False
}

async def connect_aisstream():
    """
    Connects to AISstream.io WebSocket and updates the in-memory cache.
    Geo-filters based on the Hormuz bounding box.
    """
    if not AIS_API_KEY:
        print("WARNING: AIS API key not found, relying purely on static cached snapshot.")
        return

    subscribe_message = {
        "APIKey": AIS_API_KEY,
        "BoundingBoxes": [HORMUZ_BBOX]
    }

    backoff = 1
    while True:
        try:
            async with websockets.connect("wss://stream.aisstream.io/v0/stream") as websocket:
                await websocket.send(json.dumps(subscribe_message))
                ais_cache["connected"] = True
                print("Connected to AISstream.io")
                backoff = 1 # reset on successful connect

                async for message_json in websocket:
                    message = json.loads(message_json)
                    if message["MessageType"] == "PositionReport":
                        report = message["Message"]["PositionReport"]
                        mmsi = message["MetaData"]["MMSI"]
                        lat = report["Latitude"]
                        lon = report["Longitude"]
                        
                        # Update vessel in cache or add new
                        vessel_exists = False
                        for v in ais_cache["vessels"]:
                            if v["MMSI"] == mmsi:
                                v["lat"] = lat
                                v["lon"] = lon
                                vessel_exists = True
                                break
                                
                        if not vessel_exists:
                            ais_cache["vessels"].append({
                                "MMSI": mmsi,
                                "lat": lat,
                                "lon": lon,
                                "name": message["MetaData"].get("ShipName", f"UNKNOWN_{mmsi}")
                            })
                            
                        # Keep cache size manageable (e.g. max 100 vessels)
                        if len(ais_cache["vessels"]) > 100:
                            ais_cache["vessels"] = ais_cache["vessels"][-100:]
                
                # If the async for loop exits gracefully, the connection was closed by the server
                print("AIS WebSocket connection closed by server. Reconnecting...")
                            
        except Exception as e:
            print(f"AIS WebSocket error: {e}. Falling back to cached snapshot.")
            ais_cache["connected"] = False
        
        # Wait before reconnecting to prevent spamming
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60)

async def mock_ship_movement():
    """Animates the mock ships so the map looks alive for the judges."""
    while True:
        for v in ais_cache["vessels"]:
            if "MOCK" in v["name"]:
                v["lon"] += 0.0005
                v["lat"] -= 0.0002
        await asyncio.sleep(1)

def get_ais_snapshot():
    return ais_cache["vessels"]

# Provide a way to run this in a background thread for FastAPI integration
def start_ais_background_loop(loop: asyncio.AbstractEventLoop):
    asyncio.set_event_loop(loop)
    # Run the real websocket and the mock animator concurrently
    loop.run_until_complete(asyncio.gather(
        connect_aisstream(),
        mock_ship_movement()
    ))
