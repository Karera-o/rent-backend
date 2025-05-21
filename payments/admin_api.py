from typing import List, Dict, Any, Optional
from ninja_extra import api_controller, route
from ninja_jwt.authentication import JWTAuth
from django.http import HttpRequest
from django.db.models import Q
import logging

from .services import PaymentService
from .models import Payment
from users.models import User
from .schemas import (
    PaymentDetailSchema,
    PaymentSummarySchema,
    PaymentFilterSchema,
    PaginatedPaymentResponse
)
from house_rental.schemas import MessageResponse

logger = logging.getLogger('house_rental')

# Admin API Controller
@api_controller("/admin/payments", tags=["Admin"])
class AdminPaymentController:
    def __init__(self):
        self.payment_service = PaymentService()

    @route.get("/", auth=None, response=PaginatedPaymentResponse)
    def get_all_payments(
        self,
        request: HttpRequest,
        page: int = 1,
        page_size: int = 10,
        status: Optional[str] = None,
        payment_method: Optional[str] = None,
        query: Optional[str] = None
    ):
        """Get all payments with pagination (admin view)"""
        # In a production environment, you would add admin permission check here
        # For now, we're making it public for testing
        # if not request.user.is_staff and request.user.role != User.Role.ADMIN:
        #     return 403, {"message": "You don't have permission to access this resource"}
        
        # Prepare filters
        filters = {}
        if status:
            filters['status'] = status
        
        # Handle payment method filter
        if payment_method:
            filters['payment_method'] = payment_method
        
        # Handle search query
        if query:
            filters['query'] = query
        
        # Get all payments
        return self.payment_service.get_all_payments(
            page=page,
            page_size=page_size,
            **filters
        )

    @route.get("/{payment_id}", auth=JWTAuth(), response={200: PaymentDetailSchema, 404: MessageResponse})
    def get_payment(self, request: HttpRequest, payment_id: int):
        """Get payment details by ID (admin view)"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}
        
        payment = self.payment_service.get_payment(payment_id, request.user)
        if not payment:
            return 404, {"message": f"Payment with ID {payment_id} not found"}
        
        return 200, payment

    @route.patch("/{payment_id}/status", auth=JWTAuth(), response={200: PaymentDetailSchema, 400: MessageResponse, 404: MessageResponse})
    def update_payment_status(self, request: HttpRequest, payment_id: int, status: str):
        """Update a payment's status (admin only)"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}
        
        try:
            payment = self.payment_service.update_payment_status(
                payment_id=payment_id,
                status=status,
                user=request.user
            )
            logger.info(f"Payment {payment_id} status updated to {status} by admin {request.user.id}")
            return 200, payment
        except ValueError as e:
            if "not found" in str(e):
                return 404, {"message": str(e)}
            return 400, {"message": str(e)}

    @route.delete("/{payment_id}", auth=JWTAuth(), response={200: MessageResponse, 404: MessageResponse})
    def delete_payment(self, request: HttpRequest, payment_id: int):
        """Delete a payment (admin only)"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}
        
        try:
            success = self.payment_service.delete_payment(
                payment_id=payment_id,
                user=request.user
            )
            if not success:
                return 404, {"message": f"Payment with ID {payment_id} not found"}
            
            logger.info(f"Payment {payment_id} deleted by admin {request.user.id}")
            return 200, {"message": "Payment deleted successfully"}
        except ValueError as e:
            return 400, {"message": str(e)}
