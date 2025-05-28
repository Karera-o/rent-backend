import logging
import uuid
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

import stripe
from django.conf import settings
from django.utils import timezone

from payments.models import PaymentIntent
from payments.repositories import PaymentIntentRepository
from bookings.repositories import BookingRepository
from users.models import User
from users.repositories import UserRepository

logger = logging.getLogger('house_rental')

class PaymentStrategy(ABC):
    """
    Abstract base class for payment strategies.
    """
    @abstractmethod
    def prepare_payment_user(self, **kwargs) -> User:
        """
        Prepare the user for payment processing.
        """
        pass
        
    @abstractmethod
    def create_payment_intent(self, booking_id: int, setup_future_usage: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a payment intent for a booking.
        """
        pass


class LoggedInPaymentStrategy(PaymentStrategy):
    """
    Strategy for creating payment intents for logged-in users.
    """
    def __init__(self, user: User, payment_intent_repository: PaymentIntentRepository = None, 
                 booking_repository: BookingRepository = None):
        self.user = user
        self.payment_intent_repository = payment_intent_repository or PaymentIntentRepository()
        self.booking_repository = booking_repository or BookingRepository()

    def prepare_payment_user(self, **kwargs) -> User:
        """
        For logged-in users, just validate the user and return them.
        """
        # Ensure the user has a stripe_customer_id
        if not self.user.stripe_customer_id:
            # Create a Stripe customer for this user
            customer = self._get_or_create_stripe_customer(self.user)
            # Update user with Stripe customer ID if needed
            if self.user.stripe_customer_id != customer.id:
                self.user.stripe_customer_id = customer.id
                self.user.save(update_fields=['stripe_customer_id'])
                
        return self.user
        
    def create_payment_intent(self, booking_id: int, setup_future_usage: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a payment intent for a booking using a logged-in user.
        """
        # Get the booking
        booking = self.booking_repository.get_booking_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking with ID {booking_id} not found")

        # Check if the user is the tenant of the booking
        if booking.tenant.id != self.user.id and self.user.role != User.Role.ADMIN:
            raise ValueError("You don't have permission to create a payment intent for this booking")

        # Check if the booking is already paid
        if booking.is_paid:
            raise ValueError("This booking is already paid")

        # Check if there's an existing active payment intent for this booking
        existing_intent = self.payment_intent_repository.get_active_payment_intent_for_booking(booking.id)
        if existing_intent:
            logger.info(f"Using existing payment intent: {existing_intent.stripe_payment_intent_id} for booking {booking.id}")
            return {
                'id': existing_intent.id,
                'booking': {
                    'id': booking.id,
                    'property': {
                        'id': booking.property.id,
                        'title': booking.property.title
                    },
                    'check_in_date': booking.check_in_date,
                    'check_out_date': booking.check_out_date
                },
                'amount': existing_intent.amount,
                'currency': existing_intent.currency,
                'status': existing_intent.status,
                'stripe_payment_intent_id': existing_intent.stripe_payment_intent_id,
                'stripe_client_secret': existing_intent.stripe_client_secret,
                'created_at': existing_intent.created_at
            }
            
        # Prepare the payment user
        payment_user = self.prepare_payment_user()
        
        # Create payment intent
        return self._create_stripe_payment_intent(booking, payment_user, setup_future_usage)
    
    def _create_stripe_payment_intent(self, booking, user, setup_future_usage=None):
        """
        Create a Stripe payment intent.
        """
        # Check if Stripe API keys are configured
        use_mock_stripe = False
        if not settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY == 'sk_test_your_test_key' or 'XXXX' in settings.STRIPE_SECRET_KEY:
            logger.warning("Using mock Stripe implementation because API keys are not properly configured")
            use_mock_stripe = True

        try:
            if use_mock_stripe:
                # Mock Stripe customer and payment intent for testing
                customer_id = f"cus_mock_{user.id}"
                payment_intent_id = f"pi_mock_{booking.id}_{int(timezone.now().timestamp())}"
                client_secret = f"{payment_intent_id}_secret_{user.id}"

                # Create a mock payment intent object
                class MockPaymentIntent:
                    def __init__(self, id, client_secret, status):
                        self.id = id
                        self.client_secret = client_secret
                        self.status = status

                payment_intent = MockPaymentIntent(
                    id=payment_intent_id,
                    client_secret=client_secret,
                    status='requires_payment_method'
                )

                logger.info(f"Created mock payment intent: {payment_intent_id}")
            else:
                # Get or create Stripe customer
                customer = self._get_or_create_stripe_customer(user)
                customer_id = customer.id

                # Create payment intent with idempotency key to prevent duplicates
                idempotency_key = f"booking_{booking.id}_{user.id}"
                
                payment_intent_data = {
                    'amount': int(booking.total_price * 100),  # Convert to cents
                    'currency': settings.STRIPE_CURRENCY,
                    'customer': customer_id,
                    'metadata': {
                        'booking_id': booking.id,
                        'user_id': user.id,
                        'property_id': booking.property.id
                    },
                    'description': f"Payment for booking {booking.id} - {booking.property.title}",
                }

                # Add setup_future_usage if provided
                if setup_future_usage:
                    payment_intent_data['setup_future_usage'] = setup_future_usage

                # Use idempotency key to prevent duplicate payment intents
                payment_intent = stripe.PaymentIntent.create(
                    **payment_intent_data,
                    idempotency_key=idempotency_key
                )

            # Save payment intent to database
            db_payment_intent = self.payment_intent_repository.create_payment_intent(
                booking=booking,
                user=user,
                amount=booking.total_price,
                currency=settings.STRIPE_CURRENCY,
                stripe_payment_intent_id=payment_intent.id,
                stripe_client_secret=payment_intent.client_secret,
                status=payment_intent.status
            )

            logger.info(f"Payment intent created: {payment_intent.id} for booking {booking.id} by user {user.id}")

            return {
                'id': db_payment_intent.id,
                'booking': {
                    'id': booking.id,
                    'property': {
                        'id': booking.property.id,
                        'title': booking.property.title
                    },
                    'check_in_date': booking.check_in_date,
                    'check_out_date': booking.check_out_date
                },
                'amount': booking.total_price,
                'currency': settings.STRIPE_CURRENCY,
                'status': payment_intent.status,
                'stripe_payment_intent_id': payment_intent.id,
                'stripe_client_secret': payment_intent.client_secret,
                'created_at': db_payment_intent.created_at
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {str(e)}")
            raise ValueError(f"Error creating payment intent: {str(e)}")
    
    def _get_or_create_stripe_customer(self, user: User) -> Any:
        """
        Get or create a Stripe customer for a user.
        """
        # Check if we're using mock Stripe
        if not settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY == 'sk_test_your_test_key' or 'XXXX' in settings.STRIPE_SECRET_KEY:
            # Create a mock customer object
            class MockCustomer:
                def __init__(self, id):
                    self.id = id

            return MockCustomer(id=f"cus_mock_{user.id}")

        # Check if user already has a Stripe customer ID
        if user.stripe_customer_id:
            try:
                # Get customer from Stripe
                return stripe.Customer.retrieve(user.stripe_customer_id)
            except stripe.error.StripeError:
                # If customer doesn't exist in Stripe, create a new one
                pass

        # Create a new customer
        customer = stripe.Customer.create(
            email=user.email,
            name=f"{user.first_name} {user.last_name}".strip() or user.username,
            metadata={
                'user_id': user.id
            }
        )

        return customer


class GuestPaymentStrategy(PaymentStrategy):
    """
    Strategy for creating payment intents for non-logged-in users (guests).
    """
    def __init__(self, payment_intent_repository: PaymentIntentRepository = None, 
                 booking_repository: BookingRepository = None,
                 user_repository: UserRepository = None):
        self.payment_intent_repository = payment_intent_repository or PaymentIntentRepository()
        self.booking_repository = booking_repository or BookingRepository()
        self.user_repository = user_repository or UserRepository()

    def prepare_payment_user(self, **kwargs) -> User:
        """
        For guest users, get the user associated with the booking.
        """
        booking_id = kwargs.get('booking_id')
        if not booking_id:
            raise ValueError("Booking ID is required for guest payment")
            
        booking = self.booking_repository.get_booking_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking with ID {booking_id} not found")
            
        user = booking.tenant
        
        # Ensure the user has a stripe_customer_id
        if not user.stripe_customer_id:
            # Create a Stripe customer for this user
            customer = self._get_or_create_stripe_customer(user)
            # Update user with Stripe customer ID
            user.stripe_customer_id = customer.id
            user.save(update_fields=['stripe_customer_id'])
            
        return user
        
    def create_payment_intent(self, booking_id: int, setup_future_usage: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a payment intent for a guest booking.
        """
        # Get the booking
        booking = self.booking_repository.get_booking_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking with ID {booking_id} not found")

        # Check if the booking is already paid
        if booking.is_paid:
            raise ValueError("This booking is already paid")

        # Check if there's an existing active payment intent for this booking
        existing_intent = self.payment_intent_repository.get_active_payment_intent_for_booking(booking.id)
        if existing_intent:
            logger.info(f"Using existing payment intent: {existing_intent.stripe_payment_intent_id} for guest booking {booking.id}")
            return {
                'id': existing_intent.id,
                'booking': {
                    'id': booking.id,
                    'property': {
                        'id': booking.property.id,
                        'title': booking.property.title
                    },
                    'check_in_date': booking.check_in_date,
                    'check_out_date': booking.check_out_date
                },
                'amount': existing_intent.amount,
                'currency': existing_intent.currency,
                'status': existing_intent.status,
                'stripe_payment_intent_id': existing_intent.stripe_payment_intent_id,
                'stripe_client_secret': existing_intent.stripe_client_secret,
                'created_at': existing_intent.created_at
            }
            
        # Prepare the payment user (get the tenant from the booking)
        payment_user = self.prepare_payment_user(booking_id=booking_id)
        
        # Create payment intent
        return self._create_stripe_payment_intent(booking, payment_user, setup_future_usage)
    
    def _create_stripe_payment_intent(self, booking, user, setup_future_usage=None):
        """
        Create a Stripe payment intent.
        """
        # Check if Stripe API keys are configured
        use_mock_stripe = False
        if not settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY == 'sk_test_your_test_key' or 'XXXX' in settings.STRIPE_SECRET_KEY:
            logger.warning("Using mock Stripe implementation because API keys are not properly configured")
            use_mock_stripe = True

        try:
            if use_mock_stripe:
                # Mock Stripe customer and payment intent for testing
                customer_id = f"cus_mock_{user.id}"
                payment_intent_id = f"pi_mock_{booking.id}_{int(timezone.now().timestamp())}"
                client_secret = f"{payment_intent_id}_secret_{user.id}"

                # Create a mock payment intent object
                class MockPaymentIntent:
                    def __init__(self, id, client_secret, status):
                        self.id = id
                        self.client_secret = client_secret
                        self.status = status

                payment_intent = MockPaymentIntent(
                    id=payment_intent_id,
                    client_secret=client_secret,
                    status='requires_payment_method'
                )

                logger.info(f"Created mock payment intent: {payment_intent_id}")
            else:
                # Get or create Stripe customer
                customer = self._get_or_create_stripe_customer(user)
                customer_id = customer.id

                # Create payment intent with idempotency key to prevent duplicates
                idempotency_key = f"booking_{booking.id}_{user.id}"
                
                payment_intent_data = {
                    'amount': int(booking.total_price * 100),  # Convert to cents
                    'currency': settings.STRIPE_CURRENCY,
                    'customer': customer_id,
                    'metadata': {
                        'booking_id': booking.id,
                        'user_id': user.id,
                        'property_id': booking.property.id,
                        'is_guest': 'true'  # Mark as guest payment
                    },
                    'description': f"Guest payment for booking {booking.id} - {booking.property.title}",
                }

                # Use idempotency key to prevent duplicate payment intents
                payment_intent = stripe.PaymentIntent.create(
                    **payment_intent_data,
                    idempotency_key=idempotency_key
                )

            # Save payment intent to database
            db_payment_intent = self.payment_intent_repository.create_payment_intent(
                booking=booking,
                user=user,
                amount=booking.total_price,
                currency=settings.STRIPE_CURRENCY,
                stripe_payment_intent_id=payment_intent.id,
                stripe_client_secret=payment_intent.client_secret,
                status=payment_intent.status
            )

            logger.info(f"Guest payment intent created: {payment_intent.id} for booking {booking.id} by user {user.id}")

            return {
                'id': db_payment_intent.id,
                'booking': {
                    'id': booking.id,
                    'property': {
                        'id': booking.property.id,
                        'title': booking.property.title
                    },
                    'check_in_date': booking.check_in_date,
                    'check_out_date': booking.check_out_date
                },
                'amount': booking.total_price,
                'currency': settings.STRIPE_CURRENCY,
                'status': payment_intent.status,
                'stripe_payment_intent_id': payment_intent.id,
                'stripe_client_secret': payment_intent.client_secret,
                'created_at': db_payment_intent.created_at
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating guest payment intent: {str(e)}")
            raise ValueError(f"Error creating payment intent: {str(e)}")
    
    def _get_or_create_stripe_customer(self, user: User) -> Any:
        """
        Get or create a Stripe customer for a user.
        """
        # Check if we're using mock Stripe
        if not settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY == 'sk_test_your_test_key' or 'XXXX' in settings.STRIPE_SECRET_KEY:
            # Create a mock customer object
            class MockCustomer:
                def __init__(self, id):
                    self.id = id

            return MockCustomer(id=f"cus_mock_{user.id}")

        # Check if user already has a Stripe customer ID
        if user.stripe_customer_id:
            try:
                # Get customer from Stripe
                return stripe.Customer.retrieve(user.stripe_customer_id)
            except stripe.error.StripeError:
                # If customer doesn't exist in Stripe, create a new one
                pass

        # Create a new customer
        customer = stripe.Customer.create(
            email=user.email,
            name=f"{user.first_name} {user.last_name}".strip() or user.username,
            metadata={
                'user_id': user.id,
                'is_guest': 'true'
            }
        )

        return customer


class PaymentStrategyFactory:
    """
    Factory class to create the appropriate payment strategy.
    """
    @staticmethod
    def create_strategy(request_user: Optional[User] = None, booking_id: Optional[int] = None) -> PaymentStrategy:
        """
        Create and return the appropriate payment strategy based on whether a user is logged in.
        """
        if request_user and request_user.is_authenticated:
            return LoggedInPaymentStrategy(request_user)
        else:
            return GuestPaymentStrategy() 