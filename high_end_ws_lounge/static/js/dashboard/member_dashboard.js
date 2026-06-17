document.addEventListener('DOMContentLoaded', () => {
    // 1. Live Clock with Date (Existing - Kept as is)
    function updateClock() {
        const now = new Date();
        const options = { 
            month: 'short', day: 'numeric', year: 'numeric',
            hour: 'numeric', minute: '2-digit', second: '2-digit',
            hour12: true 
        };
        const timeString = now.toLocaleString('en-US', options);
        const clockEl = document.getElementById('dashboardClock');
        if (clockEl) clockEl.textContent = timeString;
    }
    setInterval(updateClock, 1000);
    updateClock();

    // =====================================================================
    // Persistent Membership Expiry Countdown with localStorage
    // =====================================================================
    function initMembershipExpiryCountdown() {
        const countdownEl = document.getElementById('membershipExpiryCountdown');
        if (!countdownEl) return;

        const expiryISO = countdownEl.dataset.expiry;
        const membershipId = countdownEl.dataset.membershipId;
        
        if (!expiryISO) {
            countdownEl.textContent = 'N/A';
            return;
        }

        // Store expiry date in localStorage for persistence across logout
        const storageKey = `membership_expiry_${membershipId}`;
        localStorage.setItem(storageKey, expiryISO);

        const updateCountdown = () => {
            const now = Date.now();
            const expiryTime = new Date(expiryISO).getTime();
            const distance = expiryTime - now;
            
            if (distance <= 0) {
                countdownEl.textContent = 'Expired';
                countdownEl.style.color = '#dc3545'; // Red for expired
                return;
            }
            
            const days = Math.floor(distance / (1000 * 60 * 60 * 24));
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);
            
            const countdownText = `${days}d ${hours.toString().padStart(2, '0')}h ${minutes.toString().padStart(2, '0')}m ${seconds.toString().padStart(2, '0')}s`;
            countdownEl.textContent = countdownText;
            
            // Color code based on time remaining
            if (distance < 86400000) { // Less than 1 day
                countdownEl.style.color = '#dc3545'; // Red
            } else if (distance < 604800000) { // Less than 7 days
                countdownEl.style.color = '#ff6c00'; // Orange
            } else {
                countdownEl.style.color = '#28a745'; // Green
            }
        };

        updateCountdown();
        setInterval(updateCountdown, 1000);
    }

    initMembershipExpiryCountdown();

    // 2. Typewriter Effect (Existing - Kept as is)
    const nameSpan = document.getElementById('userName');
    if (nameSpan) {
        const fullText = nameSpan.textContent; 
        nameSpan.textContent = '';
        let i = 0;
        let isDeleting = false;

        function type() {
            const currentText = isDeleting ? fullText.substring(0, i--) : fullText.substring(0, i++);
            nameSpan.textContent = currentText;

            if (!isDeleting && i > fullText.length) {
                setTimeout(() => { isDeleting = true; type(); }, 3000);
            } 
            else if (isDeleting && i < 0) {
                isDeleting = false;
                i = 0;
                setTimeout(type, 500);
            } 
            else {
                setTimeout(type, isDeleting ? 50 : 100);
            }
        }
        setTimeout(type, 1000);
    }

    // Make welcome text animate exactly like admin (same slide-in timing and easing)
    const welcomeEl = document.querySelector('.welcome-text');
    if (welcomeEl) {
        welcomeEl.style.opacity = '0';
        welcomeEl.style.transform = 'translateX(-10px)';
        setTimeout(() => {
            welcomeEl.style.transition = 'all 0.45s ease-out';
            welcomeEl.style.opacity = '1';
            welcomeEl.style.transform = 'translateX(0)';
        }, 400);
    }

    // 3. Real-time Session Timer (Issue #5)
    // Timer is handled through membership API updates; only render when a check-in session exists.

    // 4. Search and Filter Functionality (Issue #8)
    const searchInput = document.getElementById('reservationSearch');
    const statusFilter = document.getElementById('statusFilter');
    const tableRows = document.querySelectorAll('#reservationTable tbody tr');

    function filterTable() {
        const searchTerm = searchInput.value.toLowerCase();
        const filterValue = statusFilter.value.toLowerCase();

        tableRows.forEach(row => {
            const text = row.innerText.toLowerCase();
            const statusBadge = row.querySelector('.status-badge');
            const status = statusBadge ? statusBadge.innerText.toLowerCase() : '';
            
            const matchesSearch = text.includes(searchTerm);
            const matchesFilter = filterValue === 'all' || status.includes(filterValue);

            if (matchesSearch && matchesFilter) {
                row.style.display = "";
            } else {
                row.style.display = "none";
            }
        });
    }

    if (searchInput) searchInput.addEventListener('input', filterTable);
    if (statusFilter) statusFilter.addEventListener('change', filterTable);

    // 5. Export to CSV (Issue #8)
    const exportBtn = document.getElementById('exportCSV');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            let csv = [];
            const rows = document.querySelectorAll("#reservationTable tr");
            
            for (let i = 0; i < rows.length; i++) {
                if (rows[i].style.display !== "none") {
                    let row = [], cols = rows[i].querySelectorAll("td, th");
                    for (let j = 0; j < cols.length; j++) 
                        row.push('"' + cols[j].innerText.trim() + '"');
                    csv.push(row.join(","));
                }
            }

            const csvFile = new Blob([csv.join("\n")], {type: "text/csv"});
            const downloadLink = document.createElement("a");
            downloadLink.download = `WSLounge_Reservations_${new Date().toLocaleDateString()}.csv`;
            downloadLink.href = window.URL.createObjectURL(csvFile);
            downloadLink.style.display = "none";
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
        });
    }

    // 6. Notification Mockup (Issue #9)
    function showNotification(message) {
        const container = document.getElementById('notificationContainer');
        if (container) {
            const toast = document.createElement('div');
            toast.className = 'status-badge badge-pending';
            toast.style.padding = '15px';
            toast.style.marginBottom = '10px';
            toast.style.boxShadow = '0 4px 10px rgba(0,0,0,0.1)';
            toast.style.display = 'block';
            toast.innerHTML = `<i class="fas fa-bell"></i> ${message}`;
            
            container.appendChild(toast);
            setTimeout(() => {
                toast.style.opacity = '0';
                setTimeout(() => toast.remove(), 500);
            }, 5000);
        }
    }

    // Check for expiring sessions (Example logic)
    const planLeftEl = document.querySelector('.member-stats-grid .stat-card:nth-child(2) .stat-number');
    if (planLeftEl && parseInt(planLeftEl.textContent) <= 2) {
        showNotification("Your plan is expiring soon! Renew now to keep access.");
    }

    // =====================================================================
    // Real-time Membership Status Updates
    // =====================================================================
    const membershipCard = document.getElementById('membershipCard');
    let currentSessionStart = null;
    let sessionIntervalId = null;

    function formatHMS(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = seconds % 60;
        return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }

    function formatHoursDecimal(seconds) {
        return (seconds / 3600).toFixed(2);
    }

    function updateSessionTimer() {
        const sessionTimer = document.getElementById('sessionTimer');
        const hoursSpent = document.getElementById('hoursSpent');
        if (!sessionTimer || !currentSessionStart) return;

        const now = new Date();
        const elapsedSeconds = Math.max(0, Math.floor((now - currentSessionStart) / 1000));
        sessionTimer.textContent = formatHMS(elapsedSeconds);
        if (hoursSpent) {
            hoursSpent.textContent = `${formatHoursDecimal(elapsedSeconds)} hrs`;
        }
    }

    function clearSessionTimer() {
        const sessionTimer = document.getElementById('sessionTimer');
        const hoursSpent = document.getElementById('hoursSpent');
        currentSessionStart = null;
        if (sessionIntervalId) {
            clearInterval(sessionIntervalId);
            sessionIntervalId = null;
        }
        if (sessionTimer) sessionTimer.textContent = '00:00:00';
        if (hoursSpent) hoursSpent.textContent = '0.00 hrs';
    }

    async function loadCurrentSession() {
        try {
            const response = await fetch('/api/membership/current-session');
            if (!response.ok) return null;
            const data = await response.json();
            if (data.status !== 'success' || !data.check_in_time) return null;

            currentSessionStart = new Date(data.check_in_time);
            updateSessionTimer();
            if (!sessionIntervalId) {
                sessionIntervalId = setInterval(updateSessionTimer, 1000);
            }

            return data;
        } catch (error) {
            console.error('Error loading current session:', error);
            return null;
        }
    }

    async function refreshMembershipStatus() {
        if (!membershipCard) return;

        try {
            const response = await fetch('/api/membership/status');
            if (!response.ok) return;
            const data = await response.json();
            if (data.status !== 'success') return;

            // Update remaining hours
            const remainingHoursEl = document.getElementById('remainingHours');
            if (remainingHoursEl && typeof data.hours_left !== 'undefined') {
                const hoursValue = remainingHoursEl.querySelector('.hours-value');
                if (hoursValue) {
                    hoursValue.textContent = parseFloat(data.hours_left).toFixed(2) + ' hrs';
                } else {
                    remainingHoursEl.textContent = parseFloat(data.hours_left).toFixed(2) + ' hrs';
                }
            }

            // Update status badge
            const statusBadge = document.querySelector('.detail-value .badge');
            if (statusBadge && typeof data.is_checked_in !== 'undefined') {
                if (data.is_checked_in) {
                    statusBadge.className = 'badge bg-success';
                    statusBadge.textContent = '✓ Checked In';
                } else {
                    statusBadge.className = 'badge bg-secondary';
                    statusBadge.textContent = 'Not Checked In';
                }
            }

            // Handle session timer
            if (data.is_checked_in) {
                await loadCurrentSession();
            } else {
                clearSessionTimer();
            }

            // Update total hours used (accumulated)
            if (typeof data.accumulated_hours !== 'undefined') {
                const totalHoursEl = document.getElementById('totalHoursUsed');
                if (totalHoursEl) {
                    const hoursValue = totalHoursEl.querySelector('.hours-value');
                    if (hoursValue) {
                        hoursValue.textContent = parseFloat(data.accumulated_hours).toFixed(2) + ' hrs';
                    } else {
                        totalHoursEl.textContent = parseFloat(data.accumulated_hours).toFixed(2) + ' hrs';
                    }
                }
            }
        } catch (error) {
            console.error('Error refreshing membership status:', error);
        }
    }

    if (membershipCard) {
        // Initial load
        refreshMembershipStatus();
        // Refresh every 5 seconds
        setInterval(refreshMembershipStatus, 5000);
    }

});
