from typing import List, Dict, Any
from ninja_extra import api_controller, route
from ninja_jwt.authentication import JWTAuth
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import logging
import json
import stripe
from django.conf import settings

from .services import PaymentService
from .schemas import (
    PaymentCreateSchema,
    PaymentIntentCreateSchema,
    PaymentMethodCreateSchema,
    PaymentMethodUpdateSchema,
    PaymentFilterSchema,
    PaymentDetailSchema,
    PaymentSummarySchema,
    PaymentMethodSchema,
    PaymentIntentSchema,
    PaginatedPaymentResponse,
    PaginatedPaymentMethodResponse,
    StripePublicKeyResponse
)
from house_rental.schemas import MessageResponse
from house_rental.decorators import rate_limit

logger = logging.getLogger('house_rental')

# Create a global payment service instance for the webhook handler
payment_service = PaymentService()

# API Controller
@api_controller("/payments", tags=["Payments"])
class PaymentController:
    def __init__(self):
        self.payment_service = payment_service

    @route.get("/public-key", response=StripePublicKeyResponse)
    def get_stripe_public_key(self, request: HttpRequest):
        """Get Stripe publishable key"""
        return {
            "publishable_key": self.payment_service.get_stripe_public_key()
        }

    @route.post("/intents", auth=JWTAuth(), response={201: PaymentIntentSchema, 400: MessageResponse, 429: MessageResponse})
    @rate_limit(key_prefix="create_payment_intent",limit=3, period=10) 
    # Reduce the limit to 3 requests per 10 seconds to prevent rapid duplicate requests
    def create_payment_intent(self, request: HttpRequest, data: PaymentIntentCreateSchema):
        """Create a payment intent for a booking"""
        try:
            logger.info(f"Payment intent creation attempt by user: {request.user.id} for booking: {data.booking_id}")
            payment_intent = self.payment_service.create_payment_intent(
                user=request.user,
                booking_id=data.booking_id,
                setup_future_usage=data.setup_future_usage
            )
            logger.info(f"Payment intent created/retrieved: {payment_intent['stripe_payment_intent_id']}")
            logger.info(f"Payment intent response: client_secret={payment_intent['stripe_client_secret']}")
            return 201, payment_intent
        except ValueError as e:
            logger.warning(f"Payment intent creation failed: {str(e)}")
            return 400, {"message": str(e)}

    @route.post("/confirm", auth=JWTAuth(), response={200: Dict, 400: MessageResponse, 429: MessageResponse})
    @rate_limit(key_prefix="confirm_payment", limit=10, period=3600)  # 10 payment confirmations per hour
    def confirm_payment(self, request: HttpRequest, data: PaymentCreateSchema):
        """Confirm a payment for a booking"""
        try:
            logger.info(f"Payment confirmation attempt by user: {request.user.id}")
            payment_result = self.payment_service.confirm_payment(
                user=request.user,
                payment_intent_id=data.payment_intent_id,
                payment_method_id=data.payment_method_id,
                save_payment_method=data.save_payment_method
            )
            logger.info(f"Payment confirmation result: {payment_result['status']}")
            return 200, payment_result
        except ValueError as e:
            logger.warning(f"Payment confirmation failed: {str(e)}")
            return 400, {"message": str(e)}

    

    @route.get("/user", auth=JWTAuth(), response=PaginatedPaymentResponse)
    def get_user_payments(
        self,
        request: HttpRequest,
        page: int = 1,
        page_size: int = 10,
        filters: PaymentFilterSchema = None
    ):
        """Get all payments for the current user"""
        filter_dict = filters.dict(exclude_unset=True) if filters else {}
        return self.payment_service.get_user_payments(
            user=request.user,
            page=page,
            page_size=page_size,
            **filter_dict
        )

    @route.get("/landlord", auth=JWTAuth(), response={200: PaginatedPaymentResponse, 400: MessageResponse})
    def get_landlord_payments(
        self,
        request: HttpRequest,
        page: int = 1,
        page_size: int = 10,
        filters: PaymentFilterSchema = None
    ):
        """Get all payments for properties owned by the landlord"""
        try:
            filter_dict = filters.dict(exclude_unset=True) if filters else {}
            return 200, self.payment_service.get_landlord_payments(
                landlord=request.user,
                page=page,
                page_size=page_size,
                **filter_dict
            )
        except ValueError as e:
            return 400, {"message": str(e)}

    @route.get("/booking/{booking_id}", auth=JWTAuth(), response={200: PaginatedPaymentResponse, 400: MessageResponse})
    def get_booking_payments(
        self,
        request: HttpRequest,
        booking_id: int,
        page: int = 1,
        page_size: int = 10,
        filters: PaymentFilterSchema = None
    ):
        """Get all payments for a booking"""
        try:
            filter_dict = filters.dict(exclude_unset=True) if filters else {}
            return 200, self.payment_service.get_booking_payments(
                booking_id=booking_id,
                user=request.user,
                page=page,
                page_size=page_size,
                **filter_dict
            )
        except ValueError as e:
            return 400, {"message": str(e)}

    @route.post("/methods", auth=JWTAuth(), response={201: PaymentMethodSchema, 400: MessageResponse, 429: MessageResponse})
    @rate_limit(key_prefix="create_payolivierkarera2020ment_method", limit=10, period=3600)  # 10 payment methods per hour
    def create_payment_method(self, request: HttpRequest, data: PaymentMethodCreateSchema):
        """Create a payment method for the current user"""
        try:
            logger.info(f"Payment method creation attempt by user: {request.user.id}")
            payment_method = self.payment_service.create_payment_method(
                user=request.user,
                payment_method_id=data.payment_method_id,
                set_as_default=data.set_as_default
            )
            logger.info(f"Payment method created successfully: {payment_method['id']}")
            return 201, payment_method
        except ValueError as e:
            logger.warning(f"Payment method creation failed: {str(e)}")
            return 400, {"message": str(e)}

    @route.get("/methods", auth=JWTAuth(), response=PaginatedPaymentMethodResponse)
    def get_payment_methods(
        self,
        request: HttpRequest,
        page: int = 1,
        page_size: int = 10
    ):
        """Get all payment methods for the current user"""
        return self.payment_service.get_payment_methods(
            user=request.user,
            page=page,
            page_size=page_size
        )

    
    @route.delete("/methods/{payment_method_id}", auth=JWTAuth(), response={204: None, 400: MessageResponse, 404: MessageResponse})
    def delete_payment_method(self, request: HttpRequest, payment_method_id: int):
        """Delete a payment method"""
        try:
            self.payment_service.delete_payment_method(
                user=request.user,
                payment_method_id=payment_method_id
            )
            logger.info(f"Payment method deleted: {payment_method_id} by user {request.user.id}")
            return 204, None
        except ValueError as e:
            if "not found" in str(e):
                return 404, {"message": str(e)}
            return 400, {"message": str(e)}

    @route.post("/webhook", auth=None, response={200: Dict, 400: MessageResponse})
    @csrf_exempt
    def webhook(self, request: HttpRequest):
        """Handle Stripe webhook events"""
        try:
            payload = request.body.decode('utf-8')
            sig_header = request.headers.get('Stripe-Signature', request.headers.get('stripe-signature'))
            
            logger.info(f"API webhook request received, signature: {sig_header[:20] if sig_header else 'None'}...")
            logger.info(f"Using webhook secret: {settings.STRIPE_WEBHOOK_SECRET[:10]}...")
            
            if not sig_header:
                return 400, {"message": "Missing Stripe signature"}

            result = self.payment_service.handle_stripe_webhook(payload, sig_header)
            return 200, result
        except ValueError as e:
            logger.error(f"Webhook error: {str(e)}")
            return 400, {"message": str(e)}

    @route.get("/debug/client-secret", auth=None, response={200: Dict})
    def get_debug_client_secret(self, request: HttpRequest):
        """Debug endpoint to get a valid client secret directly"""
        # This is just for debugging purposes
        client_secret = "pi_3PX9ynXXXXXXXXXX_secret_XXXXXXXX"
        return 200, {
            "client_secret": client_secret,
            "message": "This is a debug client secret for testing"
        }

    @route.post("/quick-intent", auth=None, response={200: Dict, 400: MessageResponse})
    def create_quick_intent(self, request: HttpRequest, data: PaymentIntentCreateSchema):
        """Create a payment intent without authentication and return only essential data"""
        try:
            logger.info(f"Quick payment intent creation attempt for booking: {data.booking_id}")
            
            # Use the guest payment intent method
            payment_intent = self.payment_service.create_guest_payment_intent(
                booking_id=data.booking_id
            )
            
            # Return only the essential data needed by the frontend
            return 200, {
                "client_secret": payment_intent['stripe_client_secret'],
                "amount": float(payment_intent['amount']),
                "id": payment_intent['stripe_payment_intent_id']
            }
        except Exception as e:
            logger.error(f"Quick payment intent creation failed: {str(e)}")
            return 400, {"message": str(e)}

    @route.post("/guest-intents", auth=None, response={201: PaymentIntentSchema, 400: MessageResponse, 429: MessageResponse})
    @rate_limit(key_prefix="create_guest_payment_intent", limit=10, period=3600)
    def create_guest_payment_intent(self, request: HttpRequest, data: PaymentIntentCreateSchema):
        """Create a payment intent for guest users without authentication"""
        try:
            logger.info(f"Guest payment intent creation attempt for booking: {data.booking_id}")
            
            # Use the dedicated method for guest payment intents
            payment_intent = self.payment_service.create_guest_payment_intent(
                booking_id=data.booking_id,
                setup_future_usage=data.setup_future_usage
            )
            
            logger.info(f"Guest payment intent created successfully: {payment_intent['stripe_payment_intent_id']}")
            logger.info(f"Guest payment intent client_secret: {payment_intent['stripe_client_secret']}")
            
            return 201, payment_intent
        except ValueError as e:
            logger.warning(f"Guest payment intent creation failed: {str(e)}")
            return 400, {"message": str(e)}

    @route.post("/guest/confirm", auth=None, response={200: Dict, 400: MessageResponse, 429: MessageResponse})
    @rate_limit(key_prefix="confirm_guest_payment", limit=10, period=3600)
    def confirm_guest_payment(self, request: HttpRequest, data: PaymentCreateSchema):
        """Confirm a payment for a guest booking without authentication"""
        try:
            logger.info(f"Guest payment confirmation attempt for payment intent: {data.payment_intent_id}")
            
            # Get the payment intent from database to find the associated user
            db_payment_intent = self.payment_service.payment_intent_repository.get_payment_intent_by_stripe_id(data.payment_intent_id)
            if not db_payment_intent:
                return 400, {"message": f"Payment intent with ID {data.payment_intent_id} not found"}
            
            # Verify this is a guest payment (inactive user)
            if db_payment_intent.user.is_active:
                return 400, {"message": "This endpoint is only for guest payments. Please use the authenticated confirmation endpoint."}
            
            # Use the guest user associated with the payment intent
            payment_result = self.payment_service.confirm_payment(
                user=db_payment_intent.user,
                payment_intent_id=data.payment_intent_id,
                payment_method_id=data.payment_method_id,
                save_payment_method=False  # Guests don't save payment methods
            )
            
            logger.info(f"Guest payment confirmation result: {payment_result['status']}")
            return 200, payment_result
            
        except ValueError as e:
            logger.warning(f"Guest payment confirmation failed: {str(e)}")
            return 400, {"message": str(e)}
        
    @route.patch("/methods/{payment_method_id}", auth=JWTAuth(), response={200: PaymentMethodSchema, 400: MessageResponse, 404: MessageResponse})
    def update_payment_method(self, request: HttpRequest, payment_method_id: int, data: PaymentMethodUpdateSchema):
        """Update a payment method"""
        try:
            payment_method = self.payment_service.update_payment_method(
                user=request.user,
                payment_method_id=payment_method_id,
                set_as_default=data.set_as_default
            )
            logger.info(f"Payment method updated: {payment_method_id} by user {request.user.id}")
            return 200, payment_method
        except ValueError as e:
            if "not found" in str(e):
                return 404, {"message": str(e)}
            return 400, {"message": str(e)}
        
        
    @route.get("/{payment_id}", auth=JWTAuth(), response={200: PaymentDetailSchema, 404: MessageResponse})
    def get_payment(self, request: HttpRequest, payment_id: int):
        """Get a payment by ID"""
        payment = self.payment_service.get_payment(payment_id, request.user)
        if not payment:
            return 404, {"message": f"Payment with ID {payment_id} not found"}

        return 200, payment

