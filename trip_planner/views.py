from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.cache import cache
from django.db.models import Avg, Min, Max, Count
from .models import FuelStation
import math
import json

class CompleteTripAPI(APIView):
    
    
    def get(self, request):
        try:
            start = request.GET.get('start', 'New York, NY').strip()
            end = request.GET.get('end', 'Chicago, IL').strip()
            
            try:
                mpg = float(request.GET.get('mpg', 10))
                tank_range = float(request.GET.get('range', 500))
            except ValueError:
                return Response(
                    {'error': 'MPG and range must be valid numbers'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            print(f"Planning trip: {start} to {end}, MPG: {mpg}, Range: {tank_range}")
            
            cache_key = f"trip_{start}_{end}_{mpg}_{tank_range}"
            cached = cache.get(cache_key)
            if cached:
                print("Returning cached result")
                cached['cached'] = True
                return Response(cached)
            
            start_coords = self._get_coordinates(start)
            end_coords = self._get_coordinates(end)
            
            distance = self._calculate_distance(start_coords, end_coords)
            
            stations = FuelStation.objects.all()
            station_count = stations.count()
            
            if station_count == 0:
                return Response(
                    {'error': 'No fuel station data available. Please import data first.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            num_stops_needed = self._calculate_stops_needed(distance, tank_range)
            fuel_stops = self._get_optimal_stops(stations, num_stops_needed, distance)
            
            total_gallons = distance / mpg
            total_cost = self._calculate_total_cost(fuel_stops, total_gallons, num_stops_needed)
            
            map_data = self._generate_map_data(start_coords, end_coords, fuel_stops)
            
            response_data = {
                'success': True,
                'trip_summary': {
                    'start_location': start,
                    'end_location': end,
                    'start_coordinates': start_coords,
                    'end_coordinates': end_coords,
                    'total_distance_miles': round(distance, 2),
                    'estimated_travel_time_hours': round(distance / 60, 1),  # 60 mph average
                },
                'vehicle': {
                    'mpg': mpg,
                    'fuel_efficiency': f"{mpg} miles per gallon",
                    'tank_range_miles': tank_range,
                    'tank_capacity_gallons': round(tank_range / mpg, 1),
                },
                'fuel_calculations': {
                    'total_gallons_needed': round(total_gallons, 2),
                    'total_fuel_cost_usd': round(total_cost, 2),
                    'cost_per_mile': round(total_cost / distance, 3),
                    'fuel_stops_needed': num_stops_needed,
                },
                'optimal_fuel_stops': fuel_stops,
                'map_visualization': map_data,
                'data_source': {
                    'total_stations_in_database': station_count,
                    'cheapest_station_price': FuelStation.objects.aggregate(min=Min('retail_price'))['min'],
                    'average_station_price': FuelStation.objects.aggregate(avg=Avg('retail_price'))['avg'],
                },
                'optimization_notes': [
                    f"Based on maximum range of {tank_range} miles",
                    f"Vehicle efficiency: {mpg} MPG",
                    f"Stops optimized for lowest fuel prices",
                    "Coordinates are approximate for demonstration",
                ],
                'cached': False,
            }
            
            cache.set(cache_key, response_data, timeout=3600)
            
            return Response(response_data)
            
        except Exception as e:
            print(f"Error in trip planning: {str(e)}")
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'message': 'An error occurred while planning your trip. Please check your inputs.'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_coordinates(self, location):
        location_lower = location.lower()
        
        city_coords = {
            'new york': {'lat': 40.7128, 'lon': -74.0060, 'name': 'New York, NY'},
            'chicago': {'lat': 41.8781, 'lon': -87.6298, 'name': 'Chicago, IL'},
            'los angeles': {'lat': 34.0522, 'lon': -118.2437, 'name': 'Los Angeles, CA'},
            'miami': {'lat': 25.7617, 'lon': -80.1918, 'name': 'Miami, FL'},
            'dallas': {'lat': 32.7767, 'lon': -96.7970, 'name': 'Dallas, TX'},
            'houston': {'lat': 29.7604, 'lon': -95.3698, 'name': 'Houston, TX'},
            'phoenix': {'lat': 33.4484, 'lon': -112.0740, 'name': 'Phoenix, AZ'},
            'philadelphia': {'lat': 39.9526, 'lon': -75.1652, 'name': 'Philadelphia, PA'},
            'san antonio': {'lat': 29.4241, 'lon': -98.4936, 'name': 'San Antonio, TX'},
            'san diego': {'lat': 32.7157, 'lon': -117.1611, 'name': 'San Diego, CA'},
            'austin': {'lat': 30.2672, 'lon': -97.7431, 'name': 'Austin, TX'},
            'san francisco': {'lat': 37.7749, 'lon': -122.4194, 'name': 'San Francisco, CA'},
            'seattle': {'lat': 47.6062, 'lon': -122.3321, 'name': 'Seattle, WA'},
            'denver': {'lat': 39.7392, 'lon': -104.9903, 'name': 'Denver, CO'},
            'washington': {'lat': 38.9072, 'lon': -77.0369, 'name': 'Washington, DC'},
            'boston': {'lat': 42.3601, 'lon': -71.0589, 'name': 'Boston, MA'},
            'atlanta': {'lat': 33.7490, 'lon': -84.3880, 'name': 'Atlanta, GA'},
            'detroit': {'lat': 42.3314, 'lon': -83.0458, 'name': 'Detroit, MI'},
            'las vegas': {'lat': 36.1699, 'lon': -115.1398, 'name': 'Las Vegas, NV'},
            'portland': {'lat': 45.5051, 'lon': -122.6750, 'name': 'Portland, OR'},
        }
        
        for city, coords in city_coords.items():
            if city in location_lower:
                return coords
        
        state_coords = {
            'ny': {'lat': 40.7128, 'lon': -74.0060, 'name': 'New York'},
            'il': {'lat': 41.8781, 'lon': -87.6298, 'name': 'Illinois'},
            'ca': {'lat': 36.7783, 'lon': -119.4179, 'name': 'California'},
            'tx': {'lat': 31.9686, 'lon': -99.9018, 'name': 'Texas'},
            'fl': {'lat': 27.6648, 'lon': -81.5158, 'name': 'Florida'},
            'az': {'lat': 34.0489, 'lon': -111.0937, 'name': 'Arizona'},
            'pa': {'lat': 41.2033, 'lon': -77.1945, 'name': 'Pennsylvania'},
            'oh': {'lat': 40.4173, 'lon': -82.9071, 'name': 'Ohio'},
            'ga': {'lat': 32.1656, 'lon': -82.9001, 'name': 'Georgia'},
            'nc': {'lat': 35.7596, 'lon': -79.0193, 'name': 'North Carolina'},
            'mi': {'lat': 44.3148, 'lon': -85.6024, 'name': 'Michigan'},
        }
        
        location_parts = location_lower.split(',')
        if len(location_parts) > 1:
            state_abbr = location_parts[-1].strip()
            if state_abbr in state_coords:
                return state_coords[state_abbr]
        
        return {
            'lat': 39.8283,
            'lon': -98.5795,
            'name': location
        }
    
    def _calculate_distance(self, start_coords, end_coords):
        lat1 = math.radians(start_coords['lat'])
        lon1 = math.radians(start_coords['lon'])
        lat2 = math.radians(end_coords['lat'])
        lon2 = math.radians(end_coords['lon'])
        
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        R = 3958.8
        distance = R * c
        
        return distance * 1.2
    
    def _calculate_stops_needed(self, distance, tank_range):
        if distance <= tank_range:
            return 0
        return math.ceil(distance / tank_range) - 1
    
    def _get_optimal_stops(self, stations, num_stops_needed, total_distance):
        if num_stops_needed <= 0:
            return []
        
        cheapest_stations = stations.order_by('retail_price')[:num_stops_needed]
        
        fuel_stops = []
        for i, station in enumerate(cheapest_stations):
            stop_distance = (i + 1) * (total_distance / (num_stops_needed + 1))
            
            fuel_stops.append({
                'stop_number': i + 1,
                'station': {
                    'id': station.id,
                    'name': station.name,
                    'address': station.address[:80] + '...' if len(station.address) > 80 else station.address,
                    'city': station.city,
                    'state': station.state,
                    'fuel_price_per_gallon': station.retail_price,
                    'rack_id': station.rack_id,
                },
                'distance_from_start_miles': round(stop_distance, 2),
                'estimated_travel_time': f"{round(stop_distance / 60, 1)} hours",  # 60 mph
                'fuel_needed_gallons': round((total_distance / (num_stops_needed + 1)) / 10, 1),  # 10 MPG
            })
        
        return fuel_stops
    
    def _calculate_total_cost(self, fuel_stops, total_gallons, num_stops_needed):
        if not fuel_stops:
            avg_price = FuelStation.objects.aggregate(avg=Avg('retail_price'))['avg'] or 3.50
            return total_gallons * avg_price
        
        num_segments = len(fuel_stops) + 1
        gallons_per_segment = total_gallons / num_segments
        
        total_cost = 0
        
        avg_price = FuelStation.objects.aggregate(avg=Avg('retail_price'))['avg'] or 3.50
        total_cost += gallons_per_segment * avg_price
        
        for stop in fuel_stops:
            total_cost += gallons_per_segment * stop['station']['fuel_price_per_gallon']
        
        return total_cost
    
    def _generate_map_data(self, start_coords, end_coords, fuel_stops):
        
        markers = []
        
        markers.append({
            'type': 'start',
            'lat': start_coords['lat'],
            'lon': start_coords['lon'],
            'label': 'Start',
            'popup': f"Start: {start_coords.get('name', 'Starting Point')}"
        })
        
        markers.append({
            'type': 'end',
            'lat': end_coords['lat'],
            'lon': end_coords['lon'],
            'label': 'End',
            'popup': f"End: {end_coords.get('name', 'Destination')}"
        })
        
        for i, stop in enumerate(fuel_stops):
            ratio = (i + 1) / (len(fuel_stops) + 1)
            lat = start_coords['lat'] + (end_coords['lat'] - start_coords['lat']) * ratio
            lon = start_coords['lon'] + (end_coords['lon'] - start_coords['lon']) * ratio
            
            markers.append({
                'type': 'fuel_stop',
                'lat': round(lat, 4),
                'lon': round(lon, 4),
                'label': f'F{i+1}',
                'popup': f"Fuel Stop {i+1}: {stop['station']['name']}<br>Price: ${stop['station']['fuel_price_per_gallon']}/gal",
                'station_info': stop['station']
            })
        
        map_url = self._generate_google_maps_url(start_coords, end_coords, markers)
        
        map_html = self._generate_leaflet_html(start_coords, end_coords, markers)
        
        return {
            'markers': markers,
            'google_maps_static_url': map_url,
            'interactive_map_html': map_html,
            'center': {
                'lat': (start_coords['lat'] + end_coords['lat']) / 2,
                'lon': (start_coords['lon'] + end_coords['lon']) / 2,
            },
            'zoom_level': 6,
        }
    
    def _generate_google_maps_url(self, start_coords, end_coords, markers):
        # Note: Requires Google Maps API key for production
        base_url = "https://maps.googleapis.com/maps/api/staticmap"
        
        center_lat = (start_coords['lat'] + end_coords['lat']) / 2
        center_lon = (start_coords['lon'] + end_coords['lon']) / 2
        
        params = {
            'center': f"{center_lat},{center_lon}",
            'zoom': '5',
            'size': '600x400',
            'scale': '2',
            'maptype': 'roadmap',
            'key': 'DEMO_KEY',  # Replace with actual key in production
        }
        
        marker_params = []
        
        marker_params.append(f"color:green|label:S|{start_coords['lat']},{start_coords['lon']}")
        
        marker_params.append(f"color:red|label:E|{end_coords['lat']},{end_coords['lon']}")
        
        for i, marker in enumerate(markers):
            if marker['type'] == 'fuel_stop':
                marker_params.append(f"color:orange|label:{i+1}|{marker['lat']},{marker['lon']}")
        
        url = f"{base_url}?{'&'.join([f'{k}={v}' for k, v in params.items()])}"
        url += "&" + "&markers=".join(marker_params)
        
        return url
    
    def _generate_leaflet_html(self, start_coords, end_coords, markers):
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Trip Route Map</title>
            <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
            <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
            <style>
                body {{ margin: 0; padding: 0; }}
                #map {{ height: 500px; width: 100%; }}
                .leaflet-popup-content {{ font-family: Arial, sans-serif; }}
            </style>
        </head>
        <body>
            <div id="map"></div>
            <script>
                // Initialize map
                var map = L.map('map').setView([{(start_coords['lat'] + end_coords['lat']) / 2}, {(start_coords['lon'] + end_coords['lon']) / 2}], 5);
                
                // Add OpenStreetMap tiles
                L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                    attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                }}).addTo(map);
                
                // Draw route line
                var routeLine = L.polyline([
                    [{start_coords['lat']}, {start_coords['lon']}],
                    [{end_coords['lat']}, {end_coords['lon']}]
                ], {{
                    color: 'blue',
                    weight: 3,
                    opacity: 0.7,
                    dashArray: '10, 10'
                }}).addTo(map);
                
                // Add markers
        """
        
        for marker in markers:
            if marker['type'] == 'start':
                html += f"""
                L.marker([{marker['lat']}, {marker['lon']}])
                    .addTo(map)
                    .bindPopup("{marker['popup']}")
                    .openPopup();
                """
            elif marker['type'] == 'end':
                html += f"""
                L.marker([{marker['lat']}, {marker['lon']}])
                    .addTo(map)
                    .bindPopup("{marker['popup']}");
                """
            elif marker['type'] == 'fuel_stop':
                station_info = marker.get('station_info', {})
                html += f"""
                L.marker([{marker['lat']}, {marker['lon']}])
                    .addTo(map)
                    .bindPopup(`
                        <b>{marker['popup']}</b><br>
                        <hr>
                        <b>Address:</b> {station_info.get('address', 'N/A')}<br>
                        <b>City:</b> {station_info.get('city', 'N/A')}, {station_info.get('state', 'N/A')}<br>
                        <b>Price:</b> ${station_info.get('fuel_price_per_gallon', 'N/A')}/gallon
                    `);
                """
        
        html += """
                // Fit map to show all markers
                map.fitBounds(routeLine.getBounds());
                
                // Add legend
                var legend = L.control({position: 'bottomright'});
                legend.onAdd = function(map) {
                    var div = L.DomUtil.create('div', 'info legend');
                    div.innerHTML = `
                        <h4>Legend</h4>
                        <div><span style="color: green">●</span> Start</div>
                        <div><span style="color: red">●</span> End</div>
                        <div><span style="color: orange">●</span> Fuel Stop</div>
                        <div style="border-top: 2px dashed blue; width: 20px; display: inline-block;"></div> Route
                    `;
                    return div;
                };
                legend.addTo(map);
            </script>
        </body>
        </html>
        """
        
        return html


class FuelStationAPI(APIView):
    
    def get(self, request):
        state = request.GET.get('state', '')
        min_price = request.GET.get('min_price')
        max_price = request.GET.get('max_price')
        limit = int(request.GET.get('limit', 20))
        
        stations = FuelStation.objects.all()
        
        if state:
            stations = stations.filter(state__iexact=state)
        
        if min_price:
            try:
                stations = stations.filter(retail_price__gte=float(min_price))
            except ValueError:
                pass
        
        if max_price:
            try:
                stations = stations.filter(retail_price__lte=float(max_price))
            except ValueError:
                pass
        
        station_list = []
        for station in stations[:limit]:
            station_list.append({
                'id': station.id,
                'name': station.name,
                'address': station.address,
                'city': station.city,
                'state': station.state,
                'price': station.retail_price,
                'rack_id': station.rack_id,
            })
        
        return Response({
            'count': len(station_list),
            'stations': station_list,
            'filters': {
                'state': state,
                'min_price': min_price,
                'max_price': max_price,
            }
        })


class HealthCheck(APIView):
    
    def get(self, request):
        station_count = FuelStation.objects.count()
        
        return Response({
            'status': 'healthy',
            'timestamp': '2024-01-01T00:00:00Z',  
            'database': {
                'fuel_stations_count': station_count,
                'connected': True,
            },
            'cache': {
                'enabled': True,
                'backend': 'local memory',
            },
            'api': {
                'version': '1.0.0',
                'endpoints': [
                    '/api/plan-trip/',
                    '/api/fuel-stations/',
                    '/api/health/',
                ]
            }
        })