/**
 * =========================================
 * ADMIN MEMBERS PAGE - JavaScript Logic
 * Handling Tabs, Modals, and Search
 * =========================================
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // === 1. TAB SWITCHING LOGIC ===
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.getAttribute('data-tab');

            // Remove active class from all buttons and panels
            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabPanels.forEach(panel => panel.classList.remove('active'));

            // Add active class to clicked button and target panel
            button.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });

    // === 2.a MOCK: Membership Requests injection (frontend-only) ===
    const requestsList = document.getElementById('requestsList');
    let mockMode = false;

    function showAlert(message, type = 'info') {
        showToast(message, type);
    }

    function createRequestCard(req, container, useMock) {
        const card = document.createElement('div');
        card.className = 'request-card';
        card.setAttribute('data-request', JSON.stringify(req));

        const info = document.createElement('div');
        info.className = 'request-info';
        info.innerHTML = `<h3 class="customer-name">${req.user?.name || 'Unknown'}</h3>
            <p class="detail-text">Email: ${req.user?.email || 'N/A'}</p>
            <p class="detail-text">Contact Number: ${req.user?.phone || 'N/A'}</p>`;

        const plan = document.createElement('div');
        plan.className = 'request-plan';
        const created = new Date(req.created_at || Date.now()).toLocaleString();
        plan.innerHTML = `<h4 class="column-title">Selected Plan</h4>
            <p class="plan-name">${req.plan_name || 'N/A'}</p>
            <p class="detail-text">Date Requested: ${created}</p>`;

        const pay = document.createElement('div');
        pay.className = 'request-payment';
        pay.innerHTML = `<h4 class="column-title">Payment Verification</h4>
            <button class="btn-check-receipt">Check</button>`;

        const actions = document.createElement('div');
        actions.className = 'request-actions';

        const approveForm = document.createElement('form');
        approveForm.method = 'POST';
        approveForm.action = '#';
        approveForm.innerHTML = `<button type="submit" class="btn-approve">Approve</button>`;

        const rejectForm = document.createElement('form');
        rejectForm.method = 'POST';
        rejectForm.action = '#';
        rejectForm.innerHTML = `<button type="submit" class="btn-reject">Reject</button>`;

        actions.appendChild(approveForm);
        actions.appendChild(rejectForm);

        card.appendChild(info);
        card.appendChild(plan);
        card.appendChild(pay);
        card.appendChild(actions);

        container.appendChild(card);

        // Attach handlers
        const checkBtn = card.querySelector('.btn-check-receipt');
        checkBtn.addEventListener('click', () => {
            showAlert(`Mock: Open receipt for ${req.user?.name || 'user'}`);
        });

        if (useMock) {
            approveForm.addEventListener('submit', (e) => {
                e.preventDefault();
                card.style.opacity = 0.6;
                card.style.transition = 'opacity 0.25s';
                card.querySelector('.request-plan .plan-name').innerText += ' (Activated)';
                const btn = approveForm.querySelector('button');
                btn.innerText = 'Approved';
                btn.disabled = true;
                // Remove the card after a short delay to simulate backend update
                setTimeout(() => card.remove(), 800);
            });

            rejectForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const btn = rejectForm.querySelector('button');
                btn.innerText = 'Rejected';
                btn.disabled = true;
                card.style.opacity = 0.6;
                setTimeout(() => card.remove(), 600);
            });
        }
    }

    // Render server-provided membership request cards.
    // Disable/mock seeding for real deployments.
    if (requestsList) {
        try {
            const raw = JSON.parse(requestsList.getAttribute('data-requests') || '[]');
            const pending = (raw && raw.length) ? raw.filter(r => (r.status || '').toString().toLowerCase() === 'pending') : [];

            // If server already rendered cards, don't override.
            const existing = requestsList.querySelectorAll('.request-card');
            if (existing.length === 0 && pending.length > 0) {
                pending.forEach(r => createRequestCard(r, requestsList, false));
            }
        } catch (e) {
            console.warn('Failed to parse membership requests data', e);
        }
    }

    function openModal(modal) {
        if (!modal) return;
        modal.style.display = 'flex';
        modal.setAttribute('aria-hidden', 'false');
    }

    function closeModal(modal) {
        if (!modal) return;
        modal.style.display = 'none';
        modal.setAttribute('aria-hidden', 'true');
    }

    function createReceiptPreview(receiptUrl, requestName) {
        const body = document.getElementById('receiptModalBody');
        if (!body) return;
        body.innerHTML = '';

        if (!receiptUrl) {
            const placeholder = document.createElement('div');
            placeholder.className = 'records-empty-state';
            placeholder.innerHTML = `<p>No receipt has been uploaded for ${requestName} yet.</p>`;
            body.appendChild(placeholder);
            return;
        }

        const isImage = /\.(png|jpe?g|gif)$/i.test(receiptUrl);
        if (isImage) {
            const img = document.createElement('img');
            img.src = receiptUrl;
            img.alt = `Receipt for ${requestName}`;
            img.className = 'receipt-modal-image';
            body.appendChild(img);
            return;
        }

        const link = document.createElement('a');
        link.href = receiptUrl;
        link.target = '_blank';
        link.rel = 'noopener noreferrer';
        link.textContent = `Open receipt for ${requestName}`;
        link.className = 'btn-view-records';
        body.appendChild(link);
    }

    const receiptModal = document.getElementById('receiptModal');
    const recordsModal = document.getElementById('recordsModal');

    document.querySelectorAll('.btn-check-receipt').forEach((btn) => {
        btn.addEventListener('click', () => {
            const receiptUrl = btn.dataset.receiptUrl;
            const requestName = btn.dataset.requestName || 'this request';
            createReceiptPreview(receiptUrl, requestName);
            openModal(receiptModal);
        });
    });

    document.querySelectorAll('.modal-close').forEach((btn) => {
        btn.addEventListener('click', (event) => {
            const modal = event.target.closest('.modal-overlay');
            closeModal(modal);
        });
    });

    document.querySelectorAll('.btn-view-records').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const membershipId = btn.dataset.membershipId;
            const body = document.getElementById('recordsModalBody');
            if (!body) return;
            if (!membershipId) {
                body.innerHTML = '<div class="records-empty-state"><p>No membership found for this user.</p></div>';
                openModal(recordsModal);
                return;
            }

            body.innerHTML = '<p class="modal-placeholder">Loading attendance history...</p>';
            openModal(recordsModal);

            try {
                const response = await fetch(`/admin/api/member/${membershipId}/attendance`);
                const data = await response.json();
                if (!response.ok || data.status !== 'success') {
                    body.innerHTML = `<div class="records-empty-state"><p>${data.message || 'Unable to get attendance history.'}</p></div>`;
                    return;
                }

                const table = document.createElement('table');
                table.className = 'records-table';
                table.innerHTML = `
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Check In</th>
                            <th>Check Out</th>
                            <th>Hours</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${data.attendance.map(log => `
                            <tr>
                                <td>${log.date}</td>
                                <td>${log.check_in}</td>
                                <td>${log.check_out}</td>
                                <td>${log.hours}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                `;

                body.innerHTML = `<div class="records-empty-state"><p><strong>${data.member_name}</strong> attendance history</p></div>`;
                body.appendChild(table);
            } catch (err) {
                body.innerHTML = `<div class="records-empty-state"><p>${err.message || 'Unable to retrieve history.'}</p></div>`;
            }
        });
    });

    document.querySelectorAll('.btn-check-in').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const membershipId = btn.dataset.membershipId;
            const isCheckedIn = btn.dataset.isCheckedIn === 'true';
            if (!membershipId) return;

            const action = isCheckedIn ? 'end session' : 'check in';
            const confirmMessage = isCheckedIn ? 'End the active session for this member?' : 'Check in this member now?';
            if (!window.confirm(confirmMessage)) return;

            const endpoint = isCheckedIn ? `/admin/api/member/${membershipId}/check-out` : `/admin/api/member/${membershipId}/check-in`;
            const options = { method: 'POST' };

            try {
                const response = await fetch(endpoint, options);
                const result = await response.json();
                if (!response.ok || result.status !== 'success') {
                    showAlert(result.message || 'Membership action failed.');
                    return;
                }
                showAlert(result.message, 'success');
                window.location.reload();
            } catch (err) {
                showAlert(err.message || 'Membership action failed.');
            }
        });
    });


    // === 3. ADMIN MEMBER ACTIONS (Renew / Deactivate) ===
    async function postJson(url, payload) {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await resp.json().catch(() => ({}));
        if (!resp.ok) {
            const msg = data && data.message ? data.message : `Request failed (HTTP ${resp.status})`;
            throw new Error(msg);
        }
        return data;
    }

    document.querySelectorAll('.btn-renew').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const userId = btn.getAttribute('data-user-id');
            if (!userId) return;

            const prevText = btn.innerText;
            btn.disabled = true;
            btn.innerText = 'Renewing...';

            try {
                const url = '/admin/renew_member';
                console.log('Renew POST:', url, { user_id: Number(userId) });
                await postJson(url, { user_id: Number(userId) });
                showAlert('Membership renewed successfully.');
                window.location.reload();
            } catch (err) {
                showAlert(err && err.message ? err.message : 'Renew failed.');
            } finally {
                btn.disabled = false;
                btn.innerText = prevText;
            }
        });
    });

    document.querySelectorAll('.btn-deactivate').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const userId = btn.getAttribute('data-user-id');
            if (!userId) return;

            const confirmed = await confirmAction('Deactivate member?', 'Deactivate this member account?', 'Deactivate', 'Cancel');
            if (!confirmed) return;

            const prevText = btn.innerText;
            btn.disabled = true;
            btn.innerText = 'Deactivating...';

            try {
                await postJson('/admin/deactivate_member', { user_id: Number(userId) });
                showAlert('Account deactivated successfully.');
                window.location.reload();
            } catch (err) {
                showAlert(err && err.message ? err.message : 'Deactivation failed.');
            } finally {
                btn.disabled = false;
                btn.innerText = prevText;
            }
        });
    });

    document.querySelectorAll('.btn-reactivate').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const userId = btn.getAttribute('data-user-id');
            if (!userId) return;

            const prevText = btn.innerText;
            btn.disabled = true;
            btn.innerText = 'Reactivating...';

            try {
                await postJson('/admin/reactivate_member', { user_id: Number(userId) });
                showAlert('Account reactivated successfully.');
                window.location.reload();
            } catch (err) {
                showAlert(err && err.message ? err.message : 'Reactivation failed.');
            } finally {
                btn.disabled = false;
                btn.innerText = prevText;
            }
        });
    });

    document.querySelectorAll('.btn-delete-member').forEach((btn) => {
        btn.addEventListener('click', async () => {
            const userId = btn.getAttribute('data-user-id');
            if (!userId) return;

            const confirmed = await confirmAction('Delete account?', 'This will permanently delete all data for this account. Are you sure?', 'Delete', 'Cancel');
            if (!confirmed) return;

            const prevText = btn.innerText;
            btn.disabled = true;
            btn.innerText = 'Deleting...';

            try {
                await postJson(`/admin/delete_member/${Number(userId)}`, {});
                showAlert('Account permanently deleted.');
                window.location.reload();
            } catch (err) {
                showAlert(err && err.message ? err.message : 'Delete failed.');
            } finally {
                btn.disabled = false;
                btn.innerText = prevText;
            }
        });
    });


    // === 4. MEMBER LIST SEARCH FILTER ===
    const searchInput = document.getElementById('memberListSearch');
    const memberCards = document.querySelectorAll('#list .member-list-card');
    const deactivatedSearchInput = document.getElementById('deactivatedListSearch');
    const deactivatedFilterDate = document.getElementById('deactivatedDateFilter');
    const deactivatedCards = document.querySelectorAll('#deactivated .member-list-card');

    if (searchInput) {
        searchInput.addEventListener('keyup', function() {
            const searchTerm = searchInput.value.toLowerCase();

            memberCards.forEach(card => {
                const cardText = card.getAttribute('data-searchable') || '';
                if (cardText.toLowerCase().includes(searchTerm)) {
                    card.style.display = 'grid'; // Maintain grid layout
                } else {
                    card.style.display = 'none';
                }
            });
        });
    }

    if (deactivatedSearchInput || deactivatedFilterDate) {
        const filterDeactivated = () => {
            const searchTerm = deactivatedSearchInput ? deactivatedSearchInput.value.toLowerCase() : '';
            const selectedDate = deactivatedFilterDate ? deactivatedFilterDate.value : '';

            deactivatedCards.forEach(card => {
                const searchable = card.getAttribute('data-searchable') || '';
                const deactivatedDate = card.getAttribute('data-deactivated-date') || '';
                const matchesText = !searchTerm || searchable.toLowerCase().includes(searchTerm);
                const matchesDate = !selectedDate || deactivatedDate >= selectedDate;

                if (matchesText && matchesDate) {
                    card.style.display = 'grid';
                } else {
                    card.style.display = 'none';
                }
            });
        };

        if (deactivatedSearchInput) {
            deactivatedSearchInput.addEventListener('keyup', filterDeactivated);
        }
        if (deactivatedFilterDate) {
            deactivatedFilterDate.addEventListener('change', filterDeactivated);
        }
    }

    // === 4. DATE DISPLAY ===
    const dateDisplay = id => {
        const element = document.getElementById(id);
        if (element) {
            const now = new Date();
            const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
            element.innerText = now.toLocaleDateString('en-US', options);
        }
    };
    dateDisplay('currentDateDisplay');

});