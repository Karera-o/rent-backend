from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Payment, PaymentMethod, PaymentIntent


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'user', 'amount', 'currency', 'status', 'created_at', 'completed_at')
    list_filter = ('status', 'currency', 'created_at', 'completed_at')
    search_fields = ('booking__id', 'user__username', 'user__email', 'stripe_payment_intent_id')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at', 'completed_at')
    fieldsets = (
        (None, {
            'fields': ('booking', 'user', 'status')
        }),
        (_('Payment Details'), {
            'fields': ('amount', 'currency')
        }),
        (_('Stripe Information'), {
            'fields': ('stripe_payment_intent_id', 'stripe_payment_method_id', 'stripe_customer_id')
        }),
        (_('Receipt Information'), {
            'fields': ('receipt_url', 'receipt_email')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at', 'completed_at')
        }),
    )


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'type', 'card_brand', 'card_last4', 'is_default', 'created_at')
    list_filter = ('type', 'is_default', 'card_brand', 'created_at')
    search_fields = ('user__username', 'user__email', 'stripe_payment_method_id')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('user', 'type', 'is_default')
        }),
        (_('Card Details'), {
            'fields': ('card_brand', 'card_last4', 'card_exp_month', 'card_exp_year')
        }),
        (_('Stripe Information'), {
            'fields': ('stripe_payment_method_id',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at')
        }),
    )


@admin.register(PaymentIntent)
class PaymentIntentAdmin(admin.ModelAdmin):
    list_display = ('id', 'booking', 'user', 'amount', 'currency', 'status', 'created_at')
    list_filter = ('status', 'currency', 'created_at')
    search_fields = ('booking__id', 'user__username', 'user__email', 'stripe_payment_intent_id')
    date_hierarchy = 'created_at'
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('booking', 'user', 'payment', 'status')
        }),
        (_('Payment Intent Details'), {
            'fields': ('amount', 'currency')
        }),
        (_('Stripe Information'), {
            'fields': ('stripe_payment_intent_id', 'stripe_client_secret')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at')
        }),
    )
