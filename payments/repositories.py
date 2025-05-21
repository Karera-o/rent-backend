from typing import List, Optional, Dict, Any
from django.db.models import Q
from django.utils import timezone
from decimal import Decimal

from .models import Payment, PaymentMethod, PaymentIntent
from bookings.models import Booking
from users.models import User


class PaymentRepository:
    """
    Repository for Payment model operations.
    """

    @staticmethod
    def create_payment(
        booking: Booking,
        user: User,
        amount: Decimal,
        currency: str = 'usd',
        status: str = Payment.PaymentStatus.PENDING,
        stripe_payment_intent_id: Optional[str] = None,
        stripe_payment_method_id: Optional[str] = None,
        stripe_customer_id: Optional[str] = None,
        receipt_url: Optional[str] = None,
        receipt_email: Optional[str] = None
    ) -> Payment:
        """
        Create a new payment.
        """
        payment = Payment.objects.create(
            booking=booking,
            user=user,
            amount=amount,
            currency=currency,
            status=status,
            stripe_payment_intent_id=stripe_payment_intent_id,
            stripe_payment_method_id=stripe_payment_method_id,
            stripe_customer_id=stripe_customer_id,
            receipt_url=receipt_url,
            receipt_email=receipt_email
        )
        return payment

    @staticmethod
    def get_payment_by_id(payment_id: int) -> Optional[Payment]:
        """
        Get a payment by ID.
        """
        try:
            return Payment.objects.select_related(
                'booking',
                'user',
                'booking__property',
                'booking__tenant',
                'booking__property__owner'
            ).get(id=payment_id)
        except Payment.DoesNotExist:
            return None

    @staticmethod
    def get_payment_by_stripe_payment_intent_id(stripe_payment_intent_id: str) -> Optional[Payment]:
        """
        Get a payment by Stripe payment intent ID.
        """
        try:
            return Payment.objects.select_related(
                'booking',
                'user',
                'booking__property',
                'booking__tenant',
                'booking__property__owner'
            ).get(stripe_payment_intent_id=stripe_payment_intent_id)
        except Payment.DoesNotExist:
            return None

    @staticmethod
    def get_payments_by_user(
        user: User,
        page: int = 1,
        page_size: int = 10,
        **filters
    ) -> List[Payment]:
        """
        Get all payments for a user with pagination and filtering.
        """
        # Start with payments for the specified user
        queryset = Payment.objects.filter(user=user)

        # Apply any additional filters
        queryset = PaymentRepository._apply_payment_filters(queryset, **filters)

        # Use select_related to fetch all related objects in a single query
        queryset = queryset.select_related(
            'booking',  # Get the booking
            'user',  # Get the user who made the payment
            'booking__property',  # Get the property associated with the booking
            'booking__tenant',  # Get the tenant who made the booking
            'booking__property__owner'  # Get the owner of the property
        )

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size

        # Execute the query and return the results
        return queryset[start:end]

    @staticmethod
    def get_payments_by_booking(
        booking: Booking,
        page: int = 1,
        page_size: int = 10,
        **filters
    ) -> List[Payment]:
        """
        Get all payments for a booking with pagination and filtering.
        """
        # Start with payments for the specified booking
        queryset = Payment.objects.filter(booking=booking)

        # Apply any additional filters
        queryset = PaymentRepository._apply_payment_filters(queryset, **filters)

        # Use select_related to fetch all related objects in a single query
        queryset = queryset.select_related(
            'booking',  # Get the booking
            'user',  # Get the user who made the payment
            'booking__property',  # Get the property associated with the booking
            'booking__tenant',  # Get the tenant who made the booking
            'booking__property__owner'  # Get the owner of the property
        )

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size

        # Execute the query and return the results
        return queryset[start:end]

    @staticmethod
    def get_payments_by_booking_ids(
        booking_ids: List[int],
        page: int = 1,
        page_size: int = 10,
        **filters
    ) -> List[Payment]:
        """
        Get all payments for a list of booking IDs with pagination and filtering.
        """
        # Start with payments for the specified booking IDs
        queryset = Payment.objects.filter(booking_id__in=booking_ids)

        # Apply any additional filters
        queryset = PaymentRepository._apply_payment_filters(queryset, **filters)

        # Use select_related to fetch all related objects in a single query
        queryset = queryset.select_related(
            'booking',  # Get the booking
            'user',  # Get the user who made the payment
            'booking__property',  # Get the property associated with the booking
            'booking__tenant',  # Get the tenant who made the booking
            'booking__property__owner'  # Get the owner of the property
        )

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size

        # Execute the query and return the results
        return queryset[start:end]

    @staticmethod
    def count_payments_by_user(user: User, **filters) -> int:
        """
        Count payments for a user with filtering.
        """
        queryset = Payment.objects.filter(user=user)
        queryset = PaymentRepository._apply_payment_filters(queryset, **filters)
        return queryset.count()

    @staticmethod
    def count_payments_by_booking(booking: Booking, **filters) -> int:
        """
        Count payments for a booking with filtering.
        """
        queryset = Payment.objects.filter(booking=booking)
        queryset = PaymentRepository._apply_payment_filters(queryset, **filters)
        return queryset.count()

    @staticmethod
    def count_payments_by_booking_ids(booking_ids: List[int], **filters) -> int:
        """
        Count payments for a list of booking IDs with filtering.
        """
        queryset = Payment.objects.filter(booking_id__in=booking_ids)
        queryset = PaymentRepository._apply_payment_filters(queryset, **filters)
        return queryset.count()

    @staticmethod
    def update_payment(payment: Payment, **kwargs) -> Payment:
        """
        Update a payment.
        """
        for key, value in kwargs.items():
            setattr(payment, key, value)

        payment.save()
        return payment

    @staticmethod
    def get_all_payments(
        page: int = 1,
        page_size: int = 10,
        **filters
    ) -> List[Payment]:
        """
        Get all payments with pagination and filtering (admin view).
        """
        # Start with all payments
        queryset = Payment.objects.all()

        # Apply filters
        queryset = PaymentRepository._apply_payment_filters(queryset, **filters)

        # Use select_related to fetch all related objects in a single query
        queryset = queryset.select_related(
            'booking',  # Get the booking
            'user',  # Get the user who made the payment
            'booking__property',  # Get the property associated with the booking
            'booking__tenant',  # Get the tenant who made the booking
            'booking__property__owner'  # Get the owner of the property
        )

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size

        # Execute the query and return the results
        return queryset[start:end]

    @staticmethod
    def count_all_payments(**filters) -> int:
        """
        Count all payments with filtering (admin view).
        """
        queryset = Payment.objects.all()
        queryset = PaymentRepository._apply_payment_filters(queryset, **filters)
        return queryset.count()

    @staticmethod
    def delete_payment(payment: Payment) -> bool:
        """
        Delete a payment.
        """
        try:
            payment.delete()
            return True
        except Exception:
            return False

    @staticmethod
    def _apply_payment_filters(queryset, **filters):
        """
        Apply filters to a payment queryset.
        """
        if 'status' in filters and filters['status']:
            queryset = queryset.filter(status=filters['status'])

        if 'booking_id' in filters and filters['booking_id']:
            queryset = queryset.filter(booking_id=filters['booking_id'])

        if 'created_from' in filters and filters['created_from']:
            queryset = queryset.filter(created_at__gte=filters['created_from'])

        if 'created_to' in filters and filters['created_to']:
            queryset = queryset.filter(created_at__lte=filters['created_to'])

        if 'payment_method' in filters and filters['payment_method']:
            payment_method = filters['payment_method'].lower()
            if payment_method == 'card' or payment_method == 'credit card':
                queryset = queryset.filter(stripe_payment_method_id__startswith='pm_')
            elif payment_method == 'visa' or payment_method == 'visa card':
                # For Visa cards, we can check if the card_brand is Visa
                # But since we don't have that info directly, we'll use the same filter as card
                queryset = queryset.filter(stripe_payment_method_id__startswith='pm_')
            elif payment_method == 'paypal':
                queryset = queryset.filter(stripe_payment_method_id__startswith='pp_')
            elif payment_method == 'bank' or payment_method == 'bank account':
                queryset = queryset.filter(stripe_payment_method_id__startswith='ba_')

        # Handle search query
        if 'query' in filters and filters['query']:
            query = filters['query']
            queryset = queryset.filter(
                Q(booking__property__title__icontains=query) |
                Q(user__username__icontains=query) |
                Q(user__email__icontains=query) |
                Q(user__first_name__icontains=query) |
                Q(user__last_name__icontains=query) |
                Q(stripe_payment_intent_id__icontains=query) |
                Q(receipt_email__icontains=query)
            )

        return queryset


