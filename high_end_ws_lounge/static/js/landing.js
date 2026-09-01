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
    const mobileNavToggle = document.querySelector('.hamburger-btn');
    const mobileMenuPanel = document.getElementById('mobileMenuPanel');
    const mobileMenuBackdrop = document.getElementById('mobileMenuBackdrop');
    const mobileLoginNavBtn = document.getElementById('mobileLoginNavBtn');
    const mobileRegisterNavBtn = document.getElementById('mobileRegisterNavBtn');

    function toggleMobileMenu(forceOpen) {
        if (!mobileNavToggle || !mobileMenuPanel || !mobileMenuBackdrop) return;

        const shouldOpen = typeof forceOpen === 'boolean' ? forceOpen : !mobileMenuPanel.classList.contains('is-open');
        mobileMenuPanel.classList.toggle('is-open', shouldOpen);
        mobileMenuBackdrop.classList.toggle('is-open', shouldOpen);
        mobileNavToggle.classList.toggle('is-open', shouldOpen);
        mobileNavToggle.setAttribute('aria-expanded', String(shouldOpen));
    }

    if (mobileNavToggle && mobileMenuPanel && mobileMenuBackdrop) {
        mobileNavToggle.addEventListener('click', function() {
            toggleMobileMenu();
        });

        mobileMenuBackdrop.addEventListener('click', function() {
            toggleMobileMenu(false);
        });

        mobileMenuPanel.querySelectorAll('a').forEach(function(link) {
            link.addEventListener('click', function() {
                toggleMobileMenu(false);
            });
        });

        window.addEventListener('resize', function() {
            if (window.innerWidth >= 768) {
                toggleMobileMenu(false);
            }
        });
    }

    function showModal(modal) {
        if (modal) {
            modal.style.display = 'flex';
            document.body.style.overflow = 'hidden';
        }
    }

    function hideModal(modal) {
        if (modal) {
            modal.style.display = 'none';
            document.body.style.overflow = '';
        }
    }

    if (loginNavBtn) {
        loginNavBtn.addEventListener('click', function(e) {
            e.preventDefault();
            showModal(loginModal);
        });
    }

    if (mobileLoginNavBtn) {
        mobileLoginNavBtn.addEventListener('click', function(e) {
            e.preventDefault();
            toggleMobileMenu(false);
            showModal(loginModal);
        });
    }

    if (registerNavBtn) {
        registerNavBtn.addEventListener('click', function(e) {
            e.preventDefault();
            showModal(registerModal);
        });
    }

    if (mobileRegisterNavBtn) {
        mobileRegisterNavBtn.addEventListener('click', function(e) {
            e.preventDefault();
            toggleMobileMenu(false);
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

        // Function para mag-hide sang flash alert box kun magbalhin sang modal
    const toRegisterBtn = document.getElementById("toRegister");
    const toLoginBtn = document.getElementById("toLogin");

    if (toRegisterBtn) {
        toRegisterBtn.addEventListener("click", function() {
            // I-hide ang tanan nga existing flash alert boxes
            document.querySelectorAll(".modal-flash").forEach(el => el.style.display = "none");
        });
    }

    if (toLoginBtn) {
        toLoginBtn.addEventListener("click", function() {
            // I-hide ang tanan nga existing flash alert boxes
            document.querySelectorAll(".modal-flash").forEach(el => el.style.display = "none");
        });
    }

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

document.addEventListener("input", function(e) {
    // 1. Pangitaon kun ang naga-type ang user ARA SA SULOD sang Register Modal (#registerModal)
    const registerModal = e.target.closest("#registerModal");
    if (!registerModal) return; // Kun wala sa Register Modal, pabayaan lang

    // 2. Kuhanon ang duha ka Password input fields sa sulod sang Register Modal
    const passInputs = registerModal.querySelectorAll("input[type='password']");
    if (passInputs.length < 2) return;

    const regPass = passInputs[0];    // Primary Password
    const regConfirm = passInputs[1]; // Confirm Password

    const regBar = document.getElementById("reg-strength-bar");
    const regText = document.getElementById("reg-strength-text");
    const regMatch = document.getElementById("reg-match-text");

    // 3. LIVE STRENGTH METER LOGIC
    if (e.target === regPass && regBar && regText) {
        const val = regPass.value;
        let score = 0;

        if (!val) {
            regBar.style.width = "0%";
            regText.textContent = "";
        } else {
            const hasLetters = /[a-zA-Z]/.test(val);
            const hasNumbers = /[0-9]/.test(val);
            const isLong = val.length >= 8;

            if (isLong) score += 33;
            if (hasLetters) score += 33;
            if (hasNumbers) score += 34;

            regBar.style.width = score + "%";

            if (!hasLetters || !hasNumbers || !isLong) {
                regBar.style.backgroundColor = "#dc3545"; // RED
                regText.style.color = "#dc3545";
                regText.textContent = "Must be 8+ characters with letters & numbers";
            } else if (val.length < 10) {
                regBar.style.backgroundColor = "#ffc107"; // YELLOW
                regText.style.color = "#d97706";
                regText.textContent = "Good Alphanumeric Password";
            } else {
                regBar.style.backgroundColor = "#198754"; // GREEN
                regText.style.color = "#198754";
                regText.textContent = "Strong Password!";
            }
        }
    }

    // --- LIVE MATCH CHECKER (IN-LINE LENGTH WAIT) ---
    if (regMatch) {
        const pVal = regPass.value;
        const cVal = regConfirm.value;

        // Kun blanko pa
        if (!cVal) {
            regMatch.textContent = "";
            return;
        }

        // 1. MATCH -> Green dayon
        if (pVal === cVal) {
            regMatch.style.color = "#198754";
            regMatch.innerHTML = '<i class="fa-solid fa-check-circle me-1"></i> Passwords match!';
            return;
        }

        // 2. KULANG PA SA KATAS-ON (Naga-type pa lang) -> Hide anay ang Red text!
        if (cVal.length < pVal.length) {
            regMatch.textContent = "";
            return;
        }

        // 3. MATAPOS NA ANG LENGTH NGA INDI PAREHO / O NALAPAWAN NA -> Red Text
        regMatch.style.color = "#dc3545";
        regMatch.innerHTML = '<i class="fa-solid fa-circle-xmark me-1"></i> Passwords do not match';
    }
});

  document.addEventListener("DOMContentLoaded", function () {
    // Function para mag-dismiss sang alerts gamit ang CSS class nga .fade-out
    function autoDismissAlerts() {
      const alerts = document.querySelectorAll(".alert, .flash-message, [role='alert']");

      alerts.forEach(function (alert) {
        // Indi na i-process liwat kon naga-fade out na o na-process na sang una
        if (alert.dataset.dismissing === "true") return;
        alert.dataset.dismissing = "true";

        // Mag-hulat 3.5 ka segundo bago mag-start fade out
        setTimeout(function () {
          // I-apply ang smooth CSS transition class
          alert.classList.add("fade-out");

          // Papanason sa DOM matapos ang animation (600ms)
          setTimeout(function () {
            alert.remove();
          }, 600);
        }, 3500); // 3.5 seconds
      });
    }

    // Run gilayon sa pag-load sang page
    autoDismissAlerts();

    // Listener para sa mga dynamic alerts (e.g., pag mag-open sang Modal)
    const observer = new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        if (mutation.addedNodes.length) {
          autoDismissAlerts();
        }
      });
    });

    observer.observe(document.body, { childList: true, subtree: true });
  });

    // EYE SHOW/HIDE PASSWORD TOGGLE
    document.querySelectorAll('.toggle-password-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            // Pangitaon ang kaangay nga input field sa sulod sang pareho nga container
            const container = this.closest('.password-wrapper') || this.parentElement;
            const input = container.querySelector('input');
            const icon = this.querySelector('i') || this;

            if (input) {
                const isPassword = input.getAttribute('type') === 'password';
                input.setAttribute('type', isPassword ? 'text' : 'password');

                // Switch icons (FontAwesome)
                if (icon) {
                    if (isPassword) {
                        icon.classList.remove('fa-eye');
                        icon.classList.add('fa-eye-slash');
                    } else {
                        icon.classList.remove('fa-eye-slash');
                        icon.classList.add('fa-eye');
                    }
                }
            }
        });
    });
});