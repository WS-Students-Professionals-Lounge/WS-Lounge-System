document.addEventListener('DOMContentLoaded', function() {


    // 2. Open Time Toggle Logic (Existing)
    const openTimeToggle = document.getElementById('open-time-toggle');
    const endTimeInput = document.getElementById('end-time');
    const hiddenOpenTime = document.getElementById('form-open-time');

    if (openTimeToggle && endTimeInput) {
        openTimeToggle.addEventListener('change', function() {
            if (hiddenOpenTime) {
                hiddenOpenTime.checked = this.checked;
            }
            if (this.checked) {
                endTimeInput.style.opacity = "0.5";
                endTimeInput.style.pointerEvents = "none";
                endTimeInput.required = false;
                endTimeInput.value = ""; 
                calculateTotal();
            } else {
                endTimeInput.style.opacity = "1";
                endTimeInput.style.pointerEvents = "auto";
                endTimeInput.required = true;
                calculateTotal();
            }
        });
    }

    // 3. Live Booking Summary & Calculation (New Upgrade)
    const roomSelector = document.getElementById('room-selector');
    const startTimeInput = document.getElementById('start-time');
        const extraFeesSelect = document.getElementById('extra-fees-select');
        // Predefined add-ons UI now uses predefined_addon_name/predefined_addon_qty

    const addonQuantityInput = document.getElementById('addon-quantity');
    const extraFeeTotalInput = document.getElementById('extra-fee-total');
    const summaryContainer = document.getElementById('booking-summary-container');
    const paymentInfoPanel = document.getElementById('payment-info-panel');
    const paymentInfoData = document.getElementById('paymentInfoData');
    const currentUserRoleEl = document.getElementById('currentUserRole');
    const currentUserRole = currentUserRoleEl?.dataset.role || '';
    const receiptUploadSection = document.getElementById('receipt-upload-section');
    const paymentMethodLabel = document.getElementById('payment-method-label');
    const paymentInstructions = document.getElementById('payment-instructions');
    const paymentModal = document.getElementById('payment-modal');
    const paymentModalClose = document.getElementById('payment-modal-close');
    const modalPaymentMethod = document.getElementById('modal-payment-method');
    const modalAccountInfo = document.getElementById('modal-account-info');
    const modalInstructions = document.getElementById('modal-instructions');
    const modalQrImage = document.getElementById('modal-qr-image');
    const paymentDetailsButton = document.getElementById('show-payment-modal');
    const summaryDeposit = document.getElementById('summary-deposit');
    
    // Payment Type Elements
    const paymentTypeSection = document.getElementById('payment-type-section');
    const paymentAmountDisplay = document.getElementById('payment-amount-display');
    const displayTotalAmount = document.getElementById('display-total-amount');
    const displayDownpaymentAmount = document.getElementById('display-downpayment-amount');
    const displayFullpaymentAmount = document.getElementById('display-fullpayment-amount');
    const downpaymentRow = document.getElementById('downpayment-row');
    const fullpaymentRow = document.getElementById('fullpayment-row');
    const receiptAmountLabel = document.getElementById('receipt-amount-label');
    const paymentTypeRadios = document.querySelectorAll('input[name="payment_type"]');

    function initializePaymentInfo() {
        if (paymentInfoData) {
            try {
                window.paymentInfo = JSON.parse(paymentInfoData.textContent || '{}');
            } catch (err) {
                console.warn('Invalid paymentInfo JSON:', err);
                window.paymentInfo = {};
            }
        }
    }

    async function loadPaymentInfo() {
        initializePaymentInfo();
        if (window.paymentInfo && Object.keys(window.paymentInfo).length) {
            updatePaymentInfo();
            return;
        }
        try {
            const res = await fetch('/api/payment-info');
            if (!res.ok) throw new Error('Failed to fetch payment info');
            const data = await res.json();
            window.paymentInfo = data;
            updatePaymentInfo();
        } catch (error) {
            console.warn('Unable to load payment info:', error);
        }
    }
    const depositNote = document.querySelector('.deposit-note');
    const paymentRadios = document.querySelectorAll('input[name="payment_method"]');

    // Summary Display Elements
    const summaryRoom = document.getElementById('summary-room');
    const summaryHours = document.getElementById('summary-hours');
    const summaryTotal = document.getElementById('summary-total');

    function updatePaymentTypeDisplay() {
        const selectedType = Array.from(paymentTypeRadios).find((radio) => radio.checked);
        if (!selectedType) return;

        const paymentType = selectedType.value;
        
        // Get current total from summaryTotal (it's already calculated)
        const totalText = summaryTotal.textContent;
        const totalAmount = parseFloat(totalText.replace(/,/g, '')) || 0;

        displayTotalAmount.textContent = '₱' + totalAmount.toLocaleString(undefined, {minimumFractionDigits: 2});
        
        if (paymentType === 'Downpayment') {
            downpaymentRow.classList.remove('d-none');
            fullpaymentRow.classList.add('d-none');
            const downpaymentAmount = (totalAmount * 0.5).toLocaleString(undefined, {minimumFractionDigits: 2});
            displayDownpaymentAmount.textContent = '₱' + downpaymentAmount;
            receiptAmountLabel.textContent = 'downpayment (50%)';
        } else {
            downpaymentRow.classList.add('d-none');
            fullpaymentRow.classList.remove('d-none');
            const fullpaymentAmount = totalAmount.toLocaleString(undefined, {minimumFractionDigits: 2});
            displayFullpaymentAmount.textContent = '₱' + fullpaymentAmount;
            receiptAmountLabel.textContent = 'full payment';
        }
    }

    function updatePaymentInfo() {
        const selected = Array.from(paymentRadios).find((radio) => radio.checked);
        if (!selected) {
            paymentInfoPanel.classList.add('d-none');
            receiptUploadSection.classList.add('d-none');
            paymentTypeSection.classList.add('d-none');
            paymentAmountDisplay.classList.add('d-none');
            return;
        }

        const method = selected.value;
        const info = window.paymentInfo && window.paymentInfo[method];
        paymentInfoPanel.classList.remove('d-none');
        receiptUploadSection.classList.remove('d-none');
        paymentTypeSection.classList.remove('d-none');
        paymentAmountDisplay.classList.remove('d-none');
        
        paymentMethodLabel.textContent = `${method} Payment`;
        paymentInstructions.textContent = info
            ? 'Click "View Payment QR & Details" to see the account, QR code, and payment instructions.'
            : 'No payment settings are configured for this method. Please contact admin.';

        if (paymentDetailsButton) {
            paymentDetailsButton.classList.remove('d-none');
        }

        if (modalPaymentMethod && modalAccountInfo && modalInstructions) {
            modalPaymentMethod.textContent = `${method} Payment Details`;
            modalAccountInfo.textContent = info
                ? `${info.account_name || method} • ${info.account_number || 'No number configured yet'}`
                : `No account configured for ${method}.`;
            modalInstructions.textContent = info
                ? info.instructions || `Transfer the payment to the ${method} account and upload the receipt.`
                : 'Please contact admin for payment details.';

            if (info && info.qr_image) {
                modalQrImage.classList.remove('d-none');
                modalQrImage.src = info.qr_image;
            } else {
                modalQrImage.classList.add('d-none');
                modalQrImage.src = '';
            }
        }
        
        updatePaymentTypeDisplay();
    }

    function openPaymentModal() {
        if (!paymentModal) return;
        paymentModal.classList.remove('d-none');
    }

    function closePaymentModal() {
        if (!paymentModal) return;
        paymentModal.classList.add('d-none');
    }

    if (paymentDetailsButton) {
        paymentDetailsButton.addEventListener('click', openPaymentModal);
    }

    if (paymentModalClose) {
        paymentModalClose.addEventListener('click', closePaymentModal);
    }

    if (paymentModal) {
        paymentModal.addEventListener('click', function(e) {
            if (e.target === paymentModal) {
                closePaymentModal();
            }
        });
    }

    function calculateTotal() {
        const selectedRoom = roomSelector.options[roomSelector.selectedIndex];
        const startVal = startTimeInput.value;
        const endVal = endTimeInput.value;


        const addonPrice = parseFloat(extraFeesSelect.value) || 0;
        const quantity = Math.max(0, parseInt(addonQuantityInput.value) || 0);
        const extraFeeTotal = addonPrice * quantity;

        if (extraFeeTotalInput) {
            extraFeeTotalInput.value = extraFeeTotal.toFixed(2);
        }

        if (selectedRoom.value && startVal && (endVal || openTimeToggle.checked)) {
            const rate = parseFloat(selectedRoom.getAttribute('data-rate'));
            let hours = 1;

            if (!openTimeToggle.checked && endVal) {
                const start = new Date(startVal);
                const end = new Date(endVal);
                const diffMs = end - start;
                const diffHrs = diffMs / (1000 * 60 * 60);
                hours = diffHrs > 0 ? diffHrs : 1;
            }

            const total = (rate * hours) + extraFeeTotal;

            const addonLabel = extraFeesSelect.options[extraFeesSelect.selectedIndex].text;
            const addonSummary = (addonPrice > 0 && quantity > 0)
                ? `${quantity} x ${addonLabel.replace(/\s*\(.*\)/, '')}`
                : 'None';

            summaryRoom.textContent = selectedRoom.text.split('(')[0];
            summaryHours.textContent = hours.toFixed(1);
            document.getElementById('summary-addons').textContent = addonSummary;
            summaryTotal.textContent = total.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
            const deposit = (total * 0.5).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2});
            if (summaryDeposit) {
                summaryDeposit.textContent = `₱${deposit}`;
            }
            if (depositNote) {
                depositNote.classList.remove('d-none');
            }
            summaryContainer.style.display = 'block';
            
            updatePaymentTypeDisplay();
        } else {
            summaryContainer.style.display = 'none';
            if (depositNote) {
                depositNote.classList.add('d-none');
            }
            paymentAmountDisplay.classList.add('d-none');
        }
    }

    // Listeners for Live Calculation
    [roomSelector, startTimeInput, endTimeInput, extraFeesSelect, addonQuantityInput].forEach(el => {
        if (!el) return;
        el.addEventListener('change', calculateTotal);
    });
    if (addonQuantityInput) {
        addonQuantityInput.addEventListener('input', calculateTotal);
    }
    if (extraFeesSelect && addonQuantityInput) {
        extraFeesSelect.addEventListener('change', function () {
            const selectedPrice = parseFloat(this.value) || 0;
            if (selectedPrice > 0 && (parseInt(addonQuantityInput.value) || 0) < 1) {
                addonQuantityInput.value = 1;
            }
            if (selectedPrice === 0) {
                addonQuantityInput.value = 0;
            }
            calculateTotal();
        });
    }

    // Payment selection listeners
    if (paymentRadios && paymentRadios.length) {
        paymentRadios.forEach((radio) => {
            radio.addEventListener('change', updatePaymentInfo);
        });
    }
    
    // Payment type selection listeners
    if (paymentTypeRadios && paymentTypeRadios.length) {
        paymentTypeRadios.forEach((radio) => {
            radio.addEventListener('change', updatePaymentTypeDisplay);
        });
    }
    updatePaymentInfo();
    loadPaymentInfo();

    // 4. Table Filtering Logic (New Upgrade)
    const filterDate = document.getElementById('filter-date');
    const filterStatus = document.getElementById('filter-status');
    const bookingRows = document.querySelectorAll('.booking-row');

    function filterTable() {
        const dateVal = filterDate.value;
        const statusVal = filterStatus.value.toLowerCase();

        bookingRows.forEach(row => {
            const rowDate = row.getAttribute('data-date'); // Expected format: YYYY-MM-DD...
            const rowStatus = row.getAttribute('data-status').toLowerCase();
            
            const matchesDate = !dateVal || rowDate.includes(dateVal);
            const matchesStatus = !statusVal || rowStatus === statusVal;

            row.style.display = (matchesDate && matchesStatus) ? '' : 'none';
        });
    }

    if (filterDate && filterStatus) {
        filterDate.addEventListener('input', filterTable);
        filterStatus.addEventListener('change', filterTable);
    }

    // 5. CSV Export Logic (New Upgrade)
    const exportBtn = document.getElementById('export-csv');
    if (exportBtn) {
        exportBtn.addEventListener('click', function() {
            let csv = 'Room,Start Time,End Time,Status\n';
            const rows = document.querySelectorAll('.booking-table tbody tr:not([style*="display: none"])');
            
            rows.forEach(row => {
                const cols = row.querySelectorAll('td');
                if (cols.length >= 4) {
                    const rowData = Array.from(cols).map(col => `"${col.textContent.trim()}"`);
                    csv += rowData.join(',') + '\n';
                }
            });

            const blob = new Blob([csv], { type: 'text/csv' });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.setAttribute('hidden', '');
            a.setAttribute('href', url);
            a.setAttribute('download', 'bookings_export.csv');
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
        });
    }

    // 6. Booking Form Submission with Confirmation Modal
    const bookingForm = document.getElementById('booking-form');
    const submitBtn = document.getElementById('submit-booking');
    
    if (submitBtn && bookingForm) {
        submitBtn.addEventListener('click', function(e) {
            e.preventDefault();

            // Prevent non-members from reserving on client-side
            if (currentUserRole && currentUserRole !== 'member') {
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'warning',
                        title: 'Members Only',
                        text: 'Only members can make reservations. Please login with a member account.',
                        confirmButtonColor: '#82cae8'
                    });
                } else {
                    if (typeof showToast === 'function') showToast('Only members can make reservations.', 'warning');
                }
                return;
            }
            
            // Validate required fields
            const customerName = document.querySelector('input[name="customer_name"]')?.value?.trim();
            const contactNumber = document.querySelector('input[name="contact_number"]')?.value?.trim();
            const roomId = roomSelector?.value;
            const startTime = startTimeInput?.value;
            const endTime = endTimeInput?.value;
            const isOpenTime = openTimeToggle?.checked;
            const paymentMethod = document.querySelector('input[name="payment_method"]:checked')?.value;
            const paymentType = document.querySelector('input[name="payment_type"]:checked')?.value;
            const receiptUpload = document.getElementById('receipt-upload');
            
            if (!customerName || !contactNumber || !roomId || !startTime || (!endTime && !isOpenTime)) {
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'warning',
                        title: 'Incomplete Information',
                        text: 'Please fill in all required fields.',
                        confirmButtonColor: '#82cae8'
                    });
                } else {
                    if (typeof showToast === 'function') showToast('Please fill in all required fields.', 'warning');
                    showToast('Please fill in all required fields.', 'warning');
                }
                return;
            }
            
            if (!paymentMethod) {
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'warning',
                        title: 'Payment Method Required',
                        text: 'Please select a payment method.',
                        confirmButtonColor: '#82cae8'
                    });
                } else {
                    if (typeof showToast === 'function') showToast('Please select a payment method.', 'warning');
                    showToast('Please select a payment method.', 'warning');
                }
                return;
            }
            
            if (!paymentType) {
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'warning',
                        title: 'Payment Type Required',
                        text: 'Please select a payment type.',
                        confirmButtonColor: '#82cae8'
                    });
                } else {
                    if (typeof showToast === 'function') showToast('Please select a payment type.', 'warning');
                    showToast('Please select a payment type.', 'warning');
                }
                return;
            }
            
            if (receiptUpload && !receiptUpload.classList.contains('d-none') && !receiptUpload.value) {
                if (typeof Swal !== 'undefined') {
                    Swal.fire({
                        icon: 'warning',
                        title: 'Receipt Required',
                        text: 'Please upload your payment receipt.',
                        confirmButtonColor: '#82cae8'
                    });
                } else {
                    if (typeof showToast === 'function') showToast('Please upload your payment receipt.', 'warning');
                    showToast('Please upload your payment receipt.', 'warning');
                }
                return;
            }
            
            // Show confirmation modal with booking details
            const selectedRoom = roomSelector.options[roomSelector.selectedIndex];
            const roomName = selectedRoom.text.split('(')[0].trim();
            const totalAmount = summaryTotal.textContent;
            
            // Use unified confirmAction helper (SweetAlert2 or DOM fallback)
            confirmAction('Confirm Reservation?', `Confirming reservation for ${customerName} in ${roomName}. Total: ₱${totalAmount}`, 'Yes, Reserve it!', 'Cancel')
                .then(confirmed => {
                    if (confirmed) {
                        // Use requestSubmit if available (preserves form validation),
                        // otherwise call the native submit function directly because
                        // `bookingForm.submit` may be shadowed by an input named "submit".
                        if (typeof bookingForm.requestSubmit === 'function') {
                            bookingForm.requestSubmit();
                        } else {
                            HTMLFormElement.prototype.submit.call(bookingForm);
                        }
                    }
                });
        });
    }

    // 7. Simple Alert Auto-dismiss (Existing)
    const alerts = document.querySelectorAll('.modern-alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.opacity = '0';
            setTimeout(() => { alert.style.display = 'none'; }, 500);
        }, 5000);
    });
});