import math
from typing import List, Dict, Tuple
from django.db.models import Q
from trip_planner import models
from trip_planner.models import FuelStation
from .geocoding import OpenRouteService

class FuelOptimizer:
    
    
    def __init__(self, mpg=10, tank_range=500):
        self.mpg = mpg
        self.tank_range = tank_range
        self.ors = OpenRouteService()
    
    def haversine_distance(self, lat1, lon1, lat2, lon2):
        
        return self.ors._haversine_distance(lat1, lon1, lat2, lon2)
    
    def find_nearby_stations(self, lat, lon, radius=50):
        
        stations = FuelStation.objects.all()
        
        nearby_stations = []
        
        for station in stations:
            if station.latitude and station.longitude:
                distance = self.haversine_distance(
                    lat, lon, station.latitude, station.longitude
                )
                if distance <= radius:
                    nearby_stations.append({
                        'station': station,
                        'distance': distance,
                        'cost_per_gallon': station.retail_price,
                    })
            else:
                state_centers = {
                    'NY': (40.7128, -74.0060),
                    'IL': (41.8781, -87.6298),
                    'CA': (36.7783, -119.4179),
                    'TX': (31.9686, -99.9018),
                    'FL': (27.6648, -81.5158),
                    'AZ': (34.0489, -111.0937),
                    'PA': (41.2033, -77.1945),
                    'OH': (40.4173, -82.9071),
                    'GA': (32.1656, -82.9001),
                    'NC': (35.7596, -79.0193),
                    'MI': (44.3148, -85.6024),
                    'IN': (40.2672, -86.1349),
                    'WI': (43.7844, -88.7879),
                    'MN': (46.7296, -94.6859),
                    'MO': (37.9643, -91.8318),
                    'OK': (35.0078, -97.0929),
                    'KS': (39.0119, -98.4842),
                    'NE': (41.4925, -99.9018),
                    'SD': (43.9695, -99.9018),
                    'ND': (47.5515, -101.0020),
                    'MT': (46.8797, -110.3626),
                    'WY': (43.0760, -107.2903),
                    'CO': (39.5501, -105.7821),
                    'NM': (34.5199, -105.8701),
                    'UT': (39.3210, -111.0937),
                    'NV': (38.8026, -116.4194),
                    'WA': (47.7511, -120.7401),
                    'OR': (43.8041, -120.5542),
                    'ID': (44.0682, -114.7420),
                }
                
                if station.state in state_centers:
                    state_lat, state_lon = state_centers[station.state]
                    distance = self.haversine_distance(lat, lon, state_lat, state_lon)
                    if distance <= radius + 100:  # Larger radius for state-level
                        nearby_stations.append({
                            'station': station,
                            'distance': distance,
                            'cost_per_gallon': station.retail_price,
                        })
        
        return sorted(nearby_stations, key=lambda x: (x['cost_per_gallon'], x['distance']))
    
    def calculate_optimal_stops(self, route_distance, start_lat, start_lon, end_lat, end_lon):
        
        if route_distance <= self.tank_range:
            return [] 
        
        num_stops = math.ceil(route_distance / self.tank_range) - 1
        
        optimal_stops = []
        
        for i in range(1, num_stops + 1):
            ratio = i / (num_stops + 1)
            
            approx_lat = start_lat + (end_lat - start_lat) * ratio
            approx_lon = start_lon + (end_lon - start_lon) * ratio
            
            nearby_stations = self.find_nearby_stations(approx_lat, approx_lon, radius=100)
            
            if nearby_stations:
                best_station = nearby_stations[0]
                
                optimal_stops.append({
                    'station': best_station['station'],
                    'distance_from_start': route_distance * ratio,
                    'distance_to_station': best_station['distance'],
                    'cost_per_gallon': best_station['cost_per_gallon'],
                    'coordinates': {
                        'lat': best_station['station'].latitude or approx_lat,
                        'lon': best_station['station'].longitude or approx_lon,
                    }
                })
        
        return optimal_stops
    
    def optimize_trip(self, start_location, end_location):
        
        start_geo = self.ors.geocode(start_location)
        end_geo = self.ors.geocode(end_location)
        
        if not start_geo or not end_geo:
            return None
        
        route = self.ors.get_route(
            [start_geo['longitude'], start_geo['latitude']],
            [end_geo['longitude'], end_geo['latitude']]
        )
        
        if not route:
            return None
        
        stops = self.calculate_optimal_stops(
            route['distance'],
            start_geo['latitude'], start_geo['longitude'],
            end_geo['latitude'], end_geo['longitude']
        )
        
        total_gallons = route['distance'] / self.mpg
        fuel_cost = 0
        
        if stops:
            gallons_per_stop = total_gallons / (len(stops) + 1)
            
            start_price = stops[0]['cost_per_gallon'] if stops else 3.50
            fuel_cost += gallons_per_stop * start_price
            
            for stop in stops:
                fuel_cost += gallons_per_stop * stop['cost_per_gallon']
        else:
            avg_result = FuelStation.objects.aggregate(avg=models.Avg('retail_price'))
            avg_price = avg_result['avg'] or 3.50
            fuel_cost = total_gallons * avg_price
        
        result = {
            'start_location': {
                'address': start_geo['address'],
                'coordinates': {
                    'lat': round(start_geo['latitude'], 4),
                    'lon': round(start_geo['longitude'], 4),
                }
            },
            'end_location': {
                'address': end_geo['address'],
                'coordinates': {
                    'lat': round(end_geo['latitude'], 4),
                    'lon': round(end_geo['longitude'], 4),
                }
            },
            'route': {
                'total_distance': round(route['distance'], 2),
                'total_duration': round(route['duration'], 2),
                'geometry': route.get('geometry'),
            },
            'vehicle': {
                'mpg': self.mpg,
                'tank_range': self.tank_range,
            },
            'fuel_stops': [],
            'total_fuel_cost': round(fuel_cost, 2),
            'total_gallons': round(total_gallons, 2),
        }
        
        for stop in stops:
            station = stop['station']
            result['fuel_stops'].append({
                'station_name': station.name,
                'address': f"{station.address}, {station.city}, {station.state}",
                'fuel_price': station.retail_price,
                'distance_from_start': round(stop['distance_from_start'], 2),
                'coordinates': {
                    'lat': round(stop['coordinates']['lat'], 4),
                    'lon': round(stop['coordinates']['lon'], 4),
                },
            })
        
        return result