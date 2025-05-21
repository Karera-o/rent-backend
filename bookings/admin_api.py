from typing import List, Dict, Any, Optional
from ninja_extra import api_controller, route
from ninja_jwt.authentication import JWTAuth
from django.http import HttpRequest
import logging

from .services import BookingService
from .models import Booking
from users.models import User
from .schemas import (
    BookingDetailSchema,
    BookingSummarySchema,
    BookingFilterSchema,
    PaginatedBookingResponse
)
from house_rental.schemas import MessageResponse

logger = logging.getLogger('house_rental')

# Admin API Controller
@api_controller("/admin/bookings", tags=["Admin"])
class AdminBookingController:
    def __init__(self):
        self.booking_service = BookingService()

    @route.get("/", auth=None, response=PaginatedBookingResponse)
    def get_all_bookings(
        self,
        request: HttpRequest,
        page: int = 1,
        page_size: int = 10,
        status: Optional[str] = None,
        payment_status: Optional[str] = None,
        query: Optional[str] = None
    ):
        """Get all bookings with pagination (admin view)"""
        # In a production environment, you would add admin permission check here
        # For now, we're making it public for testing
        # if not request.user.is_staff and request.user.role != User.Role.ADMIN:
        #     return 403, {"message": "You don't have permission to access this resource"}

        # Prepare filters
        filters = {}
        if status:
            filters['status'] = status

        # Handle payment status filter
        if payment_status:
            if payment_status.lower() == 'paid':
                filters['is_paid'] = True
            elif payment_status.lower() == 'pending':
                filters['is_paid'] = False

        # Handle search query
        if query:
            filters['query'] = query

        # Get all bookings
        return self.booking_service.get_all_bookings(
            page=page,
            page_size=page_size,
            **filters
        )

    @route.get("/{booking_id}", auth=JWTAuth(), response={200: BookingDetailSchema, 404: MessageResponse})
    def get_booking(self, request: HttpRequest, booking_id: int):
        """Get booking details by ID (admin view)"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}

        booking = self.booking_service.get_booking(booking_id)
        if not booking:
            return 404, {"message": f"Booking with ID {booking_id} not found"}

        return 200, booking

    @route.patch("/{booking_id}/status", auth=JWTAuth(), response={200: BookingDetailSchema, 400: MessageResponse, 404: MessageResponse})
    def update_booking_status(self, request: HttpRequest, booking_id: int, status: str):
        """Update a booking's status (admin only)"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}

        try:
            booking = self.booking_service.update_booking_status(
                booking_id=booking_id,
                status=status,
                user=request.user
            )
            logger.info(f"Booking {booking_id} status updated to {status} by admin {request.user.id}")
            return 200, booking
        except ValueError as e:
            if "not found" in str(e):
                return 404, {"message": str(e)}
            return 400, {"message": str(e)}

    @route.patch("/{booking_id}/payment", auth=JWTAuth(), response={200: BookingDetailSchema, 400: MessageResponse, 404: MessageResponse})
    def update_booking_payment(self, request: HttpRequest, booking_id: int, is_paid: bool, payment_id: Optional[str] = None):
        """Update a booking's payment status (admin only)"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}

        try:
            if is_paid and not payment_id:
                return 400, {"message": "Payment ID is required when marking as paid"}

            booking = self.booking_service.update_booking_payment(
                booking_id=booking_id,
                is_paid=is_paid,
                payment_id=payment_id,
                user=request.user
            )
            logger.info(f"Booking {booking_id} payment status updated to {is_paid} by admin {request.user.id}")
            return 200, booking
        except ValueError as e:
            if "not found" in str(e):
                return 404, {"message": str(e)}
            return 400, {"message": str(e)}

    @route.delete("/{booking_id}", auth=JWTAuth(), response={200: MessageResponse, 404: MessageResponse})
    def delete_booking(self, request: HttpRequest, booking_id: int):
        """Delete a booking (admin only)"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}

        try:
            success = self.booking_service.delete_booking(
                booking_id=booking_id,
                user=request.user
            )
            if not success:
                return 404, {"message": f"Booking with ID {booking_id} not found"}

            logger.info(f"Booking {booking_id} deleted by admin {request.user.id}")
            return 200, {"message": "Booking deleted successfully"}
        except ValueError as e:
            return 400, {"message": str(e)}
