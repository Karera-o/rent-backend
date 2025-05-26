from django.core.management.base import BaseCommand
from properties.models import Property

class Command(BaseCommand):
    help = 'Displays property locations and coordinates'

    def handle(self, *args, **options):
        properties = Property.objects.all()
        self.stdout.write(f"Found {properties.count()} properties")
        
        for prop in properties:
            self.stdout.write(f"ID: {prop.id}")
            self.stdout.write(f"Title: {prop.title}")
            self.stdout.write(f"Address: {prop.address}")
            self.stdout.write(f"City: {prop.city}")
            self.stdout.write(f"State: {prop.state}")
            self.stdout.write(f"Country: {prop.country}")
            self.stdout.write(f"Latitude: {prop.latitude}")
            self.stdout.write(f"Longitude: {prop.longitude}")
            self.stdout.write("-" * 50) 