from typing import List, Dict, Any, Optional
from django.core.mail import send_mail
from django.conf import settings
import logging

from .repositories import ContactRepository
from .models import ContactMessage

logger = logging.getLogger('house_rental')


class ContactService:
    """
    Service for contact-related business logic.
    """
    
    def __init__(self, contact_repository: ContactRepository = None):
        self.contact_repository = contact_repository or ContactRepository()
    
    def create_contact_message(self, **message_data) -> ContactMessage:
        """
        Create a new contact message and send notification email.
        """
        # Create the contact message
        contact_message = self.contact_repository.create_contact_message(**message_data)
        
        # Send notification email to admin (if email settings are configured)
        try:
            if hasattr(settings, 'DEFAULT_FROM_EMAIL') and hasattr(settings, 'ADMIN_EMAIL'):
                subject = f"New Contact Message: {contact_message.subject}"
                message = f"""
                New contact message received:
                
                From: {contact_message.first_name} {contact_message.last_name}
                Email: {contact_message.email}
                Phone: {contact_message.phone}
                Subject: {contact_message.subject}
                
                Message:
                {contact_message.message}
                
                ---
                This is an automated notification.
                """
                
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.ADMIN_EMAIL],
                    fail_silently=True,
                )
                logger.info(f"Notification email sent for contact message ID: {contact_message.id}")
        except Exception as e:
            # Log the error but don't fail the request
            logger.error(f"Failed to send notification email: {str(e)}")
        
        return contact_message
    
    def get_contact_message_details(self, message_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed contact message information.
        """
        message = self.contact_repository.get_contact_message_by_id(message_id)
        if not message:
            return None
        
        return self._get_contact_message_detail(message)
    
    def get_all_contact_messages(self, page: int = 1, page_size: int = 10) -> Dict[str, Any]:
        """
        Get all contact messages with pagination.
        """
        messages = self.contact_repository.get_all_contact_messages(page, page_size)
        total = self.contact_repository.count_contact_messages()
        
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
            "results": [self._get_contact_message_summary(message) for message in messages]
        }
    
    def mark_as_read(self, message_id: int) -> bool:
        """
        Mark a contact message as read.
        """
        return self.contact_repository.mark_as_read(message_id)
    
    def delete_contact_message(self, message_id: int) -> bool:
        """
        Delete a contact message.
        """
        return self.contact_repository.delete_contact_message(message_id)
    
    def _get_contact_message_detail(self, message: ContactMessage) -> Dict[str, Any]:
        """
        Convert a ContactMessage model instance to a detailed dictionary.
        """
        return {
            "id": message.id,
            "first_name": message.first_name,
            "last_name": message.last_name,
            "email": message.email,
            "phone": message.phone,
            "subject": message.subject,
            "message": message.message,
            "is_read": message.is_read,
            "created_at": message.created_at,
            "updated_at": message.updated_at
        }
    
    def _get_contact_message_summary(self, message: ContactMessage) -> Dict[str, Any]:
        """
        Convert a ContactMessage model instance to a summary dictionary.
        """
        return {
            "id": message.id,
            "first_name": message.first_name,
            "last_name": message.last_name,
            "email": message.email,
            "subject": message.subject,
            "is_read": message.is_read,
            "created_at": message.created_at
        }
