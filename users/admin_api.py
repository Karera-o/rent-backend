from typing import List, Dict, Any, Optional
from ninja_extra import api_controller, route
from ninja_jwt.authentication import JWTAuth
from django.http import HttpRequest
from django.db.models import Count
import logging

from .services import UserService
from .models import User
from .schemas import (
    UserProfileSchema,
    UserProfileUpdateSchema,
    PaginatedUserResponse,
    AdminUserListSchema
)
from house_rental.schemas import MessageResponse

logger = logging.getLogger('house_rental')

# Admin API Controller
@api_controller("/admin/users", tags=["Admin"])
class AdminUserController:
    def __init__(self):
        self.user_service = UserService()

    @route.get("/", auth=JWTAuth(), response=PaginatedUserResponse)
    def get_all_users(self, request: HttpRequest, page: int = 1, page_size: int = 10,
                      role: Optional[str] = None, status: Optional[str] = None,
                      is_active: Optional[str] = None, pending: Optional[str] = None,
                      query: Optional[str] = None):
        """Get all users with pagination (admin only)"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}

        # Convert is_active string to boolean
        is_active_bool = None
        if is_active is not None:
            is_active_bool = is_active.lower() == 'true'

        # Handle pending status (agents waiting for approval)
        if pending and pending.lower() == 'true':
            role = User.Role.AGENT
            is_active_bool = False

        # Get users with pagination
        users, total, total_pages = self.user_service.get_all_users(
            page=page,
            page_size=page_size,
            role=role,
            is_active=is_active_bool,
            search_query=query
        )

        # Transform users to response format
        user_items = []
        for user in users:
            # Get property and booking counts
            properties_count = getattr(user, 'properties_count', 0)
            bookings_count = getattr(user, 'bookings_count', 0)

            # Create user item
            user_item = AdminUserListSchema(
                id=user.id,
                username=user.username,
                email=user.email,
                first_name=user.first_name,
                last_name=user.last_name,
                role=user.role,
                is_active=user.is_active,
                date_joined=user.date_joined,
                properties_count=properties_count,
                bookings_count=bookings_count
            )
            user_items.append(user_item)

        # Return paginated response
        return {
            "items": user_items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }

    @route.get("/{user_id}", auth=JWTAuth(), response={200: UserProfileSchema, 404: MessageResponse})
    def get_user(self, request: HttpRequest, user_id: int):
        """Get a user by ID (admin only)"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}

        # Get user
        user_profile = self.user_service.get_user_profile(user_id)
        if not user_profile:
            return 404, {"message": f"User with ID {user_id} not found"}

        return 200, user_profile

    @route.put("/{user_id}", auth=JWTAuth(), response={200: UserProfileSchema, 404: MessageResponse})
    def update_user(self, request: HttpRequest, user_id: int, data: UserProfileUpdateSchema):
        """Update a user (admin only)"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}

        # Update user
        user = self.user_service.update_user_profile(
            user_id=user_id,
            **data.dict(exclude_unset=True)
        )

        if not user:
            return 404, {"message": f"User with ID {user_id} not found"}

        return 200, self.user_service.get_user_profile(user.id)

    @route.delete("/{user_id}", auth=JWTAuth(), response={200: MessageResponse, 404: MessageResponse})
    def delete_user(self, request: HttpRequest, user_id: int):
        """Delete a user (admin only)"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}

        # Delete user
        success = self.user_service.delete_user(user_id)
        if not success:
            return 404, {"message": f"User with ID {user_id} not found"}

        return 200, {"message": "User deleted successfully"}

    @route.put("/{user_id}/activate", auth=JWTAuth(), response={200: MessageResponse, 404: MessageResponse})
    def activate_user(self, request: HttpRequest, user_id: int):
        """Activate a user (admin only)"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}

        # Activate user
        success = self.user_service.update_user_status(user_id, is_active=True)
        if not success:
            return 404, {"message": f"User with ID {user_id} not found"}

        return 200, {"message": "User activated successfully"}

    @route.put("/{user_id}/deactivate", auth=JWTAuth(), response={200: MessageResponse, 404: MessageResponse})
    def deactivate_user(self, request: HttpRequest, user_id: int):
        """Deactivate a user (admin only)"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}

        # Deactivate user
        success = self.user_service.update_user_status(user_id, is_active=False)
        if not success:
            return 404, {"message": f"User with ID {user_id} not found"}

        return 200, {"message": "User deactivated successfully"}
