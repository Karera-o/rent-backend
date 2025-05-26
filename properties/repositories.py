from typing import Optional, List
from django.db.models import Q
from .models import Property, PropertyImage, PropertyDocument, DocumentFeedback
from users.models import User
import logging

class PropertyRepository:
    """
    Repository for Property model operations.
    """

    @staticmethod
    def create_property(owner: User, **kwargs) -> Property:
        """
        Create a new property.
        """
        property_obj = Property.objects.create(owner=owner, **kwargs)
        return property_obj

    @staticmethod
    def get_property_by_id(property_id: int) -> Optional[Property]:
        """
        Get a property by ID.
        """
        try:
            return Property.objects.get(id=property_id)
        except Property.DoesNotExist:
            return None

    @staticmethod
    def get_properties_by_owner(owner: User) -> List[Property]:
        """
        Get properties by owner with prefetched images.
        """
        properties = Property.objects.filter(owner=owner).prefetch_related('images')

        # Attach prefetched images to each property for easy access
        for prop in properties:
            prop.prefetched_images = list(prop.images.all())

        return properties

    @staticmethod
    def get_properties_by_status(status: str) -> List[Property]:
        """
        Get properties by status with prefetched images.
        """
        properties = Property.objects.filter(status=status).prefetch_related('images')

        # Attach prefetched images to each property for easy access
        for prop in properties:
            prop.prefetched_images = list(prop.images.all())

        return properties

    @staticmethod
    def get_available_properties() -> List[Property]:
        """
        Get all available properties (approved and not rented) with prefetched images.
        """
        properties = Property.objects.filter(status=Property.PropertyStatus.APPROVED).prefetch_related('images')

        # Attach prefetched images to each property for easy access
        for prop in properties:
            prop.prefetched_images = list(prop.images.all())

        return properties

    @staticmethod
    def search_properties(query: str = None, city: str = None, property_type: str = None,
                          min_price: float = None, max_price: float = None, price_range: str = None,
                          bedrooms: int = None, bathrooms: float = None,
                          status: str = None, include_all_statuses: bool = False,
                          owner: User = None,
                          page: int = 1, page_size: int = 10) -> List[Property]:
        """
        Search properties with various filters and pagination.
        """
        # Start with an empty filter
        filters = Q()
        
        # Debug logs
        logger = logging.getLogger('house_rental')
        logger.info(f"Search params - city: {city}, property_type: {property_type}")

        # Apply status filter
        if not include_all_statuses:
            # Default to approved properties only
            if status:
                filters &= Q(status=status)
            else:
                filters &= Q(status=Property.PropertyStatus.APPROVED)
        elif status:
            # If include_all_statuses is True but a specific status is requested
            filters &= Q(status=status)

        if query:
            filters &= (
                Q(title__icontains=query) |
                Q(address__icontains=query) |
                Q(city__icontains=query) |
                Q(state__icontains=query)
            )

        if city:
            filters &= Q(city__icontains=city)
            logger.info(f"Added city filter: {city}")

        if property_type:
            # Handle property type filtering - allow case-insensitive matching
            logger.info(f"Adding property_type filter: {property_type}")
            filters &= Q(property_type__iexact=property_type)
            
        # Log the final filter
        logger.info(f"Final filters: {filters}")

        # Handle price filtering
        if price_range:
            # Parse price range in format "min-max" (e.g., "0-100", "100-200", "1000-any")
            price_parts = price_range.split('-')
            if len(price_parts) == 2:
                min_val, max_val = price_parts

                # Set min price if it's a number
                if min_val.isdigit():
                    min_price_val = float(min_val)
                    filters &= Q(price_per_night__gte=min_price_val)

                # Set max price if it's a number and not "any"
                if max_val.isdigit():
                    max_price_val = float(max_val)
                    filters &= Q(price_per_night__lte=max_price_val)
        else:
            # Use traditional min_price and max_price if price_range is not provided
            if min_price is not None:
                filters &= Q(price_per_night__gte=min_price)

            if max_price is not None:
                filters &= Q(price_per_night__lte=max_price)

        # Handle bedrooms filtering (supports "X+" format from frontend)
        if bedrooms is not None:
            filters &= Q(bedrooms__gte=bedrooms)

        if bathrooms is not None:
            filters &= Q(bathrooms__gte=bathrooms)

        # Filter by owner if provided
        if owner is not None:
            filters &= Q(owner=owner)

        # Calculate pagination offsets
        offset = (page - 1) * page_size
        limit = page_size

        # Get properties with prefetched images and apply pagination
        properties = Property.objects.filter(filters).prefetch_related('images')[offset:offset+limit]

        # Attach prefetched images to each property for easy access
        for prop in properties:
            prop.prefetched_images = list(prop.images.all())

        return properties

    @staticmethod
    def count_properties(query: str = None, city: str = None, property_type: str = None,
                         min_price: float = None, max_price: float = None, price_range: str = None,
                         bedrooms: int = None, bathrooms: float = None,
                         status: str = None, include_all_statuses: bool = False,
                         owner: User = None) -> int:
        """
        Count properties matching the search criteria.
        """
        # Start with an empty filter
        filters = Q()

        # Apply status filter
        if not include_all_statuses:
            # Default to approved properties only
            if status:
                filters &= Q(status=status)
            else:
                filters &= Q(status=Property.PropertyStatus.APPROVED)
        elif status:
            # If include_all_statuses is True but a specific status is requested
            filters &= Q(status=status)

        if query:
            filters &= (
                Q(title__icontains=query) |
                Q(address__icontains=query) |
                Q(city__icontains=query) |
                Q(state__icontains=query)
            )

        if city:
            filters &= Q(city__icontains=city)

        if property_type:
            # Handle property type filtering - allow case-insensitive matching
            filters &= Q(property_type__iexact=property_type)

        # Handle price filtering
        if price_range:
            # Parse price range in format "min-max" (e.g., "0-100", "100-200", "1000-any")
            price_parts = price_range.split('-')
            if len(price_parts) == 2:
                min_val, max_val = price_parts

                # Set min price if it's a number
                if min_val.isdigit():
                    min_price_val = float(min_val)
                    filters &= Q(price_per_night__gte=min_price_val)

                # Set max price if it's a number and not "any"
                if max_val.isdigit():
                    max_price_val = float(max_val)
                    filters &= Q(price_per_night__lte=max_price_val)
        else:
            # Use traditional min_price and max_price if price_range is not provided
            if min_price is not None:
                filters &= Q(price_per_night__gte=min_price)

            if max_price is not None:
                filters &= Q(price_per_night__lte=max_price)

        if bedrooms is not None:
            filters &= Q(bedrooms__gte=bedrooms)

        if bathrooms is not None:
            filters &= Q(bathrooms__gte=bathrooms)

        # Filter by owner if provided
        if owner is not None:
            filters &= Q(owner=owner)

        return Property.objects.filter(filters).count()

    @staticmethod
    def update_property(property_obj: Property, **kwargs) -> Property:
        """
        Update a property.
        """
        for key, value in kwargs.items():
            setattr(property_obj, key, value)

        property_obj.save()
        return property_obj

    @staticmethod
    def delete_property(property_obj: Property) -> bool:
        """
        Delete a property.
        """
        property_obj.delete()
        return True

    @staticmethod
    def add_property_image(property_obj: Property, image, caption: str = None, is_primary: bool = False) -> PropertyImage:
        """
        Add an image to a property.
        """
        # If this is the primary image, set all other images to non-primary
        if is_primary:
            PropertyImage.objects.filter(property=property_obj, is_primary=True).update(is_primary=False)

        return PropertyImage.objects.create(
            property=property_obj,
            image=image,
            caption=caption,
            is_primary=is_primary
        )

    @staticmethod
    def get_property_images(property_obj: Property) -> List[PropertyImage]:
        """
        Get all images for a property.
        """
        return PropertyImage.objects.filter(property=property_obj)

    @staticmethod
    def add_property_document(property_obj: Property, document, document_type: str, description: str = None) -> PropertyDocument:
        """
        Add a document to a property.
        """
        return PropertyDocument.objects.create(
            property=property_obj,
            document=document,
            document_type=document_type,
            description=description,
            status=PropertyDocument.DocumentStatus.PENDING
        )

    @staticmethod
    def get_property_documents(property_obj: Property) -> List[PropertyDocument]:
        """
        Get all documents for a property.
        """
        return PropertyDocument.objects.filter(property=property_obj)

    @staticmethod
    def get_document_by_id(document_id: int) -> Optional[PropertyDocument]:
        """
        Get a document by ID.
        """
        try:
            return PropertyDocument.objects.get(id=document_id)
        except PropertyDocument.DoesNotExist:
            return None

    @staticmethod
    def update_document_status(document_obj: PropertyDocument, status: str, rejection_reason: str = None, feedback: str = None) -> PropertyDocument:
        """
        Update the status of a document.
        """
        document_obj.status = status
        if rejection_reason:
            document_obj.rejection_reason = rejection_reason
        if feedback:
            document_obj.feedback = feedback
        document_obj.save()
        return document_obj

    @staticmethod
    def add_document_feedback(document_obj: PropertyDocument, feedback: str) -> PropertyDocument:
        """
        Add feedback to a document without changing its status.
        """
        document_obj.feedback = feedback
        document_obj.feedback_read = False  # Reset feedback_read flag when new feedback is added
        document_obj.save()
        return document_obj

    @staticmethod
    def mark_document_feedback_read(document_obj: PropertyDocument) -> PropertyDocument:
        """
        Mark document feedback as read.
        """
        document_obj.feedback_read = True
        document_obj.save()
        return document_obj

    @staticmethod
    def get_pending_documents() -> List[PropertyDocument]:
        """
        Get all pending documents with related property and owner information.
        """
        return PropertyDocument.objects.filter(
            status=PropertyDocument.DocumentStatus.PENDING
        ).select_related('property', 'property__owner')

    @staticmethod
    def update_property_document_verification_status(property_obj: Property, status: str) -> Property:
        """
        Update the document verification status of a property.
        """
        property_obj.document_verification_status = status
        property_obj.save()
        return property_obj

    # Document Feedback methods
    @staticmethod
    def add_document_feedback_message(document_obj: PropertyDocument, user: User, message: str, sender_type: str) -> DocumentFeedback:
        """
        Add a feedback message to a document's feedback thread.
        """
        return DocumentFeedback.objects.create(
            document=document_obj,
            user=user,
            message=message,
            sender_type=sender_type,
            is_read=False
        )

    @staticmethod
    def get_document_feedback_thread(document_obj: PropertyDocument) -> List[DocumentFeedback]:
        """
        Get all feedback messages for a document.
        """
        return DocumentFeedback.objects.filter(document=document_obj).select_related('user').order_by('created_at')

    @staticmethod
    def mark_feedback_thread_as_read(document_obj: PropertyDocument, user_type: str) -> bool:
        """
        Mark all feedback messages as read for a specific recipient type.
        If user_type is 'admin', mark all landlord messages as read.
        If user_type is 'landlord', mark all admin messages as read.
        """
        recipient_type = 'admin' if user_type == 'landlord' else 'landlord'
        DocumentFeedback.objects.filter(
            document=document_obj,
            sender_type=recipient_type,
            is_read=False
        ).update(is_read=True)
        return True

    @staticmethod
    def get_unread_feedback_count(document_obj: PropertyDocument, user_type: str) -> int:
        """
        Get count of unread feedback messages for a specific recipient type.
        """
        recipient_type = 'admin' if user_type == 'landlord' else 'landlord'
        return DocumentFeedback.objects.filter(
            document=document_obj,
            sender_type=recipient_type,
            is_read=False
        ).count()