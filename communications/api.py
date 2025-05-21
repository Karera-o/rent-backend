from typing import List
from ninja_extra import api_controller, route
from ninja_jwt.authentication import JWTAuth
from django.http import HttpRequest
import logging

from .services import ContactService
from .schemas import (
    ContactMessageCreateSchema,
    ContactMessageDetailSchema,
    ContactMessageSummarySchema,
    PaginatedContactMessageResponse
)
from house_rental.schemas import MessageResponse
from house_rental.decorators import rate_limit

logger = logging.getLogger('house_rental')

# API Controller
@api_controller("/contact", tags=["Contact"])
class ContactController:
    def __init__(self):
        self.contact_service = ContactService()
    
    @route.post("/", response={201: MessageResponse, 400: MessageResponse, 429: MessageResponse})
    @rate_limit(key_prefix="create_contact", limit=5, period=3600)  # 5 contact messages per hour
    def create_contact_message(self, request: HttpRequest, data: ContactMessageCreateSchema):
        """Create a new contact message"""
        try:
            logger.info(f"Contact message creation attempt")
            contact_message = self.contact_service.create_contact_message(
                **data.dict()
            )
            logger.info(f"Contact message created successfully: {contact_message.id}")
            return 201, {"message": "Your message has been sent successfully! Our team will get back to you soon."}
        except ValueError as e:
            logger.warning(f"Contact message creation failed: {str(e)}")
            return 400, {"message": str(e)}
    
    @route.get("/", auth=JWTAuth(), response=PaginatedContactMessageResponse)
    def get_all_contact_messages(self, request: HttpRequest, page: int = 1, page_size: int = 10):
        """Get all contact messages (admin only)"""
        # Check if user is admin
        if not request.user.is_staff:
            return 403, {"message": "You don't have permission to access this resource"}
        
        return self.contact_service.get_all_contact_messages(page, page_size)
    
    @route.get("/{message_id}", auth=JWTAuth(), response={200: ContactMessageDetailSchema, 404: MessageResponse})
    def get_contact_message(self, request: HttpRequest, message_id: int):
        """Get contact message details (admin only)"""
        # Check if user is admin
        if not request.user.is_staff:
            return 403, {"message": "You don't have permission to access this resource"}
        
        message_details = self.contact_service.get_contact_message_details(message_id)
        if not message_details:
            return 404, {"message": "Contact message not found"}
        
        return 200, message_details
    
    @route.put("/{message_id}/read", auth=JWTAuth(), response={200: MessageResponse, 404: MessageResponse})
    def mark_as_read(self, request: HttpRequest, message_id: int):
        """Mark a contact message as read (admin only)"""
        # Check if user is admin
        if not request.user.is_staff:
            return 403, {"message": "You don't have permission to access this resource"}
        
        success = self.contact_service.mark_as_read(message_id)
        if not success:
            return 404, {"message": "Contact message not found"}
        
        return 200, {"message": "Contact message marked as read"}
    
    @route.delete("/{message_id}", auth=JWTAuth(), response={200: MessageResponse, 404: MessageResponse})
    def delete_contact_message(self, request: HttpRequest, message_id: int):
        """Delete a contact message (admin only)"""
        # Check if user is admin
        if not request.user.is_staff:
            return 403, {"message": "You don't have permission to access this resource"}
        
        success = self.contact_service.delete_contact_message(message_id)
        if not success:
            return 404, {"message": "Contact message not found"}
        
        return 200, {"message": "Contact message deleted successfully"}
