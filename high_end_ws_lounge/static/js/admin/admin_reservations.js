document.addEventListener('DOMContentLoaded', function() {
    const resForm = document.getElementById('resForm');
    const customerName = document.getElementById('customer_name');
    const contactNumber = document.getElementById('contact_number');
    const roomId = document.getElementById('room_id');

    const startTime = document.getElementById('start_time');
    const endTime = document.getElementById('end_time');
    const extraFeeInput = document.getElementById('extra_fee_input');
    const openTimeToggle = document.getElementById('openTimeToggle');
    const discountSelect = document.getElementById('f-discount');

    const previewName = document.getElementById('preview_name');
    const previewContact = document.getElementById('preview_contact');
    const previewRoom = document.getElementById('preview_room');
    const previewDate = document.getElementById('preview_date');

    const previewStart = document.getElementById('preview_start');
    const previewEnd = document.getElementById('preview_end');

    const previewDuration = document.getElementById('preview_duration');
    const previewExtra = document.getElementById('preview_extra');
    const previewTotal = document.getElementById('preview_total');
    const hiddenTotalPrice = document.getElementById('hidden_total_price');

    let openTimeInterval;
    let secondsElapsed = 0;

    function formatDateTime(value) {
        if (!value) return '----';
        const date = new Date(value);
        if (Number.isNaN(date.getTime())) return value;
        return date.toLocaleString(undefined, {
            year: 'numeric',
            month: 'short',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
        });
    }

    function updateSummary() {
        if (previewName) previewName.innerText = customerName.value.trim() || '----';
        if (previewContact) previewContact.innerText = contactNumber.value.trim() || '----';


        const extraFee = parseFloat(extraFeeInput.value) || 0;
        const addonSubtotal = parseFloat(document.getElementById('addon_subtotal')?.value || 0) || 0;
        const discountPercent = discountSelect ? parseFloat(discountSelect.value) : 0;
        if (previewExtra) previewExtra.innerText = '₱' + extraFee.toFixed(2);
        if (document.getElementById('preview_addon_subtotal')) {
            document.getElementById('preview_addon_subtotal').innerText = '₱' + addonSubtotal.toFixed(2);
        }

        const selectedOption = roomId.options[roomId.selectedIndex];
        const selectedRoomText = selectedOption ? selectedOption.text : '';
        if (previewRoom) previewRoom.innerText = selectedRoomText.split(' (')[0] || '----';

        if (previewDate) previewDate.innerText = formatDateTime(startTime.value);
        if (previewStart) previewStart.innerText = formatDateTime(startTime.value);

        let duration = 0;
        if (openTimeToggle && openTimeToggle.checked) {
            if (previewEnd) previewEnd.innerText = 'OPEN TIME';
            duration = 1;
        } else if (endTime && endTime.value) {
            if (previewEnd) previewEnd.innerText = formatDateTime(endTime.value);
            const start = new Date(startTime.value);
            const end = new Date(endTime.value);
            duration = (end - start) / (1000 * 60 * 60);
            if (duration <= 0) duration += 24;
        }

        if (previewDuration) {
            previewDuration.innerText = openTimeToggle && openTimeToggle.checked
                ? 'Open Time'
                : duration > 0
                ? duration.toFixed(1) + ' Hr/s'
                : '----';
        }

        const rateMatch = selectedRoomText.match(/₱(\d+)/);
        const baseRate = rateMatch ? parseFloat(rateMatch[1]) : 0;
        let total = 0;
        if (openTimeToggle && openTimeToggle.checked) {
            let roomCost = baseRate * (1 - discountPercent);
            total = roomCost + extraFee + addonSubtotal;
        } else {
            let roomCost = baseRate * duration;
            roomCost = roomCost * (1 - discountPercent);
            total = roomCost + extraFee + addonSubtotal;
        }

        if (previewTotal) {
            previewTotal.innerText = '₱' + total.toLocaleString(undefined, { minimumFractionDigits: 2 });
        }
        if (hiddenTotalPrice) {
            hiddenTotalPrice.value = total.toFixed(2);
        }
    }

    // Make updateSummary available globally so Add-ons widgets can call it
    window.updateTotalPrice = updateSummary;


    function startRunningTimer() {
        secondsElapsed = 0;
        clearInterval(openTimeInterval);
        openTimeInterval = setInterval(() => {
            secondsElapsed++;
            const hrs = Math.floor(secondsElapsed / 3600);
            const mins = Math.floor((secondsElapsed % 3600) / 60);
            const secs = secondsElapsed % 60;
            const timeDisplay = `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
            if (previewDuration) previewDuration.innerText = timeDisplay;
        }, 1000);
    }

    function updateOpenTimeToggleState() {
        if (!roomId || !openTimeToggle) return;
        openTimeToggle.disabled = false;
        openTimeToggle.style.cursor = 'pointer';
        if (openTimeToggle.parentElement) openTimeToggle.parentElement.style.opacity = '1';
        updateSummary();
    }

    if (openTimeToggle) {
        openTimeToggle.addEventListener('change', function() {
            if (this.disabled) {
                this.checked = false;
                return;
            }
            if (this.checked) {
                // Preserve any user-selected start time. Only default to 'now'
                // when the start time field is empty to avoid unexpected changes.
                if (!startTime.value) {
                    const now = new Date();
                    startTime.value = now.toISOString().slice(0, 16);
                }
                endTime.disabled = true;
                endTime.value = '';
                endTime.style.opacity = '0.5';
                endTime.required = false;
                startRunningTimer();
            } else {
                endTime.disabled = false;
                endTime.style.opacity = '1';
                endTime.required = true;
                clearInterval(openTimeInterval);
                if (previewDuration) previewDuration.innerText = '----';
            }
            updateSummary();
        });
    }











    [customerName, contactNumber, roomId, startTime, endTime, extraFeeInput, discountSelect].forEach(el => {




        if (!el) return;
        const eventType = el.tagName === 'SELECT' ? 'change' : 'input';
        el.addEventListener(eventType, function() {
            updateSummary();
            if (el === roomId) updateOpenTimeToggleState();
        });
    });

    setTimeout(updateOpenTimeToggleState, 100);

    function confirmReservation() {
        if (!customerName.value.trim() || !startTime.value.trim() || (!endTime.value.trim() && !openTimeToggle.checked)) {
            Swal.fire({
                icon: 'warning',
                title: 'Incomplete Data',
                text: 'Please fill in the Customer Name and complete the reservation date/time.',
                confirmButtonColor: '#82cae8'
            });
            return;
        }

        updateSummary();
        const checkUrl = `/admin/check_availability?room_id=${roomId.value}&start=${encodeURIComponent(startTime.value)}&end=${encodeURIComponent(endTime.value || '')}&open_time=${openTimeToggle.checked}`;

        fetch(checkUrl)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'conflict') {
                    Swal.fire({
                        icon: 'error',
                        title: 'Schedule Conflict',
                        text: data.message || 'The selected room is already booked for the requested time slot.',
                        confirmButtonColor: '#d90429'
                    });
                } else {
                    Swal.fire({
                        title: 'Save Reservation?',
                        text: `Confirming reservation for ${customerName.value}. Total: ${previewTotal.innerText}`,
                        icon: 'question',
                        showCancelButton: true,
                        confirmButtonColor: '#82cae8',
                        cancelButtonColor: '#d90429',
                        confirmButtonText: 'Yes, Save it!'
                    }).then(result => {
                        if (result.isConfirmed) {
                            if (openTimeToggle.checked) {
                                endTime.disabled = false;
                                endTime.value = '';
                            }
                            resForm.submit();
                        }
                    });
                }
            })
            .catch(error => {
                console.error('Error checking availability:', error);
                resForm.submit();
            });
    }

    const confirmButton = document.getElementById('confirmReservation');
    const cancelButton = document.getElementById('cancelReservation');

    if (confirmButton) {
        confirmButton.addEventListener('click', confirmReservation);
    }

    if (cancelButton) {
        cancelButton.addEventListener('click', () => window.location.reload());
    }

    updateSummary();
});