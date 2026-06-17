-- ============================================================================
-- HIGH-END WORKSPACE LOUNGE - ADD-ONS SYSTEM MIGRATION
-- ============================================================================
-- 
-- This migration adds the complete Add-ons system to support:
-- 1. Multiple add-ons per reservation
-- 2. Quantity-based pricing
-- 3. Real-time calculations
-- 4. Add-on revenue tracking in reports
--
-- Tables Added:
--   - addons (master list of available add-ons)
--   - reservation_addons (add-ons selected per reservation)
--   - walkin_addons (add-ons selected per walk-in reservation)
--
-- Tables Modified:
--   - reservations (added addon_subtotal)
--   - walkin_reservations (added addon_subtotal)
--
-- ============================================================================

-- Step 1: Add addon_subtotal column to reservations table
-- ============================================================================
ALTER TABLE reservations ADD COLUMN addon_subtotal FLOAT DEFAULT 0.0;

-- Step 2: Add addon_subtotal column to walkin_reservations table
-- ============================================================================
ALTER TABLE walkin_reservations ADD COLUMN addon_subtotal FLOAT DEFAULT 0.0;

-- Step 3: Create addons table (master list of available add-ons)
-- ============================================================================
CREATE TABLE IF NOT EXISTS addons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(128) NOT NULL UNIQUE,
    description VARCHAR(255),
    unit_price FLOAT NOT NULL,
    requires_quantity BOOLEAN DEFAULT TRUE,
    min_quantity INT DEFAULT 1,
    max_quantity INT DEFAULT 100,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Step 4: Create reservation_addons table (add-ons per reservation)
-- ============================================================================
CREATE TABLE IF NOT EXISTS reservation_addons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    reservation_id INT NOT NULL,
    addon_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price FLOAT NOT NULL,
    subtotal FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (reservation_id) REFERENCES reservations(id) ON DELETE CASCADE,
    FOREIGN KEY (addon_id) REFERENCES addons(id) ON DELETE CASCADE,
    INDEX idx_reservation_id (reservation_id),
    INDEX idx_addon_id (addon_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Step 5: Create walkin_addons table (add-ons per walk-in reservation)
-- ============================================================================
CREATE TABLE IF NOT EXISTS walkin_addons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    walkin_reservation_id INT NOT NULL,
    addon_id INT NOT NULL,
    quantity INT NOT NULL DEFAULT 1,
    unit_price FLOAT NOT NULL,
    subtotal FLOAT DEFAULT 0.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (walkin_reservation_id) REFERENCES walkin_reservations(id) ON DELETE CASCADE,
    FOREIGN KEY (addon_id) REFERENCES addons(id) ON DELETE CASCADE,
    INDEX idx_walkin_reservation_id (walkin_reservation_id),
    INDEX idx_addon_id (addon_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Step 6: Insert default add-ons into addons table
-- ============================================================================
INSERT INTO addons (name, description, unit_price, requires_quantity, min_quantity, max_quantity, is_active)
VALUES 
    ('Projector', 'High-quality projector for presentations', 150.00, FALSE, 1, 1, TRUE),
    ('Extra Chairs', 'Additional chairs per piece', 50.00, TRUE, 1, 50, TRUE),
    ('Extension Cord', 'Electrical extension cord per piece', 100.00, TRUE, 1, 10, TRUE),
    ('Whiteboard Set', 'Complete whiteboard set with markers', 200.00, FALSE, 1, 1, TRUE),
    ('Flip Chart', 'Portable flip chart stand', 75.00, FALSE, 1, 1, TRUE),
    ('WiFi Booster', 'WiFi range extender', 120.00, FALSE, 1, 1, TRUE)
ON DUPLICATE KEY UPDATE unit_price=VALUES(unit_price);

-- ============================================================================
-- VERIFICATION QUERIES (run these to verify migration success)
-- ============================================================================

-- Check if addons table exists and has data
-- SELECT * FROM addons WHERE is_active = TRUE;

-- Check if reservation_addons table exists
-- DESCRIBE reservation_addons;

-- Check if walkin_addons table exists
-- DESCRIBE walkin_addons;

-- Check if addon_subtotal columns exist
-- SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'reservations' AND COLUMN_NAME = 'addon_subtotal';
-- SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'walkin_reservations' AND COLUMN_NAME = 'addon_subtotal';

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
