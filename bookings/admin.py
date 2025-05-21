from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Booking, BookingReview


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ('id', 'property', 'tenant', 'check_in_date', 'check_out_date', 'guests', 'total_price', 'status', 'is_paid')
    list_filter = ('status', 'is_paid', 'check_in_date', 'check_out_date')
    search_fields = ('property__title', 'tenant__username', 'tenant__email', 'guest_name', 'guest_email')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('property', 'tenant', 'status')
        }),
        (_('Booking Details'), {
            'fields': ('check_in_date', 'check_out_date', 'guests', 'total_price', 'special_requests')
        }),
        (_('Guest Information'), {
            'fields': ('guest_name', 'guest_email', 'guest_phone')
        }),
        (_('Payment Information'), {
            'fields': ('is_paid', 'payment_date', 'payment_id')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(BookingReview)
class BookingReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('booking__property__title', 'booking__tenant__username', 'comment')
    readonly_fields = ('created_at',)
