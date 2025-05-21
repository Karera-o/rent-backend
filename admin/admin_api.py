from typing import Dict, Any
from ninja_extra import api_controller, route
from ninja_jwt.authentication import JWTAuth
from django.http import HttpRequest
from django.db.models import Sum, Count
import logging
from decimal import Decimal

from users.models import User
from properties.models import Property
from bookings.models import Booking
from payments.models import Payment
from house_rental.schemas import MessageResponse

logger = logging.getLogger('house_rental')

# Admin Stats API Controller
@api_controller("/admin/stats", tags=["Admin"])
class AdminStatsController:
    
    @route.get("/", auth=JWTAuth(), response={200: Dict[str, Any], 403: MessageResponse})
    def get_dashboard_stats(self, request: HttpRequest):
        """Get dashboard statistics for admin"""
        # Check if user is admin
        if not request.user.is_staff and request.user.role != User.Role.ADMIN:
            return 403, {"message": "You don't have permission to access this resource"}
        
        try:
            # Get total users count
            total_users = User.objects.count()
            
            # Get total properties count
            total_properties = Property.objects.count()
            
            # Get total bookings count
            total_bookings = Booking.objects.count()
            
            # Get total revenue from completed payments
            total_revenue = Payment.objects.filter(status=Payment.PaymentStatus.COMPLETED).aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            # Format the revenue
            formatted_revenue = f"${total_revenue:,.2f}"
            
            # For now, we'll use static change percentages
            # In a real application, you would calculate these based on historical data
            return 200, {
                "users": {
                    "total": total_users,
                    "change": "+5.2%",
                    "trend": "up"
                },
                "properties": {
                    "total": total_properties,
                    "change": "+3.8%",
                    "trend": "up"
                },
                "bookings": {
                    "total": total_bookings,
                    "change": "+7.1%",
                    "trend": "up"
                },
                "revenue": {
                    "total": float(total_revenue),
                    "formatted": formatted_revenue,
                    "change": "+4.3%",
                    "trend": "up"
                }
            }
        except Exception as e:
            logger.error(f"Error getting admin stats: {str(e)}")
            return 500, {"message": f"Error getting admin stats: {str(e)}"}
