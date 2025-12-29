import csv
import os
from django.core.management.base import BaseCommand
from trip_planner.models import FuelStation
from django.db import transaction

class Command(BaseCommand):
    help = 'Import fuel stations from CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to CSV file')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']
        
        if not os.path.exists(csv_file):
            self.stdout.write(self.style.ERROR(f'File {csv_file} does not exist'))
            return
        
        self.stdout.write(f'Importing fuel stations from {csv_file}...')
        
        imported_count = 0
        skipped_count = 0
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            
            with transaction.atomic():
                FuelStation.objects.all().delete()  # Clear existing data
                
                for row in reader:
                    try:
                        price = float(row['Retail Price'].strip())
                        
                        if price <= 0:
                            skipped_count += 1
                            continue
                        
                        FuelStation.objects.create(
                            truckstop_id=int(row['OPIS Truckstop ID']),
                            name=row['Truckstop Name'].strip(),
                            address=row['Address'].strip(),
                            city=row['City'].strip(),
                            state=row['State'].strip(),
                            rack_id=int(row['Rack ID']),
                            retail_price=price,
                        )
                        imported_count += 1
                        
                        if imported_count % 100 == 0:
                            self.stdout.write(f'Imported {imported_count} stations...')
                    
                    except (ValueError, KeyError) as e:
                        skipped_count += 1
                        continue
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully imported {imported_count} fuel stations. '
                f'Skipped {skipped_count} rows.'
            )
        )