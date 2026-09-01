document.addEventListener('DOMContentLoaded', function() {
    
    // === HELPER FALLBACKS (Prevents Uncaught ReferenceErrors) ===
    function showToastFallback(message, type = 'info') {
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
        } else {
            alert(`[${type.toUpperCase()}]: ${message}`);
        }
    }

    async function confirmActionFallback(title, message, confirmBtnText = 'Confirm', cancelBtnText = 'Cancel') {
        if (typeof window.confirmAction === 'function') {
            return await window.confirmAction(title, message, confirmBtnText, cancelBtnText);
        } else {
            return window.confirm(`${title}\n\n${message}`);
        }
    }

    function showAlert(message, type = 'info') {
        showToastFallback(message, type);
    }


    // === 1. TAB SWITCHING LOGIC ===
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');

    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const targetTab = button.getAttribute('data-tab');

            tabButtons.forEach(btn => btn.classList.remove('active'));
            tabPanels.forEach(panel => panel.classList.remove('active'));

            button.classList.add('active');
            const targetPanel = document.getElementById(targetTab);
            if (targetPanel) {
                targetPanel.classList.add('active');
            }
        });
    });


    // === 2. MODAL HELPER FUNCTIONS ===
    const receiptModal = document.getElementById('receiptModal');
    const recordsModal = document.getElementById('recordsModal');

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

        const isImage = /\.(png|jpe?g|gif|webp)$/i.test(receiptUrl);
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


    // === 3. MEMBERSHIP REQUEST CARD INJECTION ===
    function createRequestCard(req, container, useMock = false) {
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
            <button class="btn-check-receipt" data-receipt-url="${req.receipt_url || ''}" data-request-name="${req.user?.name || 'User'}">Check</button>`;

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

        // Attach receipt viewer logic to dynamic button
        const checkBtn = card.querySelector('.btn-check-receipt');
        checkBtn.addEventListener('click', () => {
            if (useMock) {
                showAlert(`Mock: Open receipt for ${req.user?.name || 'user'}`);
            } else {
                createReceiptPreview(req.receipt_url, req.user?.name || 'this request');
                openModal(receiptModal);
            }
        });

        if (useMock) {
            approveForm.addEventListener('submit', (e) => {
                e.preventDefault();
                card.style.opacity = '0.6';
                card.style.transition = 'opacity 0.25s';
                card.querySelector('.request-plan .plan-name').innerText += ' (Activated)';
                const btn = approveForm.querySelector('button');
                btn.innerText = 'Approved';
                btn.disabled = true;
                setTimeout(() => card.remove(), 800);
            });

            rejectForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const btn = rejectForm.querySelector('button');
                btn.innerText = 'Rejected';
                btn.disabled = true;
                card.style.opacity = '0.6';
                setTimeout(() => card.remove(), 600);
            });
        }
    }

    const requestsList = document.getElementById('requestsList');
    if (requestsList) {
        try {
            const raw = JSON.parse(requestsList.getAttribute('data-requests') || '[]');
            const pending = (raw && Array.isArray(raw)) ? raw.filter(r => (r.status || '').toString().toLowerCase() === 'pending') : [];

            const existing = requestsList.querySelectorAll('.request-card');
            if (existing.length === 0 && pending.length > 0) {
                pending.forEach(r => createRequestCard(r, requestsList, false));
            }
        } catch (e) {
            console.warn('Failed to parse membership requests data', e);
        }
    }


    // === 4. GLOBAL MODAL EVENT BINDINGS ===
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


    // === 5. ATTENDANCE RECORDS & CHECK-IN LOGIC ===
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

                if (!data.attendance || data.attendance.length === 0) {
                    body.innerHTML = `<div class="records-empty-state"><p>No attendance records recorded for <strong>${data.member_name || 'this member'}</strong>.</p></div>`;
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
                                <td>${log.date || 'N/A'}</td>
                                <td>${log.check_in || 'N/A'}</td>
                                <td>${log.check_out || 'N/A'}</td>
                                <td>${log.hours || '0'}</td>
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
            // Kuhaon ang membershipId O user-id bilang fallback
            const membershipId = btn.dataset.membershipId || btn.dataset.userId;
            const isCheckedIn = btn.dataset.isCheckedIn === 'true';
            
            if (!membershipId) {
                showAlert('User or Membership ID missing.', 'error');
                return;
            }

            const confirmMessage = isCheckedIn ? 'End the active session for this member?' : 'Check in this member now?';
            const confirmed = await confirmActionFallback(isCheckedIn ? 'End Session' : 'Check In', confirmMessage);
            if (!confirmed) return;

            const endpoint = isCheckedIn 
                ? `/admin/api/member/${membershipId}/check-out` 
                : `/admin/api/member/${membershipId}/check-in`;

            try {
                const response = await fetch(endpoint, { 
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' }
                });
                const result = await response.json().catch(() => ({}));

                if (!response.ok || result.status !== 'success') {
                    showAlert(result.message || 'Membership action failed.', 'error');
                    return;
                }
                showAlert(result.message || 'Action completed successfully.', 'success');
                window.location.reload();
            } catch (err) {
                showAlert(err.message || 'Membership action failed.', 'error');
            }
        });
    });


    // ADMIN MEMBER ACTIONS (Renew / Deactivate / Reactivate / Delete)
    async function postJson(url, payload) {
        // Kuhaon ang CSRF Token gikan sa HTML meta tag (kon naga-gamit sang Flask-WTF CSRF)
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content') || '';

        const headers = { 
            'Content-Type': 'application/json' 
        };
        if (csrfToken) {
            headers['X-CSRFToken'] = csrfToken;
        }

        const resp = await fetch(url, {
            method: 'POST',
            headers: headers,
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
                await postJson('/admin/renew_member', { user_id: Number(userId) });
                showAlert('Membership renewed successfully.', 'success');
                window.location.reload();
            } catch (err) {
                showAlert(err && err.message ? err.message : 'Renew failed.', 'error');
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

            const confirmed = await confirmActionFallback('Deactivate member?', 'Deactivate this member account?', 'Deactivate', 'Cancel');
            if (!confirmed) return;

            const prevText = btn.innerText;
            btn.disabled = true;
            btn.innerText = 'Deactivating...';

            try {
                await postJson('/admin/deactivate_member', { user_id: Number(userId) });
                showAlert('Account deactivated successfully.', 'success');
                window.location.reload();
            } catch (err) {
                showAlert(err && err.message ? err.message : 'Deactivation failed.', 'error');
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
                showAlert('Account reactivated successfully.', 'success');
                window.location.reload();
            } catch (err) {
                showAlert(err && err.message ? err.message : 'Reactivation failed.', 'error');
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

            const confirmed = await confirmActionFallback('Delete account?', 'This will permanently delete all data for this account. Are you sure?', 'Delete', 'Cancel');
            if (!confirmed) return;

            const prevText = btn.innerText;
            btn.disabled = true;
            btn.innerText = 'Deleting...';

            try {
                await postJson(`/admin/delete_member/${Number(userId)}`, {});
                showAlert('Account permanently deleted.', 'success');
                window.location.reload();
            } catch (err) {
                showAlert(err && err.message ? err.message : 'Delete failed.', 'error');
            } finally {
                btn.disabled = false;
                btn.innerText = prevText;
            }
        });
    });


    // === 7. SEARCH & FILTER LOGIC ===
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
                    card.style.display = 'grid';
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


    // === 8. DATE DISPLAY ===
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