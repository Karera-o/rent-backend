from ninja_extra import NinjaExtraAPI, api_controller, route
from ninja_jwt.controller import NinjaJWTDefaultController
from ninja_jwt.authentication import JWTAuth
from typing import List, Dict, Any

# Import controllers from apps
from users.api import UserController
from users.admin_api import AdminUserController
from properties.api import PropertyController
from properties.admin_api import AdminPropertyController
from properties.document_api import PropertyDocumentController, AdminDocumentController
from bookings.api import BookingController
from bookings.admin_api import AdminBookingController
from payments.api import PaymentController
from payments.admin_api import AdminPaymentController
from communications.api import ContactController
from admin.admin_api import AdminStatsController

# Create the API instance
api = NinjaExtraAPI(
    title="House Rental API",
    version="1.0.0",
    description="API for House Rental Management System",
)

# Register the JWT controller for authentication
api.register_controllers(NinjaJWTDefaultController)

# Health check endpoint
@api_controller("/", tags=["Health"])
class HealthController:
    @route.get("/health", auth=None)
    def health_check(self):
        """Health check endpoint to verify API is running"""
        return {"status": "ok", "message": "API is running"}

# Register controllers
api.register_controllers(
    HealthController,
    UserController,
    AdminUserController,
    PropertyController,
    AdminPropertyController,
    PropertyDocumentController,
    AdminDocumentController,
    BookingController,
    AdminBookingController,
    PaymentController,
    AdminPaymentController,
    ContactController,
    AdminStatsController,
)