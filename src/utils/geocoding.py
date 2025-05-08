import requests
import os

API_HERE_MAP = os.getenv('API_MAP')
print(f"API_HERE_MAP: {API_HERE_MAP}")
def geocode_address(address):
    url = 'https://geocode.search.hereapi.com/v1/geocode'
    params = {
        'q': address,
        'apiKey': API_HERE_MAP,
    }
    print(url, params)
    res = requests.get(url, params=params)
    # res.raise_for_status()
    items = res.json().get('items')
    if not items:
        return None
    position = items[0]['position']
    print(f"Geocoding result for '{address}': {position}")
    return position['lat'], position['lng']
