from typing import List, Dict, Any, Optional
from ninja import Schema
from pydantic import Field, condecimal
from decimal import Decimal
from enum import Enum

from house_rental.schemas import MessageResponse, PaginatedResponse

# Enum for sender types
class SenderType(str, Enum):
    ADMIN = 'admin'
    LANDLORD = 'landlord'

# Property schemas
class PropertyCreateSchema(Schema):
    title: str = Field(..., min_length=5, max_length=255)
    description: str = Field(..., min_length=20)
    property_type: str
    address: str
    city: str
    state: str
    country: str
    zip_code: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    bedrooms: int = Field(..., ge=1)
    bathrooms: Decimal = Field(..., ge=0.5)
    area: int = Field(..., ge=1)
    price_per_night: condecimal(ge=0) = Field(...)
    has_wifi: bool = False
    has_kitchen: bool = False
    has_air_conditioning: bool = False
    has_heating: bool = False
    has_tv: bool = False
    has_parking: bool = False
    has_pool: bool = False
    has_gym: bool = False
    has_maid_service: bool = False
    has_car_rental: bool = False

class PropertyUpdateSchema(Schema):
    title: Optional[str] = Field(None, min_length=5, max_length=255)
    description: Optional[str] = Field(None, min_length=20)
    property_type: Optional[str] = None
    status: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zip_code: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    bedrooms: Optional[int] = Field(None, ge=1)
    bathrooms: Optional[Decimal] = Field(None, ge=0.5)
    area: Optional[int] = Field(None, ge=1)
    price_per_night: Optional[condecimal(ge=0)] = None
    has_wifi: Optional[bool] = None
    has_kitchen: Optional[bool] = None
    has_air_conditioning: Optional[bool] = None
    has_heating: Optional[bool] = None
    has_tv: Optional[bool] = None
    has_parking: Optional[bool] = None
    has_pool: Optional[bool] = None
    has_gym: Optional[bool] = None
    has_maid_service: Optional[bool] = None
    has_car_rental: Optional[bool] = None

class PropertySearchSchema(Schema):
    query: Optional[str] = None
    city: Optional[str] = None
    property_type: Optional[str] = None
    min_price: Optional[float] = None
    max_price: Optional[float] = None
    price_range: Optional[str] = None  # Format: "min-max" (e.g., "0-100", "100-200", "1000-any")
    bedrooms: Optional[int] = None  # Can be used for "X+" format in frontend
    bathrooms: Optional[float] = None
    owner: Optional[str] = None  # Can be 'current' to filter by current user

class PropertyImageSchema(Schema):
    caption: Optional[str] = None
    is_primary: bool = False

class PropertyDetailSchema(Schema):
    id: int
    title: str
    description: str
    property_type: str
    status: str
    document_verification_status: Optional[str] = 'not_submitted'
    owner: Dict[str, Any]
    address: str
    city: str
    state: str
    country: str
    zip_code: str
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    bedrooms: int
    bathrooms: Decimal
    area: int
    price_per_night: Decimal
    amenities: Dict[str, bool]
    additional_services: Dict[str, bool]
    images: List[Dict[str, Any]]
    documents: Optional[List[Dict[str, Any]]] = None
    created_at: Any
    updated_at: Any

class PropertySummarySchema(Schema):
    id: int
    title: str
    property_type: str
    status: str
    document_verification_status: Optional[str] = 'not_submitted'
    owner: Dict[str, Any]
    address: str
    city: str
    state: str
    country: str
    bedrooms: int
    bathrooms: Decimal
    price_per_night: Decimal
    primary_image: Optional[str] = None
    images: Optional[List[Dict[str, Any]]] = None
    created_at: Any

# Property document schemas
class PropertyDocumentCreateSchema(Schema):
    document_type: str
    description: Optional[str] = None

class PropertyDocumentUpdateSchema(Schema):
    document_type: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    rejection_reason: Optional[str] = None
    feedback: Optional[str] = None
    feedback_read: Optional[bool] = None

# Document feedback schemas
class DocumentFeedbackCreateSchema(Schema):
    message: str = Field(..., min_length=1)
    sender_type: SenderType

class DocumentFeedbackUpdateSchema(Schema):
    is_read: bool = True

class DocumentFeedbackDetailSchema(Schema):
    id: int
    document_id: int
    sender_type: str
    user: Dict[str, Any]
    message: str
    is_read: bool
    created_at: Any
    updated_at: Any

class PropertyDocumentDetailSchema(Schema):
    id: int
    property_id: int
    document_type: str
    document: str
    description: Optional[str] = None
    status: str
    rejection_reason: Optional[str] = None
    feedback: Optional[str] = None
    feedback_read: Optional[bool] = False
    feedback_thread: Optional[List[DocumentFeedbackDetailSchema]] = None
    created_at: Any
    updated_at: Any

class PropertyDocumentSummarySchema(Schema):
    id: int
    property_id: int
    property_title: Optional[str] = None
    property_type: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    owner_email: Optional[str] = None
    owner_username: Optional[str] = None
    owner: Optional[Dict[str, Any]] = None
    property: Optional[Dict[str, Any]] = None
    document_type: str
    document: Optional[str] = None
    description: Optional[str] = None
    status: str
    rejection_reason: Optional[str] = None
    feedback: Optional[str] = None
    feedback_read: Optional[bool] = False
    created_at: Any
    updated_at: Optional[Any] = None

# Paginated response schemas
class PaginatedPropertyResponse(PaginatedResponse):
    results: List[PropertySummarySchema]

class PaginatedDocumentResponse(PaginatedResponse):
    results: List[PropertyDocumentSummarySchema]

class PaginatedFeedbackResponse(PaginatedResponse):
    results: List[DocumentFeedbackDetailSchema]