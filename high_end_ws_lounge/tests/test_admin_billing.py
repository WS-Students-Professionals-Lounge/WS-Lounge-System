import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from admin import calculate_admin_total_amount


def test_calculate_admin_total_includes_addons_discount_and_fees():
    total = calculate_admin_total_amount(
        room_rate=150,
        duration_hours=1,
        extra_fee=25,
        addon_subtotal=300,
        discount_rate=0.1,
        is_open_time=False,
    )

    assert total == 460.0


def test_calculate_admin_total_includes_addons_for_open_time():
    total = calculate_admin_total_amount(
        room_rate=150,
        duration_hours=1,
        extra_fee=25,
        addon_subtotal=300,
        discount_rate=0.1,
        is_open_time=True,
    )

    assert total == 460.0
