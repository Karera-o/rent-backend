from users.models import User
from properties.models import Property
from bookings.models import Booking
from decimal import Decimal
from datetime import date, timedelta, datetime

# Create test users if they don't exist
try:
    agent = User.objects.get(username='testagent')
except User.DoesNotExist:
    agent = User.objects.create_user(
        username='testagent',
        email='agent@example.com',
        password='password123',
        role='agent',
        first_name='Agent',
        last_name='User'
    )

try:
    guest_user = User.objects.get(username='guestuser')
except User.DoesNotExist:
    guest_user = User.objects.create_user(
        username='guestuser',
        email='guest@example.com',
        password='password123',
        role='tenant',
        first_name='Guest',
        last_name='User'
    )

# Create test property if it doesn't exist
try:
    property_obj = Property.objects.get(title='Hono apartment')
except Property.DoesNotExist:
    property_obj = Property.objects.create(
        title='Hono apartment',
        description='A beautiful apartment in Kigali',
        property_type='apartment',
        status='available',
        owner=agent,
        address='Kigali Rwanda',
        city='Kigali',
        state='Kigali',
        country='Rwanda',
        zip_code='12345',
        bedrooms=2,
        bathrooms=1.5,
        area=1000,
        price_per_night=Decimal('100.00')
    )

# Create a booking with ID 79 if possible
try:
    existing_booking = Booking.objects.get(id=79)
    print(f"Booking with ID 79 already exists")
except Booking.DoesNotExist:
    # We might need to create bookings until we reach ID 79
    last_booking = Booking.objects.order_by('-id').first()
    
    if last_booking and last_booking.id < 79:
        # Create dummy bookings until we reach ID 79
        for i in range(last_booking.id + 1, 79):
            dummy_booking = Booking.objects.create(
                property=property_obj,
                tenant=guest_user,
                check_in_date=date.today(),
                check_out_date=date.today() + timedelta(days=1),
                guests=1,
                total_price=Decimal('100.00'),
                guest_name='Dummy Guest',
                guest_email='dummy@example.com',
                guest_phone='+1234567890',
                status='pending'
            )
            print(f"Created dummy booking with ID {dummy_booking.id}")
    
    # Create the actual booking we want with ID 79 (hopefully)
    booking = Booking.objects.create(
        property=property_obj,
        tenant=guest_user,
        check_in_date=date(2025, 6, 12),
        check_out_date=date(2025, 6, 30),
        guests=2,
        total_price=Decimal('3500.00'),
        guest_name='Arlene Doe',
        guest_email='kareraol1@gmail.com',
        guest_phone='+1234567890',
        status='confirmed',
        is_paid=True,
        payment_date=datetime(2025, 6, 1, 12, 0, 0)
    )
    
    print(f"Created booking with ID {booking.id}")

# Verify the booking we want to test
try:
    target_booking = Booking.objects.get(guest_email='kareraol1@gmail.com')
    print(f"Testing booking has ID {target_booking.id}, guest: {target_booking.guest_name}, email: {target_booking.guest_email}")
except Booking.DoesNotExist:
    print("Could not find the test booking with email kareraol1@gmail.com") 