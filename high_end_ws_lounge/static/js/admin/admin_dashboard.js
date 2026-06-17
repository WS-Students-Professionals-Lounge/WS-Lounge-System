const socket = (typeof io !== 'undefined') ? io() : null;

document.addEventListener('DOMContentLoaded', function() {
    console.log("Admin Dashboard Modern UI Active", socket ? "+ SocketIO" : "(no socket)");

    // Welcome typewriter effect (mirror of member dashboard)
    const adminNameSpan = document.getElementById('adminUserName');
    if (adminNameSpan) {
        const fullText = adminNameSpan.textContent;
        adminNameSpan.textContent = '';
        let i = 0;
        let isDeleting = false;

        function typeAdmin() {
            const currentText = isDeleting ? fullText.substring(0, i--) : fullText.substring(0, i++);
            adminNameSpan.textContent = currentText;

            if (!isDeleting && i > fullText.length) {
                setTimeout(() => { isDeleting = true; typeAdmin(); }, 3000);
            } else if (isDeleting && i < 0) {
                isDeleting = false;
                i = 0;
                setTimeout(typeAdmin, 500);
            } else {
                setTimeout(typeAdmin, isDeleting ? 50 : 100);
            }
        }
        setTimeout(typeAdmin, 800);
    }

    if (socket) {
        socket.on('new_reservation', function(data) {
            console.log('New reservation via socket:', data);
            // Only refresh dashboard for active sessions
            try {
                const activeStatuses = ['Checked-In', 'Walk-in', 'Active'];
                if (data && activeStatuses.includes(data.status)) {
                    try { showToast(`Now Active: ${data.customer} in ${data.room} (ID: ${data.id})`, 'info'); } catch (e) {}
                    location.reload();
                } else {
                    console.log('Reservation update (non-active) ignored for full reload:', data.status);
                }
            } catch (e) {
                console.error('Socket handler error', e);
            }
        });
    }

    function formatTime(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return `(${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')})`;
    }

    function updateTimers() {
        const timers = document.querySelectorAll('.timer-text');
        const cards = document.querySelectorAll('.room-card');
        const now = new Date();
        let newlyExpired = false;

        // 1. Update Live Timers (Count up for Open Time)
        timers.forEach(timer => {
            const startStr = timer.getAttribute('data-starttime');
            if (!startStr) {
                timer.textContent = "(00:00:00)";
                return;
            }
            const startTime = new Date(startStr);
            const elapsed = Math.max(0, Math.floor((now - startTime) / 1000));
            
            if (elapsed < 2) {
                timer.textContent = formatTime(0);
            } else {
                timer.textContent = formatTime(elapsed);
            }
        });

        // 2. Check for Expired Sessions (For Fixed Time)
        cards.forEach(card => {
            const endStr = card.getAttribute('data-endtime');
            const isOpenTime = card.getAttribute('data-isopentime') === 'true';

            if (endStr && !isOpenTime) {
                const endTime = new Date(endStr);
                if (now > endTime) {
                    if (!card.classList.contains('session-expired')) {
                        card.classList.add('session-expired');
                        newlyExpired = true;
                    }
                }
            }
        });

        // Move expired cards to top if new ones were detected
        if (newlyExpired) {
            sortExpiredCards();
        }
    }

    // Function to move expired cards to the top of their grid
    function sortExpiredCards() {
        const grids = document.querySelectorAll('.room-grid, .common-area-grid');
        grids.forEach(grid => {
            const cards = Array.from(grid.querySelectorAll('.room-card'));
            cards.sort((a, b) => {
                const aExpired = a.classList.contains('session-expired') ? 1 : 0;
                const bExpired = b.classList.contains('session-expired') ? 1 : 0;
                return bExpired - aExpired;
            });
            // Re-append in sorted order
            cards.forEach(card => grid.appendChild(card));
        });
    }

    function updateClock() {
        const clockEl = document.getElementById('dashboardClock');
        if (!clockEl) return;
        const now = new Date();
        let hours = now.getHours();
        const minutes = now.getMinutes().toString().padStart(2, '0');
        const seconds = now.getSeconds().toString().padStart(2, '0');
        const ampm = hours >= 12 ? 'PM' : 'AM';
        hours = hours % 12 || 12;
        clockEl.textContent = `${hours.toString().padStart(2, '0')}:${minutes}:${seconds} ${ampm}`;
    }

    const searchInput = document.getElementById('dashboardSearch');
    const dashboardCards = document.querySelectorAll('.room-card'); 
    const noResultsEl = document.getElementById('noSearchResults');

    function filterDashboardCards() {
        const query = searchInput?.value.trim().toLowerCase() || '';
        let visibleCount = 0;

        dashboardCards.forEach(card => {
            const customer = (card.dataset.customer || '').toLowerCase();
            const room = (card.dataset.room || '').toLowerCase();
            const matches = !query || customer.includes(query) || room.includes(query);
            card.style.display = matches ? '' : 'none';
            if (matches) visibleCount += 1;
        });

        if (noResultsEl) {
            noResultsEl.style.display = visibleCount === 0 ? 'block' : 'none';
        }
    }

    if (searchInput) {
        searchInput.addEventListener('input', filterDashboardCards);
    }

    function bindAdminActionButtons() {
        document.body.addEventListener('click', (event) => {
            const addTimeBtn = event.target.closest('.add-time-btn');
            if (addTimeBtn) {
                event.preventDefault();
                const resId = addTimeBtn.dataset.reservationId;
                if (resId) {
                    openExtendTimeModal(resId);
                }
                return;
            }

            const endSessionBtn = event.target.closest('.end-session-btn');
            if (endSessionBtn) {
                event.preventDefault();
                const resId = endSessionBtn.dataset.reservationId;
                if (resId) {
                    handleCheckout(resId);
                }
            }
        });
    }

    bindAdminActionButtons();

    function formatDuration(seconds) {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = seconds % 60;
        return `${hours.toString().padStart(2, '0')}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    function renderOccupants(list) {
        const container = document.getElementById('occupantsList');
        const countEl = document.getElementById('occupantsCount');

        if (!container || !countEl) {
            return;
        }

        container.innerHTML = '';
        countEl.textContent = list.length.toString();

        if (!list.length) {
            const empty = document.createElement('p');
            empty.className = 'no-occupants';
            empty.textContent = 'No active common area occupants.';
            container.appendChild(empty);
            return;
        }

        list.forEach(member => {
            const item = document.createElement('div');
            item.className = 'occupant-item';
            item.innerHTML = `
                <div class="occupant-name">${member.name}</div>
                <div class="occupant-time">Checked in: ${member.formatted_check_in || 'N/A'}</div>
                <div class="occupant-elapsed">Time Used: <span class="time-used" data-starttime="${member.check_in_time}">00:00:00</span></div>
            `;
            container.appendChild(item);
        });

        updateOccupantTimers();
    }

    function updateOccupantTimers() {
        const now = new Date();
        document.querySelectorAll('.time-used').forEach(el => {
            const startTime = new Date(el.dataset.starttime);
            if (isNaN(startTime)) {
                el.textContent = '00:00:00';
                return;
            }
            const elapsedSeconds = Math.max(0, Math.floor((now - startTime) / 1000));
            el.textContent = formatDuration(elapsedSeconds);
        });
    }

    function fetchCommonAreaOccupants() {
        fetch('/admin/api/dashboard/common-area-occupants')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success' && Array.isArray(data.occupants)) {
                    renderOccupants(data.occupants);
                }
            })
            .catch(err => {
                console.error('Failed to load common area occupants', err);
            });
    }

    fetchCommonAreaOccupants();
    setInterval(fetchCommonAreaOccupants, 10000);
    setInterval(updateOccupantTimers, 1000);

    // End Session Button Logic
    window.handleCheckout = function(resId) {
        // Updated selector to be more robust
        const btn = document.querySelector(`.end-session-btn[data-reservation-id="${resId}"]`);
        if (!btn) {
            console.error("End Session button not found for ID:", resId);
            return;
        }

        const customerName = btn.dataset.customerName || 'Customer';
        const roomName = btn.dataset.roomName || 'Room';
        
        const storedTotal = parseFloat(btn.getAttribute('data-total-amount')) || 0;
        const rate = parseFloat(btn.getAttribute('data-room-rate')) || 0;
        const extra = parseFloat(btn.getAttribute('data-extra-fee')) || 0;
        const startStr = btn.getAttribute('data-start-time');
        const isOpenTime = btn.getAttribute('data-is-open-time') === 'true';
        
        let total = 0;
        let displayDuration = "";

        // CHECKOUT LOGIC:
        if (!isOpenTime) {
            total = storedTotal.toFixed(2);
            displayDuration = "Fixed Session (Original Time)";
        } 
        // If Open Time: Calculate based on CURRENT time
        else if (isOpenTime && startStr) {
            const start = new Date(startStr);
            const now = new Date();
            const diffMs = Math.max(60000, now - start);
            const hours = Math.ceil(diffMs / (1000 * 60 * 60)); 
            total = (hours * rate + extra).toFixed(2);
            displayDuration = `${(diffMs / 60000).toFixed(0)} mins (${hours} hr/s)`;
        } else {
            total = (rate + extra).toFixed(2);
            displayDuration = "Fixed Session";
        }
        
        const confirmMsg = `End session for ${customerName} (${roomName})?\n\n` +
                           `Duration: ${displayDuration}\n` +
                           `Total Payable: ₱${total}`;

        confirmAction('End Session?', confirmMsg, 'End Session', 'Cancel').then(confirmed => {
            if (!confirmed) return;
            // Redirect to the backend route to finalize the checkout
            window.location.href = `/admin/walkin_checkout/${resId}?final_bill=${total}`;
        });
    };

    const addTimeModal = document.getElementById('addTimeModal');
    const extendHoursInput = document.getElementById('extendHoursInput');
    const extendCustomerEl = document.getElementById('extendCustomer');
    const extendRoomEl = document.getElementById('extendRoom');
    const extendCurrentEndEl = document.getElementById('extendCurrentEnd');
    const extendOriginalTotalEl = document.getElementById('extendOriginalTotal');
    const extendUpdatedTotalEl = document.getElementById('extendUpdatedTotal');
    const extendRateEl = document.getElementById('extendRate');
    const extendSummaryCustomer = document.getElementById('extendSummaryCustomer');
    const extendSummaryRoom = document.getElementById('extendSummaryRoom');
    const extendSummaryHours = document.getElementById('extendSummaryHours');
    const extendSummaryEnd = document.getElementById('extendSummaryEnd');
    const extendSummaryTotal = document.getElementById('extendSummaryTotal');
    const confirmExtendBtn = document.getElementById('confirmExtendBtn');
    const closeExtendModalBtn = document.getElementById('closeExtendModalBtn');

    let activeExtendReservation = null;

    function formatCurrency(value) {
        return `₱${parseFloat(value || 0).toFixed(2)}`;
    }

    function formatDateTime(date) {
        return date.toLocaleTimeString(undefined, {
            hour: '2-digit',
            minute: '2-digit',
            hour12: true,
        });
    }

    function closeExtendModal() {
        if (addTimeModal) {
            addTimeModal.classList.remove('active');
        }
        activeExtendReservation = null;
    }

    function updateExtendModalPreview() {
        if (!activeExtendReservation || !extendHoursInput) return;

        const addedHours = Math.max(1, parseInt(extendHoursInput.value, 10) || 1);
        const originalTotal = parseFloat(activeExtendReservation.currentTotal || 0);
        const rate = parseFloat(activeExtendReservation.roomRate || 0);
        const extraTotal = originalTotal + addedHours * rate;

        extendSummaryHours.textContent = addedHours;
        extendSummaryTotal.textContent = formatCurrency(extraTotal);
        extendUpdatedTotalEl.textContent = formatCurrency(extraTotal);

        if (activeExtendReservation.currentEnd && !activeExtendReservation.isOpenTime) {
            const endDate = new Date(activeExtendReservation.currentEnd);
            endDate.setHours(endDate.getHours() + addedHours);
            extendSummaryEnd.textContent = formatDateTime(endDate);
        } else if (activeExtendReservation.isOpenTime) {
            extendSummaryEnd.textContent = 'Open-time session';
        } else {
            extendSummaryEnd.textContent = '---';
        }
    }

    window.openExtendTimeModal = function(resId) {
        const btn = document.querySelector(`.add-time-btn[data-reservation-id="${resId}"]`);
        if (!btn) {
            console.error('Add Time button not found for ID:', resId);
            return;
        }

        const isOpenTime = btn.getAttribute('data-is-open-time') === 'true';

        activeExtendReservation = {
            resId,
            customer: btn.dataset.customerName || 'Customer',
            room: btn.dataset.roomName || 'Room',
            currentEnd: btn.dataset.endTime || '',
            roomRate: parseFloat(btn.dataset.roomRate) || 0,
            currentTotal: parseFloat(btn.dataset.totalAmount) || 0,
            extraFee: parseFloat(btn.dataset.extraFee) || 0,
            isOpenTime,
        };

        if (extendCustomerEl) extendCustomerEl.textContent = activeExtendReservation.customer;
        if (extendRoomEl) extendRoomEl.textContent = activeExtendReservation.room;
        if (extendCurrentEndEl) {
            extendCurrentEndEl.textContent = activeExtendReservation.currentEnd
                ? formatDateTime(new Date(activeExtendReservation.currentEnd))
                : '---';
        }
        if (extendRateEl) extendRateEl.textContent = formatCurrency(activeExtendReservation.roomRate);
        if (extendOriginalTotalEl) extendOriginalTotalEl.textContent = formatCurrency(activeExtendReservation.currentTotal);
        if (extendSummaryCustomer) extendSummaryCustomer.textContent = activeExtendReservation.customer;
        if (extendSummaryRoom) extendSummaryRoom.textContent = activeExtendReservation.room;
        if (extendHoursInput) extendHoursInput.value = '1';

        const modalTitle = document.getElementById('extendModalTitle');
        const modalNote = document.getElementById('extendModalNote');
        if (modalTitle) {
            modalTitle.textContent = activeExtendReservation.isOpenTime ? 'Adjust Open-Time Session' : 'Extend Fixed Session';
        }
        if (modalNote) {
            modalNote.textContent = activeExtendReservation.isOpenTime
                ? 'This is an open-time session. Adding hours will add billable amount, not change the live timer.'
                : 'Add extra time to the fixed session. The end time and total bill will update.';
        }

        updateExtendModalPreview();

        if (addTimeModal) {
            addTimeModal.classList.add('active');
        }
    };

    if (extendHoursInput) {
        extendHoursInput.addEventListener('input', updateExtendModalPreview);
    }

    if (closeExtendModalBtn) {
        closeExtendModalBtn.addEventListener('click', closeExtendModal);
    }

    if (confirmExtendBtn) {
        confirmExtendBtn.addEventListener('click', function() {
            if (!activeExtendReservation) return;
            const addedHours = Math.max(1, parseInt(extendHoursInput.value, 10) || 1);
            confirmExtendBtn.disabled = true;
            confirmExtendBtn.textContent = 'Extending...';

            fetch(`/admin/extend_time/${activeExtendReservation.resId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Requested-With': 'XMLHttpRequest',
                },
                body: JSON.stringify({ added_hours: addedHours }),
            })
                .then(response => response.json())
                .then(data => {
                    if (data.status !== 'success') {
                        throw new Error(data.message || 'Failed to extend time.');
                    }

                    const card = document.querySelector(`.add-time-btn[data-reservation-id="${activeExtendReservation.resId}"]`)?.closest('.room-card');
                    if (card) {
                        card.dataset.endtime = data.new_end_time || card.dataset.endtime;
                        card.classList.remove('session-expired');
                        const endRow = Array.from(card.querySelectorAll('.info-row')).find(row => {
                            const label = row.querySelector('.info-label');
                            return label && label.textContent.trim() === 'End';
                        });
                        if (endRow) {
                            const value = endRow.querySelector('.info-value');
                            if (value) {
                                value.textContent = formatDateTime(new Date(data.new_end_time));
                            }
                        }
                        const buttons = card.querySelectorAll(`[data-reservation-id="${activeExtendReservation.resId}"]`);
                        buttons.forEach(el => {
                            el.dataset.totalAmount = data.new_total;
                            if (data.new_end_time) {
                                el.dataset.endTime = data.new_end_time;
                            }
                            if (typeof data.new_extra_fee !== 'undefined') {
                                el.dataset.extraFee = data.new_extra_fee;
                            }
                        });
                    }

                    showToast(data.message, 'success');
                    closeExtendModal();
                })
                .catch(error => {
                    console.error('Extend Time error:', error);
                    showToast(error.message || 'Unable to extend time at the moment.', 'error');
                })
                .finally(() => {
                    confirmExtendBtn.disabled = false;
                    confirmExtendBtn.textContent = 'Confirm Extend';
                });
        });
    }

    // Initialize systems
    setInterval(updateTimers, 1000);
    updateTimers();
    sortExpiredCards(); 

    updateClock();
    setInterval(updateClock, 1000);
});