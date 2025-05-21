from typing import List, Dict, Any, Optional
from ninja_extra import api_controller, route
from ninja_jwt.authentication import JWTAuth
from ninja import File, UploadedFile
from django.http import HttpRequest
import logging

from .services import PropertyService
from .models import PropertyDocument
from .schemas import (
    PropertyDocumentCreateSchema,
    PropertyDocumentUpdateSchema,
    PropertyDocumentDetailSchema,
    PropertyDocumentSummarySchema,
    DocumentFeedbackCreateSchema,
    DocumentFeedbackDetailSchema,
    PaginatedDocumentResponse
)
from house_rental.schemas import MessageResponse
from house_rental.decorators import rate_limit

logger = logging.getLogger('house_rental')

# Document API Controller for Landlords
@api_controller("/properties/documents", tags=["Property Documents"])
class PropertyDocumentController:
    def __init__(self):
        self.property_service = PropertyService()

    @route.post("/{property_id}", auth=JWTAuth(), response={201: PropertyDocumentDetailSchema, 400: MessageResponse, 404: MessageResponse, 500: MessageResponse})
    @rate_limit(key_prefix="upload_document", limit=10, period=3600)  # 10 documents per hour
    def add_document(self, request: HttpRequest, property_id: int):
        """Add a document to a property"""
        try:
            logger.info(f"Document upload attempt for property: {property_id} by user: {request.user.id}")

            # Log the raw request for debugging
            logger.info(f"Request method: {request.method}")
            logger.info(f"Request content type: {request.content_type}")
            logger.info(f"Request headers: {request.headers}")
            logger.info(f"Request POST data: {dict(request.POST)}")
            logger.info(f"Request FILES: {list(request.FILES.keys())}")

            # Extract document type and description directly from the request POST data
            document_type = request.POST.get('document_type')
            description = request.POST.get('description')

            # Get the uploaded file from request.FILES
            if 'document' not in request.FILES:
                logger.warning("No document file found in the request")
                return 400, {"message": "No document file provided"}

            document = request.FILES['document']

            # Log the document file details
            logger.info(f"Document file name: {document.name}, size: {document.size}, content type: {document.content_type}")

            if not document_type:
                return 400, {"message": "Document type is required"}

            document_obj = self.property_service.add_property_document(
                property_id=property_id,
                user=request.user,
                document=document,
                document_type=document_type,
                description=description
            )

            if not document_obj:
                logger.warning(f"Document upload failed: Property not found - {property_id}")
                return 404, {"message": "Property not found"}

            logger.info(f"Document added successfully to property: {property_id}")

            # Get document details
            document_details = self.property_service.get_document_details(document_obj.id, request.user)
            return 201, document_details

        except ValueError as e:
            logger.warning(f"Document upload failed: {str(e)}")
            return 400, {"message": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error uploading document: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return 500, {"message": "An unexpected error occurred"}

    @route.get("/{property_id}", auth=JWTAuth(), response=List[PropertyDocumentSummarySchema])
    def get_property_documents(self, request: HttpRequest, property_id: int):
        """Get all documents for a property"""
        try:
            documents = self.property_service.get_property_documents(
                property_id=property_id,
                user=request.user
            )
            return documents
        except ValueError as e:
            logger.warning(f"Error fetching documents: {str(e)}")
            return []

    @route.get("/{property_id}/{document_id}", auth=JWTAuth(), response={200: PropertyDocumentDetailSchema, 404: MessageResponse})
    def get_document(self, request: HttpRequest, property_id: int, document_id: int):
        """Get document details"""
        try:
            document = self.property_service.get_document_details(
                document_id=document_id,
                user=request.user
            )

            if not document:
                return 404, {"message": "Document not found"}

            return 200, document
        except ValueError as e:
            logger.warning(f"Error fetching document: {str(e)}")
            return 400, {"message": str(e)}

    @route.put("/{property_id}/{document_id}/mark-feedback-read", auth=JWTAuth(), response={200: MessageResponse, 404: MessageResponse})
    def mark_feedback_read(self, request: HttpRequest, property_id: int, document_id: int):
        """Mark document feedback as read"""
        try:
            success = self.property_service.mark_document_feedback_read(
                document_id=document_id,
                user=request.user
            )

            if not success:
                return 404, {"message": "Document not found"}

            return 200, {"message": "Feedback marked as read"}
        except ValueError as e:
            logger.warning(f"Error marking feedback as read: {str(e)}")
            return 400, {"message": str(e)}

    @route.post("/{property_id}/{document_id}/feedback", auth=JWTAuth(), response={201: DocumentFeedbackDetailSchema, 400: MessageResponse, 404: MessageResponse})
    def add_feedback_message(self, request: HttpRequest, property_id: int, document_id: int, data: DocumentFeedbackCreateSchema):
        """Add a feedback message to a document's feedback thread"""
        try:
            feedback = self.property_service.add_document_feedback_message(
                document_id=document_id,
                user=request.user,
                message=data.message
            )

            if not feedback:
                return 404, {"message": "Document not found"}

            return 201, feedback
        except ValueError as e:
            logger.warning(f"Error adding feedback message: {str(e)}")
            return 400, {"message": str(e)}

# Admin Document API Controller
@api_controller("/admin/documents", tags=["Admin"])
class AdminDocumentController:
    def __init__(self):
        self.property_service = PropertyService()

    @route.get("/pending", auth=JWTAuth(), response=List[PropertyDocumentSummarySchema])
    def get_pending_documents(self, request: HttpRequest):
        """Get all pending documents (admin only)"""
        try:
            # Check if user is admin
            if not request.user.is_staff and request.user.role != 'admin':
                return []

            documents = self.property_service.get_pending_documents(request.user)
            return documents
        except ValueError as e:
            logger.warning(f"Error fetching pending documents: {str(e)}")
            return []

    @route.put("/{document_id}/approve", auth=JWTAuth(), response={200: MessageResponse, 404: MessageResponse})
    def approve_document(self, request: HttpRequest, document_id: int):
        """Approve a document (admin only)"""
        try:
            # Check if user is admin
            if not request.user.is_staff and request.user.role != 'admin':
                return 403, {"message": "You don't have permission to access this resource"}

            document = self.property_service.update_document_status(
                document_id=document_id,
                user=request.user,
                status=PropertyDocument.DocumentStatus.APPROVED
            )

            if not document:
                return 404, {"message": "Document not found"}

            return 200, {"message": "Document approved successfully"}
        except ValueError as e:
            logger.warning(f"Error approving document: {str(e)}")
            return 400, {"message": str(e)}

    @route.put("/{document_id}/reject", auth=JWTAuth(), response={200: MessageResponse, 404: MessageResponse})
    def reject_document(self, request: HttpRequest, document_id: int, data: PropertyDocumentUpdateSchema):
        """Reject a document (admin only)"""
        try:
            # Check if user is admin
            if not request.user.is_staff and request.user.role != 'admin':
                return 403, {"message": "You don't have permission to access this resource"}

            document = self.property_service.update_document_status(
                document_id=document_id,
                user=request.user,
                status=PropertyDocument.DocumentStatus.REJECTED,
                rejection_reason=data.rejection_reason
            )

            if not document:
                return 404, {"message": "Document not found"}

            return 200, {"message": "Document rejected successfully"}
        except ValueError as e:
            logger.warning(f"Error rejecting document: {str(e)}")
            return 400, {"message": str(e)}

    @route.put("/{document_id}/feedback", auth=JWTAuth(), response={200: MessageResponse, 404: MessageResponse})
    def send_document_feedback(self, request: HttpRequest, document_id: int, data: PropertyDocumentUpdateSchema):
        """Send feedback on a document without changing its status (admin only)"""
        try:
            # Check if user is admin
            if not request.user.is_staff and request.user.role != 'admin':
                return 403, {"message": "You don't have permission to access this resource"}

            # Validate feedback
            if not data.feedback:
                return 400, {"message": "Feedback message is required"}

            # Add feedback to the thread instead of overwriting the old feedback
            feedback = self.property_service.add_document_feedback_message(
                document_id=document_id,
                user=request.user,
                message=data.feedback
            )

            if not feedback:
                return 404, {"message": "Document not found"}

            return 200, {"message": "Feedback sent successfully"}
        except ValueError as e:
            logger.warning(f"Error sending document feedback: {str(e)}")
            return 400, {"message": str(e)}

    @route.post("/{document_id}/feedback-thread", auth=JWTAuth(), response={201: DocumentFeedbackDetailSchema, 400: MessageResponse, 404: MessageResponse})
    def add_admin_feedback_message(self, request: HttpRequest, document_id: int, data: DocumentFeedbackCreateSchema):
        """Add a feedback message to a document's feedback thread (admin only)"""
        try:
            # Check if user is admin
            if not request.user.is_staff and request.user.role != 'admin':
                return 403, {"message": "You don't have permission to access this resource"}

            feedback = self.property_service.add_document_feedback_message(
                document_id=document_id,
                user=request.user,
                message=data.message
            )

            if not feedback:
                return 404, {"message": "Document not found"}

            return 201, feedback
        except ValueError as e:
            logger.warning(f"Error adding admin feedback message: {str(e)}")
            return 400, {"message": str(e)}
