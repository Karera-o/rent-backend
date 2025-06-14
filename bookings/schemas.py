from typing import List, Dict, Any, Optional
from datetime import date
from ninja import Schema
from pydantic import Field, EmailStr, validator
from decimal import Decimal

from house_rental.schemas import MessageResponse, PaginatedResponse


# User information schema for guest booking
class GuestUserSchema(Schema):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    phone_number: str = Field(..., min_length=5, max_length=20)
    birthday: Optional[date] = None
    
    @validator('birthday')
    def validate_age(cls, v):
        if v:
            from datetime import datetime
            from dateutil.relativedelta import relativedelta
            today = datetime.now().date()
            age = relativedelta(today, v).years
            if age < 18:
                raise ValueError("User must be at least 18 years old")
        return v


# Booking schemas
class BookingCreateSchema(Schema):
    property_id: int
    check_in_date: date
    check_out_date: date
    guests: int = Field(..., ge=1)
    guest_name: str = Field(..., min_length=2, max_length=255)
    guest_email: EmailStr
    guest_phone: str = Field(..., min_length=5, max_length=20)
    special_requests: Optional[str] = None

    @validator('check_out_date')
    def check_out_after_check_in(cls, v, values):
        if 'check_in_date' in values and v <= values['check_in_date']:
            raise ValueError('Check-out date must be after check-in date')
        return v


# Extended schema for guest booking (when user is not logged in)
class GuestBookingCreateSchema(BookingCreateSchema):
    user_info: GuestUserSchema


class GuestBookingAccessSchema(Schema):
    guest_email: EmailStr


class BookingUpdateSchema(Schema):
    status: Optional[str] = None
    is_paid: Optional[bool] = None
    payment_id: Optional[str] = None


class BookingReviewCreateSchema(Schema):
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., min_length=10)


class BookingFilterSchema(Schema):
    status: Optional[str] = None
    property_id: Optional[int] = None
    check_in_date_from: Optional[date] = None
    check_in_date_to: Optional[date] = None
    check_out_date_from: Optional[date] = None
    check_out_date_to: Optional[date] = None


class BookingDetailSchema(Schema):
    id: int
    property: Dict[str, Any]
    tenant: Dict[str, Any]
    check_in_date: date
    check_out_date: date
    guests: int
    total_price: Decimal
    status: str
    guest_name: str
    guest_email: str
    guest_phone: str
    special_requests: Optional[str] = None
    is_paid: bool
    payment_date: Optional[Any] = None
    payment_id: Optional[str] = None
    review: Optional[Dict[str, Any]] = None
    created_at: Any
    updated_at: Any
    duration_days: int


class BookingSummarySchema(Schema):
    id: int
    property: Dict[str, Any]
    tenant: Dict[str, Any]
    check_in_date: date
    check_out_date: date
    guests: int
    total_price: Decimal
    status: str
    is_paid: bool
    created_at: Any


class PaginatedBookingResponse(PaginatedResponse):
    items: List[BookingSummarySchema]


# Custom response schema for guest booking access
class GuestBookingConfirmationSchema(Schema):
    first_name: str
    property_name: str
    property_address: str
    property_id: int
    checkin_date: str
    checkout_date: str
    guest_count: int
    guest_email: str
    booking_id: int
    nights: int
    accommodation_cost: Decimal
    taxes: Decimal
    total_amount: Decimal
    payment_method: str
    payment_date: str
    reply_to_email: str
    current_year: int
