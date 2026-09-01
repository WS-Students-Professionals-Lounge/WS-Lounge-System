document.addEventListener('DOMContentLoaded', function() {
    // 1. Live Clock with Date (PHT Synchronized local display)
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

    // Persistent Membership Expiry Countdown with localStorage
function initMembershipExpiryCountdown() {
    const countdownEl = document.getElementById('membershipExpiryCountdown');
    if (!countdownEl) return;

    const expiryISO = countdownEl.dataset.expiry;
    const membershipId = countdownEl.dataset.membershipId;

    if (!expiryISO || expiryISO === 'None' || expiryISO === '') {
        countdownEl.textContent = 'N/A';
        return;
    }

    if (membershipId) {
        localStorage.setItem(`membership_expiry_${membershipId}`, expiryISO);
    }

    let countdownInterval = null;

    const updateCountdown = () => {
        // Dynamic & Strict Boolean Reading
        const rawCheckedIn = (countdownEl.getAttribute('data-is-checked-in') || '').toString().toLowerCase().trim();
        const isCheckedIn = (rawCheckedIn === 'true' || rawCheckedIn === '1');

        // KON MATUOD NGA CHECKED OUT / INACTIVE
        if (!isCheckedIn) {
            countdownEl.textContent = 'Not Checked In';
            countdownEl.style.color = '#6c757d'; // Muted Gray
            countdownEl.setAttribute('data-remaining-seconds', '0');

            if (typeof checkExpiringSessionNotification === 'function') {
                checkExpiringSessionNotification();
            }
            return; 
        }

        const now = Date.now();
        const expiryTime = new Date(expiryISO).getTime();

        if (isNaN(expiryTime)) {
            countdownEl.textContent = 'N/A';
            return;
        }

        const distance = expiryTime - now;
        
        if (distance <= 0) {
            countdownEl.textContent = 'Expired';
            countdownEl.style.color = '#dc3545';
            countdownEl.setAttribute('data-remaining-seconds', '0');
            if (countdownInterval) clearInterval(countdownInterval);

            if (typeof checkExpiringSessionNotification === 'function') {
                checkExpiringSessionNotification();
            }
            return;
        }
        
        const totalRemainingSeconds = Math.floor(distance / 1000);
        countdownEl.setAttribute('data-remaining-seconds', totalRemainingSeconds);

        const days = Math.floor(distance / (1000 * 60 * 60 * 24));
        const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);
        
        let countdownText = '';
        if (days > 0) countdownText += `${days}d `;
        countdownText += `${hours.toString().padStart(2, '0')}h ${minutes.toString().padStart(2, '0')}m ${seconds.toString().padStart(2, '0')}s`;
        
        countdownEl.textContent = countdownText;
        
        if (distance < 86400000) {
            countdownEl.style.color = '#dc3545';
        } else if (distance < 604800000) {
            countdownEl.style.color = '#ff6c00';
        } else {
            countdownEl.style.color = '#28a745';
        }

        if (typeof checkExpiringSessionNotification === 'function') {
            checkExpiringSessionNotification();
        }
    };

    updateCountdown();
    countdownInterval = setInterval(updateCountdown, 1000);
}

// Automatic Run
initMembershipExpiryCountdown();

// 2. Typewriter Effect
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

    // Welcome text animation
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

    // 3. Real-time Session Timer (Fetches exact elapsed seconds from Backend)
    function initActiveSessionTimer() {
        const timerEl = document.getElementById('sessionTimer');
        if (!timerEl) return;

        fetch('/api/membership/current-session')
            .then(res => res.json())
            .then(data => {
                if (data.status === 'success' && data.elapsed_seconds !== undefined) {
                    let totalSeconds = data.elapsed_seconds;

                    const updateTimerDisplay = () => {
                        totalSeconds++;
                        const hrs = Math.floor(totalSeconds / 3600);
                        const mins = Math.floor((totalSeconds % 3600) / 60);
                        const secs = totalSeconds % 60;

                        timerEl.textContent = 
                            `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
                    };

                    updateTimerDisplay();
                    setInterval(updateTimerDisplay, 1000);
                } else {
                    timerEl.textContent = 'No Active Session';
                }
            })
            .catch(() => {
                timerEl.textContent = '--:--:--';
            });
    }

    initActiveSessionTimer();

// ==========================================
    // 4. SEARCH AND FILTER FUNCTIONALITY
    // ==========================================
    const searchInput = document.getElementById('reservationSearch');
    const statusFilter = document.getElementById('statusFilter');

    function filterTable() {
        const searchTerm = searchInput ? searchInput.value.toLowerCase().trim() : '';
        const filterValue = statusFilter ? statusFilter.value.toLowerCase().trim() : 'all';

        // 1. Filter Table Rows
        const tableRows = document.querySelectorAll('#reservationTable tbody tr, table .filterable-row');
        tableRows.forEach(row => {
            const text = row.innerText.toLowerCase();
            const rowStatusAttr = (row.getAttribute('data-status') || '').toLowerCase().trim();
            const statusBadge = row.querySelector('.status-badge, .badge');
            const badgeText = statusBadge ? statusBadge.innerText.toLowerCase().trim() : '';
            const status = rowStatusAttr || badgeText;

            const matchesSearch = text.includes(searchTerm);
            const matchesFilter = (filterValue === 'all' || filterValue === 'all status' || status.includes(filterValue));

            if (filterValue === 'ended' || filterValue === 'completed') {
                // I-match kon completed, ended, o expired
                matchesFilter = (status.includes('ended') || status.includes('completed') || status.includes('expired'));
            } else if (filterValue === 'confirmed' || filterValue === 'approved') {
                matchesFilter = (status.includes('approved') || status.includes('confirmed') || status.includes('active'));
            } else {
                matchesFilter = (filterValue === 'all' || filterValue === 'all status' || status.includes(filterValue));
            }

            if (matchesSearch && matchesFilter) {
                row.style.setProperty('display', '', 'important');
            } else {
                row.style.setProperty('display', 'none', 'important');
            }
        });

        // 2. Filter Solo Plans Cards
        const planCards = document.querySelectorAll('.plan-card, .solo-plan-card, div.filterable-row, .reservations-section .card');
        planCards.forEach(card => {
            // Likawan i-filter ang mga parent section o stat cards
            if (card.closest('.member-stats-grid') || card.classList.contains('stat-card')) return;

            const text = card.innerText.toLowerCase();
            const cardStatusAttr = (card.getAttribute('data-status') || '').toLowerCase().trim();
            const badgeEl = card.querySelector('.badge, .status-badge, [class*="badge"]');
            const badgeText = badgeEl ? badgeEl.innerText.toLowerCase().trim() : '';
            const status = cardStatusAttr || badgeText;

            const matchesSearch = text.includes(searchTerm);
            const matchesFilter = (filterValue === 'all' || filterValue === 'all status' || status.includes(filterValue));

            if (matchesSearch && matchesFilter) {
                card.style.setProperty('display', '', 'important');
            } else {
                card.style.setProperty('display', 'none', 'important');
            }
        });
    }

    if (searchInput) searchInput.addEventListener('input', filterTable);
    if (statusFilter) statusFilter.addEventListener('change', filterTable);

    document.addEventListener('click', function(e) {
    if (e.target && e.target.classList.contains('delete-plan-btn')) {
        const btn = e.target;
        const planId = btn.getAttribute('data-plan-id');
        const cardElement = btn.closest('.filterable-row');

        if (confirm('Sigurado ka nga gusto mo idelete ini nga plan?')) {
            if (cardElement) {
                cardElement.style.transition = 'all 0.3s ease';
                cardElement.style.opacity = '0';
                setTimeout(() => {
                    cardElement.remove();
                }, 300);
            }
        }
    }
});
    
    // ==========================================
    // 5. EXPORT TO CSV
    // ==========================================
    const exportBtn = document.getElementById('exportCSV');
    if (exportBtn) {
        exportBtn.addEventListener('click', () => {
            let csv = [];
            const rows = document.querySelectorAll("#reservationTable tr");
            
            for (let i = 0; i < rows.length; i++) {
                if (rows[i].style.display !== "none") {
                    let row = [], cols = rows[i].querySelectorAll("td, th");
                    for (let j = 0; j < cols.length; j++) {
                        let cellText = cols[j].innerText.trim().replace(/\n/g, ' '); 
                        // Dugangan sang single quote (') sa unahan sang date/time string para indi mag-hashtag sa Excel
                        row.push('"' + cellText + '"');
                    }
                    csv.push(row.join(","));
                }
            }

            const csvFile = new Blob(["\uFEFF" + csv.join("\n")], {type: "text/csv;charset=utf-8;"}); // \uFEFF para sa Excel UTF-8 support
            const downloadLink = document.createElement("a");
            downloadLink.download = `WSLounge_Reservations_${new Date().toLocaleDateString()}.csv`;
            downloadLink.href = window.URL.createObjectURL(csvFile);
            downloadLink.style.display = "none";
            document.body.appendChild(downloadLink);
            downloadLink.click();
            document.body.removeChild(downloadLink);
        });
    }

    // 6. Notification System
    function showNotification(message) {
    const container = document.getElementById('notificationContainer');
    if (container) {
        // Para indi mag-duplicate ang toast warning kon yara na sa screen
        if (container.children.length > 0) return;

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

// Check for expiring sessions/plans
// Variable para siguraduhon nga ISA LANG KA BESES mag-popup ang warning
let hasShownExpiringWarning = false;

function checkExpiringSessionNotification() {
    const countdownEl = document.getElementById('membershipExpiryCountdown');
    const container = document.getElementById('notificationContainer');

    // 1. I-CHECK KON NAKA-CHECK IN ANG USER
    if (!countdownEl) return;

    const rawCheckedIn = (countdownEl.getAttribute('data-is-checked-in') || '').toString().toLowerCase().trim();
    const isCheckedIn = (rawCheckedIn === 'true' || rawCheckedIn === '1');

    // KON NOT CHECKED IN -> DAPAT INDI GID MAG-PAKITA ANG WARNING!
    if (!isCheckedIn) {
        if (container) container.innerHTML = ''; // Taguin/kasa kon may nabilin nga warning
        hasShownExpiringWarning = false; // Reset flag
        return;
    }

    // 2. GET REMAINING SECONDS DIRECTLY FROM LIVE COUNTDOWN TIMER
    // Siguraduha nga ang countdownEl may attribute o data-seconds nga naga-update
    const remainingSeconds = parseInt(countdownEl.getAttribute('data-remaining-seconds')) || 0;

    // THRESHOLD: 15 MINUTES (15 * 60 = 900 SECONDS)
    // Pwede mo man liwaton sa 10 mins (600) or 5 mins (300)
    const THRESHOLD_SECONDS = 900; 

    // 3. CHECK KON GAMAY NA LANG ANG ORAS SA LIVE TIMER
    if (remainingSeconds > 0 && remainingSeconds <= THRESHOLD_SECONDS) {
        if (!hasShownExpiringWarning) {
            showNotification("YOUR PLAN IS EXPIRING SOON! RENEW NOW TO KEEP ACCESS.");
            hasShownExpiringWarning = true; // Markahi para indi mag-sige popup
        }
    } else {
        // Kon labaw pa sa 15 mins ang oras, siguraduhon nga waay warning
        if (container && remainingSeconds > THRESHOLD_SECONDS) {
            container.innerHTML = '';
        }
    }
}

// TIP: Tawagon man ini nga function sa SULOD sang inyo live timer setInterval() loop 
// para kada seconds tick naga-check sya kon nag-hit na sa 15 minutes!

// Real-time Membership Status Updates

    const membershipCard = document.getElementById('membershipCard');
    let currentElapsedSeconds = 0;
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
        if (!sessionTimer) return;

        currentElapsedSeconds++; // Increment continuously in seconds
        sessionTimer.textContent = formatHMS(currentElapsedSeconds);
        if (hoursSpent) {
            hoursSpent.textContent = `${formatHoursDecimal(currentElapsedSeconds)} hrs`;
        }
    }

    function clearSessionTimer() {
        const sessionTimer = document.getElementById('sessionTimer');
        const hoursSpent = document.getElementById('hoursSpent');
        currentElapsedSeconds = 0;
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
            if (data.status !== 'success' || data.elapsed_seconds === undefined) return null;

            // Direct sync with backend server seconds (bypass PC browser time check)
            currentElapsedSeconds = Math.max(0, Math.floor(data.elapsed_seconds));
            
            const sessionTimer = document.getElementById('sessionTimer');
            const hoursSpent = document.getElementById('hoursSpent');
            if (sessionTimer) sessionTimer.textContent = formatHMS(currentElapsedSeconds);
            if (hoursSpent) hoursSpent.textContent = `${formatHoursDecimal(currentElapsedSeconds)} hrs`;

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
                const formattedHours = parseFloat(data.accumulated_hours).toFixed(2) + ' hrs';

                // 1. Target sa sulod sang Membership Details panel
                const totalHoursEl = document.getElementById('totalHoursUsed');
                if (totalHoursEl) {
                    const hoursValue = totalHoursEl.querySelector('.hours-value');
                    if (hoursValue) {
                        hoursValue.textContent = formattedHours;
                    } else {
                        totalHoursEl.textContent = formattedHours;
                    }

                }
                const totalSoloHoursCard = document.querySelector('.member-stats-grid .stat-card:nth-child(2) .stat-number');
                if (totalSoloHoursCard) {
                    totalSoloHoursCard.textContent = formattedHours;
                }
        
            }
        } catch (error) {
            console.error('Error refreshing membership status:', error);
        }
    }

    if (membershipCard) {
        // Initial load
        refreshMembershipStatus();
        // Refresh every 5 seconds to stay perfectly synced with DB
        setInterval(refreshMembershipStatus, 5000);
    }
});