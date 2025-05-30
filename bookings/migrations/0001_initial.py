# Generated by Django 5.2 on 2025-04-07 23:20

import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('properties', '0002_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Booking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('check_in_date', models.DateField(verbose_name='Check-in Date')),
                ('check_out_date', models.DateField(verbose_name='Check-out Date')),
                ('guests', models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)], verbose_name='Number of Guests')),
                ('total_price', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Total Price')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('confirmed', 'Confirmed'), ('cancelled', 'Cancelled'), ('completed', 'Completed')], default='pending', max_length=20, verbose_name='Status')),
                ('guest_name', models.CharField(max_length=255, verbose_name='Guest Name')),
                ('guest_email', models.EmailField(max_length=254, verbose_name='Guest Email')),
                ('guest_phone', models.CharField(max_length=20, verbose_name='Guest Phone')),
                ('special_requests', models.TextField(blank=True, null=True, verbose_name='Special Requests')),
                ('is_paid', models.BooleanField(default=False, verbose_name='Is Paid')),
                ('payment_date', models.DateTimeField(blank=True, null=True, verbose_name='Payment Date')),
                ('payment_id', models.CharField(blank=True, max_length=255, null=True, verbose_name='Payment ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='Updated At')),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookings', to='properties.property', verbose_name='Property')),
                ('tenant', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='bookings', to=settings.AUTH_USER_MODEL, verbose_name='Tenant')),
            ],
            options={
                'verbose_name': 'Booking',
                'verbose_name_plural': 'Bookings',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='BookingReview',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('rating', models.PositiveSmallIntegerField(help_text='Rating from 1 to 5', validators=[django.core.validators.MinValueValidator(1)], verbose_name='Rating')),
                ('comment', models.TextField(verbose_name='Comment')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Created At')),
                ('booking', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='review', to='bookings.booking', verbose_name='Booking')),
            ],
            options={
                'verbose_name': 'Booking Review',
                'verbose_name_plural': 'Booking Reviews',
            },
        ),
        migrations.AddIndex(
            model_name='booking',
            index=models.Index(fields=['property', 'check_in_date', 'check_out_date'], name='bookings_bo_propert_a3c1f4_idx'),
        ),
        migrations.AddIndex(
            model_name='booking',
            index=models.Index(fields=['tenant'], name='bookings_bo_tenant__7ac65b_idx'),
        ),
        migrations.AddIndex(
            model_name='booking',
            index=models.Index(fields=['status'], name='bookings_bo_status_233e96_idx'),
        ),
    ]
