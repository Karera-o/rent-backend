from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal
import json

from properties.models import Property
from .models import Booking, BookingReview
from .repositories import BookingRepository
from .services import BookingService

User = get_user_model()


class BookingModelTestCase(TestCase):
    """Test case for the Booking model"""

    def setUp(self):
        # Create test users
        self.tenant = User.objects.create_user(
            username='testtenant',
            email='tenant@example.com',
            password='password123',
            role='tenant'
        )

        self.agent = User.objects.create_user(
            username='testagent',
            email='agent@example.com',
            password='password123',
            role='agent'
        )

        # Create test property
        self.property = Property.objects.create(
            title='Test Property',
            description='A test property',
            property_type='apartment',
            status='approved',
            owner=self.agent,
            address='123 Test St',
            city='Test City',
            state='Test State',
            country='Test Country',
            zip_code='12345',
            bedrooms=2,
            bathrooms=1.5,
            area=1000,
            price_per_night=Decimal('100.00')
        )

        # Create test booking
        self.today = timezone.now().date()
        self.check_in_date = self.today + timedelta(days=1)
        self.check_out_date = self.today + timedelta(days=5)

        self.booking = Booking.objects.create(
            property=self.property,
            tenant=self.tenant,
            check_in_date=self.check_in_date,
            check_out_date=self.check_out_date,
            guests=2,
            total_price=Decimal('400.00'),
            status=Booking.BookingStatus.PENDING,
            guest_name='Test Guest',
            guest_email='guest@example.com',
            guest_phone='123-456-7890'
        )

    def test_booking_creation(self):
        """Test that a booking can be created"""
        self.assertEqual(self.booking.property, self.property)
        self.assertEqual(self.booking.tenant, self.tenant)
        self.assertEqual(self.booking.check_in_date, self.check_in_date)
        self.assertEqual(self.booking.check_out_date, self.check_out_date)
        self.assertEqual(self.booking.guests, 2)
        self.assertEqual(self.booking.total_price, Decimal('400.00'))
        self.assertEqual(self.booking.status, Booking.BookingStatus.PENDING)
        self.assertEqual(self.booking.guest_name, 'Test Guest')
        self.assertEqual(self.booking.guest_email, 'guest@example.com')
        self.assertEqual(self.booking.guest_phone, '123-456-7890')

    def test_booking_str_representation(self):
        """Test the string representation of a booking"""
        expected_str = f"Booking {self.booking.id} - {self.property.title} ({self.check_in_date} to {self.check_out_date})"
        self.assertEqual(str(self.booking), expected_str)


class BookingReviewModelTestCase(TestCase):
    """Test case for the BookingReview model"""

    def setUp(self):
        # Create test users
        self.tenant = User.objects.create_user(
            username='testtenant',
            email='tenant@example.com',
            password='password123',
            role='tenant'
        )

        self.agent = User.objects.create_user(
            username='testagent',
            email='agent@example.com',
            password='password123',
            role='agent'
        )

        # Create test property
        self.property = Property.objects.create(
            title='Test Property',
            description='A test property',
            property_type='apartment',
            status='approved',
            owner=self.agent,
            address='123 Test St',
            city='Test City',
            state='Test State',
            country='Test Country',
            zip_code='12345',
            bedrooms=2,
            bathrooms=1.5,
            area=1000,
            price_per_night=Decimal('100.00')
        )

        # Create test booking
        self.today = timezone.now().date()
        self.booking = Booking.objects.create(
            property=self.property,
            tenant=self.tenant,
            check_in_date=self.today - timedelta(days=5),
            check_out_date=self.today - timedelta(days=1),
            guests=2,
            total_price=Decimal('400.00'),
            status=Booking.BookingStatus.COMPLETED,
            guest_name='Test Guest',
            guest_email='guest@example.com',
            guest_phone='123-456-7890'
        )

        # Create test review
        self.review = BookingReview.objects.create(
            booking=self.booking,
            rating=5,
            comment='Great stay!'
        )

    def test_review_creation(self):
        """Test that a review can be created"""
        self.assertEqual(self.review.booking, self.booking)
        self.assertEqual(self.review.rating, 5)
        self.assertEqual(self.review.comment, 'Great stay!')

    def test_review_str_representation(self):
        """Test the string representation of a review"""
        expected_str = f"Review for {self.booking}"
        self.assertEqual(str(self.review), expected_str)


