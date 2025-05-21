from typing import List, Optional, Dict, Any
from django.db.models import Q
from django.utils import timezone

from .models import Booking, BookingReview
from properties.models import Property
from users.models import User


class BookingRepository:
    """
    Repository for Booking model operations.
    """

    @staticmethod
    def create_booking(
        property_obj: Property,
        tenant: User,
        check_in_date,
        check_out_date,
        guests: int,
        total_price: float,
        guest_name: str,
        guest_email: str,
        guest_phone: str,
        special_requests: Optional[str] = None,
        status: str = Booking.BookingStatus.PENDING
    ) -> Booking:
        """
        Create a new booking.
        """
        booking = Booking.objects.create(
            property=property_obj,
            tenant=tenant,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            guests=guests,
            total_price=total_price,
            guest_name=guest_name,
            guest_email=guest_email,
            guest_phone=guest_phone,
            special_requests=special_requests,
            status=status
        )
        return booking

    @staticmethod
    def get_booking_by_id(booking_id: int) -> Optional[Booking]:
        """
        Get a booking by ID.
        """
        try:
            return Booking.objects.select_related('property', 'tenant', 'review').get(id=booking_id)
        except Booking.DoesNotExist:
            return None

    @staticmethod
    def get_bookings_by_tenant(tenant: User, page: int = 1, page_size: int = 10, **filters) -> List[Booking]:
        """
        Get all bookings for a tenant with pagination and filtering.
        """
        queryset = Booking.objects.filter(tenant=tenant)
        queryset = BookingRepository._apply_filters(queryset, **filters)

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size

        return queryset.select_related('property', 'tenant')[start:end]

    @staticmethod
    def get_bookings_by_property(property_obj: Property, page: int = 1, page_size: int = 10, **filters) -> List[Booking]:
        """
        Get all bookings for a property with pagination and filtering.
        """
        queryset = Booking.objects.filter(property=property_obj)
        queryset = BookingRepository._apply_filters(queryset, **filters)

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size

        return queryset.select_related('property', 'tenant')[start:end]

    @staticmethod
    def get_bookings_by_property_ids(property_ids: List[int], page: int = 1, page_size: int = 10, **filters) -> List[Booking]:
        """
        Get all bookings for a list of property IDs with pagination and filtering.
        """
        queryset = Booking.objects.filter(property_id__in=property_ids)
        queryset = BookingRepository._apply_filters(queryset, **filters)

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size

        return queryset.select_related('property', 'tenant', 'property__owner')[start:end]

    @staticmethod
    def get_bookings_by_property_owner(owner: User, page: int = 1, page_size: int = 10, **filters) -> List[Booking]:
        """
        Get all bookings for properties owned by a user with pagination and filtering.
        """
        queryset = Booking.objects.filter(property__owner=owner)
        queryset = BookingRepository._apply_filters(queryset, **filters)

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size

        return queryset.select_related('property', 'tenant')[start:end]

    @staticmethod
    def count_bookings_by_tenant(tenant: User, **filters) -> int:
        """
        Count bookings for a tenant with filtering.
        """
        queryset = Booking.objects.filter(tenant=tenant)
        queryset = BookingRepository._apply_filters(queryset, **filters)
        return queryset.count()

    @staticmethod
    def count_bookings_by_property(property_obj: Property, **filters) -> int:
        """
        Count bookings for a property with filtering.
        """
        queryset = Booking.objects.filter(property=property_obj)
        queryset = BookingRepository._apply_filters(queryset, **filters)
        return queryset.count()

    @staticmethod
    def count_bookings_by_property_owner(owner: User, **filters) -> int:
        """
        Count bookings for properties owned by a user with filtering.
        """
        queryset = Booking.objects.filter(property__owner=owner)
        queryset = BookingRepository._apply_filters(queryset, **filters)
        return queryset.count()

    @staticmethod
    def update_booking(booking: Booking, **kwargs) -> Booking:
        """
        Update a booking.
        """
        for key, value in kwargs.items():
            setattr(booking, key, value)

        booking.save()
        return booking

    @staticmethod
    def check_property_availability(property_obj: Property, check_in_date, check_out_date) -> bool:
        """
        Check if a property is available for the given dates.
        """
        # Check if there are any confirmed bookings that overlap with the requested dates
        overlapping_bookings = Booking.objects.filter(
            property=property_obj,
            status=Booking.BookingStatus.CONFIRMED,
            check_in_date__lt=check_out_date,
            check_out_date__gt=check_in_date
        ).exists()

        # Property is available if there are no overlapping bookings and it's not rented
        return not overlapping_bookings and property_obj.status != Property.PropertyStatus.RENTED

    @staticmethod
    def create_booking_review(booking: Booking, rating: int, comment: str) -> BookingReview:
        """
        Create a review for a booking.
        """
        review = BookingReview.objects.create(
            booking=booking,
            rating=rating,
            comment=comment
        )
        return review

    @staticmethod
    def _apply_filters(queryset, **filters):
        """
        Apply filters to a booking queryset.
        """
        if 'status' in filters and filters['status']:
            queryset = queryset.filter(status=filters['status'])

        if 'property_id' in filters and filters['property_id']:
            queryset = queryset.filter(property_id=filters['property_id'])

        if 'is_paid' in filters and filters['is_paid'] is not None:
            queryset = queryset.filter(is_paid=filters['is_paid'])

        if 'check_in_date_from' in filters and filters['check_in_date_from']:
            queryset = queryset.filter(check_in_date__gte=filters['check_in_date_from'])

        if 'check_in_date_to' in filters and filters['check_in_date_to']:
            queryset = queryset.filter(check_in_date__lte=filters['check_in_date_to'])

        if 'check_out_date_from' in filters and filters['check_out_date_from']:
            queryset = queryset.filter(check_out_date__gte=filters['check_out_date_from'])

        if 'check_out_date_to' in filters and filters['check_out_date_to']:
            queryset = queryset.filter(check_out_date__lte=filters['check_out_date_to'])

        # Handle search query
        if 'query' in filters and filters['query']:
            query = filters['query']
            queryset = queryset.filter(
                Q(property__title__icontains=query) |
                Q(tenant__username__icontains=query) |
                Q(tenant__email__icontains=query) |
                Q(tenant__first_name__icontains=query) |
                Q(tenant__last_name__icontains=query) |
                Q(guest_name__icontains=query) |
                Q(guest_email__icontains=query) |
                Q(guest_phone__icontains=query)
            )

        return queryset

    @staticmethod
    def get_all_bookings(page: int = 1, page_size: int = 10, **filters) -> List[Booking]:
        """
        Get all bookings with pagination and filtering (admin view).
        """
        queryset = Booking.objects.all()
        queryset = BookingRepository._apply_filters(queryset, **filters)

        # Apply pagination
        start = (page - 1) * page_size
        end = start + page_size

        return queryset.select_related('property', 'tenant', 'property__owner')[start:end]

    @staticmethod
    def count_all_bookings(**filters) -> int:
        """
        Count all bookings with filtering (admin view).
        """
        queryset = Booking.objects.all()
        queryset = BookingRepository._apply_filters(queryset, **filters)
        return queryset.count()

    @staticmethod
    def delete_booking(booking: Booking) -> bool:
        """
        Delete a booking.
        """
        try:
            booking.delete()
            return True
        except Exception:
            return False
