document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('memberSearchInput');
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            filterMembers(searchInput.value);
        });
    }

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

async function postJson(url, payload = {}) {
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Requested-With': 'XMLHttpRequest'
        },
        body: JSON.stringify(payload)
    });
    const data = await response.json();
    if (!response.ok || data.status !== 'success') {
        throw new Error(data.message || `Request failed with status ${response.status}`);
    }
    return data;
}

function toggleCheckInOut(membershipId, memberName, button) {
    if (!button) return;
    const endpoint = button.classList.contains('checked-in') ? 'check-out' : 'check-in';
    const originalText = button.textContent.trim();

    if (!window.confirm(`Are you sure you want to ${endpoint.replace('-', ' ')} for ${memberName}?`)) {
        return;
    }

    button.disabled = true;
    button.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';

    postJson(`/admin/api/member/${membershipId}/${endpoint}`)
        .then((data) => {
            if (endpoint === 'check-in') {
                button.classList.remove('btn-success');
                button.classList.add('checked-in');
                button.textContent = '🛑 End Session';
            } else {
                button.classList.remove('checked-in');
                button.classList.add('btn-success');
                button.textContent = '✓ Check-In';
            }
            showNotification('success', data.message || 'Membership updated.');
        })
        .catch((error) => {
            console.error(error);
            button.textContent = originalText;
            showNotification('danger', error.message || 'An error occurred.');
        })
        .finally(() => {
            button.disabled = false;
        });
}

function showHistory(membershipId, memberName) {
    const historyModalElement = document.getElementById('historyModal');
    if (!historyModalElement) return;

    const modal = new bootstrap.Modal(historyModalElement);
    const title = document.getElementById('historyTitle');
    const content = document.getElementById('historyContent');

    if (title) {
        title.textContent = `Attendance History - ${memberName}`;
    }

    if (content) {
        content.innerHTML = '<div class="text-center"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';
    }

    fetch(`/admin/api/member/${membershipId}/attendance`)
        .then((response) => response.json())
        .then((data) => {
            if (data.status !== 'success') {
                throw new Error(data.message || 'Unable to load attendance history');
            }

            let html = `<div class="mb-3">
                <p><strong>Total Hours Credited:</strong> ${Number(data.total_hours || 0).toFixed(2)} hrs</p>
                <p><strong>Hours Remaining:</strong> ${Number(data.hours_left || 0).toFixed(2)} hrs</p>
            </div>`;

            if (Array.isArray(data.attendance) && data.attendance.length > 0) {
                html += `<table class="table table-sm attendance-table">
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
                    html += `<tr>
                        <td>${log.date || '-'}</td>
                        <td>${log.check_in || '-'}</td>
                        <td>${log.check_out || '-'}</td>
                        <td>${log.hours || '-'}</td>
                    </tr>`;
                });

                html += '</tbody></table>';
            } else {
                html += '<p class="text-muted text-center">No attendance records yet.</p>';
            }

            if (content) {
                content.innerHTML = html;
            }
        })
        .catch((error) => {
            console.error(error);
            if (content) {
                content.innerHTML = '<p class="text-danger">Error loading attendance history.</p>';
            }
        });

    modal.show();
}

function approveMembership(membershipId, memberName) {
    if (!window.confirm(`Approve membership for ${memberName}?`)) {
        return;
    }

    postJson(`/admin/approve_membership/${membershipId}`)
        .then(() => {
            showNotification('success', 'Membership approved');
            setTimeout(() => location.reload(), 1500);
        })
        .catch((error) => {
            showNotification('danger', error.message || 'Error approving membership');
        });
}

function rejectMembership(membershipId, memberName) {
    if (!window.confirm(`Reject membership for ${memberName}?`)) {
        return;
    }

    postJson(`/admin/reject_membership/${membershipId}`)
        .then(() => {
            showNotification('success', 'Membership rejected');
            setTimeout(() => location.reload(), 1500);
        })
        .catch((error) => {
            showNotification('danger', error.message || 'Error rejecting membership');
        });
}

function filterMembers(searchText) {
    const cards = document.querySelectorAll('.member-card');
    const normalized = (searchText || '').toLowerCase();

    cards.forEach((card) => {
        const text = card.textContent.toLowerCase();
        card.style.display = text.includes(normalized) ? '' : 'none';
    });
}

function showNotification(type, message) {
    const alertHtml = `<div class="alert alert-${type} alert-dismissible fade show" role="alert">
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    </div>`;

    const container = document.querySelector('.container-fluid');
    if (!container) return;

    const alertWrapper = document.createElement('div');
    alertWrapper.innerHTML = alertHtml;
    container.insertBefore(alertWrapper.firstElementChild, container.firstElementChild);

    setTimeout(() => {
        const alert = document.querySelector('.alert');
        if (alert) {
            alert.remove();
        }
    }, 5000);
}
