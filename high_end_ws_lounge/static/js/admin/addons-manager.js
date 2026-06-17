/**
 * Add-ons System Manager
 * 
 * Handles:
 * - Loading available add-ons from API
 * - Managing add-on selection and quantities
 * - Real-time calculation of add-on subtotal
 * - Updating reservation total with add-ons
 * - Displaying add-on summary
 * 
 * Usage:
 *   const manager = new AddOnsManager({
 *       containerSelector: '#addons-container',
 *       onSubtotalChange: updateTotal
 *   });
 *   manager.initialize();
 */

class AddOnsManager {
    constructor(options = {}) {
        this.containerSelector = options.containerSelector || '#addons-container';
        this.addonsJsonFieldSelector = options.addonsJsonFieldSelector || '#addons_json';
        this.addonSubtotalFieldSelector = options.addonSubtotalFieldSelector || '#addon_subtotal';
        this.onSubtotalChange = options.onSubtotalChange || null;
        
        this.addons = [];
        this.selectedAddons = new Map(); // Map<addon_id, {addon, quantity}>
        this.baseRoomRate = 0;
        this.extraFee = 0;
        this.discountRate = 0;
    }

    /**
     * Initialize the add-ons manager
     * Loads available add-ons from API and sets up UI
     */
    async initialize() {
        try {
            // Load available add-ons from API
            await this.loadAddons();
            
            // Render add-ons UI
            this.render();
            
            // Attach event listeners
            this.attachEventListeners();
            
            console.log('Add-ons manager initialized successfully');
        } catch (error) {
            console.error('Error initializing add-ons manager:', error);
        }
    }

    /**
     * Load available add-ons from the API
     */
    async loadAddons() {
        try {
            const response = await fetch('/api/addons', {
                method: 'GET',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            if (!response.ok) {
                throw new Error(`Failed to load add-ons: ${response.statusText}`);
            }
            
            const data = await response.json();
            this.addons = data.addons || [];
            
            console.log(`Loaded ${this.addons.length} available add-ons`);
        } catch (error) {
            console.error('Error loading add-ons:', error);
            this.addons = [];
        }
    }

    /**
     * Render the add-ons selection UI
     */
    render() {
        const container = document.querySelector(this.containerSelector);
        if (!container) {
            console.warn(`Container not found: ${this.containerSelector}`);
            return;
        }

        // Clear container
        container.innerHTML = '';

        if (this.addons.length === 0) {
            container.innerHTML = '<p class="text-muted">No add-ons available</p>';
            return;
        }

        // Create add-ons list
        const addonsHtml = this.addons.map(addon => this.createAddonItemHtml(addon)).join('');
        container.innerHTML = `
            <div class="addons-section">
                <h5 class="addons-title">
                    <i class="bi bi-plus-circle"></i> Add-ons
                </h5>
                <div class="addons-list">
                    ${addonsHtml}
                </div>
                <div class="addons-summary mt-3" id="addons-summary">
                    <!-- Summary will be displayed here -->
                </div>
            </div>
        `;

        this.updateSummary();
    }

    /**
     * Create HTML for a single add-on item
     */
    createAddonItemHtml(addon) {
        const isSelected = this.selectedAddons.has(addon.id);
        const selectedData = isSelected ? this.selectedAddons.get(addon.id) : { quantity: 1 };
        
        const quantityInput = addon.requires_quantity
            ? `<div class="addon-quantity-control">
                   <label class="addon-quantity-label">Quantity:</label>
                   <div class="quantity-input-group">
                       <button type="button" class="qty-btn qty-minus" data-addon-id="${addon.id}" data-action="minus">−</button>
                       <input type="number" class="addon-quantity-input" data-addon-id="${addon.id}" 
                              value="${selectedData.quantity}" min="${addon.min_quantity}" max="${addon.max_quantity}" readonly>
                       <button type="button" class="qty-btn qty-plus" data-addon-id="${addon.id}" data-action="plus">+</button>
                   </div>
               </div>`
            : '';

        return `
            <div class="addon-item ${isSelected ? 'selected' : ''}" data-addon-id="${addon.id}">
                <div class="addon-header">
                    <input type="checkbox" class="addon-checkbox" data-addon-id="${addon.id}" 
                           ${isSelected ? 'checked' : ''}>
                    <div class="addon-info">
                        <label class="addon-name">${addon.name}</label>
                        <small class="addon-description">${addon.description || ''}</small>
                    </div>
                    <span class="addon-price">₱${addon.unit_price.toFixed(2)}</span>

                </div>
                ${quantityInput}
                <div class="addon-subtotal">
                    Subtotal: <span class="addon-subtotal-value">₱${(selectedData.quantity * addon.unit_price).toFixed(2)}</span>
                </div>
            </div>
        `;
    }

    /**
     * Attach event listeners for add-on interactions
     */
    attachEventListeners() {
        const container = document.querySelector(this.containerSelector);
        if (!container) return;

        // Checkbox listeners
        container.querySelectorAll('.addon-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => this.handleAddonToggle(e));
        });

        // Quantity increment/decrement listeners
        container.querySelectorAll('.qty-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.handleQuantityChange(e));
        });

        // Quantity input listeners
        container.querySelectorAll('.addon-quantity-input').forEach(input => {
            input.addEventListener('change', (e) => this.handleQuantityInputChange(e));
        });
    }