class BookingRepositoryTestCase(TestCase):
    """Test case for the BookingRepository"""

    def setUp(self):
        # Create test users
        self.tenant = User.objects.create_user(
            username='testtenant',
            email='tenant@example.com',
            password='password123',
            role='tenant'
        )

        self.agent = User.objects.create_user(
            username='testagent',
            email='agent@example.com',
            password='password123',
            role='agent'
        )

        # Create test property
        self.property = Property.objects.create(
            title='Test Property',
            description='A test property',
            property_type='apartment',
            status='approved',
            owner=self.agent,
            address='123 Test St',
            city='Test City',
            state='Test State',
            country='Test Country',
            zip_code='12345',
            bedrooms=2,
            bathrooms=1.5,
            area=1000,
            price_per_night=Decimal('100.00')
        )

        # Initialize repository
        self.repository = BookingRepository()

        # Set up dates
        self.today = timezone.now().date()
        self.check_in_date = self.today + timedelta(days=1)
        self.check_out_date = self.today + timedelta(days=5)

    def test_create_booking(self):
        """Test creating a booking through the repository"""
        booking = self.repository.create_booking(
            property_obj=self.property,
            tenant=self.tenant,
            check_in_date=self.check_in_date,
            check_out_date=self.check_out_date,
            guests=2,
            total_price=Decimal('400.00'),
            guest_name='Test Guest',
            guest_email='guest@example.com',
            guest_phone='123-456-7890'
        )

        self.assertIsNotNone(booking.id)
        self.assertEqual(booking.property, self.property)
        self.assertEqual(booking.tenant, self.tenant)
        self.assertEqual(booking.check_in_date, self.check_in_date)
        self.assertEqual(booking.check_out_date, self.check_out_date)
        self.assertEqual(booking.guests, 2)
        self.assertEqual(booking.total_price, Decimal('400.00'))
        self.assertEqual(booking.status, Booking.BookingStatus.PENDING)

    def test_get_booking_by_id(self):
        """Test retrieving a booking by ID"""
        # Create a booking
        booking = self.repository.create_booking(
            property_obj=self.property,
            tenant=self.tenant,
            check_in_date=self.check_in_date,
            check_out_date=self.check_out_date,
            guests=2,
            total_price=Decimal('400.00'),
            guest_name='Test Guest',
            guest_email='guest@example.com',
            guest_phone='123-456-7890'
        )

        # Retrieve the booking
        retrieved_booking = self.repository.get_booking_by_id(booking.id)

        self.assertEqual(retrieved_booking, booking)

    def test_get_bookings_by_tenant(self):
        """Test retrieving bookings by tenant"""
        # Create multiple bookings
        booking1 = self.repository.create_booking(
            property_obj=self.property,
            tenant=self.tenant,
            check_in_date=self.check_in_date,
            check_out_date=self.check_out_date,
            guests=2,
            total_price=Decimal('400.00'),
            guest_name='Test Guest',
            guest_email='guest@example.com',
            guest_phone='123-456-7890'
        )

        booking2 = self.repository.create_booking(
            property_obj=self.property,
            tenant=self.tenant,
            check_in_date=self.check_in_date + timedelta(days=10),
            check_out_date=self.check_out_date + timedelta(days=10),
            guests=3,
            total_price=Decimal('500.00'),
            guest_name='Test Guest 2',
            guest_email='guest2@example.com',
            guest_phone='123-456-7891'
        )

        # Retrieve bookings by tenant
        bookings = self.repository.get_bookings_by_tenant(self.tenant)

        self.assertEqual(len(bookings), 2)
        self.assertIn(booking1, bookings)
        self.assertIn(booking2, bookings)

    def test_check_property_availability(self):
        """Test checking property availability"""
        # Initially, the property should be available
        is_available = self.repository.check_property_availability(
            property_obj=self.property,
            check_in_date=self.check_in_date,
            check_out_date=self.check_out_date
        )

        self.assertTrue(is_available)

        # Create a confirmed booking
        self.repository.create_booking(
            property_obj=self.property,
            tenant=self.tenant,
            check_in_date=self.check_in_date,
            check_out_date=self.check_out_date,
            guests=2,
            total_price=Decimal('400.00'),
            guest_name='Test Guest',
            guest_email='guest@example.com',
            guest_phone='123-456-7890',
            status=Booking.BookingStatus.CONFIRMED
        )

        # Now the property should not be available for the same dates
        is_available = self.repository.check_property_availability(
            property_obj=self.property,
            check_in_date=self.check_in_date,
            check_out_date=self.check_out_date
        )

        self.assertFalse(is_available)

        # But it should be available for different dates
        is_available = self.repository.check_property_availability(
            property_obj=self.property,
            check_in_date=self.check_in_date + timedelta(days=10),
            check_out_date=self.check_out_date + timedelta(days=10)
        )

        self.assertTrue(is_available)


