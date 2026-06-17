"""
addons_helper.py
Helper functions for processing add-ons in reservations and walk-ins

Usage in admin.py:
    from addons_helper import process_reservation_addons, process_walkin_addons
    
    # When saving a reservation
    addons_json = request.form.get('addons_json', '[]')
    process_reservation_addons(reservation.id, addons_json)
    
    # When saving a walk-in
    addons_json = request.form.get('addons_json', '[]')
    process_walkin_addons(walkin_reservation.id, addons_json)
"""

import json

from database_fixed import AddOn, ReservationAddOn, WalkinAddOn, db
from sqlalchemy import func


def process_reservation_addons(reservation_id, addons_json_str):
    """
    Process and save add-ons for a reservation
    
    Args:
        reservation_id: ID of the reservation
        addons_json_str: JSON string containing add-on selections
        
    Returns:
        dict with status and message
    """
    try:
        # Clear existing add-ons for this reservation
        ReservationAddOn.query.filter_by(reservation_id=reservation_id).delete()
        
        # Parse JSON if provided
        if not addons_json_str:
            return {'status': 'success', 'message': 'No add-ons to process'}
        
        try:
            addons_data = json.loads(addons_json_str)
        except json.JSONDecodeError:
            return {'status': 'error', 'message': 'Invalid add-ons JSON format'}
        
        if not addons_data or not isinstance(addons_data, list):
            return {'status': 'success', 'message': 'No add-ons selected'}
        
        total_addon_subtotal = 0

        def _normalize_quantity(raw_quantity):
            # Rules:
            # - missing/null/empty/whitespace => 1
            # - cannot convert to int => 1
            # - < 1 => 1
            if raw_quantity is None:
                return 1
            if isinstance(raw_quantity, str):
                if raw_quantity.strip() == '':
                    return 1
            try:
                qty = int(raw_quantity)
            except (ValueError, TypeError):
                return 1
            if qty < 1:
                return 1
            return qty
        
        # Process each add-on
        for addon_data in addons_data:
            try:
                addon_id = addon_data.get('addon_id')
                quantity = _normalize_quantity(addon_data.get('quantity', 1))
                unit_price = float(addon_data.get('unit_price', 0))
                
                if not addon_id or quantity < 1 or unit_price < 0:
                    continue
                
                # Verify the add-on exists
                addon = AddOn.query.get(addon_id)
                if not addon or not addon.is_active:
                    continue
                
                # Create reservation add-on record
                res_addon = ReservationAddOn(
                    reservation_id=reservation_id,
                    addon_id=addon_id,
                    quantity=quantity,
                    unit_price=unit_price
                )
                res_addon.calculate_subtotal()
                total_addon_subtotal += res_addon.subtotal
                
                db.session.add(res_addon)
            except (ValueError, TypeError, AttributeError) as e:
                print(f"Error processing add-on {addon_data}: {str(e)}")
                continue
        
        # Update reservation's addon_subtotal
        from database_fixed import Reservation
        reservation = Reservation.query.get(reservation_id)
        if reservation:
            reservation.addon_subtotal = total_addon_subtotal
        
        db.session.commit()
        
        return {
            'status': 'success',
            'message': f'Processed {len(addons_data)} add-ons',
            'total_addon_subtotal': total_addon_subtotal
        }
    
    except Exception as e:
        db.session.rollback()
        return {
            'status': 'error',
            'message': f'Failed to process add-ons: {str(e)}'
        }



