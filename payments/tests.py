from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from properties.models import Property
from bookings.models import Booking
from .models import Payment, PaymentMethod, PaymentIntent
from .repositories import PaymentRepository, PaymentMethodRepository, PaymentIntentRepository
from .services import PaymentService

User = get_user_model()


class PaymentModelTestCase(TestCase):
    """Test case for the Payment model"""

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

        # Create test payment
        self.payment = Payment.objects.create(
            booking=self.booking,
            user=self.tenant,
            amount=Decimal('400.00'),
            currency='usd',
            status=Payment.PaymentStatus.PENDING,
            stripe_payment_intent_id='pi_test123',
            stripe_payment_method_id='pm_test123',
            stripe_customer_id='cus_test123'
        )

    def test_payment_creation(self):
        """Test that a payment can be created"""
        self.assertEqual(self.payment.booking, self.booking)
        self.assertEqual(self.payment.user, self.tenant)
        self.assertEqual(self.payment.amount, Decimal('400.00'))
        self.assertEqual(self.payment.currency, 'usd')
        self.assertEqual(self.payment.status, Payment.PaymentStatus.PENDING)
        self.assertEqual(self.payment.stripe_payment_intent_id, 'pi_test123')
        self.assertEqual(self.payment.stripe_payment_method_id, 'pm_test123')
        self.assertEqual(self.payment.stripe_customer_id, 'cus_test123')

    def test_payment_str_representation(self):
        """Test the string representation of a payment"""
        expected_str = f"Payment {self.payment.id} - {self.booking} - {self.payment.amount} {self.payment.currency}"
        self.assertEqual(str(self.payment), expected_str)

    def test_payment_completion(self):
        """Test that a payment can be marked as completed"""
        self.payment.status = Payment.PaymentStatus.COMPLETED
        self.payment.save()

        # Refresh booking from database
        self.booking.refresh_from_db()

        # Check that payment is marked as completed
        self.assertIsNotNone(self.payment.completed_at)

        # Check that booking is marked as paid
        self.assertTrue(self.booking.is_paid)
        self.assertIsNotNone(self.booking.payment_date)
        self.assertEqual(self.booking.payment_id, 'pi_test123')


class PaymentMethodModelTestCase(TestCase):
    """Test case for the PaymentMethod model"""

    def setUp(self):
        # Create test user
        self.user = User.objects.create_user(
            username='testuser',
            email='user@example.com',
            password='password123',
            role='tenant'
        )

        # Create test payment method
        self.payment_method = PaymentMethod.objects.create(
            user=self.user,
            type=PaymentMethod.PaymentType.CARD,
            is_default=True,
            card_brand='visa',
            card_last4='4242',
            card_exp_month=12,
            card_exp_year=2025,
            stripe_payment_method_id='pm_test123'
        )

    def test_payment_method_creation(self):
        """Test that a payment method can be created"""
        self.assertEqual(self.payment_method.user, self.user)
        self.assertEqual(self.payment_method.type, PaymentMethod.PaymentType.CARD)
        self.assertTrue(self.payment_method.is_default)
        self.assertEqual(self.payment_method.card_brand, 'visa')
        self.assertEqual(self.payment_method.card_last4, '4242')
        self.assertEqual(self.payment_method.card_exp_month, 12)
        self.assertEqual(self.payment_method.card_exp_year, 2025)
        self.assertEqual(self.payment_method.stripe_payment_method_id, 'pm_test123')

    def test_payment_method_str_representation(self):
        """Test the string representation of a payment method"""
        expected_str = f"visa **** 4242"
        self.assertEqual(str(self.payment_method), expected_str)

    def test_payment_method_default_behavior(self):
        """Test that only one payment method can be default"""
        # Create another payment method
        payment_method2 = PaymentMethod.objects.create(
            user=self.user,
            type=PaymentMethod.PaymentType.CARD,
            is_default=True,
            card_brand='mastercard',
            card_last4='5555',
            card_exp_month=1,
            card_exp_year=2026,
            stripe_payment_method_id='pm_test456'
        )

        # Refresh first payment method from database
        self.payment_method.refresh_from_db()

        # Check that the first payment method is no longer default
        self.assertFalse(self.payment_method.is_default)

        # Check that the second payment method is default
        self.assertTrue(payment_method2.is_default)