class BookingServiceTestCase(TestCase):
    """Test case for the BookingService"""

    def setUp(self):
        # Create test users
        self.tenant = User.objects.create_user(
            username='testtenant',
            email='tenant@example.com',
            password='password123',
            role='tenant'
        )

        self.agent = User.objects.create_user(
            username='testagent',
            email='agent@example.com',
            password='password123',
            role='agent'
        )

        # Create test property
        self.property = Property.objects.create(
            title='Test Property',
            description='A test property',
            property_type='apartment',
            status='approved',
            owner=self.agent,
            address='123 Test St',
            city='Test City',
            state='Test State',
            country='Test Country',
            zip_code='12345',
            bedrooms=2,
            bathrooms=1.5,
            area=1000,
            price_per_night=Decimal('100.00')
        )

        # Initialize service
        self.service = BookingService()

        # Set up dates
        self.today = timezone.now().date()
        self.check_in_date = self.today + timedelta(days=1)
        self.check_out_date = self.today + timedelta(days=5)

    def test_create_booking(self):
        """Test creating a booking through the service"""
        booking = self.service.create_booking(
            tenant=self.tenant,
            property_id=self.property.id,
            check_in_date=self.check_in_date,
            check_out_date=self.check_out_date,
            guests=2,
            guest_name='Test Guest',
            guest_email='guest@example.com',
            guest_phone='123-456-7890'
        )

        self.assertIsNotNone(booking.id)
        self.assertEqual(booking.property, self.property)
        self.assertEqual(booking.tenant, self.tenant)
        self.assertEqual(booking.check_in_date, self.check_in_date)
        self.assertEqual(booking.check_out_date, self.check_out_date)
        self.assertEqual(booking.guests, 2)
        # Total price should be calculated based on property price and duration
        expected_price = self.property.price_per_night * (self.check_out_date - self.check_in_date).days
        self.assertEqual(booking.total_price, expected_price)
        self.assertEqual(booking.status, Booking.BookingStatus.PENDING)

    def test_create_booking_validation_errors(self):
        """Test validation errors when creating a booking"""
        # Test past check-in date
        with self.assertRaises(ValueError):
            self.service.create_booking(
                tenant=self.tenant,
                property_id=self.property.id,
                check_in_date=self.today - timedelta(days=1),
                check_out_date=self.check_out_date,
                guests=2,
                guest_name='Test Guest',
                guest_email='guest@example.com',
                guest_phone='123-456-7890'
            )

        # Test check-out date before check-in date
        with self.assertRaises(ValueError):
            self.service.create_booking(
                tenant=self.tenant,
                property_id=self.property.id,
                check_in_date=self.check_in_date,
                check_out_date=self.check_in_date - timedelta(days=1),
                guests=2,
                guest_name='Test Guest',
                guest_email='guest@example.com',
                guest_phone='123-456-7890'
            )

        # Test non-existent property
        with self.assertRaises(ValueError):
            self.service.create_booking(
                tenant=self.tenant,
                property_id=9999,  # Non-existent ID
                check_in_date=self.check_in_date,
                check_out_date=self.check_out_date,
                guests=2,
                guest_name='Test Guest',
                guest_email='guest@example.com',
                guest_phone='123-456-7890'
            )

    def test_get_tenant_bookings(self):
        """Test retrieving bookings for a tenant"""
        # Create bookings
        booking1 = self.service.create_booking(
            tenant=self.tenant,
            property_id=self.property.id,
            check_in_date=self.check_in_date,
            check_out_date=self.check_out_date,
            guests=2,
            guest_name='Test Guest',
            guest_email='guest@example.com',
            guest_phone='123-456-7890'
        )

        booking2 = self.service.create_booking(
            tenant=self.tenant,
            property_id=self.property.id,
            check_in_date=self.check_in_date + timedelta(days=10),
            check_out_date=self.check_out_date + timedelta(days=10),
            guests=3,
            guest_name='Test Guest 2',
            guest_email='guest2@example.com',
            guest_phone='123-456-7891'
        )

        # Get tenant bookings
        result = self.service.get_tenant_bookings(self.tenant)

        self.assertEqual(result['total'], 2)
        self.assertEqual(len(result['items']), 2)

        # Check that the bookings are in the result
        booking_ids = [item['id'] for item in result['items']]
        self.assertIn(booking1.id, booking_ids)
        self.assertIn(booking2.id, booking_ids)


# Note: API tests are skipped for now as they require more complex setup with JWT authentication
# class BookingAPITestCase(TestCase):
#     """Test case for the Booking API endpoints"""
#     pass