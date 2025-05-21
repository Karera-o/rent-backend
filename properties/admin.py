from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Property, PropertyImage, PropertyDocument, DocumentFeedback

class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 1

class PropertyDocumentInline(admin.TabularInline):
    model = PropertyDocument
    extra = 0
    fields = ('document_type', 'document', 'status', 'feedback', 'feedback_read')
    readonly_fields = ('created_at',)

class DocumentFeedbackInline(admin.TabularInline):
    model = DocumentFeedback
    extra = 0
    fields = ('sender_type', 'user', 'message', 'is_read', 'created_at')
    readonly_fields = ('created_at',)

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'property_type', 'status', 'document_verification_status', 'owner', 'city', 'price_per_night', 'created_at')
    list_filter = ('status', 'property_type', 'city', 'has_wifi', 'has_pool', 'has_parking', 'document_verification_status')
    search_fields = ('title', 'description', 'address', 'city')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [PropertyImageInline, PropertyDocumentInline]
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'property_type', 'status', 'document_verification_status', 'owner')
        }),
        (_('Location'), {
            'fields': ('address', 'city', 'state', 'country', 'zip_code', 'latitude', 'longitude')
        }),
        (_('Details'), {
            'fields': ('bedrooms', 'bathrooms', 'area', 'price_per_night')
        }),
        (_('Amenities'), {
            'fields': (
                'has_wifi', 'has_kitchen', 'has_air_conditioning', 'has_heating',
                'has_tv', 'has_parking', 'has_pool', 'has_gym'
            )
        }),
        (_('Additional Services'), {
            'fields': ('has_maid_service', 'has_car_rental')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ('property', 'caption', 'is_primary', 'created_at')
    list_filter = ('is_primary', 'created_at')
    search_fields = ('property__title', 'caption')
    readonly_fields = ('created_at',)

@admin.register(PropertyDocument)
class PropertyDocumentAdmin(admin.ModelAdmin):
    list_display = ('property', 'document_type', 'status', 'feedback_read', 'created_at')
    list_filter = ('status', 'document_type', 'feedback_read', 'created_at')
    search_fields = ('property__title', 'description', 'feedback', 'rejection_reason')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [DocumentFeedbackInline]
    fieldsets = (
        (None, {
            'fields': ('property', 'document_type', 'document', 'description', 'status')
        }),
        (_('Feedback & Rejection'), {
            'fields': ('feedback', 'feedback_read', 'rejection_reason')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at')
        }),
    )

@admin.register(DocumentFeedback)
class DocumentFeedbackAdmin(admin.ModelAdmin):
    list_display = ('document', 'sender_type', 'user', 'is_read', 'created_at')
    list_filter = ('sender_type', 'is_read', 'created_at')
    search_fields = ('document__property__title', 'message', 'user__username', 'user__email')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('document', 'sender_type', 'user', 'message', 'is_read')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at')
        }),
    )
