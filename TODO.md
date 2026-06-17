# TODO - Add-ons + Remove Pax (Admin/Client)

## Step 1: Locate templates
- [x] Read `high_end_ws_lounge/app/templates/admin/admin_reservations.html` (Admin → New Reservation)
- [ ] Locate Admin → Walk-in Check-in template
- [ ] Locate client Reservation template

## Step 2: Remove “No. of Pax” section
- [ ] Remove pax-counter block from Admin New Reservation
- [ ] Remove pax-counter block from Admin Walk-in Check-in
- [ ] Remove pax-counter block from client Reservation

## Step 3: Add/verify “Predefined Add-ons” UI
- [ ] Ensure dropdown options and quantity input (default 1, min 1, empty => 1)
- [ ] Ensure “Selected Add-on Total: ₱...” real-time calculation

## Step 4: Ensure Extra Chairs multiplication
- [ ] Verify JS sends unit_price=50 per chair for Extra Chairs

## Step 5: Backend persistence
- [ ] Ensure addons JSON submission still reaches `process_reservation_addons` / `process_walkin_addons`
- [ ] Verify backend stores name, quantity, unit_price, subtotal (already in `addons_helper.py`)

## Step 6: Display add-ons in admin/client history & details
- [ ] Update admin Reservation Details template
- [ ] Update admin Walk-in Details template
- [ ] Update Reservation History / Booking History / Reports templates

## Step 7: Regression checks
- [ ] Run tests / basic flows: reservation save, payments, approval, check-in

