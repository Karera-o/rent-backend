from typing import Optional, List
from django.db.models import Q
from .models import ContactMessage


class ContactRepository:
    """
    Repository for ContactMessage model operations.
    """
    
    @staticmethod
    def create_contact_message(**kwargs) -> ContactMessage:
        """
        Create a new contact message.
        """
        contact_message = ContactMessage.objects.create(**kwargs)
        return contact_message
    
    @staticmethod
    def get_contact_message_by_id(message_id: int) -> Optional[ContactMessage]:
        """
        Get a contact message by ID.
        """
        try:
            return ContactMessage.objects.get(id=message_id)
        except ContactMessage.DoesNotExist:
            return None
    
    @staticmethod
    def get_all_contact_messages(page: int = 1, page_size: int = 10) -> List[ContactMessage]:
        """
        Get all contact messages with pagination.
        """
        offset = (page - 1) * page_size
        return ContactMessage.objects.all()[offset:offset + page_size]
    
    @staticmethod
    def count_contact_messages() -> int:
        """
        Count all contact messages.
        """
        return ContactMessage.objects.count()
    
    @staticmethod
    def mark_as_read(message_id: int) -> bool:
        """
        Mark a contact message as read.
        """
        try:
            message = ContactMessage.objects.get(id=message_id)
            message.is_read = True
            message.save()
            return True
        except ContactMessage.DoesNotExist:
            return False
    
    @staticmethod
    def delete_contact_message(message_id: int) -> bool:
        """
        Delete a contact message.
        """
        try:
            message = ContactMessage.objects.get(id=message_id)
            message.delete()
            return True
        except ContactMessage.DoesNotExist:
            return False
