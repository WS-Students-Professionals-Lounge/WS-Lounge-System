document.addEventListener('DOMContentLoaded', function() {
    
    // === 1. SEARCH INPUT LISTENER ===
    const searchInput = document.getElementById('memberSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            filterMembers(searchInput.value);
        });
    }

    // === 2. EVENT DELEGATION / DIRECT BINDINGS FOR BUTTONS ===
    document.querySelectorAll('.btn-membership-toggle').forEach((button) => {
        button.addEventListener('click', () => {
            const membershipId = button.dataset.membershipId;
            const membershipName = button.dataset.membershipName;
            if (!membershipId) return;
            toggleCheckInOut(membershipId, membershipName, button);
        });
    });

    document.querySelectorAll('.btn-history').forEach((button) => {
        button.addEventListener('click', () => {
            const membershipId = button.dataset.membershipId;
            const membershipName = button.dataset.membershipName;
            if (!membershipId) return;
            showHistory(membershipId, membershipName);
        });
    });

    document.querySelectorAll('.btn-approve').forEach((button) => {
        button.addEventListener('click', () => {
            const membershipId = button.dataset.membershipId;
            const membershipName = button.dataset.membershipName;
            if (!membershipId) return;
            approveMembership(membershipId, membershipName);
        });
    });

    document.querySelectorAll('.btn-reject').forEach((button) => {
        button.addEventListener('click', () => {
            const membershipId = button.dataset.membershipId;
            const membershipName = button.dataset.membershipName;
            if (!membershipId) return;
            rejectMembership(membershipId, membershipName);
        });
    });
});

// === HELPER: FETCH API WITH JSON HEADERS ===
async function postJson(url, payload = {}) {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(payload)
    });
    
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.status !== 'success') {
        throw new Error(data.message || `Request failed with status ${response.status}`);
    }
    return data;
}

// === CHECK-IN / CHECK-OUT TOGGLE ===
function toggleCheckInOut(membershipId, memberName, button) {
    if (!button) return;
    const isCheckedIn = button.classList.contains('checked-in');
    const endpoint = isCheckedIn ? 'check-out' : 'check-in';
    const originalText = button.textContent.trim();

    const actionText = endpoint.replace('-', ' ');
    if (!window.confirm(`Are you sure you want to ${actionText} for ${memberName}?`)) {
        return;
    }

    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';

    postJson(`/admin/api/member/${membershipId}/${endpoint}`, {})
        .then((data) => {
            if (data.status === 'success') {
                // Pangitaon ang container card sang member para ma-update ang Status Text
                const card = button.closest('.card') || button.closest('.member-card') || button.parentElement.parentElement;
                const statusElement = card ? card.querySelector('.member-status-text, [class*="status"]') : null;

                if (endpoint === 'check-in') {
                    button.classList.remove('btn-success', 'btn-primary');
                    button.classList.add('checked-in', 'btn-danger');
                    button.textContent = '🛑 Check Out';

                    if (statusElement && statusElement.textContent.includes('Status:')) {
                        statusElement.textContent = 'Status: Checked In';
                    }
                } else {
                    button.classList.remove('checked-in', 'btn-danger');
                    button.classList.add('btn-primary', 'btn-success');
                    button.textContent = '✓ Check In';

                    if (statusElement && statusElement.textContent.includes('Status:')) {
                        statusElement.textContent = 'Status: Checked Out';
                    }
                }

                showNotification('success', data.message || 'Updated successfully.');
                
                // Reload para mag-sync ang tanan nga data fields kag Renew Membership button state
                setTimeout(() => {
                    window.location.reload();
                }, 800);
            } else {
                alert(data.message || 'Error updating status');
                button.textContent = originalText;
                button.disabled = false;
            }
        })
        .catch((error) => {
            console.error('Check-In/Out Error:', error);
            button.textContent = originalText;
            button.disabled = false;
            showNotification('danger', error.message || 'An error occurred.');
        });
}

