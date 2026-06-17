document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('resSearch');
    const tableRows = document.querySelectorAll('.custom-table tbody tr');

    if (searchInput) {
        searchInput.addEventListener('keyup', function(e) {
            const term = e.target.value.toLowerCase();

            tableRows.forEach(row => {
                const text = row.textContent.toLowerCase();
                if (text.includes(term)) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        });
    }

    const receiptModal = document.getElementById('receipt-modal');
    const receiptModalImage = document.getElementById('receipt-modal-image');
    const receiptModalClose = document.getElementById('receipt-modal-close');
    const receiptLinks = document.querySelectorAll('.receipt-link');

    receiptLinks.forEach(link => {
        link.addEventListener('click', function(event) {
            event.preventDefault();
            const imageSrc = this.dataset.img;
            if (!imageSrc) {
                return;
            }
            receiptModalImage.src = imageSrc;
            receiptModal.classList.remove('d-none');
        });
    });

    if (receiptModalClose) {
        receiptModalClose.addEventListener('click', function() {
            receiptModal.classList.add('d-none');
        });
    }

    if (receiptModal) {
        receiptModal.addEventListener('click', function(event) {
            if (event.target === receiptModal) {
                receiptModal.classList.add('d-none');
            }
        });
    }
});