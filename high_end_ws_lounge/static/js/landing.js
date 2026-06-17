document.addEventListener('DOMContentLoaded', function() {
    const loginModal = document.getElementById('loginModal');
    const registerModal = document.getElementById('registerModal');
    const loginNavBtn = document.getElementById('loginNavBtn');
    const registerNavBtn = document.getElementById('registerNavBtn');
    const bookNowBtn = document.getElementById('bookNowBtn');
    const closeLogin = document.getElementById('closeLogin');
    const closeRegister = document.getElementById('closeRegister');
    const toRegister = document.getElementById('toRegister');
    const toLogin = document.getElementById('toLogin');

    function showModal(modal) {
        modal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    function hideModal(modal) {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }

    if (loginNavBtn) {
        loginNavBtn.addEventListener('click', function(e) {
            e.preventDefault();
            showModal(loginModal);
        });
    }

    if (registerNavBtn) {
        registerNavBtn.addEventListener('click', function(e) {
            e.preventDefault();
            showModal(registerModal);
        });
    }

    if (bookNowBtn) {
        bookNowBtn.addEventListener('click', function(e) {
            e.preventDefault();
            showModal(registerModal);
        });
    }

    if (closeLogin) {
        closeLogin.addEventListener('click', function() {
            hideModal(loginModal);
        });
    }

    if (closeRegister) {
        closeRegister.addEventListener('click', function() {
            hideModal(registerModal);
        });
    }

    if (toRegister) {
        toRegister.addEventListener('click', function(e) {
            e.preventDefault();
            hideModal(loginModal);
            showModal(registerModal);
        });
    }

    if (toLogin) {
        toLogin.addEventListener('click', function(e) {
            e.preventDefault();
            hideModal(registerModal);
            showModal(loginModal);
        });
    }

    // Close modals on outside click
    window.addEventListener('click', function(e) {
        if (e.target === loginModal) {
            hideModal(loginModal);
        }
        if (e.target === registerModal) {
            hideModal(registerModal);
        }
    });

    // Close modals on Escape key
    window.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            hideModal(loginModal);
            hideModal(registerModal);
        }
    });

    // Smooth scroll for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            const href = this.getAttribute('href');
            if (href !== '#') {
                e.preventDefault();
                const target = document.querySelector(href);
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            }
        });
    });

    // Show register or login modal if redirected from auth routes
    const showRegister = document.body.dataset.showRegister === 'true';
    const showLogin = document.body.dataset.showLogin === 'true';

    if (showRegister) {
        showModal(registerModal);
    }
    if (showLogin) {
        showModal(loginModal);
    }

    document.querySelectorAll('.btn-apply').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            showModal(registerModal);
        });
    });
});

