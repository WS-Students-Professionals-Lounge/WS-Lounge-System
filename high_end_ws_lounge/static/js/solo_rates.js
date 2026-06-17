document.addEventListener("DOMContentLoaded", () => {
    const modal = document.getElementById("plan-selection-modal");
    const planTitle = document.getElementById("modal-plan-title");
    const planPrice = document.getElementById("modal-plan-price");
    const paymentDetails = document.getElementById("modal-payment-details");
    const accountName = document.getElementById("modal-account-name");
    const accountNumber = document.getElementById("modal-account-number");
    const instructions = document.getElementById("modal-instructions");
    const qrWrap = document.getElementById("modal-qr-wrap");
    const qrImage = document.getElementById("modal-qr-image");
    const receiptInput = document.getElementById("modal-receipt");
    const termsCheckbox = document.getElementById("modal-terms");
    const errorContainer = document.getElementById("modal-error");
    const submitButton = document.getElementById("modal-submit");
    const cancelButton = document.getElementById("modal-cancel");
    const closeButton = document.getElementById("plan-modal-close");
    const paymentMethodRadios = Array.from(document.querySelectorAll("input[name='modal_payment_method']"));

    let selectedPlan = null;
    let paymentInfo = {};
    let selectedMethod = null;

    async function loadPaymentInfo() {
        try {
            const response = await fetch('/api/payment-info');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: Unable to load payment instructions.`);
            }
            paymentInfo = await response.json();
            console.log('Payment info loaded:', paymentInfo);
            
            // Validate that payment methods have QR codes
            for (const method in paymentInfo) {
                const info = paymentInfo[method];
                if (!info.qr_image) {
                    console.warn(`Warning: ${method} payment method has no QR code configured.`);
                } else {
                    console.log(`✓ ${method} QR code: ${info.qr_image}`);
                }
            }
        } catch (err) {
            console.error('Error loading payment info:', err);
            errorContainer.textContent = 'Unable to load payment instructions. Please refresh the page and try again.';
        }
    }

    function showModal() {
        if (!selectedPlan) return;
        planTitle.textContent = `Purchase ${selectedPlan.name}`;
        planPrice.textContent = selectedPlan.price;
        paymentDetails.classList.add('d-none');
        qrWrap.classList.add('d-none');
        accountName.textContent = '';
        accountNumber.textContent = '';
        instructions.textContent = '';
        receiptInput.value = '';
        termsCheckbox.checked = false;
        errorContainer.textContent = '';
        selectedMethod = null;
        paymentMethodRadios.forEach(radio => radio.checked = false);
        modal.classList.remove('d-none');
        modal.setAttribute('aria-hidden', 'false');
        // Prevent background scroll while modal is open
        document.body.style.overflow = 'hidden';
    }

    function hideModal() {
        modal.classList.add('d-none');
        modal.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
        selectedPlan = null;
        selectedMethod = null;
    }

    function updatePaymentInstructions() {
        const method = selectedMethod;
        
        // Wait for payment info to load if not ready yet
        if (Object.keys(paymentInfo).length === 0) {
            paymentDetails.classList.add('d-none');
            errorContainer.textContent = 'Loading payment information... Please wait.';
            return;
        }
        
        if (!method || !paymentInfo[method]) {
            paymentDetails.classList.add('d-none');
            errorContainer.textContent = 'Payment method not available.';
            return;
        }
        
        const info = paymentInfo[method];
        errorContainer.textContent = '';
        paymentDetails.classList.remove('d-none');
        accountName.textContent = info.account_name || 'Not available';
        accountNumber.textContent = info.account_number || 'Not available';
        instructions.textContent = info.instructions || 'Follow the selected payment method instructions.';
        
        if (info.qr_image) {
            qrImage.src = info.qr_image;
            qrImage.alt = `${method} QR Code`;
            qrWrap.classList.remove('d-none');
        } else {
            qrWrap.classList.add('d-none');
        }
    }

    function getSelectedPaymentMethod() {
        const radio = document.querySelector("input[name='modal_payment_method']:checked");
        return radio ? radio.value : null;
    }

    function validateModal() {
        if (!selectedPlan) {
            errorContainer.textContent = 'No plan selected.';
            return false;
        }
        selectedMethod = getSelectedPaymentMethod();
        if (!selectedMethod) {
            errorContainer.textContent = 'Please choose a payment method.';
            return false;
        }
        if (!receiptInput.files || receiptInput.files.length === 0) {
            errorContainer.textContent = 'Please upload your payment receipt.';
            return false;
        }
        if (!termsCheckbox.checked) {
            errorContainer.textContent = 'You must agree to the terms before submitting.';
            return false;
        }
        return true;
    }

    async function submitPayment() {
        if (!validateModal()) return;

        submitButton.disabled = true;
        errorContainer.textContent = '';

        const formData = new FormData();
        formData.append('plan_name', selectedPlan.name);
        formData.append('payment_method', selectedMethod);
        formData.append('receipt_image', receiptInput.files[0]);

        try {
            const response = await fetch('/api/submit-solo-payment', {
                method: 'POST',
                body: formData,
            });
            const data = await response.json();
            if (!response.ok || !data.success) {
                throw new Error(data.message || 'Submission failed.');
            }
            window.location.href = window.location.pathname;
        } catch (err) {
            errorContainer.textContent = err.message || 'Unable to submit payment.';
            console.error(err);
        } finally {
            submitButton.disabled = false;
        }
    }

    document.querySelectorAll('.purchase-plan-btn').forEach(button => {
        button.addEventListener('click', () => {
            selectedPlan = {
                name: button.dataset.planName,
                price: button.dataset.planPrice,
            };
            showModal();
        });
    });

    paymentMethodRadios.forEach(radio => {
        radio.addEventListener('change', () => {
            selectedMethod = radio.value;
            updatePaymentInstructions();
        });
    });

    cancelButton.addEventListener('click', hideModal);
    closeButton.addEventListener('click', hideModal);
    submitButton.addEventListener('click', submitPayment);
    modal.addEventListener('click', (event) => {
        if (event.target === modal) {
            hideModal();
        }
    });

    function initMembershipCountdown() {
        const countdownEl = document.getElementById('membership-countdown');
        if (!countdownEl) return;

        const expiryISO = countdownEl.dataset.expiry;
        if (!expiryISO) {
            countdownEl.textContent = 'Not available';
            return;
        }

        const expiryTime = new Date(expiryISO).getTime();
        const intervalId = setInterval(() => {
            const now = Date.now();
            const distance = expiryTime - now;
            if (distance <= 0) {
                countdownEl.textContent = 'Expired';
                clearInterval(intervalId);
                return;
            }

            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);

            countdownEl.textContent = `${days}d ${hours.toString().padStart(2, '0')}h ${minutes.toString().padStart(2, '0')}m ${seconds.toString().padStart(2, '0')}s`;
        }, 1000);
    }

    initMembershipCountdown();
    
    // Load payment info and ensure it's ready before page is fully interactive
    loadPaymentInfo().catch(err => {
        console.error('Failed to load payment info:', err);
    });
});
