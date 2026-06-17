document.addEventListener('DOMContentLoaded', () => {
    // 1. Digital Clock (Existing Function Kept)
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

    // 2. Automatic Session Timer (New Logic for Automatic Tracking)
    function initSessionTimer() {
        const timerDisplay = document.getElementById('sessionTimer');
        if (!timerDisplay) return;

        // Get the end time from the data attribute (provided by Jinja)
        const endTimeStr = timerDisplay.getAttribute('data-endtime');
        if (!endTimeStr) return;

        const endTime = new Date(endTimeStr).getTime();

        const countdownInterval = setInterval(() => {
            const now = new Date().getTime();
            const distance = endTime - now;

            // Time calculations for hours, minutes and seconds
            const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
            const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((distance % (1000 * 60)) / 1000);

            // Display the result in the element
            if (distance < 0) {
                clearInterval(countdownInterval);
                timerDisplay.textContent = "SESSION ENDED";
                timerDisplay.style.color = "#EB3223";
                // Optional: Refresh page to update status automatically when session ends
                setTimeout(() => { location.reload(); }, 2000);
            } else {
                // Formatting with leading zeros
                const hDisplay = hours < 10 ? "0" + hours : hours;
                const mDisplay = minutes < 10 ? "0" + minutes : minutes;
                const sDisplay = seconds < 10 ? "0" + seconds : seconds;
                
                timerDisplay.textContent = `${hDisplay}:${mDisplay}:${sDisplay}`;
            }
        }, 1000);
    }
    initSessionTimer();

    // 3. Status Tracker (Kept and adjusted for background sync)
    function updateStatus() {
        fetch('/get_time_inside')
            .then(r => r.json())
            .then(data => {
                const statusText = document.getElementById('statusText');
                if (!statusText) return;

                if (data.status === 'inside') {
                    // Logic for when system detects user is within reservation period
                    statusText.textContent = 'Session in Progress';
                    statusText.className = 'status-inside';
                } else {
                    statusText.textContent = 'Awaiting Reservation';
                    statusText.className = 'status-muted';
                }
            })
            .catch(err => console.log("Status check error:", err));
    }
    // Only run status check if no active timer is displayed to save resources
    if (!document.getElementById('sessionTimer')) {
        setInterval(updateStatus, 5000);
        updateStatus();
    }

    // 4. Modal Logic (Kept for generic notifications/errors)
    const modal = document.getElementById('confirmModal');
    const btnCloseModal = document.getElementById('btnCloseModal');
    
    if (btnCloseModal) {
        btnCloseModal.addEventListener('click', () => {
            modal.style.display = 'none';
        });
    }

    window.onclick = (event) => {
        if (modal && event.target == modal) {
            modal.style.display = 'none';
        }
    };
});