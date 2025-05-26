from typing import Optional, Dict, Any, List
import logging
from django.core.cache import cache
from django.conf import settings

from .repositories import PropertyRepository
from .models import Property, PropertyImage, PropertyDocument
from users.models import User

logger = logging.getLogger('house_rental')

# Cache timeout in seconds (10 minutes)
CACHE_TIMEOUT = 60 * 10

class PropertyService:
    """
    Service for property-related business logic.
    """

    def __init__(self, property_repository: PropertyRepository = None):
        self.property_repository = property_repository or PropertyRepository()

    def _invalidate_property_cache(self, property_id: int):
        """
        Invalidate cache for a property.
        """
        cache_key = f"property_details:{property_id}"
        cache.delete(cache_key)
        logger.debug(f"Cache invalidated for property: {property_id}")

    def create_property(self, owner: User, **property_data) -> Property:
        """
        Create a new property listing.
        """
        # Validate owner is an agent
        if owner.role != User.Role.AGENT and owner.role != User.Role.ADMIN:
            raise ValueError("Only agents and admins can create property listings")

        # Create the property
        return self.property_repository.create_property(owner=owner, **property_data)

    def get_property_details(self, property_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed property information with caching.
        """
        # Try to get from cache first
        cache_key = f"property_details:{property_id}"
        cached_data = cache.get(cache_key)

        if cached_data:
            logger.debug(f"Cache hit for property details: {property_id}")
            return cached_data

        logger.debug(f"Cache miss for property details: {property_id}")

        property_obj = self.property_repository.get_property_by_id(property_id)
        if not property_obj:
            return None

        # Get property images
        images = self.property_repository.get_property_images(property_obj)

        # Format property data
        property_data = {
            'id': property_obj.id,
            'title': property_obj.title,
            'description': property_obj.description,
            'property_type': property_obj.property_type,
            'status': property_obj.status,
            'document_verification_status': property_obj.document_verification_status or 'not_submitted',
            'owner': {
                'id': property_obj.owner.id,
                'username': property_obj.owner.username,
                'first_name': property_obj.owner.first_name,
                'last_name': property_obj.owner.last_name,
            },
            'address': property_obj.address,
            'city': property_obj.city,
            'state': property_obj.state,
            'country': property_obj.country,
            'zip_code': property_obj.zip_code,
            'latitude': property_obj.latitude,
            'longitude': property_obj.longitude,
            'bedrooms': property_obj.bedrooms,
            'bathrooms': property_obj.bathrooms,
            'area': property_obj.area,
            'price_per_night': property_obj.price_per_night,
            'amenities': {
                'wifi': property_obj.has_wifi,
                'kitchen': property_obj.has_kitchen,
                'air_conditioning': property_obj.has_air_conditioning,
                'heating': property_obj.has_heating,
                'tv': property_obj.has_tv,
                'parking': property_obj.has_parking,
                'pool': property_obj.has_pool,
                'gym': property_obj.has_gym,
            },
            'additional_services': {
                'maid_service': property_obj.has_maid_service,
                'car_rental': property_obj.has_car_rental,
            },
            'images': [
                {
                    'id': img.id,
                    'url': img.image.url,
                    'caption': img.caption,
                    'is_primary': img.is_primary,
                }
                for img in images
            ],
            'created_at': property_obj.created_at,
            'updated_at': property_obj.updated_at,
        }

        # Cache the result
        cache.set(cache_key, property_data, CACHE_TIMEOUT)

        return property_data

    def get_owner_properties(self, owner: User, include_all_images: bool = False) -> List[Dict[str, Any]]:
        """
        Get all properties for an owner.

        Args:
            owner: The owner (landlord/agent) whose properties to retrieve
            include_all_images: Whether to include all images or just the primary image
                               Default is False to improve performance for landlord dashboard
        """
        properties = self.property_repository.get_properties_by_owner(owner)
        return [self._get_property_summary(prop, include_all_images=include_all_images) for prop in properties]

    def search_properties(self, page: int = 1, page_size: int = 10, include_all_images: bool = True, owner: User = None, **search_params) -> List[Dict[str, Any]]:
        """
        Search for properties with various filters and pagination.

        Args:
            page: Page number for pagination
            page_size: Number of items per page
            include_all_images: Whether to include all images or just the primary image
                               Default is True for public property listings
            owner: The owner to filter by (if any)
            **search_params: Additional search parameters including:
                - query: Text search across title, description, address, city
                - city: Filter by city
                - property_type: Filter by property type
                - price_range: Filter by price range in format "min-max" (e.g., "0-100", "100-200", "1000-any")
                - min_price/max_price: Alternative price filtering
                - bedrooms: Filter by minimum number of bedrooms (X+)
                - bathrooms: Filter by minimum number of bathrooms
        """
        # Add pagination parameters
        properties = self.property_repository.search_properties(
            page=page,
            page_size=page_size,
            owner=owner,
            **search_params
        )
        return [self._get_property_summary(prop, include_all_images=include_all_images) for prop in properties]

    def count_properties(self, owner: User = None, **search_params) -> int:
        """
        Count properties matching the search criteria.

        Args:
            owner: The owner to filter by (if any)
            **search_params: Additional search parameters including:
                - query: Text search across title, description, address, city
                - city: Filter by city
                - property_type: Filter by property type
                - price_range: Filter by price range in format "min-max" (e.g., "0-100", "100-200", "1000-any")
                - min_price/max_price: Alternative price filtering
                - bedrooms: Filter by minimum number of bedrooms (X+)
                - bathrooms: Filter by minimum number of bathrooms
        """
        return self.property_repository.count_properties(owner=owner, **search_params)

    def update_property(self, property_id: int, owner: User, **property_data) -> Optional[Property]:
        """
        Update a property and invalidate cache.
        """
        property_obj = self.property_repository.get_property_by_id(property_id)
        if not property_obj:
            return None

        # Check if user is the owner or an admin
        if property_obj.owner.id != owner.id and owner.role != User.Role.ADMIN:
            raise ValueError("You don't have permission to update this property")

        # Don't allow changing the owner through this method
        if 'owner' in property_data:
            del property_data['owner']

        # Update the property
        updated_property = self.property_repository.update_property(property_obj, **property_data)

        # Invalidate cache
        cache_key = f"property_details:{property_id}"
        cache.delete(cache_key)
        logger.debug(f"Cache invalidated for property: {property_id}")

        return updated_property

    def delete_property(self, property_id: int, user: User) -> bool:
        """
        Delete a property and invalidate cache.
        """
        property_obj = self.property_repository.get_property_by_id(property_id)
        if not property_obj:
            return False

        # Check if user is the owner or an admin
        if property_obj.owner.id != user.id and user.role != User.Role.ADMIN:
            raise ValueError("You don't have permission to delete this property")

        # Delete the property
        result = self.property_repository.delete_property(property_obj)

        # Invalidate cache
        cache_key = f"property_details:{property_id}"
        cache.delete(cache_key)
        logger.debug(f"Cache invalidated for deleted property: {property_id}")

        return result

    def update_property_status(self, property_id: int, status: str) -> bool:
        """
        Update property status and invalidate cache.
        """
        property_obj = self.property_repository.get_property_by_id(property_id)
        if not property_obj:
            return False

        # Update the status
        property_obj.status = status
        property_obj.save()

        # Invalidate cache
        cache_key = f"property_details:{property_id}"
        cache.delete(cache_key)
        logger.debug(f"Cache invalidated for updated property status: {property_id}")

        return True

    def add_property_image(self, property_id: int, user: User, image, caption: str = None, is_primary: bool = False) -> Optional[PropertyImage]:
        """
        Add an image to a property and invalidate cache.
        """
        property_obj = self.property_repository.get_property_by_id(property_id)
        if not property_obj:
            return None

        # Check if user is the owner or an admin
        if property_obj.owner.id != user.id and user.role != User.Role.ADMIN:
            raise ValueError("You don't have permission to add images to this property")

        # Add the image
        property_image = self.property_repository.add_property_image(
            property_obj=property_obj,
            image=image,
            caption=caption,
            is_primary=is_primary
        )

        # Invalidate cache
        cache_key = f"property_details:{property_id}"
        cache.delete(cache_key)
        logger.debug(f"Cache invalidated for property with new image: {property_id}")

        return property_image

    def _get_property_summary(self, property_obj: Property, include_all_images: bool = False) -> Dict[str, Any]:
        """
        Get a summary of property information.

        Args:
            property_obj: The property object to summarize
            include_all_images: Whether to include all images or just the primary image
                               Set to False for landlord property listings to improve performance
        """
        # Get primary image if available - this is now optimized to avoid N+1 queries
        # by using prefetch_related in the repository methods
        primary_image = None
        if hasattr(property_obj, 'prefetched_images'):
            # Use prefetched images if available
            images = property_obj.prefetched_images
            primary_images = [img for img in images if img.is_primary]
            primary_image = primary_images[0] if primary_images else (images[0] if images else None)
        else:
            # Fallback to database query if prefetched images not available
            primary_image = PropertyImage.objects.filter(property=property_obj, is_primary=True).first()
            if not primary_image:
                primary_image = PropertyImage.objects.filter(property=property_obj).first()

        # Get all images for the property only if requested
        images = []
        if include_all_images and hasattr(property_obj, 'prefetched_images'):
            images = [{
                'id': img.id,
                'url': img.image.url,
                'caption': img.caption,
                'is_primary': img.is_primary
            } for img in property_obj.prefetched_images]

        return {
            'id': property_obj.id,
            'title': property_obj.title,
            'property_type': property_obj.property_type,
            'status': property_obj.status,
            'document_verification_status': property_obj.document_verification_status or 'not_submitted',
            'owner': {
                'id': property_obj.owner.id,
                'username': property_obj.owner.username,
                'first_name': property_obj.owner.first_name,
                'last_name': property_obj.owner.last_name,
                'name': f"{property_obj.owner.first_name} {property_obj.owner.last_name}".strip() or property_obj.owner.username
            },
            'address': property_obj.address,
            'city': property_obj.city,
            'state': property_obj.state,
            'country': property_obj.country,
            'bedrooms': property_obj.bedrooms,
            'bathrooms': property_obj.bathrooms,
            'price_per_night': property_obj.price_per_night,
            'primary_image': primary_image.image.url if primary_image else None,
            'images': images,
            'created_at': property_obj.created_at,
        }

    def add_property_document(self, property_id: int, user: User, document, document_type: str, description: str = None) -> Optional[PropertyDocument]:
        """
        Add a document to a property and update cache.
        """
        property_obj = self.property_repository.get_property_by_id(property_id)
        if not property_obj:
            return None

        # Check if user is the owner or an admin
        if property_obj.owner.id != user.id and user.role != User.Role.ADMIN:
            raise ValueError("You don't have permission to add documents to this property")

        # Add the document
        document_obj = self.property_repository.add_property_document(
            property_obj=property_obj,
            document=document,
            document_type=document_type,
            description=description
        )

        # Update property document verification status if it was not submitted before
        if property_obj.document_verification_status == Property.DocumentVerificationStatus.NOT_SUBMITTED:
            self.property_repository.update_property_document_verification_status(
                property_obj=property_obj,
                status=Property.DocumentVerificationStatus.PENDING
            )

        # Invalidate cache
        self._invalidate_property_cache(property_id)

        return document_obj

    def get_property_documents(self, property_id: int, user: User) -> List[Dict[str, Any]]:
        """
        Get all documents for a property.
        """
        property_obj = self.property_repository.get_property_by_id(property_id)
        if not property_obj:
            return []

        # Check if user is the owner or an admin
        if property_obj.owner.id != user.id and user.role != User.Role.ADMIN:
            raise ValueError("You don't have permission to view documents for this property")

        documents = self.property_repository.get_property_documents(property_obj)

        result = []
        for doc in documents:
            # Get feedback thread if it exists
            feedback_thread = self.property_repository.get_document_feedback_thread(doc)
            feedback_thread_data = []

            for feedback in feedback_thread:
                feedback_thread_data.append({
                    'id': feedback.id,
                    'document_id': doc.id,
                    'sender_type': feedback.sender_type,
                    'user': {
                        'id': feedback.user.id,
                        'username': feedback.user.username,
                        'email': feedback.user.email,
                        'first_name': feedback.user.first_name,
                        'last_name': feedback.user.last_name,
                        'name': f"{feedback.user.first_name} {feedback.user.last_name}".strip() or feedback.user.username
                    },
                    'message': feedback.message,
                    'is_read': feedback.is_read,
                    'created_at': feedback.created_at,
                    'updated_at': feedback.updated_at
                })

            result.append({
                'id': doc.id,
                'property_id': property_obj.id,
                'document_type': doc.document_type,
                'document': doc.document.url,
                'description': doc.description,
                'status': doc.status,
                'rejection_reason': doc.rejection_reason,
                'feedback': doc.feedback,
                'feedback_read': doc.feedback_read,
                'feedback_thread': feedback_thread_data,
                'created_at': doc.created_at,
                'updated_at': doc.updated_at
            })

        return result

    def get_document_details(self, document_id: int, user: User) -> Optional[Dict[str, Any]]:
        """
        Get detailed document information.
        """
        document_obj = self.property_repository.get_document_by_id(document_id)
        if not document_obj:
            return None

        property_obj = document_obj.property

        # Check if user is the owner or an admin
        if property_obj.owner.id != user.id and user.role != User.Role.ADMIN:
            raise ValueError("You don't have permission to view this document")

        # Get feedback thread if it exists
        feedback_thread = self.property_repository.get_document_feedback_thread(document_obj)
        feedback_thread_data = []

        for feedback in feedback_thread:
            feedback_thread_data.append({
                'id': feedback.id,
                'document_id': document_obj.id,
                'sender_type': feedback.sender_type,
                'user': {
                    'id': feedback.user.id,
                    'username': feedback.user.username,
                    'email': feedback.user.email,
                    'first_name': feedback.user.first_name,
                    'last_name': feedback.user.last_name,
                    'name': f"{feedback.user.first_name} {feedback.user.last_name}".strip() or feedback.user.username
                },
                'message': feedback.message,
                'is_read': feedback.is_read,
                'created_at': feedback.created_at,
                'updated_at': feedback.updated_at
            })

        return {
            'id': document_obj.id,
            'property_id': property_obj.id,
            'document_type': document_obj.document_type,
            'document': document_obj.document.url,
            'description': document_obj.description,
            'status': document_obj.status,
            'rejection_reason': document_obj.rejection_reason,
            'feedback': document_obj.feedback,
            'feedback_read': document_obj.feedback_read,
            'feedback_thread': feedback_thread_data,
            'created_at': document_obj.created_at,
            'updated_at': document_obj.updated_at
        }

    def update_document_status(self, document_id: int, user: User, status: str, rejection_reason: str = None, feedback: str = None) -> Optional[PropertyDocument]:
        """
        Update the status of a document.
        """
        # Check if user is an admin
        if user.role != User.Role.ADMIN:
            raise ValueError("Only admins can update document status")

        document_obj = self.property_repository.get_document_by_id(document_id)
        if not document_obj:
            return None

        property_obj = document_obj.property

        # Update document status
        updated_document = self.property_repository.update_document_status(
            document_obj=document_obj,
            status=status,
            rejection_reason=rejection_reason,
            feedback=feedback
        )

        # Update property document verification status based on document status
        if status == PropertyDocument.DocumentStatus.APPROVED:
            self.property_repository.update_property_document_verification_status(
                property_obj=property_obj,
                status=Property.DocumentVerificationStatus.VERIFIED
            )
        elif status == PropertyDocument.DocumentStatus.REJECTED:
            self.property_repository.update_property_document_verification_status(
                property_obj=property_obj,
                status=Property.DocumentVerificationStatus.REJECTED
            )

        # Invalidate cache
        self._invalidate_property_cache(property_obj.id)

        return updated_document

    def add_document_feedback(self, document_id: int, user: User, feedback: str) -> Optional[PropertyDocument]:
        """
        Add feedback to a document without changing its status.
        """
        # Check if user is an admin
        if user.role != User.Role.ADMIN:
            raise ValueError("Only admins can add document feedback")

        document_obj = self.property_repository.get_document_by_id(document_id)
        if not document_obj:
            return None

        property_obj = document_obj.property

        # Add feedback to document and reset feedback_read flag
        updated_document = self.property_repository.add_document_feedback(
            document_obj=document_obj,
            feedback=feedback
        )

        # Invalidate cache
        self._invalidate_property_cache(property_obj.id)

        return updated_document

    def mark_document_feedback_read(self, document_id: int, user: User) -> bool:
        """
        Mark document feedback as read.
        """
        document_obj = self.property_repository.get_document_by_id(document_id)
        if not document_obj:
            return False

        property_obj = document_obj.property

        # Check if user is the owner of the property
        if property_obj.owner.id != user.id and user.role != User.Role.ADMIN:
            raise ValueError("You don't have permission to mark this feedback as read")

        # Mark feedback as read
        updated_document = self.property_repository.mark_document_feedback_read(document_obj)

        # Also mark all admin messages in the feedback thread as read if the user is a landlord
        if property_obj.owner.id == user.id:
            self.property_repository.mark_feedback_thread_as_read(document_obj, 'landlord')
        elif user.role == User.Role.ADMIN:
            self.property_repository.mark_feedback_thread_as_read(document_obj, 'admin')

        # Invalidate cache
        self._invalidate_property_cache(property_obj.id)

        return True

    def add_document_feedback_message(self, document_id: int, user: User, message: str) -> Optional[Dict[str, Any]]:
        """
        Add a feedback message to a document's feedback thread.
        """
        document_obj = self.property_repository.get_document_by_id(document_id)
        if not document_obj:
            return None

        property_obj = document_obj.property

        # Determine sender type based on user role
        if user.role == User.Role.ADMIN:
            sender_type = 'admin'
        elif property_obj.owner.id == user.id:
            sender_type = 'landlord'
        else:
            raise ValueError("You don't have permission to add feedback to this document")

        # Add feedback message
        feedback = self.property_repository.add_document_feedback_message(
            document_obj=document_obj,
            user=user,
            message=message,
            sender_type=sender_type
        )

        # Invalidate cache
        self._invalidate_property_cache(property_obj.id)

        return {
            'id': feedback.id,
            'document_id': document_obj.id,
            'sender_type': feedback.sender_type,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'name': f"{user.first_name} {user.last_name}".strip() or user.username
            },
            'message': feedback.message,
            'is_read': feedback.is_read,
            'created_at': feedback.created_at,
            'updated_at': feedback.updated_at
        }

    def get_pending_documents(self, user: User) -> List[Dict[str, Any]]:
        """
        Get all pending documents (admin only).
        """
        # Check if user is an admin
        if user.role != User.Role.ADMIN:
            raise ValueError("Only admins can view pending documents")

        documents = self.property_repository.get_pending_documents()

        result = []
        for doc in documents:
            try:
                # Get property information
                property_data = {
                    'id': doc.property.id,
                    'title': doc.property.title,
                    'property_type': doc.property.property_type,
                    'city': doc.property.city,
                    'state': doc.property.state,
                    'country': doc.property.country,
                }

                # Get owner information
                owner_data = {
                    'id': doc.property.owner.id,
                    'username': doc.property.owner.username,
                    'email': doc.property.owner.email,
                    'first_name': doc.property.owner.first_name,
                    'last_name': doc.property.owner.last_name,
                    'name': f"{doc.property.owner.first_name} {doc.property.owner.last_name}".strip() or doc.property.owner.username
                }

                # Get feedback thread if it exists
                feedback_thread = self.property_repository.get_document_feedback_thread(doc)
                feedback_thread_data = []

                for feedback in feedback_thread:
                    feedback_thread_data.append({
                        'id': feedback.id,
                        'document_id': doc.id,
                        'sender_type': feedback.sender_type,
                        'user': {
                            'id': feedback.user.id,
                            'username': feedback.user.username,
                            'email': feedback.user.email,
                            'first_name': feedback.user.first_name,
                            'last_name': feedback.user.last_name,
                            'name': f"{feedback.user.first_name} {feedback.user.last_name}".strip() or feedback.user.username
                        },
                        'message': feedback.message,
                        'is_read': feedback.is_read,
                        'created_at': feedback.created_at,
                        'updated_at': feedback.updated_at
                    })

                # Create document data
                document_data = {
                    'id': doc.id,
                    'property_id': doc.property.id,
                    'property_title': doc.property.title,
                    'property_type': doc.property.property_type,
                    'city': doc.property.city,
                    'state': doc.property.state,
                    'country': doc.property.country,
                    'owner_id': doc.property.owner.id,
                    'owner_name': owner_data['name'],
                    'owner_email': doc.property.owner.email,
                    'owner_username': doc.property.owner.username,
                    'owner': owner_data,
                    'property': property_data,
                    'document_type': doc.document_type,
                    'document': doc.document.url if doc.document else None,
                    'description': doc.description,
                    'status': doc.status,
                    'rejection_reason': doc.rejection_reason,
                    'feedback': doc.feedback,
                    'feedback_read': doc.feedback_read,
                    'feedback_thread': feedback_thread_data,
                    'created_at': doc.created_at,
                    'updated_at': doc.updated_at
                }

                result.append(document_data)
            except Exception as e:
                logger.error(f"Error processing document {doc.id}: {str(e)}")
                # Add a minimal document record even if there's an error
                result.append({
                    'id': doc.id,
                    'property_id': getattr(doc.property, 'id', None),
                    'document_type': doc.document_type,
                    'status': doc.status,
                    'created_at': doc.created_at
                })

        return result