class PaymentMethodRepository:
    """
    Repository for PaymentMethod model operations.
    """

    @staticmethod
    def create_payment_method(
        user: User,
        stripe_payment_method_id: str,
        type: str = PaymentMethod.PaymentType.CARD,
        is_default: bool = False,
        card_brand: Optional[str] = None,
        card_last4: Optional[str] = None,
        card_exp_month: Optional[int] = None,
        card_exp_year: Optional[int] = None
    ) -> PaymentMethod:
        """
        Create a new payment method.
        """
        payment_method = PaymentMethod.objects.create(
            user=user,
            stripe_payment_method_id=stripe_payment_method_id,
            type=type,
            is_default=is_default,
            card_brand=card_brand,
            card_last4=card_last4,
            card_exp_month=card_exp_month,
            card_exp_year=card_exp_year
        )
        return payment_method

    @staticmethod
    def get_payment_method_by_id(payment_method_id: int) -> Optional[PaymentMethod]:
        """
        Get a payment method by ID.
        """
        try:
            return PaymentMethod.objects.get(id=payment_method_id)
        except PaymentMethod.DoesNotExist:
            return None

    @staticmethod
    def get_payment_method_by_stripe_id(stripe_payment_method_id: str) -> Optional[PaymentMethod]:
        """
        Get a payment method by Stripe payment method ID.
        """
        try:
            return PaymentMethod.objects.get(stripe_payment_method_id=stripe_payment_method_id)
        except PaymentMethod.DoesNotExist:
            return None

    @staticmethod
    def get_payment_methods_by_user(
        user: User,
        page: int = 1,
        page_size: int = 10
    ) -> List[PaymentMethod]:
        """
        Get all payment methods for a user with pagination.
        """
        queryset = PaymentMethod.objects.filter(user=user)

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size

        return queryset[start:end]

    @staticmethod
    def count_payment_methods_by_user(user: User) -> int:
        """
        Count payment methods for a user.
        """
        return PaymentMethod.objects.filter(user=user).count()

    @staticmethod
    def get_default_payment_method(user: User) -> Optional[PaymentMethod]:
        """
        Get the default payment method for a user.
        """
        try:
            return PaymentMethod.objects.filter(user=user, is_default=True).first()
        except PaymentMethod.DoesNotExist:
            return None

    @staticmethod
    def update_payment_method(payment_method: PaymentMethod, **kwargs) -> PaymentMethod:
        """
        Update a payment method.
        """
        for key, value in kwargs.items():
            setattr(payment_method, key, value)

        payment_method.save()
        return payment_method

    @staticmethod
    def delete_payment_method(payment_method: PaymentMethod) -> None:
        """
        Delete a payment method.
        """
        payment_method.delete()


