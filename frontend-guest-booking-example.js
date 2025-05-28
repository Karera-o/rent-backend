/**
 * Example frontend code for guest booking and payment flow
 * 
 * This code demonstrates how to implement the guest booking and payment flow
 * on the frontend using vanilla JavaScript and the Stripe.js library.
 */

// Step 1: Set up Stripe.js
const loadStripe = async () => {
  // Get the publishable key
  const { publishable_key } = await fetch('/api/payments/public-key')
    .then(res => res.json());
  
  return Stripe(publishable_key);
};

// Step 2: Collect booking information
const bookingForm = document.getElementById('booking-form');
bookingForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  
  // Show loading state
  const submitButton = bookingForm.querySelector('button[type="submit"]');
  submitButton.disabled = true;
  submitButton.textContent = 'Processing...';
  
  // Collect form data
  const formData = new FormData(bookingForm);
  
  // Prepare booking data (IMPORTANT: Using the guest endpoint!)
  const bookingData = {
    property_id: parseInt(formData.get('property_id')),
    check_in_date: formData.get('check_in_date'),
    check_out_date: formData.get('check_out_date'),
    guests: parseInt(formData.get('guests')),
    guest_name: formData.get('guest_name'),
    guest_email: formData.get('guest_email'),
    guest_phone: formData.get('guest_phone'),
    special_requests: formData.get('special_requests') || null,
    // This user_info field is required for guest bookings
    user_info: {
      full_name: formData.get('full_name'),
      email: formData.get('email'),
      phone_number: formData.get('phone_number'),
      birthday: formData.get('birthday')
    }
  };
  
  try {
    // Step 3: Create a guest booking
    const bookingResponse = await fetch('/api/bookings/guest', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(bookingData)
    });
    
    if (!bookingResponse.ok) {
      const errorData = await bookingResponse.json();
      throw new Error(errorData.message || 'Failed to create booking');
    }
    
    const booking = await bookingResponse.json();
    console.log('Booking created:', booking);
    
    // Proceed to payment
    await handlePayment(booking.id);
    
  } catch (error) {
    console.error('Error creating booking:', error);
    alert('Error creating booking: ' + error.message);
    
    // Reset form state
    submitButton.disabled = false;
    submitButton.textContent = 'Book Now';
  }
});

// Step 4: Handle payment
const handlePayment = async (bookingId) => {
  try {
    // Show payment form
    document.getElementById('booking-form-container').style.display = 'none';
    document.getElementById('payment-form-container').style.display = 'block';
    
    // Initialize Stripe
    const stripe = await loadStripe();
    
    // Step 5: Create a payment intent using the guest endpoint
    const { client_secret } = await fetch(`/api/payments/quick-intent?booking_id=${bookingId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    }).then(res => res.json());
    
    if (!client_secret) {
      throw new Error('Failed to create payment intent');
    }
    
    // Step 6: Set up Stripe Elements
    const elements = stripe.elements();
    
    // Style the card element
    const style = {
      base: {
        color: '#32325d',
        fontFamily: '"Helvetica Neue", Helvetica, sans-serif',
        fontSmoothing: 'antialiased',
        fontSize: '16px',
        '::placeholder': {
          color: '#aab7c4'
        }
      },
      invalid: {
        color: '#fa755a',
        iconColor: '#fa755a'
      }
    };
    
    // Create and mount the card element
    const cardElement = elements.create('card', { style });
    cardElement.mount('#card-element');
    
    // Handle payment form submission
    const paymentForm = document.getElementById('payment-form');
    paymentForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      
      const submitButton = paymentForm.querySelector('button[type="submit"]');
      submitButton.disabled = true;
      submitButton.textContent = 'Processing Payment...';
      
      // Step 7: Process the payment
      const { error, paymentIntent } = await stripe.confirmCardPayment(client_secret, {
        payment_method: {
          card: cardElement,
          billing_details: {
            name: document.getElementById('cardholder-name').value,
            email: document.getElementById('cardholder-email').value
          }
        }
      });
      
      if (error) {
        // Show error to customer
        console.error('Payment error:', error);
        document.getElementById('card-errors').textContent = error.message;
        submitButton.disabled = false;
        submitButton.textContent = 'Pay Now';
      } else if (paymentIntent.status === 'succeeded') {
        // Step 8: Payment successful
        console.log('Payment successful:', paymentIntent);
        
        // Show success message
        document.getElementById('payment-form-container').style.display = 'none';
        document.getElementById('success-container').style.display = 'block';
        document.getElementById('booking-reference').textContent = bookingId;
        
        // Optional: Redirect to success page
        // window.location.href = `/booking/success?id=${bookingId}`;
      }
    });
    
  } catch (error) {
    console.error('Error handling payment:', error);
    alert('Error processing payment: ' + error.message);
  }
};

// Example HTML structure:
/*
<div id="booking-form-container">
  <form id="booking-form">
    <input type="hidden" name="property_id" value="123">
    
    <div class="form-group">
      <label for="check_in_date">Check-in Date</label>
      <input type="date" id="check_in_date" name="check_in_date" required>
    </div>
    
    <div class="form-group">
      <label for="check_out_date">Check-out Date</label>
      <input type="date" id="check_out_date" name="check_out_date" required>
    </div>
    
    <div class="form-group">
      <label for="guests">Number of Guests</label>
      <input type="number" id="guests" name="guests" min="1" max="10" value="2" required>
    </div>
    
    <div class="form-group">
      <label for="full_name">Full Name</label>
      <input type="text" id="full_name" name="full_name" required>
    </div>
    
    <div class="form-group">
      <label for="email">Email</label>
      <input type="email" id="email" name="email" required>
    </div>
    
    <div class="form-group">
      <label for="phone_number">Phone Number</label>
      <input type="tel" id="phone_number" name="phone_number" required>
    </div>
    
    <div class="form-group">
      <label for="birthday">Date of Birth</label>
      <input type="date" id="birthday" name="birthday" required>
    </div>
    
    <div class="form-group">
      <label for="guest_name">Guest Name (if different)</label>
      <input type="text" id="guest_name" name="guest_name" required>
    </div>
    
    <div class="form-group">
      <label for="guest_email">Guest Email (if different)</label>
      <input type="email" id="guest_email" name="guest_email" required>
    </div>
    
    <div class="form-group">
      <label for="guest_phone">Guest Phone (if different)</label>
      <input type="tel" id="guest_phone" name="guest_phone" required>
    </div>
    
    <div class="form-group">
      <label for="special_requests">Special Requests</label>
      <textarea id="special_requests" name="special_requests"></textarea>
    </div>
    
    <button type="submit">Book Now</button>
  </form>
</div>

<div id="payment-form-container" style="display: none;">
  <h2>Payment Information</h2>
  
  <form id="payment-form">
    <div class="form-group">
      <label for="cardholder-name">Cardholder Name</label>
      <input type="text" id="cardholder-name" required>
    </div>
    
    <div class="form-group">
      <label for="cardholder-email">Cardholder Email</label>
      <input type="email" id="cardholder-email" required>
    </div>
    
    <div class="form-group">
      <label for="card-element">Credit or Debit Card</label>
      <div id="card-element">
        <!-- Stripe Card Element will be inserted here -->
      </div>
      <div id="card-errors" role="alert"></div>
    </div>
    
    <button type="submit">Pay Now</button>
  </form>
</div>

<div id="success-container" style="display: none;">
  <h2>Booking Confirmed!</h2>
  <p>Your booking reference: <strong id="booking-reference"></strong></p>
  <p>Thank you for your reservation. A confirmation email has been sent to your email address.</p>
</div>
*/ 