# Guest Booking and Payment Flow

This document outlines the complete flow for non-logged-in users (guests) to book and pay for properties on the House Rental platform.

## Overview

The platform supports two types of users making bookings:
1. **Logged-in users** - Authenticated users with active accounts
2. **Guest users** - Non-logged-in users who can book without creating an active account

The system uses strategy patterns for both booking and payment processes to handle these different user types while maintaining clean, DRY code.

## Guest Booking Flow

### 1. Property Selection
- Guest browses properties without logging in
- Guest selects a property and dates for booking

### 2. Guest Booking Creation
- **Endpoint**: `POST /api/bookings/guest` ⚠️ **IMPORTANT: Use this specific endpoint for guest bookings, NOT `/api/bookings/`**
- **Authentication**: None required
- **Request Data**:
  ```json
  {
    "property_id": 123,
    "check_in_date": "2023-06-01",
    "check_out_date": "2023-06-07",
    "guests": 2,
    "guest_name": "John Doe",
    "guest_email": "john@example.com",
    "guest_phone": "123-456-7890",
    "special_requests": "Late check-in",
    "user_info": {
      "full_name": "John Doe",
      "email": "john@example.com",
      "phone_number": "123-456-7890",
      "birthday": "1985-01-01"
    }
  }
  ```

### 3. Behind the Scenes - Booking Strategy Pattern
- `GuestBookingStrategy` is used for non-logged-in users
- Creates an inactive user account with:
  - Username derived from email
  - Random password (user can't log in with it)
  - TENANT role
  - `is_active=False`
- Creates a booking linked to this inactive user

## Guest Payment Flow

### 1. Create Payment Intent
Guest users have two options for creating payment intents:

#### Option A: Full Payment Intent
- **Endpoint**: `POST /api/payments/guest-intents` ⚠️ **IMPORTANT: Use this specific endpoint for guest payments**
- **Authentication**: None required
- **Request Data**:
  ```json
  {
    "booking_id": 123,
    "setup_future_usage": null
  }
  ```
- **Response**: Full payment intent details

#### Option B: Quick Payment Intent
- **Endpoint**: `POST /api/payments/quick-intent?booking_id=123` ⚠️ **IMPORTANT: Use this specific endpoint for simplified guest payments**
- **Authentication**: None required
- **Response**: Simplified payment intent with just the essential data:
  ```json
  {
    "client_secret": "pi_XXXXX_secret_YYYYY",
    "amount": 750.00,
    "id": "pi_XXXXX"
  }
  ```

### 2. Behind the Scenes - Payment Strategy Pattern
- `GuestPaymentStrategy` is used for non-logged-in users
- Gets the inactive user associated with the booking
- Ensures the user has a Stripe customer ID
- Creates a Stripe payment intent linked to this user
- Marks the payment intent with `is_guest: true` metadata

### 3. Process Payment on Frontend
```javascript
// Get the client secret from the response
const { client_secret } = await fetch('/api/payments/quick-intent', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ booking_id: bookingId })
}).then(res => res.json());

// Create a card element
const elements = stripe.elements();
const cardElement = elements.create('card');
cardElement.mount('#card-element');

// Process the payment
const { error, paymentIntent } = await stripe.confirmCardPayment(client_secret, {
  payment_method: {
    card: cardElement,
    billing_details: {
      name: 'Guest Name',
      email: 'guest@example.com'
    }
  }
});

// Handle the result
if (error) {
  // Show error to the customer
} else if (paymentIntent.status === 'succeeded') {
  // Payment successful, redirect to success page
  window.location.href = '/booking/success?id=' + bookingId;
}
```

## Complete User Flow

1. Guest browses properties without logging in
2. Guest selects a property and dates
3. Guest provides their information and creates a booking **using the `/api/bookings/guest` endpoint**
4. System creates an inactive user account and a booking
5. Guest proceeds to payment **using either `/api/payments/guest-intents` or `/api/payments/quick-intent`**
6. System creates a payment intent for the booking
7. Guest enters payment details and completes payment
8. System marks the booking as paid
9. Guest receives confirmation email with booking details

## Benefits of This Approach

1. **Seamless Guest Experience** - Users can book without the friction of creating an account
2. **Data Consistency** - All bookings are still linked to user records
3. **Future Account Activation** - Guests can later activate their account if they wish
4. **Clean Architecture** - Strategy pattern keeps code organized and maintainable
5. **DRY Code** - Common logic is reused between guest and logged-in flows

## Security Considerations

1. **Rate Limiting** - Guest booking and payment endpoints are rate-limited to prevent abuse
2. **Validation** - All guest data is validated, including age verification (must be 18+)
3. **Inactive Accounts** - Guest user accounts are created as inactive to prevent unauthorized access

## Common Issues and Troubleshooting

1. **401 Unauthorized Error**: If you get this error when creating a guest booking, you're likely using the wrong endpoint. Make sure to use `/api/bookings/guest` for guest bookings, not `/api/bookings/`.

2. **Missing user_info**: When making a guest booking, you must include the `user_info` field with full_name, email, phone_number, and birthday.

3. **Missing client_secret**: When processing payments, make sure you're using the correct guest payment endpoint and properly extracting the client_secret from the response. 