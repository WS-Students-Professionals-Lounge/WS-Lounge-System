/**
 * Base.js - Global utilities and auto-dismiss functionality for all pages
 */

function initializeBaseJs() {
    /**
     * 1. Auto-dismiss Flask flash messages (modern-alert and alert classes)
     * - Fade out and hide after 5 seconds
     */
    const flashAlerts = document.querySelectorAll('.modern-alert, .alert-container .alert');
    flashAlerts.forEach(alert => {
        if (!alert.dataset.autoDismissSet) {
            alert.dataset.autoDismissSet = 'true';
            setTimeout(() => {
                alert.style.transition = 'opacity 0.5s ease';
                alert.style.opacity = '0';
                setTimeout(() => {
                    alert.style.display = 'none';
                }, 500);
            }, 5000);
        }
    });

    /**
     * 2. Watch for dynamically added alerts and apply auto-dismiss
     */
    const observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.addedNodes.length) {
                mutation.addedNodes.forEach(function(node) {
                    if (node.nodeType === 1) {
                        if (node.classList && (node.classList.contains('modern-alert') || node.classList.contains('alert'))) {
                            if (!node.dataset.autoDismissSet) {
                                node.dataset.autoDismissSet = 'true';
                                setTimeout(() => {
                                    node.style.transition = 'opacity 0.5s ease';
                                    node.style.opacity = '0';
                                    setTimeout(() => {
                                        node.style.display = 'none';
                                    }, 500);
                                }, 5000);
                            }
                        }
                        const childAlerts = node.querySelectorAll('.modern-alert, .alert');
                        childAlerts.forEach(alert => {
                            if (!alert.dataset.autoDismissSet) {
                                alert.dataset.autoDismissSet = 'true';
                                setTimeout(() => {
                                    alert.style.transition = 'opacity 0.5s ease';
                                    alert.style.opacity = '0';
                                    setTimeout(() => {
                                        alert.style.display = 'none';
                                    }, 500);
                                }, 5000);
                            }
                        });
                    }
                });
            }
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true
    });

    /**
     * 3. Dismiss button handler for alerts
     */
    document.addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('alert-dismiss')) {
            const alert = e.target.closest('.modern-alert');
            if (alert) {
                alert.style.transition = 'opacity 0.3s ease';
                alert.style.opacity = '0';
                setTimeout(() => {
                    alert.style.display = 'none';
                }, 300);
            }
        }
    });

    /**
     * 4. Generic form confirmation handler for forms using data-confirm
     */
    document.addEventListener('submit', function(e) {
        const form = e.target;
        if (form.matches('form[data-confirm]')) {
            const message = form.dataset.confirm || 'Are you sure you want to continue?';
            if (!window.confirm(message)) {
                e.preventDefault();
            }
        }
    });

    /**
     * 5. Sidebar logo fallback handling without inline onerror attributes
     */
    const sidebarLogo = document.getElementById('sidebarLogo');
    const fallbackIcon = document.getElementById('fallback-icon');
    if (sidebarLogo && fallbackIcon) {
        sidebarLogo.addEventListener('error', function() {
            sidebarLogo.style.display = 'none';
            fallbackIcon.style.display = 'block';
        });
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeBaseJs);
} else {
    initializeBaseJs();
}

/**
 * showToast - global helper to show non-blocking toasts.
 * Falls back to creating a `.modern-alert` element if SweetAlert2 isn't available.
 */
function showToast(message, icon = 'info', timer = 5000) {
    if (window.Swal && typeof Swal.fire === 'function') {
        Swal.fire({
            toast: true,
            position: 'top-end',
            icon: icon,
            title: message,
            showConfirmButton: false,
            timer: timer,
            timerProgressBar: true
        });
        return;
    }

    // Fallback: create a modern-alert inside .alert-container or body
    const container = document.querySelector('.alert-container') || document.body;
    const div = document.createElement('div');
    div.className = 'modern-alert alert alert-info';
    div.textContent = message;
    container.prepend(div);
    // let the initializeBaseJs observer pick it up and dismiss after timer
}

/**
 * confirmAction - Promise-based confirmation helper.
 * Uses SweetAlert2 when available; otherwise shows a simple DOM fallback modal.
 * Returns a Promise that resolves to true when confirmed, false otherwise.
 */
function confirmAction(titleOrText, textOrOptions, confirmText = 'Yes', cancelText = 'Cancel') {
    // Normalize args: allow confirmAction(text) or confirmAction(title, text)
    let title = '';
    let text = '';
    if (typeof textOrOptions === 'undefined') {
        text = titleOrText || '';
    } else {
        title = titleOrText || '';
        text = textOrOptions || '';
    }

    if (window.Swal && typeof Swal.fire === 'function') {
        return Swal.fire({
            title: title || undefined,
            text: text || undefined,
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: confirmText,
            cancelButtonText: cancelText
        }).then(result => !!result.isConfirmed);
    }

    // DOM fallback (non-blocking)
    return new Promise(resolve => {
        const overlay = document.createElement('div');
        overlay.style.position = 'fixed';
        overlay.style.left = '0';
        overlay.style.top = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.background = 'rgba(0,0,0,0.45)';
        overlay.style.display = 'flex';
        overlay.style.alignItems = 'center';
        overlay.style.justifyContent = 'center';
        overlay.style.zIndex = '99999';

        const box = document.createElement('div');
        box.style.background = '#fff';
        box.style.padding = '18px';
        box.style.borderRadius = '8px';
        box.style.maxWidth = '480px';
        box.style.width = '90%';
        box.style.boxShadow = '0 6px 18px rgba(0,0,0,0.2)';

        if (title) {
            const h = document.createElement('h3');
            h.style.margin = '0 0 8px 0';
            h.textContent = title;
            box.appendChild(h);
        }
        if (text) {
            const p = document.createElement('p');
            p.style.margin = '0 0 12px 0';
            p.textContent = text;
            box.appendChild(p);
        }

        const actions = document.createElement('div');
        actions.style.display = 'flex';
        actions.style.justifyContent = 'flex-end';
        actions.style.gap = '8px';

        const btnCancel = document.createElement('button');
        btnCancel.textContent = cancelText;
        btnCancel.style.padding = '6px 12px';
        btnCancel.style.background = '#eee';
        btnCancel.style.border = 'none';
        btnCancel.style.borderRadius = '4px';

        const btnConfirm = document.createElement('button');
        btnConfirm.textContent = confirmText;
        btnConfirm.style.padding = '6px 12px';
        btnConfirm.style.background = '#82cae8';
        btnConfirm.style.border = 'none';
        btnConfirm.style.borderRadius = '4px';

        actions.appendChild(btnCancel);
        actions.appendChild(btnConfirm);
        box.appendChild(actions);
        overlay.appendChild(box);
        document.body.appendChild(overlay);

        btnCancel.addEventListener('click', () => { overlay.remove(); resolve(false); });
        btnConfirm.addEventListener('click', () => { overlay.remove(); resolve(true); });
    });
}

