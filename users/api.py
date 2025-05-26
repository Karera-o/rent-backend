from typing import List, Optional
from ninja_extra import api_controller, route
from ninja_jwt.authentication import JWTAuth
from django.http import HttpRequest
from django.db.models import Q
import logging

from .services import UserService
from .models import User
from .schemas import (
    UserRegistrationSchema,
    UserProfileSchema,
    UserProfileUpdateSchema,
    PasswordChangeSchema,
    GoogleAuthSchema,
    GoogleAuthResponseSchema,
    TwitterInitResponseSchema,
    TwitterCallbackSchema,
    TwitterAuthResponseSchema
)
from house_rental.schemas import MessageResponse
from house_rental.decorators import rate_limit

logger = logging.getLogger('house_rental')

# API Controller
@api_controller("/users", tags=["Users"])
class UserController:
    def __init__(self):
        self.user_service = UserService()

    @route.post("/register", response={201: UserProfileSchema, 400: MessageResponse, 429: MessageResponse})
    # Removed rate limiting for now as it's causing issues
    def register(self, request, data: UserRegistrationSchema):
        """Register a new user"""
        try:
            # Debug logging
            logger.info(f"Request received: {request}")
            logger.info(f"Request body: {request.body}")
            logger.info(f"Data received: {data}")

            if data is None:
                logger.error("Data is None, registration cannot proceed")
                return 400, {"message": "Invalid request data"}

            logger.info(f"Registration attempt for username: {data.username}, email: {data.email}")
            user = self.user_service.register_user(
                username=data.username,
                email=data.email,
                password=data.password,
                role=data.role,
                first_name=data.first_name,
                last_name=data.last_name,
                phone_number=data.phone_number,
                birthday=data.birthday
            )
            logger.info(f"User registered successfully: {user.id}")
            return 201, self.user_service.get_user_profile(user.id)
        except ValueError as e:
            logger.warning(f"Registration failed: {str(e)}")
            return 400, {"message": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error during registration: {str(e)}")
            return 500, {"message": "An unexpected error occurred"}

    @route.get("/profile", auth=JWTAuth(), response=UserProfileSchema)
    def get_profile(self, request: HttpRequest):
        """Get the current user's profile"""
        return self.user_service.get_user_profile(request.user.id)

    @route.put("/profile", auth=JWTAuth(), response=UserProfileSchema)
    def update_profile(self, request: HttpRequest, data: UserProfileUpdateSchema):
        """Update the current user's profile"""
        user = self.user_service.update_user_profile(
            user_id=request.user.id,
            **data.dict(exclude_unset=True)
        )
        return self.user_service.get_user_profile(user.id)

    @route.post("/change-password", auth=JWTAuth(), response={200: MessageResponse, 400: MessageResponse})
    def change_password(self, request: HttpRequest, data: PasswordChangeSchema):
        """Change the current user's password"""
        success = self.user_service.change_password(
            user_id=request.user.id,
            old_password=data.old_password,
            new_password=data.new_password
        )
        if success:
            return 200, {"message": "Password changed successfully"}
        return 400, {"message": "Invalid old password"}

    @route.post("/auth/google", auth=None, response={200: GoogleAuthResponseSchema, 400: MessageResponse})
    def google_auth(self, request, data: GoogleAuthSchema):
        """Authenticate with Google"""
        try:
            logger.info(f"Google auth attempt with token: {data.credential[:10]}..., role: {data.role}, role type: {type(data.role)}")
            result = self.user_service.authenticate_google(
                credential=data.credential,
                role=data.role
            )

            # If user_exists is False, return the result directly
            if result.get('user_exists') is False:
                logger.info(f"Google auth: new user detected, email: {result.get('email')}")
                return 200, result

            # Otherwise, log the success and return the result
            logger.info(f"Google auth successful for user: {result['user']['username']}")
            return 200, result
        except ValueError as e:
            logger.warning(f"Google auth failed: {str(e)}")
            return 400, {"message": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error during Google auth: {str(e)}")
            return 400, {"message": "Authentication failed"}

    @route.get("/auth/twitter/init", auth=None, response={200: TwitterInitResponseSchema, 400: MessageResponse})
    def twitter_auth_init(self, request):
        """Initialize Twitter authentication"""
        try:
            logger.info("Twitter auth initialization attempt")
            result = self.user_service.initialize_twitter_auth()
            logger.info(f"Twitter auth initialization successful: {result['oauth_token'][:10]}...")
            return 200, result
        except ValueError as e:
            logger.warning(f"Twitter auth initialization failed: {str(e)}")
            return 400, {"message": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error during Twitter auth initialization: {str(e)}")
            return 400, {"message": "Failed to initialize Twitter authentication"}

    @route.post("/auth/twitter/callback", auth=None, response={200: TwitterAuthResponseSchema, 400: MessageResponse})
    def twitter_auth_callback(self, request, data: TwitterCallbackSchema):
        """Authenticate with Twitter"""
        try:
            logger.info(f"Twitter auth callback attempt with token: {data.oauth_token[:10]}..., role: {data.role}")
            result = self.user_service.authenticate_twitter(
                oauth_token=data.oauth_token,
                oauth_verifier=data.oauth_verifier,
                role=data.role
            )

            # If user_exists is False, return the result directly
            if result.get('user_exists') is False:
                logger.info(f"Twitter auth: new user detected")
                return 200, result

            # Otherwise, log the success and return the result
            logger.info(f"Twitter auth successful for user: {result['user']['username']}")
            return 200, result
        except ValueError as e:
            logger.warning(f"Twitter auth callback failed: {str(e)}")
            return 400, {"message": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error during Twitter auth callback: {str(e)}")
            return 400, {"message": "Authentication failed"}

    @route.get("/agents", response=List[UserProfileSchema])
    def get_agents(self, request: HttpRequest):
        """Get all agents/landlords"""
        users = self.user_service.get_users_by_role(User.Role.AGENT)
        return [self.user_service.get_user_profile(user.id) for user in users]

    @route.get("/", auth=None, response=List[UserProfileSchema])
    def get_all_users(self, request: HttpRequest, role: Optional[str] = None,
                      is_active: Optional[str] = None, pending: Optional[str] = None,
                      query: Optional[str] = None):
        """Get all users (public for testing)"""
        # Start with all users
        queryset = User.objects.all()

        # Apply filters
        if role:
            queryset = queryset.filter(role=role)

        # Convert is_active string to boolean
        if is_active is not None:
            is_active_bool = is_active.lower() == 'true'
            queryset = queryset.filter(is_active=is_active_bool)

        # Handle pending status (agents waiting for approval)
        if pending and pending.lower() == 'true':
            queryset = queryset.filter(role=User.Role.AGENT, is_active=False)

        # Apply search query
        if query:
            queryset = queryset.filter(
                Q(username__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query)
            )

        return [self.user_service.get_user_profile(user.id) for user in queryset]