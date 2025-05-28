import json
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone

from users.models import User
from properties.models import Property
from bookings.models import Booking
from payments.models import PaymentIntent
from payments.strategies import GuestPaymentStrategy, PaymentStrategyFactory


class GuestPaymentStrategyTestCase(TestCase):
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
        
        # Create an inactive user (guest tenant)
        self.guest_tenant = User.objects.create_user(
            username='guest',
            email='guest@example.com',
            password='password123',
            role=User.Role.TENANT,
            birthday=date(1990, 1, 1),
            is_active=False,
            first_name='Guest',
            last_name='User'
        )
        
        # Create a booking for the guest tenant
        tomorrow = date.today() + timedelta(days=1)
        next_week = date.today() + timedelta(days=7)
        
        self.booking = Booking.objects.create(
            property=self.property,
            tenant=self.guest_tenant,
            check_in_date=tomorrow,
            check_out_date=next_week,
            guests=2,
            total_price=Decimal('600.00'),
            guest_name='Guest User',
            guest_email='guest@example.com',
            guest_phone='123-456-7890'
        )
        
        self.client = Client()
    
    @patch('stripe.PaymentIntent.create')
    @patch('stripe.Customer.create')
    @patch('stripe.Customer.retrieve')
    def test_guest_payment_strategy(self, mock_customer_retrieve, mock_customer_create, mock_payment_intent_create):
        # Mock Stripe responses
        mock_customer = MagicMock()
        mock_customer.id = 'cus_test123'
        mock_customer_create.return_value = mock_customer
        mock_customer_retrieve.return_value = mock_customer
        
        mock_payment_intent = MagicMock()
        mock_payment_intent.id = 'pi_test123'
        mock_payment_intent.client_secret = 'pi_test123_secret_456'
        mock_payment_intent.status = 'requires_payment_method'
        mock_payment_intent_create.return_value = mock_payment_intent
        
        # Create a guest payment strategy
        strategy = GuestPaymentStrategy()
        
        # Test prepare_payment_user method
        user = strategy.prepare_payment_user(booking_id=self.booking.id)
        self.assertEqual(user.id, self.guest_tenant.id)
        self.assertEqual(user.stripe_customer_id, 'cus_test123')
        
        # Test create_payment_intent method
        payment_intent = strategy.create_payment_intent(booking_id=self.booking.id)
        
        # Verify the payment intent was created correctly
        self.assertEqual(payment_intent['stripe_payment_intent_id'], 'pi_test123')
        self.assertEqual(payment_intent['stripe_client_secret'], 'pi_test123_secret_456')
        self.assertEqual(payment_intent['booking']['id'], self.booking.id)
        
        # Verify a payment intent was saved to the database
        db_payment_intent = PaymentIntent.objects.filter(booking=self.booking).first()
        self.assertIsNotNone(db_payment_intent)
        self.assertEqual(db_payment_intent.stripe_payment_intent_id, 'pi_test123')
        self.assertEqual(db_payment_intent.user, self.guest_tenant)
    
    @patch('stripe.PaymentIntent.create')
    @patch('stripe.Customer.create')
    @patch('stripe.Customer.retrieve')
    def test_payment_strategy_factory(self, mock_customer_retrieve, mock_customer_create, mock_payment_intent_create):
        # Mock Stripe responses
        mock_customer = MagicMock()
        mock_customer.id = 'cus_test123'
        mock_customer_create.return_value = mock_customer
        mock_customer_retrieve.return_value = mock_customer
        
        mock_payment_intent = MagicMock()
        mock_payment_intent.id = 'pi_test123'
        mock_payment_intent.client_secret = 'pi_test123_secret_456'
        mock_payment_intent.status = 'requires_payment_method'
        mock_payment_intent_create.return_value = mock_payment_intent
        
        # Test factory with logged-in user
        logged_in_user = User.objects.create_user(
            username='loggedin',
            email='loggedin@example.com',
            password='password123',
            role=User.Role.TENANT,
            birthday=date(1985, 1, 1),
            is_active=True
        )
        
        strategy = PaymentStrategyFactory.create_strategy(request_user=logged_in_user)
        self.assertEqual(strategy.__class__.__name__, 'LoggedInPaymentStrategy')
        
        # Test factory with guest user (None)
        strategy = PaymentStrategyFactory.create_strategy(request_user=None)
        self.assertEqual(strategy.__class__.__name__, 'GuestPaymentStrategy')
    
    @patch('payments.services.PaymentService.create_guest_payment_intent')
    def test_guest_payment_intent_api(self, mock_create_guest_payment_intent):
        # Mock the service method response
        mock_create_guest_payment_intent.return_value = {
            'id': 1,
            'booking': {
                'id': self.booking.id,
                'property': {
                    'id': self.property.id,
                    'title': 'Test Property'
                },
                'check_in_date': self.booking.check_in_date,
                'check_out_date': self.booking.check_out_date
            },
            'amount': self.booking.total_price,
            'currency': 'usd',
            'status': 'requires_payment_method',
            'stripe_payment_intent_id': 'pi_test123',
            'stripe_client_secret': 'pi_test123_secret_456',
            'created_at': timezone.now()
        }
        
        # Test the guest-intents endpoint
        url = '/api/payments/guest-intents'
        data = {
            'booking_id': self.booking.id,
            'setup_future_usage': None
        }
        
        response = self.client.post(
            url, 
            json.dumps(data), 
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 201)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['stripe_payment_intent_id'], 'pi_test123')
        self.assertEqual(response_data['stripe_client_secret'], 'pi_test123_secret_456')
        
        # Test the quick-intent endpoint
        url = '/api/payments/quick-intent'
        data = {
            'booking_id': self.booking.id,
            'setup_future_usage': None
        }
        
        response = self.client.post(
            url, 
            json.dumps(data), 
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['id'], 'pi_test123')
        self.assertEqual(response_data['client_secret'], 'pi_test123_secret_456')

    @patch('payments.services.PaymentService.confirm_payment')
    def test_guest_payment_confirmation_api(self, mock_confirm_payment):
        # Create a payment intent for the guest booking
        payment_intent = PaymentIntent.objects.create(
            booking=self.booking,
            user=self.guest_tenant,
            amount=self.booking.total_price,
            currency='usd',
            stripe_payment_intent_id='pi_test123',
            stripe_client_secret='pi_test123_secret_456',
            status='requires_payment_method'
        )
        
        # Mock the service method response
        mock_confirm_payment.return_value = {
            'id': payment_intent.id,
            'booking': {
                'id': self.booking.id,
                'property': {
                    'id': self.property.id,
                    'title': 'Test Property'
                },
                'check_in_date': self.booking.check_in_date,
                'check_out_date': self.booking.check_out_date
            },
            'amount': self.booking.total_price,
            'currency': 'usd',
            'status': 'succeeded',
            'stripe_payment_intent_id': 'pi_test123',
            'requires_action': False,
            'payment_intent_client_secret': None,
            'created_at': payment_intent.created_at
        }
        
        # Test the guest confirmation endpoint
        url = '/api/payments/guest/confirm'
        data = {
            'payment_intent_id': 'pi_test123',
            'payment_method_id': 'pm_test456',
            'save_payment_method': False
        }
        
        response = self.client.post(
            url, 
            json.dumps(data), 
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'succeeded')
        self.assertEqual(response_data['stripe_payment_intent_id'], 'pi_test123')
        
        # Verify the service method was called with the guest user
        mock_confirm_payment.assert_called_once_with(
            user=self.guest_tenant,
            payment_intent_id='pi_test123',
            payment_method_id='pm_test456',
            save_payment_method=False
        )

    def test_guest_confirmation_rejects_active_user_payment(self):
        # Create an active user
        active_user = User.objects.create_user(
            username='activeuser',
            email='active@example.com',
            password='password123',
            role=User.Role.TENANT,
            birthday=date(1985, 1, 1),
            is_active=True  # Active user
        )
        
        # Create a payment intent for the active user
        payment_intent = PaymentIntent.objects.create(
            booking=self.booking,
            user=active_user,  # Active user instead of guest
            amount=self.booking.total_price,
            currency='usd',
            stripe_payment_intent_id='pi_test789',
            stripe_client_secret='pi_test789_secret_abc',
            status='requires_payment_method'
        )
        
        # Try to confirm using guest endpoint
        url = '/api/payments/guest/confirm'
        data = {
            'payment_intent_id': 'pi_test789',
            'payment_method_id': 'pm_test456',
            'save_payment_method': False
        }
        
        response = self.client.post(
            url, 
            json.dumps(data), 
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.content)
        self.assertIn('This endpoint is only for guest payments', response_data['message']) 