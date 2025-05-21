from django.db import models
from django.utils.translation import gettext_lazy as _
from users.models import User

class Property(models.Model):
    """
    Property model for house rental listings.
    """
    class PropertyType(models.TextChoices):
        APARTMENT = 'apartment', _('Apartment')
        HOUSE = 'house', _('House')
        DUPLEX = 'duplex', _('Duplex')
        TOWNHOUSE = 'townhouse', _('Townhouse')
        VILLA = 'villa', _('Villa')
        STUDIO = 'studio', _('Studio')
        OTHER = 'other', _('Other')

    class PropertyStatus(models.TextChoices):
        PENDING = 'pending', _('Pending Approval')
        APPROVED = 'approved', _('Approved')
        DENIED = 'denied', _('Denied')
        RENTED = 'rented', _('Rented')

    class DocumentVerificationStatus(models.TextChoices):
        NOT_SUBMITTED = 'not_submitted', _('Not Submitted')
        PENDING = 'pending', _('Pending Verification')
        VERIFIED = 'verified', _('Verified')
        REJECTED = 'rejected', _('Rejected')

    # Basic information
    title = models.CharField(max_length=255)
    description = models.TextField()
    property_type = models.CharField(
        max_length=20,
        choices=PropertyType.choices,
        default=PropertyType.APARTMENT
    )
    status = models.CharField(
        max_length=20,
        choices=PropertyStatus.choices,
        default=PropertyStatus.PENDING
    )
    document_verification_status = models.CharField(
        max_length=20,
        choices=DocumentVerificationStatus.choices,
        default=DocumentVerificationStatus.NOT_SUBMITTED,
        help_text=_('Status of document verification for this property'),
        null=True,  # Allow null for existing records during migration
        blank=True  # Allow blank in forms
    )

    # Owner/Agent
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='properties'
    )

    # Location
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100)
    zip_code = models.CharField(max_length=20)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Details
    bedrooms = models.PositiveIntegerField(default=1)
    bathrooms = models.DecimalField(max_digits=3, decimal_places=1, default=1.0)
    area = models.PositiveIntegerField(help_text=_('Area in square feet'))
    price_per_night = models.DecimalField(max_digits=10, decimal_places=2)

    # Amenities
    has_wifi = models.BooleanField(default=False)
    has_kitchen = models.BooleanField(default=False)
    has_air_conditioning = models.BooleanField(default=False)
    has_heating = models.BooleanField(default=False)
    has_tv = models.BooleanField(default=False)
    has_parking = models.BooleanField(default=False)
    has_pool = models.BooleanField(default=False)
    has_gym = models.BooleanField(default=False)

    # Additional services
    has_maid_service = models.BooleanField(default=False)
    has_car_rental = models.BooleanField(default=False)

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Property')
        verbose_name_plural = _('Properties')
        ordering = ['-created_at']

    def __str__(self):
        return self.title

class PropertyImage(models.Model):
    """
    Images for properties.
    """
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='images'
    )
    image = models.ImageField(upload_to='property_images/')
    caption = models.CharField(max_length=255, blank=True, null=True)
    is_primary = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Property Image')
        verbose_name_plural = _('Property Images')
        ordering = ['-is_primary', 'created_at']

    def __str__(self):
        return f"Image for {self.property.title}"


class PropertyDocument(models.Model):
    """
    Verification documents for properties to prove ownership or existence.
    """
    class DocumentType(models.TextChoices):
        DEED = 'deed', _('Property Deed')
        TAX = 'tax', _('Property Tax Document')
        UTILITY = 'utility', _('Utility Bill')
        INSURANCE = 'insurance', _('Property Insurance')
        ID = 'id', _('ID Card with Address')
        OTHER = 'other', _('Other Document')

    class DocumentStatus(models.TextChoices):
        PENDING = 'pending', _('Pending Review')
        APPROVED = 'approved', _('Approved')
        REJECTED = 'rejected', _('Rejected')

    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='documents'
    )
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
        default=DocumentType.OTHER
    )
    document = models.FileField(upload_to='property_documents/')
    description = models.TextField(blank=True, null=True, help_text=_('Additional information about the document'))
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING
    )
    rejection_reason = models.TextField(blank=True, null=True, help_text=_('Reason for rejection if applicable'))
    feedback = models.TextField(blank=True, null=True, help_text=_('Feedback for the document owner without changing status'))
    feedback_read = models.BooleanField(default=False, help_text=_('Whether the feedback has been read by the owner'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Property Document')
        verbose_name_plural = _('Property Documents')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_document_type_display()} for {self.property.title}"


class DocumentFeedback(models.Model):
    """
    Threaded feedback for property documents.
    """
    class SenderType(models.TextChoices):
        ADMIN = 'admin', _('Admin')
        LANDLORD = 'landlord', _('Landlord')

    document = models.ForeignKey(
        PropertyDocument,
        on_delete=models.CASCADE,
        related_name='feedback_thread'
    )
    sender_type = models.CharField(
        max_length=10,
        choices=SenderType.choices,
        help_text=_('Type of user who sent this feedback')
    )
    user = models.ForeignKey(
        'users.User',
        on_delete=models.CASCADE,
        related_name='document_feedback'
    )
    message = models.TextField(help_text=_('Feedback message'))
    is_read = models.BooleanField(default=False, help_text=_('Whether this feedback has been read by the recipient'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _('Document Feedback')
        verbose_name_plural = _('Document Feedback')
        ordering = ['created_at']  # Chronological order

    def __str__(self):
        return f"Feedback on {self.document} by {self.user.username}"
