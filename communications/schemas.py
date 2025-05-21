from typing import List, Dict, Any, Optional
from ninja import Schema
from pydantic import Field, EmailStr

from house_rental.schemas import MessageResponse, PaginatedResponse


# Contact schemas
class ContactMessageCreateSchema(Schema):
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: str = Field(..., min_length=5, max_length=20)
    subject: str
    message: str = Field(..., min_length=10)


class ContactMessageDetailSchema(Schema):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str
    subject: str
    message: str
    is_read: bool
    created_at: Any
    updated_at: Any


class ContactMessageSummarySchema(Schema):
    id: int
    first_name: str
    last_name: str
    email: str
    subject: str
    is_read: bool
    created_at: Any


# Paginated contact message response
class PaginatedContactMessageResponse(PaginatedResponse):
    results: List[ContactMessageSummarySchema]
