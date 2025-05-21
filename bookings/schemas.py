from typing import List, Dict, Any, Optional
from datetime import date
from ninja import Schema
from pydantic import Field, EmailStr, validator
from decimal import Decimal

from house_rental.schemas import MessageResponse, PaginatedResponse


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
