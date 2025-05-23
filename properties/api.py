from typing import List
from ninja_extra import api_controller, route
from ninja_jwt.authentication import JWTAuth
from ninja import File, UploadedFile
from django.http import HttpRequest
import logging

from .services import PropertyService
from .models import Property
from users.models import User
from .schemas import (
    PropertyCreateSchema,
    PropertyUpdateSchema,
    PropertySearchSchema,
    PropertyImageSchema,
    PropertyDetailSchema,
    PropertySummarySchema,
    PaginatedPropertyResponse
)
from house_rental.schemas import MessageResponse
from house_rental.decorators import rate_limit

logger = logging.getLogger('house_rental')

# API Controller
@api_controller("/properties", tags=["Properties"])
class PropertyController:
    def __init__(self):
        self.property_service = PropertyService()

    @route.post("/", auth=JWTAuth(), response={201: PropertyDetailSchema, 400: MessageResponse, 429: MessageResponse})
    @rate_limit(key_prefix="create_property", limit=10, period=3600)  # 10 properties per hour
    def create_property(self, request: HttpRequest, data: PropertyCreateSchema):
        """Create a new property listing"""
        try:
            logger.info(f"Property creation attempt by user: {request.user.id}")
            property_obj = self.property_service.create_property(
                owner=request.user,
                **data.dict()
            )
            logger.info(f"Property created successfully: {property_obj.id}")
            return 201, self.property_service.get_property_details(property_obj.id)
        except ValueError as e:
            logger.warning(f"Property creation failed: {str(e)}")
            return 400, {"message": str(e)}

    @route.get("/{property_id}", response={200: PropertyDetailSchema, 404: MessageResponse})
    def get_property(self, request: HttpRequest, property_id: int):
        """Get property details by ID"""
        property_details = self.property_service.get_property_details(property_id)
        if not property_details:
            return 404, {"message": "Property not found"}
        return 200, property_details

    @route.get("/", response=PaginatedPropertyResponse)
    def search_properties(self, request: HttpRequest, search: PropertySearchSchema = None,
                         page: int = 1, page_size: int = 10, include_all_statuses: bool = False):
        """Search for properties with filters and pagination"""
        search_params = search.dict(exclude_unset=True) if search else {}

        # Extract owner parameter from search_params
        owner = search_params.pop('owner', None) if search_params else None

        # Handle owner parameter
        if owner == 'current' and request.user and request.user.is_authenticated:
            # If owner=current is specified and user is authenticated, filter by current user
            current_user = request.user
            include_all_statuses = True  # Show all statuses for the owner's properties
        else:
            current_user = None

        # Add parameters to search_params
        if include_all_statuses:
            search_params['include_all_statuses'] = True

        # Process price_range if it exists
        if 'price_range' in search_params and search_params['price_range']:
            price_range = search_params['price_range']
            # Keep price_range in search_params for the repository to handle

        # Process bedrooms filter - it's already handled as gte in the repository
        # The frontend sends values like "1", "2", etc. which are interpreted as "1+", "2+", etc.

        # Get total count
        total = self.property_service.count_properties(owner=current_user, **search_params)

        # Check if this is a request for landlord properties
        include_all_images = True
        if owner == 'current':
            # For landlord properties, don't include all images to improve performance
            include_all_images = False

        # Get paginated results
        properties = self.property_service.search_properties(
            page=page,
            page_size=page_size,
            include_all_images=include_all_images,
            owner=current_user,
            **search_params
        )

        # Calculate total pages
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "results": properties
        }

    @route.get("/my-properties", auth=JWTAuth(), response=List[PropertySummarySchema])
    def get_my_properties(self, request: HttpRequest):
        """Get properties owned by the current user"""
        # Don't include all images for landlord dashboard to improve performance
        return self.property_service.get_owner_properties(request.user, include_all_images=False)

    @route.put("/{property_id}", auth=JWTAuth(), response={200: PropertyDetailSchema, 400: MessageResponse, 404: MessageResponse})
    def update_property(self, request: HttpRequest, property_id: int, data: PropertyUpdateSchema):
        """Update a property"""
        try:
            property_obj = self.property_service.update_property(
                property_id=property_id,
                owner=request.user,
                **data.dict(exclude_unset=True)
            )
            if not property_obj:
                return 404, {"message": "Property not found"}
            return 200, self.property_service.get_property_details(property_obj.id)
        except ValueError as e:
            return 400, {"message": str(e)}

    @route.delete("/{property_id}", auth=JWTAuth(), response={200: MessageResponse, 400: MessageResponse, 404: MessageResponse})
    def delete_property(self, request: HttpRequest, property_id: int):
        """Delete a property"""
        try:
            success = self.property_service.delete_property(
                property_id=property_id,
                user=request.user
            )
            if not success:
                return 404, {"message": "Property not found"}
            return 200, {"message": "Property deleted successfully"}
        except ValueError as e:
            return 400, {"message": str(e)}

    @route.post("/{property_id}/images", auth=JWTAuth(), response={201: MessageResponse, 400: MessageResponse, 404: MessageResponse, 429: MessageResponse})
    @rate_limit(key_prefix="upload_image", limit=20, period=3600)  # 20 images per hour
    def add_property_image(self, request: HttpRequest, property_id: int, image: UploadedFile = File(...), data: PropertyImageSchema = None):
        """Add an image to a property"""
        try:
            logger.info(f"Image upload attempt for property: {property_id} by user: {request.user.id}")
            image_data = data.dict() if data else {}
            property_image = self.property_service.add_property_image(
                property_id=property_id,
                user=request.user,
                image=image,
                **image_data
            )
            if not property_image:
                logger.warning(f"Image upload failed: Property not found - {property_id}")
                return 404, {"message": "Property not found"}
            logger.info(f"Image added successfully to property: {property_id}")
            return 201, {"message": "Image added successfully"}
        except ValueError as e:
            logger.warning(f"Image upload failed: {str(e)}")
            return 400, {"message": str(e)}