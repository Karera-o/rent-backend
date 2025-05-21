from typing import Optional, Dict, Any, List
import requests
import json
import tweepy
import secrets
from django.contrib.auth import authenticate
from django.conf import settings
from allauth.socialaccount.models import SocialApp, SocialAccount, SocialToken
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from .repositories import UserRepository
from .models import User

class UserService:
    """
    Service for user-related business logic.
    """

    def __init__(self, user_repository: UserRepository = None):
        self.user_repository = user_repository or UserRepository()

    def register_user(self, username: str, email: str, password: str, role: str = User.Role.TENANT, **kwargs) -> User:
        """
        Register a new user.
        """
        # Check if user with email already exists
        existing_user = self.user_repository.get_user_by_email(email)
        if existing_user:
            raise ValueError("User with this email already exists")

        # Check if user with username already exists
        existing_user = self.user_repository.get_user_by_username(username)
        if existing_user:
            raise ValueError("User with this username already exists")

        # Create the user
        return self.user_repository.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            **kwargs
        )

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user with username/email and password.
        """
        # Try to authenticate with username
        user = authenticate(username=username, password=password)

        # If authentication failed, try with email
        if not user:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass

        return user

    def authenticate_google(self, credential: str, role: Optional[str] = None) -> Dict[str, Any]:
        """
        Authenticate a user with Google OAuth using ID token.
        """
        # Verify the ID token with Google
        google_user_info = self._verify_google_id_token(credential)

        if not google_user_info:
            raise ValueError("Invalid Google token")

        # Get user info
        email = google_user_info.get('email')
        if not email:
            raise ValueError("Email not provided by Google")

        # Check if user exists with this email
        user = self.user_repository.get_user_by_email(email)

        # If user doesn't exist and no role is provided, return user_exists=False
        # This will trigger the frontend to show the role selection modal
        if not user and not role:
            return {
                'user_exists': False,
                'email': email,
                'first_name': google_user_info.get('given_name', ''),
                'last_name': google_user_info.get('family_name', ''),
                'google_id': google_user_info.get('id'),
                'picture': google_user_info.get('picture')
            }

        if not user:
            # Validate role
            print(f"Validating role: {role}, type: {type(role)}")
            print(f"Valid roles: {User.Role.TENANT}, {User.Role.AGENT}, types: {type(User.Role.TENANT)}, {type(User.Role.AGENT)}")

            # Convert role string to User.Role enum value if needed
            if role == 'tenant':
                role = User.Role.TENANT
            elif role == 'agent':
                role = User.Role.AGENT

            if role not in [User.Role.TENANT, User.Role.AGENT]:
                raise ValueError(f"Invalid role: {role}. Must be 'tenant' or 'agent'. Valid roles are: {User.Role.TENANT}, {User.Role.AGENT}")

            # Create a new user
            username = email.split('@')[0]  # Use part before @ as username
            base_username = username
            counter = 1

            # Make sure username is unique
            while self.user_repository.get_user_by_username(username):
                username = f"{base_username}{counter}"
                counter += 1

            # Create user with the selected role
            user = self.user_repository.create_user(
                username=username,
                email=email,
                password=None,  # No password for social auth users
                first_name=google_user_info.get('given_name', ''),
                last_name=google_user_info.get('family_name', ''),
                role=role,  # Use the selected role
                is_active=True
            )

            # Update Google ID
            user.google_id = google_user_info.get('id')
            user.save()
        elif not user.google_id:
            # Update existing user with Google ID
            user.google_id = google_user_info.get('id')
            user.save()
        elif role:
            # Convert role string to User.Role enum value if needed
            if role == 'tenant':
                role_value = User.Role.TENANT
            elif role == 'agent':
                role_value = User.Role.AGENT
            else:
                role_value = role

            # If the user exists but is trying to sign in with a different role,
            # return an error message
            if role_value != user.role:
                raise ValueError(f"You already have an account with the role '{user.role}'. Please sign in with that role.")

        # Generate JWT tokens
        from ninja_jwt.tokens import RefreshToken
        refresh = RefreshToken.for_user(user)

        return {
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'user': self.get_user_profile(user.id),
            'user_exists': True
        }

    def _verify_google_id_token(self, id_token: str) -> Dict[str, Any]:
        """
        Verify the Google ID token and extract user information.
        """
        try:
            # Verify the token with Google's tokeninfo endpoint
            response = requests.get(
                f'https://oauth2.googleapis.com/tokeninfo?id_token={id_token}'
            )

            if response.status_code != 200:
                return None

            token_info = response.json()

            # Check if the token is valid
            if 'error' in token_info:
                return None

            # Extract user information
            user_info = {
                'id': token_info.get('sub'),
                'email': token_info.get('email'),
                'given_name': token_info.get('given_name'),
                'family_name': token_info.get('family_name'),
                'picture': token_info.get('picture'),
                'verified_email': token_info.get('email_verified') == 'true'
            }

            return user_info
        except Exception as e:
            print(f"Error verifying Google ID token: {e}")
            return None

    def initialize_twitter_auth(self) -> Dict[str, str]:
        """
        Initialize Twitter OAuth authentication.
        """
        try:
            # Create OAuth1 handler
            auth = tweepy.OAuth1UserHandler(
                consumer_key=settings.TWITTER_CONSUMER_KEY,
                consumer_secret=settings.TWITTER_CONSUMER_SECRET,
                callback=settings.TWITTER_CALLBACK_URL
            )

            # Get request token
            auth_url = auth.get_authorization_url()
            request_token = auth.request_token

            return {
                'oauth_token': request_token['oauth_token'],
                'oauth_token_secret': request_token['oauth_token_secret'],
                'auth_url': auth_url
            }
        except Exception as e:
            print(f"Error initializing Twitter auth: {e}")
            raise ValueError(f"Failed to initialize Twitter authentication: {str(e)}")

    def authenticate_twitter(self, oauth_token: str, oauth_verifier: str, role: Optional[str] = None) -> Dict[str, Any]:
        """
        Authenticate a user with Twitter OAuth.
        """
        try:
            # Create OAuth1 handler
            auth = tweepy.OAuth1UserHandler(
                consumer_key=settings.TWITTER_CONSUMER_KEY,
                consumer_secret=settings.TWITTER_CONSUMER_SECRET
            )

            # Get access token
            auth.request_token = {
                'oauth_token': oauth_token,
                'oauth_token_secret': oauth_verifier
            }

            access_token, access_token_secret = auth.get_access_token(oauth_verifier)

            # Create API client
            auth.set_access_token(access_token, access_token_secret)
            api = tweepy.API(auth)

            # Get user info
            twitter_user = api.verify_credentials(include_email=True)

            # Check if user exists with this Twitter ID
            user = User.objects.filter(twitter_id=twitter_user.id_str).first()

            # If user doesn't exist and no role is provided, return user_exists=False
            if not user and not role:
                return {
                    'user_exists': False,
                    'email': getattr(twitter_user, 'email', None),
                    'first_name': twitter_user.name.split(' ')[0] if twitter_user.name else '',
                    'last_name': ' '.join(twitter_user.name.split(' ')[1:]) if twitter_user.name and ' ' in twitter_user.name else '',
                    'twitter_id': twitter_user.id_str,
                    'picture': twitter_user.profile_image_url_https
                }

            if not user:
                # Validate role
                if role == 'tenant':
                    role_value = User.Role.TENANT
                elif role == 'agent':
                    role_value = User.Role.AGENT
                else:
                    role_value = role

                if role_value not in [User.Role.TENANT, User.Role.AGENT]:
                    raise ValueError(f"Invalid role: {role}. Must be 'tenant' or 'agent'")

                # Create a new user
                email = getattr(twitter_user, 'email', None)
                if not email:
                    # Generate a temporary email if Twitter doesn't provide one
                    random_string = secrets.token_hex(8)
                    email = f"twitter_{twitter_user.id_str}_{random_string}@example.com"

                # Use Twitter username or screen name as username
                username = twitter_user.screen_name
                base_username = username
                counter = 1

                # Make sure username is unique
                while self.user_repository.get_user_by_username(username):
                    username = f"{base_username}{counter}"
                    counter += 1

                # Create user with the selected role
                user = self.user_repository.create_user(
                    username=username,
                    email=email,
                    password=None,  # No password for social auth users
                    first_name=twitter_user.name.split(' ')[0] if twitter_user.name else '',
                    last_name=' '.join(twitter_user.name.split(' ')[1:]) if twitter_user.name and ' ' in twitter_user.name else '',
                    role=role_value,
                    is_active=True
                )

                # Update Twitter ID
                user.twitter_id = twitter_user.id_str
                user.save()
            elif role:
                # Convert role string to User.Role enum value if needed
                if role == 'tenant':
                    role_value = User.Role.TENANT
                elif role == 'agent':
                    role_value = User.Role.AGENT
                else:
                    role_value = role

                # If the user exists but is trying to sign in with a different role,
                # return an error message
                if role_value != user.role:
                    raise ValueError(f"You already have an account with the role '{user.role}'. Please sign in with that role.")

            # Generate JWT tokens
            from ninja_jwt.tokens import RefreshToken
            refresh = RefreshToken.for_user(user)

            return {
                'access_token': str(refresh.access_token),
                'refresh_token': str(refresh),
                'user': self.get_user_profile(user.id),
                'user_exists': True
            }
        except Exception as e:
            print(f"Error authenticating with Twitter: {e}")
            raise ValueError(f"Failed to authenticate with Twitter: {str(e)}")

    def get_user_profile(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        Get user profile data.
        """
        user = self.user_repository.get_user_by_id(user_id)
        if not user:
            return None

        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
            'phone_number': user.phone_number,
            'bio': user.bio,
            'profile_picture': user.profile_picture.url if user.profile_picture else None,
            'date_joined': user.date_joined,
        }

    def update_user_profile(self, user_id: int, **kwargs) -> Optional[User]:
        """
        Update user profile.
        """
        user = self.user_repository.get_user_by_id(user_id)
        if not user:
            return None

        # Don't allow changing role through this method for security
        if 'role' in kwargs:
            del kwargs['role']

        return self.user_repository.update_user(user, **kwargs)

    def change_password(self, user_id: int, old_password: str, new_password: str) -> bool:
        """
        Change user password.
        """
        user = self.user_repository.get_user_by_id(user_id)
        if not user:
            return False

        # Verify old password
        if not user.check_password(old_password):
            return False

        # Update password
        user.set_password(new_password)
        user.save()
        return True

    def get_users_by_role(self, role: str) -> List[User]:
        """
        Get users by role.
        """
        return self.user_repository.get_users_by_role(role)

    def search_users(self, query: str) -> List[User]:
        """
        Search users.
        """
        return self.user_repository.search_users(query)

    def get_all_users(self, page: int = 1, page_size: int = 10, role: Optional[str] = None,
                      is_active: Optional[bool] = None, search_query: Optional[str] = None) -> tuple:
        """
        Get all users with pagination and filtering.
        """
        return self.user_repository.get_all_users(
            page=page,
            page_size=page_size,
            role=role,
            is_active=is_active,
            search_query=search_query
        )

    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user.
        """
        return self.user_repository.delete_user(user_id)

    def update_user_status(self, user_id: int, is_active: bool) -> bool:
        """
        Update user status (active/inactive).
        """
        user = self.user_repository.get_user_by_id(user_id)
        if not user:
            return False

        user.is_active = is_active
        user.save()
        return True