    /**
     * Handle add-on checkbox toggle
     */
    handleAddonToggle(event) {
        const checkbox = event.target;
        const addonId = parseInt(checkbox.dataset.addonId);
        const addon = this.addons.find(a => a.id === addonId);

        if (!addon) return;

        if (checkbox.checked) {
            // Add add-on to selection
            this.selectedAddons.set(addonId, {
                addon: addon,
                quantity: 1
            });
        } else {
            // Remove add-on from selection
            this.selectedAddons.delete(addonId);
        }

        this.updateSummary();
        this.persistAddons();
    }

    /**
     * Handle quantity increment/decrement buttons
     */
    handleQuantityChange(event) {
        event.preventDefault();
        
        const btn = event.target;
        const addonId = parseInt(btn.dataset.addonId);
        const action = btn.dataset.action;
        const addon = this.addons.find(a => a.id === addonId);

        if (!addon || !this.selectedAddons.has(addonId)) return;

        const selectedData = this.selectedAddons.get(addonId);
        let newQuantity = selectedData.quantity;

        if (action === 'plus') {
            if (newQuantity < addon.max_quantity) {
                newQuantity++;
            }
        } else if (action === 'minus') {
            if (newQuantity > addon.min_quantity) {
                newQuantity--;
            }
        }

        selectedData.quantity = newQuantity;
        
        // Update input field
        const input = document.querySelector(`input.addon-quantity-input[data-addon-id="${addonId}"]`);
        if (input) {
            input.value = newQuantity;
        }

        this.updateSummary();
        this.persistAddons();
    }

    /**
     * Handle direct quantity input changes
     */
    handleQuantityInputChange(event) {
        const input = event.target;
        const addonId = parseInt(input.dataset.addonId);
        const addon = this.addons.find(a => a.id === addonId);

        if (!addon || !this.selectedAddons.has(addonId)) return;

        let quantity = parseInt(input.value) || 1;
        
        // Validate quantity
        quantity = Math.max(addon.min_quantity, Math.min(addon.max_quantity, quantity));
        
        const selectedData = this.selectedAddons.get(addonId);
        selectedData.quantity = quantity;
        input.value = quantity;

        this.updateSummary();
        this.persistAddons();
    }

