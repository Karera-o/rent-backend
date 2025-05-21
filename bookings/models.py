from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.conf import settings


class Booking(models.Model):
    """
    Booking model for property reservations.
    """
    class BookingStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        CONFIRMED = 'confirmed', _('Confirmed')
        CANCELLED = 'cancelled', _('Cancelled')
        COMPLETED = 'completed', _('Completed')

    # Relationships
    property = models.ForeignKey(
        'properties.Property',
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name=_('Property')
    )
    tenant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name=_('Tenant')
    )

    # Booking details
    check_in_date = models.DateField(_('Check-in Date'))
    check_out_date = models.DateField(_('Check-out Date'))
    guests = models.PositiveIntegerField(_('Number of Guests'), default=1, validators=[MinValueValidator(1)])
    total_price = models.DecimalField(_('Total Price'), max_digits=10, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        verbose_name=_('Status')
    )

    # Guest information
    guest_name = models.CharField(_('Guest Name'), max_length=255)
    guest_email = models.EmailField(_('Guest Email'))
    guest_phone = models.CharField(_('Guest Phone'), max_length=20)

    # Additional information
    special_requests = models.TextField(_('Special Requests'), blank=True, null=True)

    # Payment information
    is_paid = models.BooleanField(_('Is Paid'), default=False)
    payment_date = models.DateTimeField(_('Payment Date'), blank=True, null=True)
    payment_id = models.CharField(_('Payment ID'), max_length=255, blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Booking')
        verbose_name_plural = _('Bookings')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['property', 'check_in_date', 'check_out_date']),
            models.Index(fields=['tenant']),
            models.Index(fields=['status']),
        ]

    def __str__(self):
        return f"Booking {self.id} - {self.property.title} ({self.check_in_date} to {self.check_out_date})"

    def get_duration_days(self):
        """Calculate the duration of the booking in days."""
        if self.check_in_date and self.check_out_date:
            return (self.check_out_date - self.check_in_date).days
        return 0


class BookingReview(models.Model):
    """
    Review for a booking after completion.
    """
    booking = models.OneToOneField(
        Booking,
        on_delete=models.CASCADE,
        related_name='review',
        verbose_name=_('Booking')
    )
    rating = models.PositiveSmallIntegerField(
        _('Rating'),
        validators=[MinValueValidator(1)],
        help_text=_('Rating from 1 to 5')
    )
    comment = models.TextField(_('Comment'))
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)

    class Meta:
        verbose_name = _('Booking Review')
        verbose_name_plural = _('Booking Reviews')

    def __str__(self):
        return f"Review for {self.booking}"