def process_walkin_addons(walkin_reservation_id, addons_json_str):
    """
    Process and save add-ons for a walk-in reservation
    
    Args:
        walkin_reservation_id: ID of the walk-in reservation
        addons_json_str: JSON string containing add-on selections
        
    Returns:
        dict with status and message
    """
    try:
        # Clear existing add-ons for this walk-in
        WalkinAddOn.query.filter_by(walkin_reservation_id=walkin_reservation_id).delete()
        
        # Parse JSON if provided
        if not addons_json_str:
            return {'status': 'success', 'message': 'No add-ons to process'}
        
        try:
            addons_data = json.loads(addons_json_str)
        except json.JSONDecodeError:
            return {'status': 'error', 'message': 'Invalid add-ons JSON format'}
        
        if not addons_data or not isinstance(addons_data, list):
            return {'status': 'success', 'message': 'No add-ons selected'}
        
        total_addon_subtotal = 0

        def _normalize_quantity(raw_quantity):
            # Rules:
            # - missing/null/empty/whitespace => 1
            # - cannot convert to int => 1
            # - < 1 => 1
            if raw_quantity is None:
                return 1
            if isinstance(raw_quantity, str):
                if raw_quantity.strip() == '':
                    return 1
            try:
                qty = int(raw_quantity)
            except (ValueError, TypeError):
                return 1
            if qty < 1:
                return 1
            return qty
        
        # Process each add-on
        for addon_data in addons_data:
            try:
                addon_id = addon_data.get('addon_id')
                quantity = _normalize_quantity(addon_data.get('quantity', 1))
                unit_price = float(addon_data.get('unit_price', 0))
                
                if not addon_id or quantity < 1 or unit_price < 0:
                    continue
                
                # Verify the add-on exists
                addon = AddOn.query.get(addon_id)
                if not addon or not addon.is_active:
                    continue
                
                # Create walk-in add-on record
                walkin_addon = WalkinAddOn(
                    walkin_reservation_id=walkin_reservation_id,
                    addon_id=addon_id,
                    quantity=quantity,
                    unit_price=unit_price
                )
                walkin_addon.calculate_subtotal()
                total_addon_subtotal += walkin_addon.subtotal
                
                db.session.add(walkin_addon)
            except (ValueError, TypeError, AttributeError) as e:
                print(f"Error processing add-on {addon_data}: {str(e)}")
                continue
        
        # Update walk-in's addon_subtotal
        from database_fixed import WalkinReservation
        walkin = WalkinReservation.query.get(walkin_reservation_id)
        if walkin:
            walkin.addon_subtotal = total_addon_subtotal
        
        db.session.commit()
        
        return {
            'status': 'success',
            'message': f'Processed {len(addons_data)} add-ons',
            'total_addon_subtotal': total_addon_subtotal
        }
    
    except Exception as e:
        db.session.rollback()
        return {
            'status': 'error',
            'message': f'Failed to process add-ons: {str(e)}'
        }



def get_reservation_addons_summary(reservation_id):
    """
    Get a formatted summary of add-ons for a reservation
    
    Args:
        reservation_id: ID of the reservation
        
    Returns:
        dict with addons list and total
    """
    addons = ReservationAddOn.query.filter_by(reservation_id=reservation_id).all()
    
    summary = {
        'addons': [],
        'total': 0.0
    }
    
    for addon in addons:
        summary['addons'].append({
            'name': addon.addon.name if addon.addon else 'Unknown',
            'quantity': addon.quantity,
            'unit_price': addon.unit_price,
            'subtotal': addon.subtotal
        })
        summary['total'] += addon.subtotal
    
    return summary


def get_walkin_addons_summary(walkin_id):
    """
    Get a formatted summary of add-ons for a walk-in reservation
    
    Args:
        walkin_id: ID of the walk-in reservation
        
    Returns:
        dict with addons list and total
    """
    addons = WalkinAddOn.query.filter_by(walkin_reservation_id=walkin_id).all()
    
    summary = {
        'addons': [],
        'total': 0.0
    }
    
    for addon in addons:
        summary['addons'].append({
            'name': addon.addon.name if addon.addon else 'Unknown',
            'quantity': addon.quantity,
            'unit_price': addon.unit_price,
            'subtotal': addon.subtotal
        })
        summary['total'] += addon.subtotal
    
    return summary


def get_addon_revenue_by_date_range(start_date=None, end_date=None):
    """
    Get add-on revenue report for a date range
    
    Args:
        start_date: datetime object or string (YYYY-MM-DD)
        end_date: datetime object or string (YYYY-MM-DD)
        
    Returns:
        dict with revenue data
    """
    query = db.session.query(
        AddOn.name,
        func.sum(ReservationAddOn.quantity).label('total_quantity'),
        func.sum(ReservationAddOn.subtotal).label('total_revenue'),
        func.count(ReservationAddOn.id).label('count')
    ).join(ReservationAddOn, AddOn.id == ReservationAddOn.addon_id)
    
    if start_date:
        query = query.filter(ReservationAddOn.created_at >= start_date)
    if end_date:
        query = query.filter(ReservationAddOn.created_at <= end_date)
    
    results = query.group_by(AddOn.name).all()
    
    report_data = []
    total_revenue = 0
    
    for row in results:
        addon_revenue = float(row.total_revenue) if row.total_revenue else 0.0
        report_data.append({
            'addon_name': row.name,
            'total_quantity': row.total_quantity or 0,
            'total_revenue': addon_revenue,
            'count': row.count or 0
        })
        total_revenue += addon_revenue
    
    return {
        'addons': report_data,
        'total_revenue': total_revenue,
        'start_date': start_date,
        'end_date': end_date
    }