// === ATTENDANCE HISTORY MODAL ===
function showHistory(membershipId, memberName) {
    const historyModalElement = document.getElementById('historyModal');
    if (!historyModalElement) {
        console.warn('historyModal element not found in DOM.');
        return;
    }

    // Safe Bootstrap Modal Initialization Fallback
    let modalInstance = null;
    if (typeof bootstrap !== 'undefined' && bootstrap.Modal) {
        modalInstance = bootstrap.Modal.getInstance(historyModalElement) || new bootstrap.Modal(historyModalElement);
    }

    const title = document.getElementById('historyTitle');
    const content = document.getElementById('historyContent');

    if (title) {
        title.textContent = `Attendance History - ${memberName}`;
    }

    if (content) {
        content.innerHTML = `
            <div class="text-center py-4">
                <div class="spinner-border text-primary" role="status">
                    <span class="visually-hidden">Loading...</span>
                </div>
            </div>`;
    }

    if (modalInstance) {
        modalInstance.show();
    } else {
        // Vanilla CSS fallback display if Bootstrap JS bundle isn't available
        historyModalElement.style.display = 'block';
        historyModalElement.classList.add('show');
    }

    fetch(`/admin/api/member/${membershipId}/attendance`)
        .then((response) => response.json())
        .then((data) => {
            if (data.status !== 'success') {
                throw new Error(data.message || 'Unable to load attendance history');
            }

            let html = `
                <div class="mb-3 p-2 bg-light rounded">
                    <p class="mb-1"><strong>Total Hours Credited:</strong> ${Number(data.total_hours || 0).toFixed(2)} hrs</p>
                    <p class="mb-0"><strong>Hours Remaining:</strong> ${Number(data.hours_left || 0).toFixed(2)} hrs</p>
                </div>`;

            if (Array.isArray(data.attendance) && data.attendance.length > 0) {
                html += `
                <div class="table-responsive">
                    <table class="table table-sm table-striped attendance-table">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Check-In</th>
                                <th>Check-Out</th>
                                <th>Hours</th>
                            </tr>
                        </thead>
                        <tbody>`;

                data.attendance.forEach((log) => {
                    html += `
                            <tr>
                                <td>${log.date || '-'}</td>
                                <td>${log.check_in || '-'}</td>
                                <td>${log.check_out || '-'}</td>
                                <td>${log.hours || '-'}</td>
                            </tr>`;
                });

                html += `
                        </tbody>
                    </table>
                </div>`;
            } else {
                html += '<p class="text-muted text-center py-3">No attendance records yet.</p>';
            }

            if (content) {
                content.innerHTML = html;
            }
        })
        .catch((error) => {
            console.error('History Fetch Error:', error);
            if (content) {
                content.innerHTML = `<p class="text-danger text-center py-3">${error.message || 'Error loading attendance history.'}</p>`;
            }
        });
}

// === APPROVE MEMBERSHIP ===
function approveMembership(membershipId, memberName) {
    if (!window.confirm(`Approve membership for ${memberName}?`)) {
        return;
    }

    postJson(`/admin/approve_membership/${membershipId}`)
        .then(() => {
            showNotification('success', 'Membership approved successfully!');
            setTimeout(() => location.reload(), 1200);
        })
        .catch((error) => {
            showNotification('danger', error.message || 'Error approving membership');
        });
}

// === REJECT MEMBERSHIP ===
function rejectMembership(membershipId, memberName) {
    if (!window.confirm(`Reject membership for ${memberName}?`)) {
        return;
    }

    postJson(`/admin/reject_membership/${membershipId}`)
        .then(() => {
            showNotification('success', 'Membership rejected.');
            setTimeout(() => location.reload(), 1200);
        })
        .catch((error) => {
            showNotification('danger', error.message || 'Error rejecting membership');
        });
}

// === FILTER / SEARCH MEMBERS ===
function filterMembers(searchText) {
    const cards = document.querySelectorAll('.member-card');
    const normalized = (searchText || '').toLowerCase().trim();

    cards.forEach((card) => {
        const text = card.textContent.toLowerCase();
        card.style.display = text.includes(normalized) ? '' : 'none';
    });
}

// === DYNAMIC TOAST / ALERT NOTIFICATION ===
function showNotification(type, message) {
    const container = document.querySelector('.container-fluid') || document.body;
    if (!container) return;

    const alertWrapper = document.createElement('div');
    alertWrapper.className = `alert alert-${type} alert-dismissible fade show position-relative mt-2`;
    alertWrapper.role = 'alert';
    alertWrapper.style.zIndex = '9999';
    alertWrapper.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;

    container.insertBefore(alertWrapper, container.firstElementChild);

    // Precise element removal to prevent alert stacking bugs
    setTimeout(() => {
        alertWrapper.classList.remove('show');
        setTimeout(() => alertWrapper.remove(), 300);
    }, 4000);
}