    /**
     * Update the add-ons summary display
     */
    updateSummary() {
        const summaryContainer = document.querySelector('#addons-summary');
        if (!summaryContainer) return;

        if (this.selectedAddons.size === 0) {
            summaryContainer.innerHTML = '<p class="text-muted">No add-ons selected</p>';
            this.updateSubtotalField(0);
            this.updateItemVisuals();
            this.triggerSubtotalChange();
            return;
        }

        const items = Array.from(this.selectedAddons.values()).map(({addon, quantity}) => {
            const subtotal = quantity * addon.unit_price;
            return `
                <div class="summary-item">
                    <span class="summary-item-name">${addon.name}</span>
                    ${addon.requires_quantity ? `<span class="summary-item-qty">(${quantity} ${quantity === 1 ? 'pc' : 'pcs'})</span>` : ''}
                    <span class="summary-item-price">₱${subtotal.toFixed(2)}</span>
                </div>
            `;
        });

        const total = this.calculateAddonsSubtotal();

        summaryContainer.innerHTML = `
            <div class="addons-summary-content">
                ${items.join('')}
                <div class="summary-total">
                    <strong>Selected Add-on Total: ₱${total.toFixed(2)}</strong>
                </div>

            </div>
        `;

        this.updateSubtotalField(total);
        this.updateItemVisuals();
        this.triggerSubtotalChange();
    }

    /**
     * Update selected item visual indicators
     */
    updateItemVisuals() {
        const container = document.querySelector(this.containerSelector);
        if (!container) return;

        container.querySelectorAll('.addon-item').forEach(item => {
            const addonId = parseInt(item.dataset.addonId);
            const isSelected = this.selectedAddons.has(addonId);
            
            if (isSelected) {
                item.classList.add('selected');
            } else {
                item.classList.remove('selected');
            }
        });
    }

    /**
     * Calculate total add-ons subtotal
     */
    calculateAddonsSubtotal() {
        let total = 0;
        this.selectedAddons.forEach(({addon, quantity}) => {
            total += quantity * addon.unit_price;
        });
        return total;
    }

    /**
     * Update the hidden addon_subtotal field
     */
    updateSubtotalField(amount) {
        const field = document.querySelector(this.addonSubtotalFieldSelector);
        if (field) {
            field.value = amount.toFixed(2);
        }
    }

    /**
     * Persist add-ons data to hidden JSON field
     */
    persistAddons() {
        const addonsData = Array.from(this.selectedAddons.entries()).map(([addonId, {addon, quantity}]) => ({
            addon_id: addonId,
            addon_name: addon.name,
            quantity: quantity,
            unit_price: addon.unit_price,
            subtotal: quantity * addon.unit_price
        }));

        const jsonField = document.querySelector(this.addonsJsonFieldSelector);
        if (jsonField) {
            jsonField.value = JSON.stringify(addonsData);
        }
    }

    /**
     * Trigger the onSubtotalChange callback
     */
    triggerSubtotalChange() {
        if (typeof this.onSubtotalChange === 'function') {
            const subtotal = this.calculateAddonsSubtotal();
            this.onSubtotalChange(subtotal);
        }
    }

    /**
     * Get selected add-ons data
     */
    getSelectedAddons() {
        return Array.from(this.selectedAddons.entries()).map(([addonId, {addon, quantity}]) => ({
            addon_id: addonId,
            addon_name: addon.name,
            quantity: quantity,
            unit_price: addon.unit_price,
            subtotal: quantity * addon.unit_price
        }));
    }

    /**
     * Load saved add-ons from JSON (for editing existing reservations)
     */
    loadAddonsFromJson(jsonString) {
        try {
            if (!jsonString) return;
            
            const addonsData = JSON.parse(jsonString);
            this.selectedAddons.clear();

            addonsData.forEach(data => {
                const addon = this.addons.find(a => a.id === data.addon_id);
                if (addon) {
                    this.selectedAddons.set(data.addon_id, {
                        addon: addon,
                        quantity: data.quantity
                    });
                }
            });

            this.updateSummary();
            this.render();
            this.attachEventListeners();
        } catch (error) {
            console.error('Error loading saved add-ons:', error);
        }
    }
}

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = AddOnsManager;
}
