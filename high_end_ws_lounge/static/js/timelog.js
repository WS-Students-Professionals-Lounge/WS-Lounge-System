document.addEventListener('DOMContentLoaded', () => {
    // 1. Digital Clock
    function updateClock() {
        const now = new Date();
        const options = { 
            month: 'short', day: 'numeric', year: 'numeric',
            hour: 'numeric', minute: '2-digit', second: '2-digit',
            hour12: true 
        };
        const clockEl = document.getElementById('clock');
        if (clockEl) clockEl.textContent = now.toLocaleString('en-US', options);
    }
    setInterval(updateClock, 1000);
    updateClock();

    // 2. Automatic Session Timer
    function initSessionTimer() {
        const timerDisplay = document.getElementById('sessionTimer');
        if (!timerDisplay) return;

        // Get the end time from the data attribute (provided by Jinja)
        let endTimeStr = timerDisplay.getAttribute('data-endtime');
        if (!endTimeStr) return;

        // Fix Safari/iOS Date Parsing compatibility issue
        endTimeStr = endTimeStr.replace(' ', 'T');
        const endTime = new Date(endTimeStr).getTime();

        if (isNaN(endTime)) {
            timerDisplay.textContent = "INVALID TIME";
            return;
        }

        const countdownInterval = setInterval(() => {
            const now = Date.now();
            const distance = endTime - now;

            // Time calculations
            if (distance <= 0) {
                clearInterval(countdownInterval);
                timerDisplay.textContent = "SESSION ENDED";
                timerDisplay.style.color = "#EB3223";
                
                // Refresh page to sync backend session status
                setTimeout(() => { location.reload(); }, 2000);
            } else {
                const totalHours = Math.floor(distance / (1000 * 60 * 60));
                const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                const seconds = Math.floor((distance % (1000 * 60)) / 1000);

                // Formatting with leading zeros
                const hDisplay = String(totalHours).padStart(2, '0');
                const mDisplay = String(minutes).padStart(2, '0');
                const sDisplay = String(seconds).padStart(2, '0');
                
                timerDisplay.textContent = `${hDisplay}:${mDisplay}:${sDisplay}`;
            }
        }, 1000);
    }
    initSessionTimer();

    // 3. Status Tracker (Syncing via API)
    function updateStatus() {
        fetch('/get_time_inside')
            .then(r => {
                if (!r.ok) throw new Error(`HTTP Error ${r.status}`);
                return r.json();
            })
            .then(data => {
                const statusText = document.getElementById('statusText');
                if (!statusText) return;

                if (data.status === 'inside') {
                    statusText.textContent = 'Session in Progress';
                    statusText.className = 'status-inside';
                } else {
                    statusText.textContent = 'Awaiting Reservation';
                    statusText.className = 'status-muted';
                }
            })
            .catch(err => console.error("Status check error:", err));
    }

    // Only run status check if no active timer is displayed to save server resources
    if (!document.getElementById('sessionTimer')) {
        setInterval(updateStatus, 5000);
        updateStatus();
    }

    // 4. Safe Modal Controller
    const modal = document.getElementById('confirmModal');
    const btnCloseModal = document.getElementById('btnCloseModal');
    
    if (btnCloseModal && modal) {
        btnCloseModal.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }

    window.addEventListener('click', (event) => {
        if (modal && event.target === modal) {
            modal.style.display = 'none';
        }
    });
});