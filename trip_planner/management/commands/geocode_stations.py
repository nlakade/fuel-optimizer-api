import time
from django.core.management.base import BaseCommand
from trip_planner.models import FuelStation
from trip_planner.utils.geocoding import OpenRouteService
from django.db import transaction

class Command(BaseCommand):
    help = 'Geocode fuel stations to get coordinates'
    
    def handle(self, *args, **options):
        ors = OpenRouteService()
        stations = FuelStation.objects.filter(latitude__isnull=True)[:1000]  # Limit to 1000
        
        self.stdout.write(f'Geocoding {len(stations)} stations...')
        
        success_count = 0
        fail_count = 0
        
        for station in stations:
            try:
                search_query = f"{station.name}, {station.city}, {station.state}"
                
                result = ors.geocode(search_query)
                
                if result:
                    station.latitude = result['latitude']
                    station.longitude = result['longitude']
                    station.save()
                    success_count += 1
                    
                    self.stdout.write(f'✓ {station.name}')
                else:
                    fail_count += 1
                    self.stdout.write(f'✗ {station.name}')
                
                time.sleep(0.1)
                
            except Exception as e:
                fail_count += 1
                self.stdout.write(f'Error: {e}')
                continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Geocoding complete: {success_count} success, {fail_count} failed'
            )
        )