class PaymentIntentRepository:
    """
    Repository for PaymentIntent model operations.
    """

    @staticmethod
    def create_payment_intent(
        booking: Booking,
        user: User,
        amount: Decimal,
        currency: str,
        stripe_payment_intent_id: str,
        stripe_client_secret: str,
        status: str = PaymentIntent.PaymentIntentStatus.REQUIRES_PAYMENT_METHOD,
        payment: Optional[Payment] = None
    ) -> PaymentIntent:
        """
        Create a new payment intent.
        """
        payment_intent = PaymentIntent.objects.create(
            booking=booking,
            user=user,
            amount=amount,
            currency=currency,
            stripe_payment_intent_id=stripe_payment_intent_id,
            stripe_client_secret=stripe_client_secret,
            status=status,
            payment=payment
        )
        return payment_intent

    @staticmethod
    def get_payment_intent_by_id(payment_intent_id: int) -> Optional[PaymentIntent]:
        """
        Get a payment intent by ID.
        """
        try:
            return PaymentIntent.objects.select_related('booking', 'user', 'payment').get(id=payment_intent_id)
        except PaymentIntent.DoesNotExist:
            return None

    @staticmethod
    def get_payment_intent_by_stripe_id(stripe_payment_intent_id: str) -> Optional[PaymentIntent]:
        """
        Get a payment intent by Stripe payment intent ID.
        """
        try:
            return PaymentIntent.objects.select_related('booking', 'user', 'payment').get(stripe_payment_intent_id=stripe_payment_intent_id)
        except PaymentIntent.DoesNotExist:
            return None

    @staticmethod
    def get_payment_intents_by_booking(booking: Booking) -> List[PaymentIntent]:
        """
        Get all payment intents for a booking.
        """
        return PaymentIntent.objects.filter(booking=booking).select_related('booking', 'user', 'payment')

    @staticmethod
    def get_payment_intents_by_user(user: User) -> List[PaymentIntent]:
        """
        Get all payment intents for a user.
        """
        return PaymentIntent.objects.filter(user=user).select_related('booking', 'user', 'payment')

    @staticmethod
    def update_payment_intent(payment_intent: PaymentIntent, **kwargs) -> PaymentIntent:
        """
        Update a payment intent.
        """
        for key, value in kwargs.items():
            setattr(payment_intent, key, value)

        payment_intent.save()
        return payment_intent