class PaymentIntentModelTestCase(TestCase):
    """Test case for the PaymentIntent model"""

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

        # Create test payment
        self.payment = Payment.objects.create(
            booking=self.booking,
            user=self.tenant,
            amount=Decimal('400.00'),
            currency='usd',
            status=Payment.PaymentStatus.PENDING,
            stripe_payment_intent_id='pi_test123',
            stripe_payment_method_id='pm_test123',
            stripe_customer_id='cus_test123'
        )

        # Create test payment intent
        self.payment_intent = PaymentIntent.objects.create(
            booking=self.booking,
            user=self.tenant,
            payment=self.payment,
            amount=Decimal('400.00'),
            currency='usd',
            status=PaymentIntent.PaymentIntentStatus.REQUIRES_PAYMENT_METHOD,
            stripe_payment_intent_id='pi_test123',
            stripe_client_secret='pi_test123_secret_test123'
        )

    def test_payment_intent_creation(self):
        """Test that a payment intent can be created"""
        self.assertEqual(self.payment_intent.booking, self.booking)
        self.assertEqual(self.payment_intent.user, self.tenant)
        self.assertEqual(self.payment_intent.payment, self.payment)
        self.assertEqual(self.payment_intent.amount, Decimal('400.00'))
        self.assertEqual(self.payment_intent.currency, 'usd')
        self.assertEqual(self.payment_intent.status, PaymentIntent.PaymentIntentStatus.REQUIRES_PAYMENT_METHOD)
        self.assertEqual(self.payment_intent.stripe_payment_intent_id, 'pi_test123')
        self.assertEqual(self.payment_intent.stripe_client_secret, 'pi_test123_secret_test123')

    def test_payment_intent_str_representation(self):
        """Test the string representation of a payment intent"""
        expected_str = f"Payment Intent {self.payment_intent.id} - {self.booking} - {self.payment_intent.amount} {self.payment_intent.currency}"
        self.assertEqual(str(self.payment_intent), expected_str)


