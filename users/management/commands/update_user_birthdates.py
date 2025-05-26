from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random
from users.models import User


class Command(BaseCommand):
    help = 'Update existing users with adult birthdates'

    def handle(self, *args, **options):
        # Get all users without a birthdate
        users = User.objects.filter(birthday__isnull=True)
        
        if not users.exists():
            self.stdout.write(self.style.SUCCESS('No users need updating'))
            return
        
        total_users = users.count()
        updated_count = 0
        
        for user in users:
            # Generate random adult age between 18-65
            age = random.randint(18, 65)
            
            # Calculate birthdate based on age
            today = timezone.now().date()
            # Subtract years plus a random offset for month/day to make it more realistic
            random_days = random.randint(0, 364)  # Random days in a year
            birthdate = today.replace(year=today.year - age) - timedelta(days=random_days)
            
            # Update user
            user.birthday = birthdate
            user.save(update_fields=['birthday'])
            updated_count += 1
            
            if updated_count % 10 == 0:
                self.stdout.write(f'Updated {updated_count}/{total_users} users...')
        
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} users with adult birthdates')) 