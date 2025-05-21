from typing import List, Dict, Any, Optional
from ninja_extra import api_controller, route
from ninja_jwt.authentication import JWTAuth
from django.http import HttpRequest
from django.db.models import Count
import logging

from .services import PropertyService
from .models import Property
from users.models import User
from .schemas import (
    PropertyDetailSchema,
    PropertySummarySchema,
    PaginatedPropertyResponse
)
from house_rental.schemas import MessageResponse

logger = logging.getLogger('house_rental')

# Admin API Controller
@api_controller("/admin/properties", tags=["Admin"])
class AdminPropertyController:
    def __init__(self):
        self.property_service = PropertyService()

    @route.get("/", auth=None, response=PaginatedPropertyResponse)
    def get_all_properties(self, request: HttpRequest, page: int = 1, page_size: int = 10,
                          status: Optional[str] = None, property_type: Optional[str] = None,
                          query: Optional[str] = None):
        """Get all properties with pagination (admin view)"""
        # In a production environment, you would add admin permission check here
        # For now, we're making it public for testing

        # Prepare search parameters
        search_params = {}
        if status:
            search_params['status'] = status
        if property_type:
            search_params['property_type'] = property_type
        if query:
            search_params['query'] = query

        # Include all statuses for admin view
        search_params['include_all_statuses'] = True

        # Get total count
        total = self.property_service.count_properties(**search_params)

        # Get paginated results - for admin view, don't include all images to improve performance
        properties = self.property_service.search_properties(
            page=page,
            page_size=page_size,
            include_all_images=False,  # Don't include all images for admin dashboard
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

    @route.get("/{property_id}", auth=JWTAuth(), response={200: PropertyDetailSchema, 404: MessageResponse})
    def get_property(self, request: HttpRequest, property_id: int):
        """Get property details by ID (admin view)"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}

        property_details = self.property_service.get_property_details(property_id)
        if not property_details:
            return 404, {"message": f"Property with ID {property_id} not found"}

        return 200, property_details

    @route.put("/{property_id}/approve", auth=JWTAuth(), response={200: MessageResponse, 404: MessageResponse})
    def approve_property(self, request: HttpRequest, property_id: int):
        """Approve a property (admin only)"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}

        try:
            success = self.property_service.update_property_status(
                property_id=property_id,
                status=Property.Status.AVAILABLE
            )
            if not success:
                return 404, {"message": f"Property with ID {property_id} not found"}

            return 200, {"message": "Property approved successfully"}
        except ValueError as e:
            return 400, {"message": str(e)}

    @route.put("/{property_id}/reject", auth=JWTAuth(), response={200: MessageResponse, 404: MessageResponse})
    def reject_property(self, request: HttpRequest, property_id: int):
        """Reject a property (admin only)"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}

        try:
            success = self.property_service.update_property_status(
                property_id=property_id,
                status=Property.Status.REJECTED
            )
            if not success:
                return 404, {"message": f"Property with ID {property_id} not found"}

            return 200, {"message": "Property rejected successfully"}
        except ValueError as e:
            return 400, {"message": str(e)}

    @route.delete("/{property_id}", auth=JWTAuth(), response={200: MessageResponse, 404: MessageResponse})
    def delete_property(self, request: HttpRequest, property_id: int):
        """Delete a property (admin only)"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}

        try:
            success = self.property_service.delete_property(
                property_id=property_id,
                user=request.user
            )
            if not success:
                return 404, {"message": f"Property with ID {property_id} not found"}

            return 200, {"message": "Property deleted successfully"}
        except ValueError as e:
            return 400, {"message": str(e)}
