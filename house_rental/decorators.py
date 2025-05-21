from functools import wraps
from django.core.cache import cache
from django.http import JsonResponse
import time
import logging

logger = logging.getLogger('house_rental')

def rate_limit(key_prefix, limit=5, period=60):
    """
    Rate limiting decorator for API endpoints.

    Args:
        key_prefix (str): Prefix for the cache key
        limit (int): Maximum number of requests allowed in the period
        period (int): Time period in seconds
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(*args, **kwargs):
            # For Django Ninja, the request is the first argument
            if len(args) > 0 and hasattr(args[0], 'META'):
                request = args[0]
            else:
                # If no request is found in args, try to find it in kwargs
                request = kwargs.get('request')
                if not request:
                    # If we can't find the request, just call the original function
                    logger.warning(f"Could not find request object for rate limiting {key_prefix}")
                    return view_func(*args, **kwargs)

            # Get client IP
            ip = get_client_ip(request)

            # Create a unique key for this IP and endpoint
            cache_key = f"ratelimit:{key_prefix}:{ip}"

            # Get current count and timestamp
            rate_data = cache.get(cache_key)

            now = time.time()

            if rate_data is None:
                # First request, set count to 1
                rate_data = {
                    'count': 1,
                    'timestamp': now
                }
                cache.set(cache_key, rate_data, period)
                return view_func(*args, **kwargs)

            # Check if the period has expired
            if now - rate_data['timestamp'] > period:
                # Reset count
                rate_data = {
                    'count': 1,
                    'timestamp': now
                }
                cache.set(cache_key, rate_data, period)
                return view_func(*args, **kwargs)

            # Check if limit is reached
            if rate_data['count'] >= limit:
                logger.warning(f"Rate limit exceeded for {ip} on {key_prefix}")
                return JsonResponse({
                    'error': 'Rate limit exceeded',
                    'message': f'Too many requests. Please try again in {int(period - (now - rate_data["timestamp"]))} seconds.'
                }, status=429)

            # Increment count
            rate_data['count'] += 1
            cache.set(cache_key, rate_data, period)

            return view_func(*args, **kwargs)

        return _wrapped_view

    return decorator

def get_client_ip(request):
    """
    Get client IP address from request.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip