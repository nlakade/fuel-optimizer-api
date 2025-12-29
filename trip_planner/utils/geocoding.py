import requests
import os
from django.conf import settings
from django.core.cache import cache
import time
import urllib.parse

class OpenRouteService:
   
    
    def __init__(self):
        self.api_key = os.getenv('OPENROUTE_API_KEY')
        self.base_url = 'https://api.openrouteservice.org'
        self.headers = {
            'Authorization': self.api_key,
        }
    
    def geocode(self, location):
        
        cache_key = f'geocode_{hash(location)}'
        cached = cache.get(cache_key)
        
        if cached:
            return cached
        
        try:
            url = f'{self.base_url}/geocode/search'
            params = {
                'api_key': self.api_key,
                'text': location,
                'boundary.country': 'USA',
                'size': 1,
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('features'):
                coords = data['features'][0]['geometry']['coordinates']
                result = {
                    'longitude': coords[0],
                    'latitude': coords[1],
                    'address': data['features'][0]['properties'].get('label', location)
                }
                
                cache.set(cache_key, result, timeout=86400)
                return result
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                print(f"API key error for {location}. Using fallback coordinates.")
                return self._fallback_geocode(location)
            else:
                print(f"Geocoding error for {location}: {e}")
        except Exception as e:
            print(f"Geocoding error for {location}: {e}")
        
        return None
    
    def _fallback_geocode(self, location):
        
        state_coords = {
            'NY': {'lat': 40.7128, 'lon': -74.0060},  # New York
            'IL': {'lat': 41.8781, 'lon': -87.6298},  # Chicago
            'CA': {'lat': 34.0522, 'lon': -118.2437}, # Los Angeles
            'TX': {'lat': 31.9686, 'lon': -99.9018},  # Texas
            'FL': {'lat': 27.6648, 'lon': -81.5158},  # Florida
            'AZ': {'lat': 34.0489, 'lon': -111.0937}, # Arizona
            'PA': {'lat': 41.2033, 'lon': -77.1945},  # Pennsylvania
            'OH': {'lat': 40.4173, 'lon': -82.9071},  # Ohio
            'GA': {'lat': 32.1656, 'lon': -82.9001},  # Georgia
            'NC': {'lat': 35.7596, 'lon': -79.0193},  # North Carolina
        }
        
        location_upper = location.upper()
        for state, coords in state_coords.items():
            if state in location_upper:
                return {
                    'longitude': coords['lon'],
                    'latitude': coords['lat'],
                    'address': f"Fallback for {location}"
                }
        
        return {
            'longitude': -98.5795,
            'latitude': 39.8283,
            'address': f"Fallback for {location}"
        }
    
    def get_route(self, start_coords, end_coords):
        
        cache_key = f'route_{start_coords[0]}_{start_coords[1]}_{end_coords[0]}_{end_coords[1]}'
        cached = cache.get(cache_key)
        
        if cached:
            return cached
        
        try:
            url = f'{self.base_url}/v2/directions/driving-car'
            
            body = {
                'coordinates': [start_coords, end_coords],
                'instructions': False,
                'geometry': True,
                'units': 'mi',
            }
            
            response = requests.post(
                url,
                json=body,
                headers=self.headers
            )
            response.raise_for_status()
            
            data = response.json()
            
            distance_miles = self._haversine_distance(
                start_coords[1], start_coords[0],
                end_coords[1], end_coords[0]
            )
            
            route_info = {
                'distance': distance_miles,
                'duration': distance_miles * 1.5,  
                'geometry': {'type': 'LineString', 'coordinates': [start_coords, end_coords]},
                'segments': [],
            }
            
            cache.set(cache_key, route_info, timeout=86400)
            return route_info
        
        except Exception as e:
            print(f"Routing error: {e}. Using straight-line distance.")
            distance_miles = self._haversine_distance(
                start_coords[1], start_coords[0],
                end_coords[1], end_coords[0]
            )
            
            return {
                'distance': distance_miles,
                'duration': distance_miles * 1.5,
                'geometry': {'type': 'LineString', 'coordinates': [start_coords, end_coords]},
                'segments': [],
            }
    
    def _haversine_distance(self, lat1, lon1, lat2, lon2):
       
        import math
        
        R = 3958.8  
        
        lat1_rad = math.radians(lat1)
        lon1_rad = math.radians(lon1)
        lat2_rad = math.radians(lat2)
        lon2_rad = math.radians(lon2)
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c