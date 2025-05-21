import logging
import json
import traceback
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger('house_rental')

class ExceptionMiddleware:
    """
    Middleware to handle unhandled exceptions in the API.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        return self.get_response(request)

    def process_exception(self, request, exception):
        """
        Process any unhandled exceptions and return a proper JSON response.
        """
        # Log the exception
        logger.error(
            f"Unhandled exception: {str(exception)}\n"
            f"Path: {request.path}\n"
            f"Method: {request.method}\n"
            f"User: {request.user}",
            exc_info=True
        )
        
        # In debug mode, include the traceback
        if settings.DEBUG:
            error_details = {
                'error': 'Internal Server Error',
                'message': str(exception),
                'traceback': traceback.format_exc()
            }
        else:
            # In production, don't expose detailed error information
            error_details = {
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            }
        
        return JsonResponse(error_details, status=500)