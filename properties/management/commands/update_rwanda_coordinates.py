from django.core.management.base import BaseCommand
from properties.models import Property
from decimal import Decimal
import random

class Command(BaseCommand):
    help = 'Updates properties with realistic Rwanda coordinates and locations'

    def handle(self, *args, **options):
        # Rwanda cities/locations with their coordinates
        rwanda_locations = [
            {
                'city': 'Kigali',
                'state': 'Kigali Province',
                'country': 'Rwanda',
                'areas': [
                    {'name': 'Nyarugenge', 'lat': -1.9536, 'lng': 30.0606},
                    {'name': 'Kacyiru', 'lat': -1.9428, 'lng': 30.0822},
                    {'name': 'Kimihurura', 'lat': -1.9539, 'lng': 30.0911},
                    {'name': 'Gisozi', 'lat': -1.9231, 'lng': 30.0850},
                    {'name': 'Remera', 'lat': -1.9544, 'lng': 30.1139},
                    {'name': 'Kicukiro', 'lat': -1.9831, 'lng': 30.0953},
                    {'name': 'Nyamirambo', 'lat': -1.9886, 'lng': 30.0453},
                    {'name': 'Kimironko', 'lat': -1.9428, 'lng': 30.1164},
                ]
            },
            {
                'city': 'Rubavu',
                'state': 'Western Province',
                'country': 'Rwanda',
                'areas': [
                    {'name': 'Gisenyi', 'lat': -1.7006, 'lng': 29.2569},
                    {'name': 'Lake Kivu Shore', 'lat': -1.7231, 'lng': 29.2508},
                ]
            },
            {
                'city': 'Musanze',
                'state': 'Northern Province',
                'country': 'Rwanda',
                'areas': [
                    {'name': 'Ruhengeri', 'lat': -1.4996, 'lng': 29.6336},
                    {'name': 'Volcanoes National Park Area', 'lat': -1.4830, 'lng': 29.6170},
                ]
            },
            {
                'city': 'Huye',
                'state': 'Southern Province',
                'country': 'Rwanda',
                'areas': [
                    {'name': 'Butare', 'lat': -2.6078, 'lng': 29.7567},
                    {'name': 'University Area', 'lat': -2.6150, 'lng': 29.7440},
                ]
            },
            {
                'city': 'Muhanga',
                'state': 'Southern Province',
                'country': 'Rwanda',
                'areas': [
                    {'name': 'Gitarama', 'lat': -2.0778, 'lng': 29.7567},
                ]
            },
            {
                'city': 'Nyagatare',
                'state': 'Eastern Province',
                'country': 'Rwanda',
                'areas': [
                    {'name': 'Nyagatare Center', 'lat': -1.2975, 'lng': 30.3272},
                ]
            },
            {
                'city': 'Rusizi',
                'state': 'Western Province',
                'country': 'Rwanda',
                'areas': [
                    {'name': 'Cyangugu', 'lat': -2.4846, 'lng': 28.9086},
                    {'name': 'Lake Kivu Area', 'lat': -2.4700, 'lng': 28.9200},
                ]
            },
        ]

        # Get all properties
        properties = Property.objects.all()
        self.stdout.write(f"Found {properties.count()} properties to update")

        # Update each property
        for property_obj in properties:
            # Select a random location from our Rwanda locations
            location = random.choice(rwanda_locations)
            area = random.choice(location['areas'])
            
            # Add small random offset to make coordinates unique (within ~500m)
            lat_offset = random.uniform(-0.004, 0.004)
            lng_offset = random.uniform(-0.004, 0.004)
            
            # Create a realistic address
            street_numbers = ["123", "456", "789", "25", "78", "101", "42", "15", "36", "50"]
            street_names = ["KG", "KN", "KK", "RN", "Avenue des", "Boulevard de"]
            street_types = ["Street", "Road", "Avenue", "Boulevard"]
            
            # Update property with Rwanda location data
            property_obj.city = location['city']
            property_obj.state = location['state']
            property_obj.country = 'Rwanda'
            property_obj.address = f"{random.choice(street_numbers)} {random.choice(street_names)} {area['name']} {random.choice(street_types)}"
            property_obj.latitude = Decimal(str(area['lat'] + lat_offset))
            property_obj.longitude = Decimal(str(area['lng'] + lng_offset))
            property_obj.save()
            
            self.stdout.write(f"Updated property {property_obj.id}: {property_obj.title} - {property_obj.address}, {property_obj.city}")
            
        self.stdout.write(self.style.SUCCESS(f"Successfully updated {properties.count()} properties with Rwanda coordinates")) 