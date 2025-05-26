from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
import logging

from bookings.models import Booking

logger = logging.getLogger('house_rental')


class Payment(models.Model):
    """
    Payment model to track payment information for bookings.
    """
    class PaymentStatus(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PROCESSING = 'processing', _('Processing')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
        REFUNDED = 'refunded', _('Refunded')
        CANCELED = 'canceled', _('Canceled')

    # Relationships
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name=_('Booking')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name=_('User')
    )

    # Payment details
    amount = models.DecimalField(_('Amount'), max_digits=10, decimal_places=2)
    currency = models.CharField(_('Currency'), max_length=3, default='usd')
    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name=_('Status')
    )

    # Stripe information
    stripe_payment_intent_id = models.CharField(_('Stripe Payment Intent ID'), max_length=255, blank=True, null=True)
    stripe_payment_method_id = models.CharField(_('Stripe Payment Method ID'), max_length=255, blank=True, null=True)
    stripe_customer_id = models.CharField(_('Stripe Customer ID'), max_length=255, blank=True, null=True)

    # Receipt information
    receipt_url = models.URLField(_('Receipt URL'), blank=True, null=True)
    receipt_email = models.EmailField(_('Receipt Email'), blank=True, null=True)

    # Timestamps
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)
    completed_at = models.DateTimeField(_('Completed At'), blank=True, null=True)
    failed_at = models.DateTimeField(_('Failed At'), blank=True, null=True)
    refunded_at = models.DateTimeField(_('Refunded At'), blank=True, null=True)
    canceled_at = models.DateTimeField(_('Cancelled At'), blank=True, null=True)

    class Meta:
        verbose_name = _('Payment')
        verbose_name_plural = _('Payments')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['booking']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['stripe_payment_intent_id']),
        ]

    def __str__(self):
        return f"Payment {self.id} - {self.booking} - {self.amount} {self.currency}"

    def save(self, *args, **kwargs):
        # Update timestamps based on status
        if self.status == self.PaymentStatus.COMPLETED and not self.completed_at:
            self.completed_at = timezone.now()
        elif self.status == self.PaymentStatus.FAILED and not self.failed_at:
            self.failed_at = timezone.now()
        elif self.status == self.PaymentStatus.REFUNDED and not self.refunded_at:
            self.refunded_at = timezone.now()
        elif self.status == self.PaymentStatus.CANCELED and not self.canceled_at:
            self.canceled_at = timezone.now()
        
        # If status is completed and booking is not None, update booking to paid
        if self.status == self.PaymentStatus.COMPLETED and self.booking and not self.booking.is_paid:
            self.booking.is_paid = True
            self.booking.payment_date = timezone.now()
            self.booking.payment_id = self.stripe_payment_intent_id
            self.booking.save()
            
        super().save(*args, **kwargs)


class PaymentMethod(models.Model):
    """
    Payment method model to store user's payment methods.
    """
    class PaymentType(models.TextChoices):
        CARD = 'card', _('Credit/Debit Card')
        BANK_ACCOUNT = 'bank_account', _('Bank Account')
        PAYPAL = 'paypal', _('PayPal')
        OTHER = 'other', _('Other')

    # Relationships
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_methods',
        verbose_name=_('User')
    )

    # Payment method details
    type = models.CharField(
        max_length=20,
        choices=PaymentType.choices,
        default=PaymentType.CARD,
        verbose_name=_('Type')
    )
    is_default = models.BooleanField(_('Is Default'), default=False)

    # Card details (if type is card)
    card_brand = models.CharField(_('Card Brand'), max_length=50, blank=True, null=True)
    card_last4 = models.CharField(_('Last 4 Digits'), max_length=4, blank=True, null=True)
    card_exp_month = models.PositiveSmallIntegerField(_('Expiration Month'), blank=True, null=True)
    card_exp_year = models.PositiveSmallIntegerField(_('Expiration Year'), blank=True, null=True)

    # Stripe information
    stripe_payment_method_id = models.CharField(_('Stripe Payment Method ID'), max_length=255, unique=True)

    # Timestamps
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Payment Method')
        verbose_name_plural = _('Payment Methods')
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['stripe_payment_method_id']),
        ]
        unique_together = [['user', 'stripe_payment_method_id']]

    def __str__(self):
        if self.type == self.PaymentType.CARD and self.card_brand and self.card_last4:
            return f"{self.card_brand} **** {self.card_last4}"
        return f"{self.get_type_display()} - {self.stripe_payment_method_id}"

    def save(self, *args, **kwargs):
        # If this is the default payment method, unset default for other payment methods
        if self.is_default:
            PaymentMethod.objects.filter(user=self.user, is_default=True).update(is_default=False)

        super().save(*args, **kwargs)


class PaymentIntent(models.Model):
    """
    Payment intent model to track Stripe payment intents.
    """
    class PaymentIntentStatus(models.TextChoices):
        REQUIRES_PAYMENT_METHOD = 'requires_payment_method', _('Requires Payment Method')
        REQUIRES_CONFIRMATION = 'requires_confirmation', _('Requires Confirmation')
        REQUIRES_ACTION = 'requires_action', _('Requires Action')
        PROCESSING = 'processing', _('Processing')
        REQUIRES_CAPTURE = 'requires_capture', _('Requires Capture')
        CANCELLED = 'cancelled', _('Cancelled')
        SUCCEEDED = 'succeeded', _('Succeeded')

    # Relationships
    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name='payment_intents',
        verbose_name=_('Booking')
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='payment_intents',
        verbose_name=_('User')
    )
    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        related_name='payment_intent',
        verbose_name=_('Payment'),
        blank=True,
        null=True
    )

    # Payment intent details
    amount = models.DecimalField(_('Amount'), max_digits=10, decimal_places=2)
    currency = models.CharField(_('Currency'), max_length=3, default='usd')
    status = models.CharField(
        max_length=30,
        choices=PaymentIntentStatus.choices,
        default=PaymentIntentStatus.REQUIRES_PAYMENT_METHOD,
        verbose_name=_('Status')
    )

    # Stripe information
    stripe_payment_intent_id = models.CharField(_('Stripe Payment Intent ID'), max_length=255, unique=True)
    stripe_client_secret = models.CharField(_('Stripe Client Secret'), max_length=255)

    # Timestamps
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Payment Intent')
        verbose_name_plural = _('Payment Intents')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['booking']),
            models.Index(fields=['user']),
            models.Index(fields=['status']),
            models.Index(fields=['stripe_payment_intent_id']),
        ]

    def __str__(self):
        return f"Payment Intent {self.id} - {self.booking} - {self.amount} {self.currency}"
