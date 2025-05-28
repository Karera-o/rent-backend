import json
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from users.models import User
from properties.models import Property
from bookings.models import Booking


class GuestBookingAPITestCase(TestCase):
    def setUp(self):
        # Create a property owner
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='password123',
            role=User.Role.AGENT,
            birthday=date(1985, 1, 1),
            is_active=True
        )
        
        # Create a property
        self.property = Property.objects.create(
            title='Test Property',
            description='Test Description',
            property_type='apartment',
            address='123 Test St',
            city='Test City',
            state='Test State',
            country='Test Country',
            zip_code='12345',
            area=800,  # Required field
            price_per_night=Decimal('100.00'),
            bedrooms=2,
            bathrooms=1,
            owner=self.owner,
            status=Property.PropertyStatus.APPROVED
        )
        
        self.client = Client()
    
    def test_regular_booking_endpoint_requires_auth(self):
        """Test that the regular booking endpoint requires authentication"""
        tomorrow = date.today() + timedelta(days=1)
        next_week = date.today() + timedelta(days=7)
        
        data = {
            'property_id': self.property.id,
            'check_in_date': tomorrow.isoformat(),
            'check_out_date': next_week.isoformat(),
            'guests': 2,
            'guest_name': 'Test Guest',
            'guest_email': 'guest@example.com',
            'guest_phone': '123-456-7890',
            'special_requests': 'None'
        }
        
        # This should fail with 401 Unauthorized
        response = self.client.post(
            '/api/bookings/', 
            json.dumps(data), 
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)
    
    def test_guest_booking_endpoint_works_without_auth(self):
        """Test that the guest booking endpoint works without authentication"""
        tomorrow = date.today() + timedelta(days=1)
        next_week = date.today() + timedelta(days=7)
        
        data = {
            'property_id': self.property.id,
            'check_in_date': tomorrow.isoformat(),
            'check_out_date': next_week.isoformat(),
            'guests': 2,
            'guest_name': 'Test Guest',
            'guest_email': 'guest@example.com',
            'guest_phone': '123-456-7890',
            'special_requests': 'None',
            'user_info': {
                'full_name': 'Test Guest',
                'email': 'guest@example.com',
                'phone_number': '123-456-7890',
                'birthday': '1980-01-01'
            }
        }
        
        # This should succeed with 201 Created
        response = self.client.post(
            '/api/bookings/guest', 
            json.dumps(data), 
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        
        # Verify a booking was created
        self.assertEqual(Booking.objects.count(), 1)
        booking = Booking.objects.first()
        self.assertEqual(booking.property.id, self.property.id)
        self.assertEqual(booking.guest_email, 'guest@example.com')
        
        # Verify a new inactive user was created
        user = User.objects.get(email='guest@example.com')
        self.assertFalse(user.is_active)
        self.assertEqual(user.role, User.Role.TENANT)
        self.assertEqual(user.first_name, 'Test')
        self.assertEqual(user.last_name, 'Guest') 