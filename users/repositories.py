from typing import Optional, List, Tuple
from django.db.models import Q, Count
from django.core.paginator import Paginator
from .models import User

class UserRepository:
    """
    Repository for User model operations.
    """

    @staticmethod
    def create_user(username: str, email: str, password: str, role: str = User.Role.TENANT, **kwargs) -> User:
        """
        Create a new user.
        """
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            role=role,
            **kwargs
        )
        return user

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """
        Get a user by ID.
        """
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_user_by_username(username: str) -> Optional[User]:
        """
        Get a user by username.
        """
        try:
            return User.objects.get(username=username)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """
        Get a user by email.
        """
        try:
            return User.objects.get(email=email)
        except User.DoesNotExist:
            return None

    @staticmethod
    def get_users_by_role(role: str) -> List[User]:
        """
        Get users by role.
        """
        return User.objects.filter(role=role)

    @staticmethod
    def search_users(query: str) -> List[User]:
        """
        Search users by username, first name, last name, or email.
        """
        return User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        )

    @staticmethod
    def update_user(user: User, **kwargs) -> User:
        """
        Update a user.
        """
        for key, value in kwargs.items():
            setattr(user, key, value)

        # Handle password separately
        if 'password' in kwargs:
            user.set_password(kwargs['password'])

        user.save()
        return user

    @staticmethod
    def delete_user(user_id: int) -> bool:
        """
        Delete a user by ID.
        """
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return True
        except User.DoesNotExist:
            return False

    @staticmethod
    def get_all_users(page: int = 1, page_size: int = 10, role: Optional[str] = None,
                      is_active: Optional[bool] = None, search_query: Optional[str] = None) -> Tuple[List[User], int, int]:
        """
        Get all users with pagination and filtering.
        Returns a tuple of (users, total_count, total_pages)
        """
        # Start with all users
        queryset = User.objects.all()

        # Apply filters
        if role:
            queryset = queryset.filter(role=role)

        if is_active is not None:
            queryset = queryset.filter(is_active=is_active)

        if search_query:
            queryset = queryset.filter(
                Q(username__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query)
            )

        # Annotate with property and booking counts
        queryset = queryset.annotate(
            properties_count=Count('properties', distinct=True),
            bookings_count=Count('bookings', distinct=True)
        )

        # Order by username
        queryset = queryset.order_by('username')

        # Paginate
        paginator = Paginator(queryset, page_size)
        total_pages = paginator.num_pages
        total_count = paginator.count

        # Get page
        try:
            users = paginator.page(page)
        except:
            # If page is out of range, return last page
            users = paginator.page(total_pages if total_pages > 0 else 1)

        return list(users), total_count, total_pages