// Real-time app functionality for WS Lounge Pro

document.addEventListener('DOMContentLoaded', function() {
    // SocketIO for real-time updates (if enabled)
    // const socket = io();
    
    // Smooth entrance animations for cards
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        
        setTimeout(() => {
            card.style.transition = 'all 0.5s ease';
            card.style.opacity = '1';
            card.style.transform = 'translateY(0)';
            
            // Clean up inline transitions after animation finishes so CSS hover effects work properly
            setTimeout(() => {
                card.style.transition = '';
            }, 500);
        }, index * 100);
    });

    // Smart Auto-refresh handling (Pauses refresh when user is typing/interacting)
    let isUserActive = false;

    // Detect user interactions to avoid interrupting them
    const markUserActive = () => { isUserActive = true; };
    document.addEventListener('keydown', markUserActive);
    document.addEventListener('mousedown', markUserActive);

    // Optional: Auto-reload after 60s ONLY IF user is idle
    /* 
    setInterval(() => {
        if (!isUserActive) {
            location.reload();
        }
        isUserActive = false; // Reset status for next check
    }, 60000);
    */
});