# Standalone webhook handler (similar to Flask example)
@csrf_exempt
@require_POST
def stripe_webhook_handler(request):
    """Handle Stripe webhook events"""
    try:
        payload = request.body.decode('utf-8')
        sig_header = request.headers.get('Stripe-Signature', request.headers.get('stripe-signature'))
        
        logger.info(f"Webhook request received, signature: {sig_header[:20]}...")
        logger.info(f"Using webhook secret: {settings.STRIPE_WEBHOOK_SECRET[:10]}...")
        logger.info(f"Payload length: {len(payload)} bytes")
        
        if not sig_header:
            logger.error("Missing Stripe signature header")
            return JsonResponse({"error": "Missing Stripe signature header"}, status=400)
        
        try:
            # Try with the correct header name
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
            
            # Log the event type
            logger.info(f"Successfully constructed event of type: {event['type']}")
            
            # Handle different event types
            if event['type'] == 'payment_intent.succeeded':
                payment_intent = event['data']['object']
                logger.info(f"Payment intent: {payment_intent}")
                logger.info(f"Payment intent succeeded: {payment_intent['id']}")
                result = payment_service._handle_payment_intent_succeeded(payment_intent)
                logger.info(f"Handled payment_intent.succeeded: {result}")
                return JsonResponse(result)
            elif event['type'] == 'payment_intent.failed':
                payment_intent = event['data']['object']
                result = payment_service._handle_payment_intent_failed(payment_intent)
                logger.info(f"Handled payment_intent.failed: {result}")
                return JsonResponse(result)
            else:
                logger.info(f"Unhandled event type: {event['type']}")
                return JsonResponse({"status": "success", "message": f"Unhandled event type: {event['type']}"})
                
        except stripe.error.SignatureVerificationError as e:
            logger.error(f"Invalid signature: {str(e)}")
            logger.error(f"First 50 chars of signature: {sig_header[:50]}")
            logger.error(f"First 50 chars of payload: {payload[:50]}")
            return JsonResponse({"error": f"Invalid signature: {str(e)}"}, status=400)
            
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        return JsonResponse({"error": f"Invalid payload: {str(e)}"}, status=400)
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}", exc_info=True)
        return JsonResponse({"error": f"Error handling webhook: {str(e)}"}, status=500)
