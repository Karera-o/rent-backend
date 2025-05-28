import stripe
import logging
from typing import Optional, Dict, Any, List
from decimal import Decimal
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from django.db.models import Q

from .repositories import PaymentRepository, PaymentMethodRepository, PaymentIntentRepository
from .models import Payment, PaymentMethod, PaymentIntent
from bookings.repositories import BookingRepository
from properties.repositories import PropertyRepository # Added import
from users.models import User
from .strategies import PaymentStrategyFactory

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = settings.STRIPE_API_VERSION

logger = logging.getLogger('house_rental')

# Cache timeout in seconds (10 minutes)
CACHE_TIMEOUT = 60 * 10


class PaymentService:
    """
    Service for payment-related business logic.
    """

    def __init__(
        self,
        payment_repository: PaymentRepository = None,
        payment_method_repository: PaymentMethodRepository = None,
        payment_intent_repository: PaymentIntentRepository = None,
        booking_repository: BookingRepository = None,
        property_repository: PropertyRepository = None # Added property_repository
    ):
        self.payment_repository = payment_repository or PaymentRepository()
        self.payment_method_repository = payment_method_repository or PaymentMethodRepository()
        self.payment_intent_repository = payment_intent_repository or PaymentIntentRepository()
        self.booking_repository = booking_repository or BookingRepository()
        self.property_repository = property_repository or PropertyRepository() # Added initialization

    def get_stripe_public_key(self) -> str:
        """
        Get the Stripe publishable key.
        """
        return settings.STRIPE_PUBLISHABLE_KEY

    def create_payment_intent(
        self,
        user: User,
        booking_id: int,
        setup_future_usage: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a payment intent for a booking.
        """
        # Use the strategy pattern to create the payment intent
        strategy = PaymentStrategyFactory.create_strategy(request_user=user)
        return strategy.create_payment_intent(booking_id, setup_future_usage)

    def create_guest_payment_intent(
        self,
        booking_id: int,
        setup_future_usage: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a payment intent for a guest booking.
        """
        # Use the guest strategy to create the payment intent
        strategy = PaymentStrategyFactory.create_strategy(request_user=None)
        return strategy.create_payment_intent(booking_id, setup_future_usage)

    def confirm_payment(
        self,
        user: User,
        payment_intent_id: str,
        payment_method_id: Optional[str] = None,
        save_payment_method: bool = False
    ) -> Dict[str, Any]:
        """
        Confirm a payment intent.
        """
        # Get the payment intent from database
        db_payment_intent = self.payment_intent_repository.get_payment_intent_by_stripe_id(payment_intent_id)
        if not db_payment_intent:
            raise ValueError(f"Payment intent with ID {payment_intent_id} not found")

        # Check if the user is the owner of the payment intent or an admin
        # For guest payments, we allow confirmation without strict user checking
        is_guest_payment = False
        if db_payment_intent.user.id != user.id and user.role != User.Role.ADMIN:
            # Check if this is a guest payment by looking at the booking tenant
            if db_payment_intent.booking and db_payment_intent.booking.tenant and not db_payment_intent.booking.tenant.is_active:
                is_guest_payment = True
            else:
                raise ValueError("You don't have permission to confirm this payment intent")

        # Get the booking
        booking = db_payment_intent.booking

        # Check if we're using mock Stripe
        use_mock_stripe = False
        if not settings.STRIPE_SECRET_KEY or settings.STRIPE_SECRET_KEY == 'sk_test_your_test_key' or 'XXXX' in settings.STRIPE_SECRET_KEY:
            logger.warning("Using mock Stripe implementation because API keys are not properly configured")
            use_mock_stripe = True

        try:
            if use_mock_stripe:
                # Create a mock payment intent object for testing
                class MockPaymentIntent:
                    def __init__(self, id, status, payment_method=None):
                        self.id = id
                        self.status = status
                        self.payment_method = payment_method
                        self.customer = f"cus_mock_{user.id}"

                # Mock successful payment
                stripe_payment_intent = MockPaymentIntent(
                    id=payment_intent_id,
                    status='succeeded',
                    payment_method=payment_method_id or f"pm_mock_{user.id}"
                )

                logger.info(f"Confirmed mock payment intent: {payment_intent_id}")
            else:
                # Get the payment intent from Stripe
                stripe_payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)

                # Check if the payment intent is already succeeded
                if stripe_payment_intent.status == 'succeeded':
                    logger.info(f"Payment intent {payment_intent_id} is already succeeded, no need to confirm again")
                    
                    # Check if we need to create a payment record
                    if not db_payment_intent.payment:
                        payment = self.payment_repository.create_payment(
                            booking=booking,
                            user=user,
                            amount=db_payment_intent.amount,
                            currency=db_payment_intent.currency,
                            status=Payment.PaymentStatus.COMPLETED,
                            stripe_payment_intent_id=payment_intent_id,
                            stripe_payment_method_id=stripe_payment_intent.payment_method,
                            stripe_customer_id=stripe_payment_intent.customer,
                            receipt_email=user.email
                        )
                        
                        # Update payment intent with payment
                        db_payment_intent = self.payment_intent_repository.update_payment_intent(
                            db_payment_intent,
                            payment=payment,
                            status='succeeded'
                        )
                        
                        logger.info(f"Created payment record for already succeeded payment intent: {payment.id}")
                else:
                    # If payment method is provided, attach it to the payment intent
                    if payment_method_id:
                        # Attach payment method to customer if save_payment_method is True
                        if save_payment_method:
                            customer = self._get_or_create_stripe_customer(user)
                            stripe.PaymentMethod.attach(
                                payment_method_id,
                                customer=customer.id
                            )

                            # Save payment method to database
                            payment_method = stripe.PaymentMethod.retrieve(payment_method_id)
                            self._save_payment_method(user, payment_method, is_default=True)

                        # Confirm the payment intent with the payment method
                        stripe_payment_intent = stripe.PaymentIntent.confirm(
                            payment_intent_id,
                            payment_method=payment_method_id
                        )
                    else:
                        # Confirm the payment intent without a payment method (using saved payment method)
                        stripe_payment_intent = stripe.PaymentIntent.confirm(payment_intent_id)

            # Update payment intent in database if status changed
            if db_payment_intent.status != stripe_payment_intent.status:
                db_payment_intent = self.payment_intent_repository.update_payment_intent(
                    db_payment_intent,
                    status=stripe_payment_intent.status
                )

            # If payment is successful, create a payment record if it doesn't exist
            if stripe_payment_intent.status == 'succeeded' and not db_payment_intent.payment:
                # Use the booking tenant's email for receipt if this is a guest payment
                receipt_email = user.email
                if is_guest_payment and booking and booking.tenant:
                    receipt_email = booking.tenant.email or booking.guest_email
                
                payment = self.payment_repository.create_payment(
                    booking=booking,
                    user=db_payment_intent.user,  # Use the original user from the payment intent
                    amount=db_payment_intent.amount,
                    currency=db_payment_intent.currency,
                    status=Payment.PaymentStatus.COMPLETED,
                    stripe_payment_intent_id=payment_intent_id,
                    stripe_payment_method_id=stripe_payment_intent.payment_method,
                    stripe_customer_id=stripe_payment_intent.customer,
                    receipt_email=receipt_email
                )

                # Update payment intent with payment
                db_payment_intent = self.payment_intent_repository.update_payment_intent(
                    db_payment_intent,
                    payment=payment
                )

                logger.info(f"Payment successful: {payment.id} for booking {booking.id} by user {db_payment_intent.user.id}")

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
                'amount': db_payment_intent.amount,
                'currency': db_payment_intent.currency,
                'status': stripe_payment_intent.status,
                'stripe_payment_intent_id': stripe_payment_intent.id,
                'requires_action': stripe_payment_intent.status == 'requires_action',
                'payment_intent_client_secret': stripe_payment_intent.client_secret if stripe_payment_intent.status == 'requires_action' else None,
                'created_at': db_payment_intent.created_at
            }

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error confirming payment: {str(e)}")
            raise ValueError(f"Error confirming payment: {str(e)}")

    def get_payment(self, payment_id: int, user: User) -> Optional[Dict[str, Any]]:
        """
        Get a payment by ID.
        """
        # Try to get from cache first
        cache_key = f"payment_{payment_id}"
        payment_data = cache.get(cache_key)

        if payment_data:
            # Check if the user has permission to view this payment
            if payment_data['user']['id'] != user.id and user.role != User.Role.ADMIN:
                if payment_data['booking']['property']['owner']['id'] != user.id:
                    return None
            return payment_data

        # If not in cache, get from database
        payment = self.payment_repository.get_payment_by_id(payment_id)
        if not payment:
            return None

        # Check if the user has permission to view this payment
        if payment.user.id != user.id and user.role != User.Role.ADMIN:
            if payment.booking.property.owner.id != user.id:
                return None

        # Format the payment data
        payment_data = self._format_payment_detail(payment)

        # Cache the result
        cache.set(cache_key, payment_data, CACHE_TIMEOUT)

        return payment_data

    def get_user_payments(
        self,
        user: User,
        page: int = 1,
        page_size: int = 10,
        **filters
    ) -> Dict[str, Any]:
        """
        Get all payments for a user with pagination and filtering.
        """
        payments = self.payment_repository.get_payments_by_user(
            user=user,
            page=page,
            page_size=page_size,
            **filters
        )

        total = self.payment_repository.count_payments_by_user(user, **filters)
        total_pages = (total + page_size - 1) // page_size

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'items': [self._format_payment_summary(payment) for payment in payments]
        }

    def get_landlord_payments(
        self,
        landlord: User,
        page: int = 1,
        page_size: int = 10,
        **filters
    ) -> Dict[str, Any]:
        """
        Get all payments for properties owned by a landlord with pagination and filtering.
        """
        # Check if the user is a landlord/agent or admin
        if landlord.role not in [User.Role.AGENT, User.Role.ADMIN]:
            raise ValueError("Only landlords/agents can access this endpoint")

        # Get all properties owned by the landlord
        properties = self.property_repository.get_properties_by_owner(landlord)

        if not properties:
            return {
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0,
                'items': []
            }

        # Get all bookings for these properties
        property_ids = [prop.id for prop in properties]
        bookings = self.booking_repository.get_bookings_by_property_ids(property_ids)

        if not bookings:
            return {
                'total': 0,
                'page': page,
                'page_size': page_size,
                'total_pages': 0,
                'items': []
            }

        # Get all payments for these bookings
        booking_ids = [booking.id for booking in bookings]
        payments = self.payment_repository.get_payments_by_booking_ids(
            booking_ids=booking_ids,
            page=page,
            page_size=page_size,
            **filters
        )

        total = self.payment_repository.count_payments_by_booking_ids(booking_ids, **filters)
        total_pages = (total + page_size - 1) // page_size

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'items': [self._format_payment_summary(payment) for payment in payments]
        }

    def get_booking_payments(
        self,
        booking_id: int,
        user: User,
        page: int = 1,
        page_size: int = 10,
        **filters
    ) -> Dict[str, Any]:
        """
        Get all payments for a booking with pagination and filtering.
        """
        booking = self.booking_repository.get_booking_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking with ID {booking_id} not found")

        # Check if the user has permission to view payments for this booking
        if booking.tenant.id != user.id and booking.property.owner.id != user.id and user.role != User.Role.ADMIN:
            raise ValueError("You don't have permission to view payments for this booking")

        payments = self.payment_repository.get_payments_by_booking(
            booking=booking,
            page=page,
            page_size=page_size,
            **filters
        )

        total = self.payment_repository.count_payments_by_booking(booking, **filters)
        total_pages = (total + page_size - 1) // page_size

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'items': [self._format_payment_summary(payment) for payment in payments]
        }

    def create_payment_method(
        self,
        user: User,
        payment_method_id: str,
        set_as_default: bool = False
    ) -> Dict[str, Any]:
        """
        Create a payment method for a user.
        """
        try:
            # Get or create Stripe customer
            customer = self._get_or_create_stripe_customer(user)

            # Attach payment method to customer
            stripe.PaymentMethod.attach(
                payment_method_id,
                customer=customer.id
            )

            # Get payment method details
            payment_method = stripe.PaymentMethod.retrieve(payment_method_id)

            # Save payment method to database
            db_payment_method = self._save_payment_method(user, payment_method, is_default=set_as_default)

            logger.info(f"Payment method created: {db_payment_method.id} for user {user.id}")

            return self._format_payment_method(db_payment_method)

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment method: {str(e)}")
            raise ValueError(f"Error creating payment method: {str(e)}")

    def get_payment_methods(
        self,
        user: User,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Get all payment methods for a user with pagination.
        """
        payment_methods = self.payment_method_repository.get_payment_methods_by_user(
            user=user,
            page=page,
            page_size=page_size
        )

        total = self.payment_method_repository.count_payment_methods_by_user(user)
        total_pages = (total + page_size - 1) // page_size

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'items': [self._format_payment_method(payment_method) for payment_method in payment_methods]
        }

    def update_payment_method(
        self,
        user: User,
        payment_method_id: int,
        set_as_default: bool = True
    ) -> Dict[str, Any]:
        """
        Update a payment method.
        """
        payment_method = self.payment_method_repository.get_payment_method_by_id(payment_method_id)
        if not payment_method:
            raise ValueError(f"Payment method with ID {payment_method_id} not found")

        # Check if the user is the owner of the payment method
        if payment_method.user.id != user.id:
            raise ValueError("You don't have permission to update this payment method")

        # Update payment method
        payment_method = self.payment_method_repository.update_payment_method(
            payment_method,
            is_default=set_as_default
        )

        logger.info(f"Payment method updated: {payment_method.id} for user {user.id}")

        return self._format_payment_method(payment_method)

    def delete_payment_method(
        self,
        user: User,
        payment_method_id: int
    ) -> None:
        """
        Delete a payment method.
        """
        payment_method = self.payment_method_repository.get_payment_method_by_id(payment_method_id)
        if not payment_method:
            raise ValueError(f"Payment method with ID {payment_method_id} not found")

        # Check if the user is the owner of the payment method
        if payment_method.user.id != user.id:
            raise ValueError("You don't have permission to delete this payment method")

        try:
            # Detach payment method from customer
            stripe.PaymentMethod.detach(payment_method.stripe_payment_method_id)

            # Delete payment method from database
            self.payment_method_repository.delete_payment_method(payment_method)

            logger.info(f"Payment method deleted: {payment_method.id} for user {user.id}")

        except stripe.error.StripeError as e:
            logger.error(f"Stripe error deleting payment method: {str(e)}")
            raise ValueError(f"Error deleting payment method: {str(e)}")

    def handle_stripe_webhook(self, payload: bytes, signature: str) -> Dict[str, Any]:
        """
        Handle Stripe webhook events.
        """
        try:
            # Convert string payload to bytes if necessary
            if isinstance(payload, str):
                payload = payload.encode('utf-8')
                
            logger.info(f"Constructing Stripe event with signature: {signature[:20]}...")
            logger.info(f"Using webhook secret: {settings.STRIPE_WEBHOOK_SECRET[:10]}...")
            
            event = stripe.Webhook.construct_event(
                payload, signature, settings.STRIPE_WEBHOOK_SECRET
            )

            logger.info(f"Received Stripe webhook event: {event.type}")

            # Handle different event types
            if event.type == 'payment_intent.succeeded':
                return self._handle_payment_intent_succeeded(event.data.object)
            elif event.type == 'payment_intent.payment_failed':
                return self._handle_payment_intent_failed(event.data.object)
            elif event.type == 'payment_intent.canceled':
                return self._handle_payment_intent_canceled(event.data.object)
            elif event.type == 'payment_method.attached':
                return self._handle_payment_method_attached(event.data.object)
            elif event.type == 'payment_method.detached':
                return self._handle_payment_method_detached(event.data.object)
            else:
                logger.info(f"Unhandled event type: {event.type}")
                return {"status": "success", "message": f"Unhandled event type: {event.type}"}

        except ValueError as e:
            logger.error(f"Invalid webhook payload: {str(e)}")
            raise ValueError(f"Invalid webhook payload: {str(e)}")
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {str(e)}")
            raise ValueError(f"Invalid signature: {str(e)}")

    def _handle_payment_intent_succeeded(self, payment_intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle payment_intent.succeeded webhook event.
        """
        try:
            # Get payment intent from database
            db_payment_intent = self.payment_intent_repository.get_payment_intent_by_stripe_id(payment_intent['id'])
            if not db_payment_intent:
                logger.warning(f"Payment intent not found in database: {payment_intent['id']}")
                return {"status": "error", "message": "Payment intent not found in database"}

            # Update payment intent status
            db_payment_intent = self.payment_intent_repository.update_payment_intent(
                db_payment_intent,
                status='succeeded'
            )

            # Create payment if it doesn't exist
            if not db_payment_intent.payment:
                payment = self.payment_repository.create_payment(
                    booking=db_payment_intent.booking,
                    user=db_payment_intent.user,
                    amount=db_payment_intent.amount,
                    currency=db_payment_intent.currency,
                    status=Payment.PaymentStatus.COMPLETED,
                    stripe_payment_intent_id=payment_intent['id'],
                    stripe_payment_method_id=payment_intent.get('payment_method'),
                    stripe_customer_id=payment_intent.get('customer'),
                    receipt_email=db_payment_intent.user.email
                )

                # Update payment intent with payment
                db_payment_intent = self.payment_intent_repository.update_payment_intent(
                    db_payment_intent,
                    payment=payment
                )

            return {"status": "success", "message": "Payment intent succeeded"}
        except Exception as e:
            logger.error(f"Error handling payment_intent.succeeded: {str(e)}")
            return {"status": "error", "message": str(e)}

    def get_all_payments(
        self,
        page: int = 1,
        page_size: int = 10,
        **filters
    ) -> Dict[str, Any]:
        """
        Get all payments with pagination and filtering (admin view).
        """
        # Get all payments
        payments = self.payment_repository.get_all_payments(
            page=page,
            page_size=page_size,
            **filters
        )

        total = self.payment_repository.count_all_payments(**filters)
        total_pages = (total + page_size - 1) // page_size

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'items': [self._format_payment_summary(payment) for payment in payments]
        }

    def update_payment_status(
        self,
        payment_id: int,
        status: str,
        user: User
    ) -> Dict[str, Any]:
        """
        Update a payment's status.
        """
        payment = self.payment_repository.get_payment_by_id(payment_id)
        if not payment:
            raise ValueError(f"Payment with ID {payment_id} not found")

        # Check if the status is valid
        if status not in [choice[0] for choice in Payment.PaymentStatus.choices]:
            raise ValueError(f"Invalid payment status: {status}")

        # Update the payment
        update_data = {'status': status}

        # If marking as completed, update completed_at timestamp
        if status == Payment.PaymentStatus.COMPLETED and not payment.completed_at:
            update_data['completed_at'] = timezone.now()

            # Update booking payment status if needed
            if payment.booking and not payment.booking.is_paid:
                self.booking_repository.update_booking(
                    payment.booking,
                    is_paid=True,
                    payment_date=timezone.now(),
                    payment_id=payment.stripe_payment_intent_id
                )

        # If marking as refunded, update booking payment status
        if status == Payment.PaymentStatus.REFUNDED and payment.booking and payment.booking.is_paid:
            self.booking_repository.update_booking(
                payment.booking,
                is_paid=False,
                payment_date=None,
                payment_id=None
            )

        payment = self.payment_repository.update_payment(payment, **update_data)
        return self._format_payment_detail(payment)

    def delete_payment(
        self,
        payment_id: int,
        user: User
    ) -> bool:
        """
        Delete a payment.
        """
        payment = self.payment_repository.get_payment_by_id(payment_id)
        if not payment:
            return False

        # Delete the payment
        return self.payment_repository.delete_payment(payment)

    def _handle_payment_intent_failed(self, payment_intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle payment_intent.payment_failed webhook event.
        """
        try:
            # Get payment intent from database
            db_payment_intent = self.payment_intent_repository.get_payment_intent_by_stripe_id(payment_intent['id'])
            if not db_payment_intent:
                logger.warning(f"Payment intent not found in database: {payment_intent['id']}")
                return {"status": "error", "message": "Payment intent not found in database"}

            # Update payment intent status
            db_payment_intent = self.payment_intent_repository.update_payment_intent(
                db_payment_intent,
                status='requires_payment_method'
            )

            return {"status": "success", "message": "Payment intent failed"}
        except Exception as e:
            logger.error(f"Error handling payment_intent.payment_failed: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _handle_payment_intent_canceled(self, payment_intent: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle payment_intent.canceled webhook event.
        """
        try:
            # Get payment intent from database
            db_payment_intent = self.payment_intent_repository.get_payment_intent_by_stripe_id(payment_intent['id'])
            if not db_payment_intent:
                logger.warning(f"Payment intent not found in database: {payment_intent['id']}")
                return {"status": "error", "message": "Payment intent not found in database"}

            # Update payment intent status
            db_payment_intent = self.payment_intent_repository.update_payment_intent(
                db_payment_intent,
                status='cancelled'
            )

            return {"status": "success", "message": "Payment intent canceled"}
        except Exception as e:
            logger.error(f"Error handling payment_intent.canceled: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _handle_payment_method_attached(self, payment_method: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle payment_method.attached webhook event.
        """
        try:
            # Check if payment method exists in database
            db_payment_method = self.payment_method_repository.get_payment_method_by_stripe_id(payment_method['id'])
            if db_payment_method:
                logger.info(f"Payment method already exists in database: {payment_method['id']}")
                return {"status": "success", "message": "Payment method already exists"}

            # Get user from customer ID
            customer_id = payment_method.get('customer')
            if not customer_id:
                logger.warning(f"No customer ID for payment method: {payment_method['id']}")
                return {"status": "error", "message": "No customer ID for payment method"}

            # We don't have a direct way to get user from customer ID, so we'll skip this for now
            logger.info(f"Payment method attached: {payment_method['id']}")
            return {"status": "success", "message": "Payment method attached"}
        except Exception as e:
            logger.error(f"Error handling payment_method.attached: {str(e)}")
            return {"status": "error", "message": str(e)}

    def _handle_payment_method_detached(self, payment_method: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle payment_method.detached webhook event.
        """
        try:
            # Get payment method from database
            db_payment_method = self.payment_method_repository.get_payment_method_by_stripe_id(payment_method['id'])
            if not db_payment_method:
                logger.warning(f"Payment method not found in database: {payment_method['id']}")
                return {"status": "error", "message": "Payment method not found in database"}

            # Delete payment method
            self.payment_method_repository.delete_payment_method(db_payment_method)

            return {"status": "success", "message": "Payment method detached"}
        except Exception as e:
            logger.error(f"Error handling payment_method.detached: {str(e)}")
            return {"status": "error", "message": str(e)}

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

        # Update user with Stripe customer ID
        user.stripe_customer_id = customer.id
        user.save(update_fields=['stripe_customer_id'])

        return customer

    def _save_payment_method(self, user: User, payment_method: Any, is_default: bool = False) -> PaymentMethod:
        """
        Save a Stripe payment method to the database.
        """
        # Check if payment method already exists
        existing_payment_method = self.payment_method_repository.get_payment_method_by_stripe_id(payment_method.id)
        if existing_payment_method:
            # Update existing payment method
            return self.payment_method_repository.update_payment_method(
                existing_payment_method,
                is_default=is_default
            )

        # Extract card details if available
        card_brand = None
        card_last4 = None
        card_exp_month = None
        card_exp_year = None

        if hasattr(payment_method, 'card') and payment_method.card:
            card_brand = payment_method.card.brand
            card_last4 = payment_method.card.last4
            card_exp_month = payment_method.card.exp_month
            card_exp_year = payment_method.card.exp_year

        # Create new payment method
        return self.payment_method_repository.create_payment_method(
            user=user,
            stripe_payment_method_id=payment_method.id,
            type=PaymentMethod.PaymentType.CARD,
            is_default=is_default,
            card_brand=card_brand,
            card_last4=card_last4,
            card_exp_month=card_exp_month,
            card_exp_year=card_exp_year
        )

    def _format_payment_detail(self, payment: Payment) -> Dict[str, Any]:
        """
        Format a payment object for detailed view.
        """
        booking_data = {
            'id': payment.booking.id,
            'property': {
                'id': payment.booking.property.id,
                'title': payment.booking.property.title,
                'owner': {
                    'id': payment.booking.property.owner.id,
                    'username': payment.booking.property.owner.username,
                    'first_name': payment.booking.property.owner.first_name,
                    'last_name': payment.booking.property.owner.last_name,
                }
            },
            'check_in_date': payment.booking.check_in_date,
            'check_out_date': payment.booking.check_out_date,
            'guests': payment.booking.guests,
            'tenant': {
                'id': payment.booking.tenant.id,
                'username': payment.booking.tenant.username,
                'first_name': payment.booking.tenant.first_name,
                'last_name': payment.booking.tenant.last_name,
            }
        }

        user_data = {
            'id': payment.user.id,
            'username': payment.user.username,
            'first_name': payment.user.first_name,
            'last_name': payment.user.last_name,
        }

        return {
            'id': payment.id,
            'booking': booking_data,
            'user': user_data,
            'amount': payment.amount,
            'currency': payment.currency,
            'status': payment.status,
            'stripe_payment_intent_id': payment.stripe_payment_intent_id,
            'stripe_payment_method_id': payment.stripe_payment_method_id,
            'stripe_customer_id': payment.stripe_customer_id,
            'receipt_url': payment.receipt_url,
            'receipt_email': payment.receipt_email,
            'created_at': payment.created_at,
            'updated_at': payment.updated_at,
            'completed_at': payment.completed_at
        }

    def _format_payment_summary(self, payment: Payment) -> Dict[str, Any]:
        """
        Format a payment object for summary view.
        """
        try:
            # Get payment method details
            payment_method_type = 'Visa Card'  # Default to Visa Card
            if payment.stripe_payment_method_id:
                if payment.stripe_payment_method_id.startswith('pm_'):
                    payment_method_type = 'Credit Card'
                elif payment.stripe_payment_method_id.startswith('pp_'):
                    payment_method_type = 'PayPal'
                elif payment.stripe_payment_method_id.startswith('ba_'):
                    payment_method_type = 'Bank Account'

            # Get booking data with error handling
            booking_data = {}
            property_data = {}
            tenant_data = {}

            # Check if booking exists
            if hasattr(payment, 'booking') and payment.booking:
                booking = payment.booking
                booking_data = {
                    'id': booking.id,
                    'check_in_date': booking.check_in_date,
                    'check_out_date': booking.check_out_date,
                    'guest_name': booking.guest_name,
                    'guests': booking.guests,
                    'total_price': booking.total_price
                }

                # Check if property exists
                if hasattr(booking, 'property') and booking.property:
                    prop = booking.property
                    images = []
                    try:
                        if hasattr(prop, 'images'):
                            property_images = prop.images.all()[:1]
                            if property_images:
                                images = [img.image.url for img in property_images]
                    except Exception as e:
                        logger.error(f"Error getting property images: {str(e)}")

                    property_data = {
                        'id': prop.id,
                        'title': prop.title,
                        'images': images
                    }
                    booking_data['property'] = property_data

                # Check if tenant exists
                if hasattr(booking, 'tenant') and booking.tenant:
                    tenant = booking.tenant
                    tenant_first_name = tenant.first_name or ''
                    tenant_last_name = tenant.last_name or ''
                    tenant_name = f"{tenant_first_name} {tenant_last_name}".strip() or tenant.username

                    tenant_data = {
                        'id': tenant.id,
                        'username': tenant.username,
                        'email': tenant.email,
                        'first_name': tenant_first_name,
                        'last_name': tenant_last_name,
                        'full_name': tenant_name
                    }
                    booking_data['tenant'] = tenant_data

            # Get user data with error handling
            user_data = {}
            if hasattr(payment, 'user') and payment.user:
                user = payment.user
                user_data = {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name or '',
                    'last_name': user.last_name or '',
                    'full_name': f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username
                }

            # Create the response with both booking_id (for schema validation) and booking object (for frontend)
            return {
                'id': payment.id,
                'booking_id': booking_data.get('id', 0),
                'user': user_data,
                'booking': booking_data,
                'tenant': tenant_data,  # Add tenant directly for easier frontend access
                'property': property_data,  # Add property directly for easier frontend access
                'amount': payment.amount,
                'currency': payment.currency,
                'status': payment.status,
                'payment_method_type': payment_method_type,
                'stripe_payment_intent_id': payment.stripe_payment_intent_id,
                'stripe_payment_method_id': payment.stripe_payment_method_id,
                'receipt_url': payment.receipt_url,
                'receipt_email': payment.receipt_email,
                'created_at': payment.created_at,
                'updated_at': payment.updated_at,
                'completed_at': payment.completed_at
            }
        except Exception as e:
            logger.error(f"Error formatting payment summary: {str(e)}")
            # Return minimal data to avoid breaking the API
            return {
                'id': payment.id,
                'booking_id': getattr(payment.booking, 'id', 0) if hasattr(payment, 'booking') else 0,
                'amount': payment.amount,
                'currency': payment.currency,
                'status': payment.status,
                'payment_method_type': 'Visa Card',
                'created_at': payment.created_at,
                'updated_at': payment.updated_at,
                'completed_at': payment.completed_at
            }

    def _format_payment_method(self, payment_method: PaymentMethod) -> Dict[str, Any]:
        """
        Format a payment method object.
        """
        return {
            'id': payment_method.id,
            'type': payment_method.type,
            'is_default': payment_method.is_default,
            'card_brand': payment_method.card_brand,
            'card_last4': payment_method.card_last4,
            'card_exp_month': payment_method.card_exp_month,
            'card_exp_year': payment_method.card_exp_year,
            'stripe_payment_method_id': payment_method.stripe_payment_method_id,
            'created_at': payment_method.created_at
        }