class PaymentRepositoryTestCase(TestCase):
    """Test case for the PaymentRepository"""

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

        # Initialize repository
        self.repository = PaymentRepository()

    def test_create_payment(self):
        """Test creating a payment through the repository"""
        payment = self.repository.create_payment(
            booking=self.booking,
            user=self.tenant,
            amount=Decimal('400.00'),
            currency='usd',
            status=Payment.PaymentStatus.PENDING,
            stripe_payment_intent_id='pi_test123',
            stripe_payment_method_id='pm_test123',
            stripe_customer_id='cus_test123'
        )

        self.assertIsNotNone(payment.id)
        self.assertEqual(payment.booking, self.booking)
        self.assertEqual(payment.user, self.tenant)
        self.assertEqual(payment.amount, Decimal('400.00'))
        self.assertEqual(payment.currency, 'usd')
        self.assertEqual(payment.status, Payment.PaymentStatus.PENDING)
        self.assertEqual(payment.stripe_payment_intent_id, 'pi_test123')
        self.assertEqual(payment.stripe_payment_method_id, 'pm_test123')
        self.assertEqual(payment.stripe_customer_id, 'cus_test123')

    def test_get_payment_by_id(self):
        """Test retrieving a payment by ID"""
        # Create a payment
        payment = self.repository.create_payment(
            booking=self.booking,
            user=self.tenant,
            amount=Decimal('400.00'),
            currency='usd',
            status=Payment.PaymentStatus.PENDING,
            stripe_payment_intent_id='pi_test123'
        )

        # Retrieve the payment
        retrieved_payment = self.repository.get_payment_by_id(payment.id)

        self.assertEqual(retrieved_payment, payment)

    def test_get_payments_by_user(self):
        """Test retrieving payments by user"""
        # Create multiple payments
        payment1 = self.repository.create_payment(
            booking=self.booking,
            user=self.tenant,
            amount=Decimal('400.00'),
            currency='usd',
            status=Payment.PaymentStatus.PENDING,
            stripe_payment_intent_id='pi_test123'
        )

        payment2 = self.repository.create_payment(
            booking=self.booking,
            user=self.tenant,
            amount=Decimal('200.00'),
            currency='usd',
            status=Payment.PaymentStatus.COMPLETED,
            stripe_payment_intent_id='pi_test456'
        )

        # Retrieve payments by user
        payments = self.repository.get_payments_by_user(self.tenant)

        self.assertEqual(len(payments), 2)
        self.assertIn(payment1, payments)
        self.assertIn(payment2, payments)

    def test_get_payments_by_booking(self):
        """Test retrieving payments by booking"""
        # Create multiple payments
        payment1 = self.repository.create_payment(
            booking=self.booking,
            user=self.tenant,
            amount=Decimal('400.00'),
            currency='usd',
            status=Payment.PaymentStatus.PENDING,
            stripe_payment_intent_id='pi_test123'
        )

        payment2 = self.repository.create_payment(
            booking=self.booking,
            user=self.tenant,
            amount=Decimal('200.00'),
            currency='usd',
            status=Payment.PaymentStatus.COMPLETED,
            stripe_payment_intent_id='pi_test456'
        )

        # Retrieve payments by booking
        payments = self.repository.get_payments_by_booking(self.booking)

        self.assertEqual(len(payments), 2)
        self.assertIn(payment1, payments)
        self.assertIn(payment2, payments)


class PaymentServiceTestCase(TestCase):
    """Test case for the PaymentService"""

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

        # Initialize service with mocked repositories
        self.payment_repository = PaymentRepository()
        self.payment_method_repository = PaymentMethodRepository()
        self.payment_intent_repository = PaymentIntentRepository()

        self.service = PaymentService(
            payment_repository=self.payment_repository,
            payment_method_repository=self.payment_method_repository,
            payment_intent_repository=self.payment_intent_repository
        )

    @patch('stripe.Customer.create')
    @patch('stripe.PaymentIntent.create')
    def test_create_payment_intent(self, mock_payment_intent_create, mock_customer_create):
        """Test creating a payment intent through the service"""
        # Mock Stripe responses
        mock_customer = MagicMock()
        mock_customer.id = 'cus_test123'
        mock_customer_create.return_value = mock_customer

        mock_payment_intent = MagicMock()
        mock_payment_intent.id = 'pi_test123'
        mock_payment_intent.client_secret = 'pi_test123_secret_test123'
        mock_payment_intent.status = 'requires_payment_method'
        mock_payment_intent_create.return_value = mock_payment_intent

        # Create payment intent
        with patch.object(self.service, '_get_or_create_stripe_customer', return_value=mock_customer):
            payment_intent = self.service.create_payment_intent(
                user=self.tenant,
                booking_id=self.booking.id
            )

        # Check that the payment intent was created correctly
        self.assertEqual(payment_intent['booking']['id'], self.booking.id)
        self.assertEqual(payment_intent['amount'], self.booking.total_price)
        self.assertEqual(payment_intent['stripe_payment_intent_id'], 'pi_test123')
        self.assertEqual(payment_intent['stripe_client_secret'], 'pi_test123_secret_test123')
        self.assertEqual(payment_intent['status'], 'requires_payment_method')

    def test_get_stripe_public_key(self):
        """Test getting the Stripe publishable key"""
        with patch('django.conf.settings.STRIPE_PUBLISHABLE_KEY', 'pk_test_123'):
            public_key = self.service.get_stripe_public_key()
            self.assertEqual(public_key, 'pk_test_123')