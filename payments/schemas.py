from typing import List, Dict, Any, Optional
from datetime import datetime
from ninja import Schema
from pydantic import Field, EmailStr, validator
from decimal import Decimal

from house_rental.schemas import MessageResponse, PaginatedResponse


# Payment schemas
class PaymentCreateSchema(Schema):
    payment_intent_id: str
    payment_method_id: Optional[str] = None
    save_payment_method: bool = False


class PaymentIntentCreateSchema(Schema):
    booking_id: int
    setup_future_usage: Optional[str] = None


class PaymentMethodCreateSchema(Schema):
    payment_method_id: str
    set_as_default: bool = False


class PaymentMethodUpdateSchema(Schema):
    set_as_default: bool = True


class PaymentFilterSchema(Schema):
    status: Optional[str] = None
    booking_id: Optional[int] = None
    created_from: Optional[datetime] = None
    created_to: Optional[datetime] = None


class PaymentMethodSchema(Schema):
    id: int
    type: str
    is_default: bool
    card_brand: Optional[str] = None
    card_last4: Optional[str] = None
    card_exp_month: Optional[int] = None
    card_exp_year: Optional[int] = None
    stripe_payment_method_id: str
    created_at: datetime


class PaymentIntentSchema(Schema):
    id: int
    booking: Dict[str, Any]
    amount: Decimal
    currency: str
    status: str
    stripe_payment_intent_id: str
    stripe_client_secret: str
    created_at: datetime


class PaymentDetailSchema(Schema):
    id: int
    booking: Dict[str, Any]
    user: Dict[str, Any]
    amount: Decimal
    currency: str
    status: str
    stripe_payment_intent_id: Optional[str] = None
    stripe_payment_method_id: Optional[str] = None
    stripe_customer_id: Optional[str] = None
    receipt_url: Optional[str] = None
    receipt_email: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None


class PropertySchema(Schema):
    id: int
    title: str
    images: Optional[List[str]] = None


class TenantSchema(Schema):
    id: int
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None


class BookingSchema(Schema):
    id: int
    property: Optional[PropertySchema] = None
    tenant: Optional[TenantSchema] = None
    check_in_date: Optional[datetime] = None
    check_out_date: Optional[datetime] = None
    guest_name: Optional[str] = None
    guests: Optional[int] = None
    total_price: Optional[Decimal] = None


class UserSchema(Schema):
    id: int
    username: str
    email: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None


class PaymentSummarySchema(Schema):
    id: int
    booking_id: int
    booking: Optional[BookingSchema] = None
    user: Optional[UserSchema] = None
    tenant: Optional[TenantSchema] = None  # Direct tenant access
    property: Optional[PropertySchema] = None  # Direct property access
    amount: Decimal
    currency: str
    status: str
    payment_method_type: Optional[str] = 'Visa Card'
    stripe_payment_intent_id: Optional[str] = None
    stripe_payment_method_id: Optional[str] = None
    receipt_url: Optional[str] = None
    receipt_email: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class PaginatedPaymentResponse(PaginatedResponse):
    items: List[PaymentSummarySchema]


class PaginatedPaymentMethodResponse(PaginatedResponse):
    items: List[PaymentMethodSchema]


class StripePublicKeyResponse(Schema):
    publishable_key: str
