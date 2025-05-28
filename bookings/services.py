from typing import Optional, Dict, Any, List
import logging
from datetime import date, timedelta
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone

from .repositories import BookingRepository
from .models import Booking, BookingReview
from properties.repositories import PropertyRepository
from users.models import User
from .strategies import BookingStrategyFactory, BookingStrategy

logger = logging.getLogger('house_rental')

# Cache timeout in seconds (10 minutes)
CACHE_TIMEOUT = 60 * 10

class BookingService:
    """
    Service for booking-related business logic.
    """

    def __init__(self, booking_repository: BookingRepository = None, property_repository: PropertyRepository = None):
        self.booking_repository = booking_repository or BookingRepository()
        self.property_repository = property_repository or PropertyRepository()

    def create_booking(
        self,
        tenant: Optional[User],
        property_id: int,
        check_in_date: date,
        check_out_date: date,
        guests: int,
        guest_name: str,
        guest_email: str,
        guest_phone: str,
        special_requests: Optional[str] = None,
        user_info: Optional[Dict[str, Any]] = None
    ) -> Booking:
        """
        Create a new booking.
        For logged in users, tenant parameter is required.
        For non-logged in users, user_info parameter is required.
        """
        # Get the property
        property_obj = self.property_repository.get_property_by_id(property_id)
        if not property_obj:
            raise ValueError(f"Property with ID {property_id} not found")

        # Validate property is approved
        if property_obj.status != property_obj.PropertyStatus.APPROVED:
            raise ValueError("Property is not available for booking")

        # Validate dates
        today = timezone.now().date()
        if check_in_date < today:
            raise ValueError("Check-in date cannot be in the past")

        if check_out_date <= check_in_date:
            raise ValueError("Check-out date must be after check-in date")

        # Calculate duration and validate minimum stay
        duration = (check_out_date - check_in_date).days
        if duration < 1:
            raise ValueError("Minimum stay is 1 day")

        # Check availability
        if not self.booking_repository.check_property_availability(property_obj, check_in_date, check_out_date):
            raise ValueError("Property is not available for the selected dates")

        # Calculate total price
        total_price = property_obj.price_per_night * duration

        # Determine the appropriate booking strategy
        strategy_factory = BookingStrategyFactory()
        
        if tenant:
            # Logged-in user booking
            strategy = strategy_factory.create_strategy(request_user=tenant)
            booking_tenant = strategy.prepare_tenant()
        elif user_info:
            # Guest booking (non-logged-in user)
            strategy = strategy_factory.create_strategy()
            booking_tenant = strategy.prepare_tenant(**user_info)
        else:
            raise ValueError("Either tenant or user_info must be provided")

        # Create the booking
        booking = self.booking_repository.create_booking(
            property_obj=property_obj,
            tenant=booking_tenant,
            check_in_date=check_in_date,
            check_out_date=check_out_date,
            guests=guests,
            total_price=total_price,
            guest_name=guest_name,
            guest_email=guest_email,
            guest_phone=guest_phone,
            special_requests=special_requests
        )

        logger.info(f"Booking created: {booking.id} for property {property_obj.id} by tenant {booking_tenant.id}")

        return booking

    def get_booking(self, booking_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a booking by ID with all details.
        """
        # Try to get from cache first
        cache_key = f"booking_{booking_id}"
        booking_data = cache.get(cache_key)

        if booking_data:
            return booking_data

        # If not in cache, get from database
        booking = self.booking_repository.get_booking_by_id(booking_id)
        if not booking:
            return None

        # Format the booking data
        booking_data = self._format_booking_detail(booking)

        # Cache the result
        cache.set(cache_key, booking_data, CACHE_TIMEOUT)

        return booking_data

    def get_tenant_bookings(
        self,
        tenant: User,
        page: int = 1,
        page_size: int = 10,
        **filters
    ) -> Dict[str, Any]:
        """
        Get all bookings for a tenant with pagination and filtering.
        """
        bookings = self.booking_repository.get_bookings_by_tenant(
            tenant=tenant,
            page=page,
            page_size=page_size,
            **filters
        )

        total = self.booking_repository.count_bookings_by_tenant(tenant, **filters)
        total_pages = (total + page_size - 1) // page_size

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'items': [self._format_booking_summary(booking) for booking in bookings]
        }

    def get_property_bookings(
        self,
        property_id: int,
        page: int = 1,
        page_size: int = 10,
        **filters
    ) -> Dict[str, Any]:
        """
        Get all bookings for a property with pagination and filtering.
        """
        property_obj = self.property_repository.get_property_by_id(property_id)
        if not property_obj:
            raise ValueError(f"Property with ID {property_id} not found")

        bookings = self.booking_repository.get_bookings_by_property(
            property_obj=property_obj,
            page=page,
            page_size=page_size,
            **filters
        )

        total = self.booking_repository.count_bookings_by_property(property_obj, **filters)
        total_pages = (total + page_size - 1) // page_size

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'items': [self._format_booking_summary(booking) for booking in bookings]
        }

    def get_owner_bookings(
        self,
        owner: User,
        page: int = 1,
        page_size: int = 10,
        **filters
    ) -> Dict[str, Any]:
        """
        Get all bookings for properties owned by a user with pagination and filtering.
        """
        # Validate owner is an agent or admin
        if owner.role != User.Role.AGENT and owner.role != User.Role.ADMIN:
            raise ValueError("Only agents and admins can view owner bookings")

        bookings = self.booking_repository.get_bookings_by_property_owner(
            owner=owner,
            page=page,
            page_size=page_size,
            **filters
        )

        total = self.booking_repository.count_bookings_by_property_owner(owner, **filters)
        total_pages = (total + page_size - 1) // page_size

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'items': [self._format_booking_summary(booking) for booking in bookings]
        }

    def update_booking_status(self, booking_id: int, status: str, user: User) -> Dict[str, Any]:
        """
        Update a booking's status.
        """
        booking = self.booking_repository.get_booking_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking with ID {booking_id} not found")

        # Check permissions
        if user.role == User.Role.TENANT and user.id != booking.tenant.id:
            raise ValueError("You don't have permission to update this booking")

        if user.role == User.Role.AGENT and user.id != booking.property.owner.id:
            raise ValueError("You don't have permission to update this booking")

        # Validate status transition
        if not self._is_valid_status_transition(booking.status, status):
            raise ValueError(f"Invalid status transition from {booking.status} to {status}")

        # Update the booking
        booking = self.booking_repository.update_booking(booking, status=status)

        # If status is confirmed, update property status
        if status == Booking.BookingStatus.CONFIRMED:
            self.property_repository.update_property(
                booking.property,
                status=booking.property.PropertyStatus.RENTED
            )

        # If status is cancelled or completed and there are no other confirmed bookings,
        # update property status back to approved
        if status in [Booking.BookingStatus.CANCELLED, Booking.BookingStatus.COMPLETED]:
            active_bookings = self.booking_repository.get_bookings_by_property(
                property_obj=booking.property,
                status=Booking.BookingStatus.CONFIRMED
            )
            if not active_bookings:
                self.property_repository.update_property(
                    booking.property,
                    status=booking.property.PropertyStatus.APPROVED
                )

        logger.info(f"Booking {booking_id} status updated to {status} by user {user.id}")

        # Clear cache
        cache_key = f"booking_{booking_id}"
        cache.delete(cache_key)

        return self._format_booking_detail(booking)

    def mark_booking_as_paid(self, booking_id: int, payment_id: str, user: User) -> Dict[str, Any]:
        """
        Mark a booking as paid.
        """
        booking = self.booking_repository.get_booking_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking with ID {booking_id} not found")

        # Check permissions
        if user.role == User.Role.TENANT and user.id != booking.tenant.id:
            raise ValueError("You don't have permission to update this booking")

        if user.role == User.Role.AGENT and user.id != booking.property.owner.id:
            raise ValueError("You don't have permission to update this booking")

        # Update the booking
        booking = self.booking_repository.update_booking(
            booking,
            is_paid=True,
            payment_id=payment_id,
            payment_date=timezone.now()
        )

        logger.info(f"Booking {booking_id} marked as paid with payment ID {payment_id} by user {user.id}")

        # Clear cache
        cache_key = f"booking_{booking_id}"
        cache.delete(cache_key)

        return self._format_booking_detail(booking)

    def create_booking_review(self, booking_id: int, rating: int, comment: str, user: User) -> Dict[str, Any]:
        """
        Create a review for a booking.
        """
        booking = self.booking_repository.get_booking_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking with ID {booking_id} not found")

        # Check if user is the tenant
        if user.id != booking.tenant.id:
            raise ValueError("Only the tenant can review a booking")

        # Check if booking is completed
        if booking.status != Booking.BookingStatus.COMPLETED:
            raise ValueError("Only completed bookings can be reviewed")

        # Check if booking already has a review
        if hasattr(booking, 'review') and booking.review:
            raise ValueError("Booking already has a review")

        # Create the review
        review = self.booking_repository.create_booking_review(
            booking=booking,
            rating=rating,
            comment=comment
        )

        logger.info(f"Review created for booking {booking_id} by user {user.id}")

        # Clear cache
        cache_key = f"booking_{booking_id}"
        cache.delete(cache_key)

        return self._format_booking_detail(booking)

    def _format_booking_detail(self, booking: Booking) -> Dict[str, Any]:
        """
        Format a booking object into a detailed dictionary.
        """
        property_data = {
            'id': booking.property.id,
            'title': booking.property.title,
            'type': booking.property.property_type,
            'address': booking.property.address,
            'city': booking.property.city,
            'state': booking.property.state,
            'country': booking.property.country,
            'price_per_night': booking.property.price_per_night,
            'bedrooms': booking.property.bedrooms,
            'bathrooms': booking.property.bathrooms,
            'owner': {
                'id': booking.property.owner.id,
                'username': booking.property.owner.username,
                'email': booking.property.owner.email,
                'phone_number': booking.property.owner.phone_number
            }
        }

        tenant_data = {
            'id': booking.tenant.id,
            'username': booking.tenant.username,
            'email': booking.tenant.email,
            'phone_number': booking.tenant.phone_number
        }

        review_data = None
        if hasattr(booking, 'review') and booking.review:
            review_data = {
                'id': booking.review.id,
                'rating': booking.review.rating,
                'comment': booking.review.comment,
                'created_at': booking.review.created_at
            }

        return {
            'id': booking.id,
            'property': property_data,
            'tenant': tenant_data,
            'check_in_date': booking.check_in_date,
            'check_out_date': booking.check_out_date,
            'guests': booking.guests,
            'total_price': booking.total_price,
            'status': booking.status,
            'guest_name': booking.guest_name,
            'guest_email': booking.guest_email,
            'guest_phone': booking.guest_phone,
            'special_requests': booking.special_requests,
            'is_paid': booking.is_paid,
            'payment_date': booking.payment_date,
            'payment_id': booking.payment_id,
            'review': review_data,
            'created_at': booking.created_at,
            'updated_at': booking.updated_at,
            'duration_days': booking.get_duration_days()
        }

    def _format_booking_summary(self, booking: Booking) -> Dict[str, Any]:
        """
        Format a booking object into a summary dictionary.
        """
        property_data = {
            'id': booking.property.id,
            'title': booking.property.title,
            'property_type': booking.property.property_type,
            'city': booking.property.city,
            'state': booking.property.state,
            'country': booking.property.country,
            'images': [img.image.url for img in booking.property.images.all()[:1]] if hasattr(booking.property, 'images') else []
        }

        tenant_data = {
            'id': booking.tenant.id,
            'username': booking.tenant.username,
            'email': booking.tenant.email,
            'first_name': booking.tenant.first_name,
            'last_name': booking.tenant.last_name,
            'role': booking.tenant.role
        }

        return {
            'id': booking.id,
            'property': property_data,
            'tenant': tenant_data,
            'check_in_date': booking.check_in_date,
            'check_out_date': booking.check_out_date,
            'guests': booking.guests,
            'total_price': booking.total_price,
            'status': booking.status,
            'is_paid': booking.is_paid,
            'created_at': booking.created_at,
            'duration_days': booking.get_duration_days()
        }

    def _format_booking_summary_without_images(self, booking: Booking) -> Dict[str, Any]:
        """
        Format a booking object into a summary dictionary without property images.
        """
        property_data = {
            'id': booking.property.id,
            'title': booking.property.title,
            'property_type': booking.property.property_type,
            'city': booking.property.city,
            'state': booking.property.state,
            'country': booking.property.country
        }

        tenant_data = {
            'id': booking.tenant.id,
            'username': booking.tenant.username,
            'email': booking.tenant.email,
            'first_name': booking.tenant.first_name,
            'last_name': booking.tenant.last_name,
            'role': booking.tenant.role
        }

        return {
            'id': booking.id,
            'property': property_data,
            'tenant': tenant_data,
            'check_in_date': booking.check_in_date,
            'check_out_date': booking.check_out_date,
            'guests': booking.guests,
            'total_price': booking.total_price,
            'status': booking.status,
            'is_paid': booking.is_paid,
            'created_at': booking.created_at,
            'duration_days': booking.get_duration_days()
        }

    def _is_valid_status_transition(self, current_status: str, new_status: str) -> bool:
        """
        Check if a status transition is valid.
        """
        # Define valid transitions
        valid_transitions = {
            Booking.BookingStatus.PENDING: [
                Booking.BookingStatus.CONFIRMED,
                Booking.BookingStatus.CANCELLED
            ],
            Booking.BookingStatus.CONFIRMED: [
                Booking.BookingStatus.CANCELLED,
                Booking.BookingStatus.COMPLETED
            ],
            Booking.BookingStatus.CANCELLED: [],  # No transitions from cancelled
            Booking.BookingStatus.COMPLETED: []   # No transitions from completed
        }

        # Check if the transition is valid
        return new_status in valid_transitions.get(current_status, [])

    def get_all_bookings(
        self,
        page: int = 1,
        page_size: int = 10,
        **filters
    ) -> Dict[str, Any]:
        """
        Get all bookings with pagination and filtering (admin view).
        """
        # Get all bookings
        bookings = self.booking_repository.get_all_bookings(
            page=page,
            page_size=page_size,
            **filters
        )

        total = self.booking_repository.count_all_bookings(**filters)
        total_pages = (total + page_size - 1) // page_size

        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages,
            'items': [self._format_booking_summary_without_images(booking) for booking in bookings]
        }

    def update_booking_payment(
        self,
        booking_id: int,
        is_paid: bool,
        payment_id: Optional[str],
        user: User
    ) -> Dict[str, Any]:
        """
        Update a booking's payment status.
        """
        booking = self.booking_repository.get_booking_by_id(booking_id)
        if not booking:
            raise ValueError(f"Booking with ID {booking_id} not found")

        # Check permissions for non-admin users
        if user.role != User.Role.ADMIN:
            if user.role == User.Role.TENANT and user.id != booking.tenant.id:
                raise ValueError("You don't have permission to update this booking")

            if user.role == User.Role.AGENT and user.id != booking.property.owner.id:
                raise ValueError("You don't have permission to update this booking")

        # Update the booking
        update_data = {'is_paid': is_paid}

        if is_paid:
            update_data['payment_id'] = payment_id
            update_data['payment_date'] = timezone.now()
        else:
            # If marking as unpaid, clear payment info
            update_data['payment_id'] = None
            update_data['payment_date'] = None

        booking = self.booking_repository.update_booking(booking, **update_data)
        return self.get_booking(booking.id)

    def delete_booking(
        self,
        booking_id: int,
        user: User
    ) -> bool:
        """
        Delete a booking.
        """
        booking = self.booking_repository.get_booking_by_id(booking_id)
        if not booking:
            return False

        # Check permissions for non-admin users
        if user.role != User.Role.ADMIN:
            if user.role == User.Role.TENANT and user.id != booking.tenant.id:
                raise ValueError("You don't have permission to delete this booking")

            if user.role == User.Role.AGENT and user.id != booking.property.owner.id:
                raise ValueError("You don't have permission to delete this booking")

        # Delete the booking
        return self.booking_repository.delete_booking(booking)

    def get_booking_by_email(self, booking_id: int, guest_email: str) -> Optional[Dict[str, Any]]:
        """
        Get a booking by ID and guest email for non-authenticated access.
        This allows guests to access their booking details using their email.
        """
        # Get booking from database
        booking = self.booking_repository.get_booking_by_id(booking_id)
        if not booking:
            return None

        # Verify the email matches the booking's guest email
        if booking.guest_email.lower() != guest_email.lower():
            logger.warning(f"Email mismatch for booking {booking_id}: {guest_email} vs {booking.guest_email}")
            return None

        # Format the booking data
        booking_data = self._format_booking_detail(booking)

        logger.info(f"Guest booking access: {booking_id} for email {guest_email}")

        return booking_data
