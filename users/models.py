from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from datetime import date
from dateutil.relativedelta import relativedelta

class User(AbstractUser):
    """
    Custom User model with role-based access control.
    """
    class Role(models.TextChoices):
        ADMIN = 'admin', _('Admin')
        AGENT = 'agent', _('Agent')
        TENANT = 'tenant', _('Tenant')
    
    role = models.CharField(
        max_length=10,
        choices=Role.choices,
        default=Role.TENANT,
        verbose_name=_('Role')
    )
    
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    birthday = models.DateField(blank=True, null=True, verbose_name=_('Date of Birth'))
    
    # Social auth fields
    google_id = models.CharField(max_length=255, blank=True, null=True)
    twitter_id = models.CharField(max_length=255, blank=True, null=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
    
    def __str__(self):
        return self.username
    
    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN
    
    @property
    def is_agent(self):
        return self.role == self.Role.AGENT
    
    @property
    def is_tenant(self):
        return self.role == self.Role.TENANT
        
    @property
    def is_adult(self):
        """
        Check if the user is at least 18 years old.
        """
        if not self.birthday:
            return False
        today = date.today()
        age = relativedelta(today, self.birthday).years
        return age >= 18
