from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import date
import uuid
import logging
from django.utils import timezone

from users.models import User
from users.repositories import UserRepository
from .models import Booking

logger = logging.getLogger('house_rental')

class BookingStrategy(ABC):
    """
    Abstract base class for booking strategies.
    """
    @abstractmethod
    def prepare_tenant(self, **kwargs) -> User:
        """
        Prepare the tenant for the booking.
        Returns a User object to be used as the tenant.
        """
        pass


class LoggedInBookingStrategy(BookingStrategy):
    """
    Strategy for creating bookings for logged-in users.
    """
    def __init__(self, user: User):
        self.user = user

    def prepare_tenant(self, **kwargs) -> User:
        """
        For logged-in users, just validate the user is a tenant or admin and return them.
        """
        if self.user.role != User.Role.TENANT and self.user.role != User.Role.ADMIN:
            raise ValueError("Only tenants and admins can create bookings")
        return self.user


class GuestBookingStrategy(BookingStrategy):
    """
    Strategy for creating bookings for non-logged-in users (guests).
    """
    def __init__(self, user_repository: UserRepository = None):
        self.user_repository = user_repository or UserRepository()

    def prepare_tenant(self, **kwargs) -> User:
        """
        For non-logged-in users, create a new inactive user account.
        Required kwargs: full_name, email, phone_number
        """
        full_name = kwargs.get('full_name')
        email = kwargs.get('email')
        phone_number = kwargs.get('phone_number')
        birthday = kwargs.get('birthday')
        
        if not full_name or not email or not phone_number:
            raise ValueError("Full name, email, and phone number are required for guest bookings")
        
        # Check if a user with this email already exists
        existing_user = self.user_repository.get_user_by_email(email)
        if existing_user:
            # If the user exists but is inactive, we can reuse it
            if not existing_user.is_active:
                return existing_user
            # If the user is active, they should log in instead
            raise ValueError("A user with this email already exists. Please log in to make a booking.")
        
        # Split full name into first and last name
        name_parts = full_name.split(' ', 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        # Generate a unique username based on email
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        
        # Make sure username is unique
        while self.user_repository.get_user_by_username(username):
            username = f"{base_username}{counter}"
            counter += 1
        
        # Generate a random password for the user account
        random_password = str(uuid.uuid4())
        
        # Create a new user with tenant role but inactive
        user = self.user_repository.create_user(
            username=username,
            email=email,
            password=random_password,  # Random password, user can't login with this
            role=User.Role.TENANT,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            birthday=birthday,
            is_active=False  # Set as inactive
        )
        
        logger.info(f"Created new inactive user account for guest booking: {user.id} ({email})")
        return user


class BookingStrategyFactory:
    """
    Factory class to create the appropriate booking strategy.
    """
    @staticmethod
    def create_strategy(request_user: Optional[User] = None, **user_data) -> BookingStrategy:
        """
        Create and return the appropriate booking strategy based on whether a user is logged in.
        """
        if request_user and request_user.is_authenticated:
            return LoggedInBookingStrategy(request_user)
        else:
            return GuestBookingStrategy(UserRepository()) 