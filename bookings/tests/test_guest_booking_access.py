import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from decimal import Decimal
from datetime import date, timedelta

from properties.models import Property
from bookings.models import Booking
from bookings.services import BookingService

User = get_user_model()


class GuestBookingAccessTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create a property owner
        self.owner = User.objects.create_user(
            username='owner',
            email='owner@example.com',
            password='testpass123',
            role='agent',
            birthday=date(1990, 1, 1)
        )
        
        # Create a guest user (inactive)
        self.guest_user = User.objects.create_user(
            username='guest@example.com',
            email='guest@example.com',
            password='testpass123',
            role='tenant',
            is_active=False,  # Guest users are inactive
            birthday=date(1992, 5, 15)
        )
        
        # Create a property
        self.property = Property.objects.create(
            title='Test Property',
            description='A nice test property',
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
            status='approved'
        )
        
        # Create a booking
        self.booking = Booking.objects.create(
            property=self.property,
            tenant=self.guest_user,
            check_in_date=date.today() + timedelta(days=1),
            check_out_date=date.today() + timedelta(days=3),
            guests=2,
            total_price=Decimal('200.00'),
            guest_name='John Doe',
            guest_email='guest@example.com',
            guest_phone='+1234567890',
            status='pending'
        )
        
        self.booking_service = BookingService()

    def test_guest_booking_access_success(self):
        """Test successful guest booking access with correct email"""
        # Test the service method directly
        booking_data = self.booking_service.get_booking_by_email(
            self.booking.id, 
            'guest@example.com'
        )
        
        self.assertIsNotNone(booking_data)
        self.assertEqual(booking_data['id'], self.booking.id)
        self.assertEqual(booking_data['guest_email'], 'guest@example.com')
        self.assertEqual(booking_data['guest_name'], 'John Doe')

    def test_guest_booking_access_wrong_email(self):
        """Test guest booking access with wrong email"""
        booking_data = self.booking_service.get_booking_by_email(
            self.booking.id, 
            'wrong@example.com'
        )
        
        self.assertIsNone(booking_data)

    def test_guest_booking_access_case_insensitive(self):
        """Test guest booking access with different case email"""
        booking_data = self.booking_service.get_booking_by_email(
            self.booking.id, 
            'GUEST@EXAMPLE.COM'
        )
        
        self.assertIsNotNone(booking_data)
        self.assertEqual(booking_data['id'], self.booking.id)

    def test_guest_booking_access_nonexistent_booking(self):
        """Test guest booking access with non-existent booking ID"""
        booking_data = self.booking_service.get_booking_by_email(
            99999, 
            'guest@example.com'
        )
        
        self.assertIsNone(booking_data)

    def test_guest_booking_api_access_success(self):
        """Test guest booking API access with correct email"""
        url = f'/api/bookings/{self.booking.id}/guest-access'
        data = {
            'guest_email': 'guest@example.com'
        }
        
        response = self.client.post(
            url, 
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(response_data['id'], self.booking.id)
        self.assertEqual(response_data['guest_email'], 'guest@example.com')

    def test_guest_booking_api_access_wrong_email(self):
        """Test guest booking API access with wrong email"""
        url = f'/api/bookings/{self.booking.id}/guest-access'
        data = {
            'guest_email': 'wrong@example.com'
        }
        
        response = self.client.post(
            url, 
            data=json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 404)
        self.assertIn('not found or email doesn\'t match', response.json()['message'])

    def test_guest_booking_api_access_invalid_data(self):
        """Test guest booking API access with invalid data"""
        url = f'/api/bookings/{self.booking.id}/guest-access'
        data = {
            'guest_email': 'invalid-email'
        }
        
        response = self.client.post(
            url, 
            data=json.dumps(data),
            content_type='application/json'
        )
        
        # Should return 422 for validation error or 400 for bad request
        self.assertIn(response.status_code, [400, 422]) 