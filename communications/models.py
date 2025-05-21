from django.db import models
from django.utils.translation import gettext_lazy as _


class ContactMessage(models.Model):
    """
    Model for storing contact form messages from users.
    """
    class ContactSubject(models.TextChoices):
        GENERAL = 'general', _('General Inquiry')
        PROPERTY = 'property', _('Property Question')
        VIEWING = 'viewing', _('Schedule a Viewing')
        SUPPORT = 'support', _('Customer Support')
        FEEDBACK = 'feedback', _('Feedback')

    # Contact information
    first_name = models.CharField(_('First Name'), max_length=100)
    last_name = models.CharField(_('Last Name'), max_length=100)
    email = models.EmailField(_('Email'))
    phone = models.CharField(_('Phone'), max_length=20)

    # Message details
    subject = models.CharField(
        _('Subject'),
        max_length=20,
        choices=ContactSubject.choices,
        default=ContactSubject.GENERAL
    )
    message = models.TextField(_('Message'))

    # Status and timestamps
    is_read = models.BooleanField(_('Is Read'), default=False)
    created_at = models.DateTimeField(_('Created At'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Updated At'), auto_now=True)

    class Meta:
        verbose_name = _('Contact Message')
        verbose_name_plural = _('Contact Messages')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.subject}"
