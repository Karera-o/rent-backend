from typing import List
from ninja_extra import api_controller, route
from ninja_jwt.authentication import JWTAuth
from django.http import HttpRequest
import logging

from .services import BookingService
from .models import Booking
from .schemas import (
    BookingCreateSchema,
    GuestBookingCreateSchema,
    BookingUpdateSchema,
    BookingReviewCreateSchema,
    BookingFilterSchema,
    BookingDetailSchema,
    BookingSummarySchema,
    PaginatedBookingResponse
)
from house_rental.schemas import MessageResponse
from house_rental.decorators import rate_limit

logger = logging.getLogger('house_rental')

# API Controller
@api_controller("/bookings", tags=["Bookings"])
class BookingController:
    def __init__(self):
        self.booking_service = BookingService()

    @route.post("/", auth=JWTAuth(), response={201: BookingDetailSchema, 400: MessageResponse, 429: MessageResponse})
    @rate_limit(key_prefix="create_booking", limit=10, period=3600)  # 10 bookings per hour
    def create_booking(self, request: HttpRequest, data: BookingCreateSchema):
        """Create a new booking for logged-in users"""
        try:
            logger.info(f"Booking creation attempt by logged-in user: {request.user.id}")
            booking = self.booking_service.create_booking(
                tenant=request.user,
                property_id=data.property_id,
                check_in_date=data.check_in_date,
                check_out_date=data.check_out_date,
                guests=data.guests,
                guest_name=data.guest_name,
                guest_email=data.guest_email,
                guest_phone=data.guest_phone,
                special_requests=data.special_requests
            )
            logger.info(f"Booking created successfully: {booking.id}")
            return 201, self.booking_service.get_booking(booking.id)
        except ValueError as e:
            logger.warning(f"Booking creation failed: {str(e)}")
            return 400, {"message": str(e)}
            
    @route.post("/guest", auth=None, response={201: BookingDetailSchema, 400: MessageResponse, 429: MessageResponse})
    @rate_limit(key_prefix="create_guest_booking", limit=5, period=3600)  # 5 guest bookings per hour
    def create_guest_booking(self, request: HttpRequest, data: GuestBookingCreateSchema):
        """Create a new booking for non-logged-in users (guests)"""
        try:
            logger.info(f"Guest booking creation attempt from IP: {request.META.get('REMOTE_ADDR')}")
            
            # Prepare user info from the guest data
            user_info = {
                'full_name': data.user_info.full_name,
                'email': data.user_info.email,
                'phone_number': data.user_info.phone_number,
                'birthday': data.user_info.birthday
            }
            
            booking = self.booking_service.create_booking(
                tenant=None,  # No logged-in tenant
                property_id=data.property_id,
                check_in_date=data.check_in_date,
                check_out_date=data.check_out_date,
                guests=data.guests,
                guest_name=data.guest_name,
                guest_email=data.guest_email,
                guest_phone=data.guest_phone,
                special_requests=data.special_requests,
                user_info=user_info  # Pass user info for creating the inactive account
            )
            logger.info(f"Guest booking created successfully: {booking.id}")
            return 201, self.booking_service.get_booking(booking.id)
        except ValueError as e:
            logger.warning(f"Guest booking creation failed: {str(e)}")
            return 400, {"message": str(e)}

    @route.get("/tenant", auth=JWTAuth(), response=PaginatedBookingResponse)
    def get_tenant_bookings(
        self,
        request: HttpRequest,
        page: int = 1,
        page_size: int = 10,
        filters: BookingFilterSchema = None
    ):
        """Get all bookings for the current tenant"""
        filter_dict = filters.dict(exclude_unset=True) if filters else {}
        return self.booking_service.get_tenant_bookings(
            tenant=request.user,
            page=page,
            page_size=page_size,
            **filter_dict
        )

    @route.get("/property/{property_id}", auth=JWTAuth(), response={200: PaginatedBookingResponse, 400: MessageResponse})
    def get_property_bookings(
        self,
        request: HttpRequest,
        property_id: int,
        page: int = 1,
        page_size: int = 10,
        filters: BookingFilterSchema = None
    ):
        """Get all bookings for a property"""
        try:
            filter_dict = filters.dict(exclude_unset=True) if filters else {}
            return 200, self.booking_service.get_property_bookings(
                property_id=property_id,
                page=page,
                page_size=page_size,
                **filter_dict
            )
        except ValueError as e:
            return 400, {"message": str(e)}

    @route.get("/owner", auth=JWTAuth(), response={200: PaginatedBookingResponse, 400: MessageResponse})
    def get_owner_bookings(
        self,
        request: HttpRequest,
        page: int = 1,
        page_size: int = 10,
        filters: BookingFilterSchema = None
    ):
        """Get all bookings for properties owned by the current user"""
        try:
            filter_dict = filters.dict(exclude_unset=True) if filters else {}
            return 200, self.booking_service.get_owner_bookings(
                owner=request.user,
                page=page,
                page_size=page_size,
                **filter_dict
            )
        except ValueError as e:
            return 400, {"message": str(e)}

    @route.get("/{booking_id}", auth=JWTAuth(), response={200: BookingDetailSchema, 404: MessageResponse})
    def get_booking(self, request: HttpRequest, booking_id: int):
        """Get a booking by ID"""
        booking = self.booking_service.get_booking(booking_id)
        if not booking:
            return 404, {"message": f"Booking with ID {booking_id} not found"}

        # Check permissions
        if (request.user.role == 'tenant' and request.user.id != booking['tenant']['id'] and
            request.user.role != 'admin' and request.user.role != 'agent'):
            return 404, {"message": f"Booking with ID {booking_id} not found"}

        return 200, booking

    @route.patch("/{booking_id}/status", auth=JWTAuth(), response={200: BookingDetailSchema, 400: MessageResponse, 404: MessageResponse})
    def update_booking_status(self, request: HttpRequest, booking_id: int, data: BookingUpdateSchema):
        """Update a booking's status"""
        try:
            if not data.status:
                return 400, {"message": "Status is required"}

            booking = self.booking_service.update_booking_status(
                booking_id=booking_id,
                status=data.status,
                user=request.user
            )
            logger.info(f"Booking {booking_id} status updated to {data.status} by user {request.user.id}")
            return 200, booking
        except ValueError as e:
            if "not found" in str(e):
                return 404, {"message": str(e)}
            return 400, {"message": str(e)}

    @route.patch("/{booking_id}/payment", auth=JWTAuth(), response={200: BookingDetailSchema, 400: MessageResponse, 404: MessageResponse})
    def mark_booking_as_paid(self, request: HttpRequest, booking_id: int, data: BookingUpdateSchema):
        """Mark a booking as paid"""
        try:
            if not data.payment_id:
                return 400, {"message": "Payment ID is required"}

            booking = self.booking_service.mark_booking_as_paid(
                booking_id=booking_id,
                payment_id=data.payment_id,
                user=request.user
            )
            logger.info(f"Booking {booking_id} marked as paid with payment ID {data.payment_id} by user {request.user.id}")
            return 200, booking
        except ValueError as e:
            if "not found" in str(e):
                return 404, {"message": str(e)}
            return 400, {"message": str(e)}

    @route.post("/{booking_id}/review", auth=JWTAuth(), response={201: BookingDetailSchema, 400: MessageResponse, 404: MessageResponse})
    def create_booking_review(self, request: HttpRequest, booking_id: int, data: BookingReviewCreateSchema):
        """Create a review for a booking"""
        try:
            booking = self.booking_service.create_booking_review(
                booking_id=booking_id,
                rating=data.rating,
                comment=data.comment,
                user=request.user
            )
            logger.info(f"Review created for booking {booking_id} by user {request.user.id}")
            return 201, booking
        except ValueError as e:
            if "not found" in str(e):
                return 404, {"message": str(e)}
            return 400, {"message": str(e)}
