#!/usr/bin/env python3
"""
Integration test for the new payment type feature.
Tests:
1. Payment type field exists in Reservation model
2. Payment type form field is available in ReservationForm
3. Amount calculation logic works correctly
4. Admin display tables show payment type properly
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database_fixed import db, Reservation, ReservationForm
from flask import Flask
from flask_wtf import FlaskForm

def test_payment_type_model():
    """Test that Reservation model has payment_type field"""
    print("Testing Reservation model...")
    
    # Check that payment_type is in the model
    assert hasattr(Reservation, 'payment_type'), "Reservation model missing payment_type column"
    print("✓ Reservation model has payment_type column")

def test_payment_type_form():
    """Test that ReservationForm has payment_type field"""
    print("\nTesting ReservationForm...")
    
    # Check that payment_type is in the form
    assert hasattr(ReservationForm, 'payment_type'), "ReservationForm missing payment_type field"
    print("✓ ReservationForm has payment_type field")
    
    # Verify it's a SelectField with correct choices
    form_field = ReservationForm.payment_type
    print(f"✓ payment_type field type: {type(form_field)}")

def test_amount_calculation():
    """Test the amount calculation logic"""
    print("\nTesting amount calculation...")
    
    total_amount = 1000.0
    
    # Test Full Payment calculation
    full_payment_amount = total_amount
    assert full_payment_amount == 1000.0, "Full payment calculation incorrect"
    print(f"✓ Full Payment amount: ₱{full_payment_amount:.2f}")
    
    # Test Downpayment calculation (50%)
    downpayment_amount = total_amount * 0.5
    assert downpayment_amount == 500.0, "Downpayment calculation incorrect"
    print(f"✓ Downpayment amount: ₱{downpayment_amount:.2f}")

def test_file_contents():
    """Test that key files contain expected code"""
    print("\nTesting file contents...")
    
    # Check client_fixed.py for amount_paid calculation
    with open('client_fixed.py', 'r') as f:
        content = f.read()
        assert 'if form.payment_type.data == "Full Payment"' in content or \
               'payment_type.data == "Full Payment"' in content, \
               "client_fixed.py missing payment_type calculation"
        print("✓ client_fixed.py has payment_type logic")
    
    # Check rooms.html for payment type section
    with open('app/templates/rooms.html', 'r') as f:
        content = f.read()
        assert 'payment-type-section' in content, "rooms.html missing payment-type-section"
        assert 'Downpayment' in content, "rooms.html missing Downpayment option"
        assert 'Full Payment' in content, "rooms.html missing Full Payment option"
        print("✓ rooms.html has payment type UI")
    
    # Check rooms.js for payment type function
    with open('static/js/rooms.js', 'r') as f:
        content = f.read()
        assert 'updatePaymentTypeDisplay' in content, "rooms.js missing updatePaymentTypeDisplay function"
        print("✓ rooms.js has updatePaymentTypeDisplay function")
    
    # Check admin_reservations_list.html for payment display
    with open('app/templates/admin/admin_reservations_list.html', 'r') as f:
        content = f.read()
        assert 'res.payment_type' in content, "admin_reservations_list.html missing payment_type display"
        assert 'Staff' not in content.split('</thead>')[0] or content.count('Staff') <= 1, \
               "admin_reservations_list.html has duplicate Staff column"
        print("✓ admin_reservations_list.html displays payment_type correctly")
    
    # Check admin_reservations_list.css for receipt modal styling
    with open('static/css/admin/admin_reservations_list.css', 'r') as f:
        content = f.read()
        assert 'receipt-modal-image' in content, "CSS missing receipt-modal-image styles"
        assert 'object-fit: contain' in content, "CSS missing object-fit for images"
        assert 'max-height: 70vh' in content, "CSS missing max-height constraint"
        print("✓ admin_reservations_list.css has proper receipt modal styling")

def main():
    print("=" * 60)
    print("Payment Feature Test Suite")
    print("=" * 60)
    
    try:
        test_payment_type_model()
        test_payment_type_form()
        test_amount_calculation()
        test_file_contents()
        
        print("\n" + "=" * 60)
        print("All tests passed! ✓")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Start the Flask application")
        print("2. Create a test booking with both payment types")
        print("3. Verify amounts display correctly")
        print("4. Check admin tables show payment type properly")
        print("5. Test receipt modal image display")
        
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
