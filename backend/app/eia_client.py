import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

EIA_API_KEY = os.getenv("EIA_KEY")

_cache = {
    "spot_price": None,
    "last_fetched": 0
}

CACHE_TTL = 3600  # 1 hour cache to strictly avoid rate limiting

def get_spot_price() -> float:
    """
    Fetches the Daily Official Benchmark from EIA API v2.
    Uses an in-memory cache to prevent rate-limit bans during demo/testing.
    """
    current_time = time.time()
    if _cache["spot_price"] is not None and (current_time - _cache["last_fetched"]) < CACHE_TTL:
        return _cache["spot_price"]

    if not EIA_API_KEY:
        print("WARNING: EIA_KEY not found. Using fallback spot price $78.50")
        return 78.50

    try:
        # Example EIA v2 API endpoint for crude oil spot prices
        url = f"https://api.eia.gov/v2/petroleum/pri/spt/data/?api_key={EIA_API_KEY}&frequency=daily&data[0]=value&facets[series][]=RWTC&sort[0][column]=period&sort[0][direction]=desc&offset=0&length=1"
        response = requests.get(url, timeout=10)
        
        # Checking for HTTP rate limit status specifically (e.g. 429)
        if response.status_code == 429:
            print("WARNING: EIA API Rate Limit hit. Using fallback spot price $78.50")
            return 78.50
            
        response.raise_for_status()
        data = response.json()
        
        # Extract the latest price
        latest_price = float(data['response']['data'][0]['value'])
        
        # Update cache
        _cache["spot_price"] = latest_price
        _cache["last_fetched"] = current_time
        
        return latest_price

    except Exception as e:
        print(f"Error fetching from EIA API: {e}. Using fallback spot price $78.50")
        return 78.50
