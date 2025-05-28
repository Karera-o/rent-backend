# Guest Booking Access Documentation

## Overview

The guest booking access functionality allows non-authenticated users (guests) to access their booking details using email verification. This is essential for guests who made bookings without creating an account and need to view their booking information later.

## Implementation Details

### Service Layer

#### `BookingService.get_booking_by_email(booking_id, guest_email)`

This method enables guest access to booking details by verifying the guest's email address against the booking record.

**Parameters:**
- `booking_id` (int): The ID of the booking to retrieve
- `guest_email` (str): The email address used when making the booking

**Returns:**
- `Dict[str, Any]`: Complete booking details if email matches
- `None`: If booking not found or email doesn't match

**Security Features:**
- Case-insensitive email comparison
- Logging of access attempts for security monitoring
- Warning logs for email mismatches

### API Layer

#### `POST /api/bookings/{booking_id}/guest-access`

Non-authenticated endpoint that allows guests to access their booking details.

**Request Schema:**
```json
{
  "guest_email": "guest@example.com"
}
```

**Response:**
- `200 OK`: Returns complete booking details
- `404 Not Found`: Booking not found or email doesn't match
- `400 Bad Request`: General error occurred
- `422 Unprocessable Entity`: Invalid email format

**Rate Limiting:**
- 20 guest accesses per hour per IP address

#### `GET /api/bookings/{booking_id}` (Enhanced)

The existing authenticated endpoint remains unchanged and requires JWT authentication for registered users.

## Usage Examples

### For Frontend Implementation

```javascript
// Guest booking access
const accessGuestBooking = async (bookingId, guestEmail) => {
  try {
    const response = await fetch(`/api/bookings/${bookingId}/guest-access`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        guest_email: guestEmail
      })
    });

    if (response.ok) {
      const booking = await response.json();
      return booking;
    } else {
      throw new Error('Booking not found or email doesn\'t match');
    }
  } catch (error) {
    console.error('Error accessing booking:', error);
    throw error;
  }
};

// Usage
const booking = await accessGuestBooking(123, 'guest@example.com');
```

### For Testing

```python
# Service layer test
def test_guest_booking_access_success(self):
    booking_data = self.booking_service.get_booking_by_email(
        self.booking.id, 
        'guest@example.com'
    )
    
    self.assertIsNotNone(booking_data)
    self.assertEqual(booking_data['guest_email'], 'guest@example.com')

# API layer test
def test_guest_booking_api_access_success(self):
    url = f'/api/bookings/{self.booking.id}/guest-access'
    data = {'guest_email': 'guest@example.com'}
    
    response = self.client.post(
        url, 
        data=json.dumps(data),
        content_type='application/json'
    )
    
    self.assertEqual(response.status_code, 200)
```

## Security Considerations

### Email Verification
- Only the exact email address used during booking can access the details
- Case-insensitive comparison for user convenience
- No password or additional authentication required

### Rate Limiting
- Prevents abuse with 20 requests per hour per IP
- Separate rate limiting from other endpoints

### Logging and Monitoring
- All access attempts are logged with INFO level
- Email mismatches are logged with WARNING level
- Failed access attempts are logged with ERROR level

### Data Privacy
- Only booking-related data is returned
- No sensitive user account information exposed
- Guest users remain inactive unless they activate their accounts

## Error Handling

### Common Scenarios

1. **Booking Not Found**
   - Returns 404 with message: "Booking with ID {id} not found or email doesn't match"

2. **Email Mismatch**
   - Returns 404 with same message (prevents information disclosure)
   - Logs warning for monitoring

3. **Invalid Email Format**
   - Returns 422 with validation error details

4. **Rate Limit Exceeded**
   - Returns 429 with rate limit message

## Integration with Guest Booking System

This functionality integrates seamlessly with the existing guest booking system:

1. **Guest makes booking** via `POST /api/bookings/guest`
2. **Inactive user account created** with guest details
3. **Booking linked to inactive user**
4. **Guest can access booking** via `POST /api/bookings/{id}/guest-access`
5. **Optional account activation** for future authenticated access

## Testing Coverage

The implementation includes comprehensive tests covering:

- ✅ Successful guest access with correct email
- ✅ Failed access with wrong email
- ✅ Case-insensitive email matching
- ✅ Non-existent booking handling
- ✅ API endpoint functionality
- ✅ Invalid data handling
- ✅ Integration with guest booking creation

## Future Enhancements

### Potential Improvements

1. **Magic Link Access**: Send time-limited access links via email
2. **Booking Code**: Generate unique booking codes for easier access
3. **SMS Verification**: Alternative verification method using phone number
4. **Guest Dashboard**: Dedicated interface for managing multiple guest bookings

### Security Enhancements

1. **IP-based restrictions**: Additional security for suspicious access patterns
2. **Time-based access limits**: Restrict access to recent bookings only
3. **Email notifications**: Alert on booking access attempts 