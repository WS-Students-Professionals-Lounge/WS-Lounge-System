"""
addons_routes.py
Contains: API endpoints for add-ons management and retrieval

This module should be integrated into the admin blueprint:
    addon_bp = Blueprint('addons', __name__, url_prefix='/api/addons')
    ... (import and register routes)
    app.register_blueprint(addon_bp)
"""

import json
from datetime import datetime, timedelta

from database_fixed import (
    AddOn,
    Reservation,
    ReservationAddOn,
    WalkinAddOnlta,
    WalkinReservation,
    db,
)
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from sqlalchemy import func


def create_addons_blueprint(addon_bp=None):
    """Create and configure the add-ons blueprint"""
    if addon_bp is None:
        addon_bp = Blueprint('addons_api', __name__, url_prefix='/api/addons')
    
    # =====================================================================
    # GET ENDPOINTS
    # =====================================================================
    
    @addon_bp.route('/', methods=['GET'])
    def get_addons():
        """
        Get all active add-ons
        
        Returns:
            JSON response with list of active add-ons
        """
        try:
            addons = AddOn.query.filter_by(is_active=True).all()
            return jsonify({
                'status': 'success',
                'addons': [addon.to_dict() for addon in addons]
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to fetch add-ons: {str(e)}'
            }), 500

    @addon_bp.route('/<int:addon_id>', methods=['GET'])
    def get_addon(addon_id):
        """
        Get a specific add-on by ID
        
        Args:
            addon_id: ID of the add-on
            
        Returns:
            JSON response with add-on details
        """
        try:
            addon = AddOn.query.get(addon_id)
            if not addon:
                return jsonify({
                    'status': 'error',
                    'message': 'Add-on not found'
                }), 404
            
            return jsonify({
                'status': 'success',
                'addon': addon.to_dict()
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to fetch add-on: {str(e)}'
            }), 500

    # =====================================================================
    # POST ENDPOINTS
    # =====================================================================
    
    @addon_bp.route('/create', methods=['POST'])
    @login_required
    def create_addon():
        """
        Create a new add-on (Admin only)
        
        Expected JSON payload:
        {
            "name": "Add-on Name",
            "description": "Description",
            "unit_price": 150.00,
            "requires_quantity": true,
            "min_quantity": 1,
            "max_quantity": 10
        }
        """
        if current_user.role != 'admin':
            return jsonify({
                'status': 'error',
                'message': 'Admin access required'
            }), 403
        
        try:
            data = request.get_json()
            
            # Validation
            if not data.get('name'):
                return jsonify({
                    'status': 'error',
                    'message': 'Add-on name is required'
                }), 400
            
            if not data.get('unit_price'):
                return jsonify({
                    'status': 'error',
                    'message': 'Unit price is required'
                }), 400
            
            # Check if add-on already exists
            existing = AddOn.query.filter_by(name=data['name']).first()
            if existing:
                return jsonify({
                    'status': 'error',
                    'message': 'Add-on with this name already exists'
                }), 409
            
            # Create new add-on
            addon = AddOn(
                name=data['name'],
                description=data.get('description', ''),
                unit_price=float(data['unit_price']),
                requires_quantity=data.get('requires_quantity', True),
                min_quantity=int(data.get('min_quantity', 1)),
                max_quantity=int(data.get('max_quantity', 100)),
                is_active=True
            )
            
            db.session.add(addon)
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Add-on created successfully',
                'addon': addon.to_dict()
            }), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': f'Failed to create add-on: {str(e)}'
            }), 500

    @addon_bp.route('/<int:addon_id>/update', methods=['POST'])
    @login_required
    def update_addon(addon_id):
        """
        Update an existing add-on (Admin only)
        """
        if current_user.role != 'admin':
            return jsonify({
                'status': 'error',
                'message': 'Admin access required'
            }), 403
        
        try:
            addon = AddOn.query.get(addon_id)
            if not addon:
                return jsonify({
                    'status': 'error',
                    'message': 'Add-on not found'
                }), 404
            
            data = request.get_json()
            
            # Update fields
            if 'name' in data:
                addon.name = data['name']
            if 'description' in data:
                addon.description = data['description']
            if 'unit_price' in data:
                addon.unit_price = float(data['unit_price'])
            if 'requires_quantity' in data:
                addon.requires_quantity = data['requires_quantity']
            if 'min_quantity' in data:
                addon.min_quantity = int(data['min_quantity'])
            if 'max_quantity' in data:
                addon.max_quantity = int(data['max_quantity'])
            if 'is_active' in data:
                addon.is_active = data['is_active']
            
            addon.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Add-on updated successfully',
                'addon': addon.to_dict()
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': f'Failed to update add-on: {str(e)}'
            }), 500

    @addon_bp.route('/<int:addon_id>/delete', methods=['POST'])
    @login_required
    def delete_addon(addon_id):
        """
        Delete an add-on by marking it as inactive (Admin only)
        """
        if current_user.role != 'admin':
            return jsonify({
                'status': 'error',
                'message': 'Admin access required'
            }), 403
        
        try:
            addon = AddOn.query.get(addon_id)
            if not addon:
                return jsonify({
                    'status': 'error',
                    'message': 'Add-on not found'
                }), 404
            
            addon.is_active = False
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Add-on deactivated successfully'
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': f'Failed to delete add-on: {str(e)}'
            }), 500

    # =====================================================================
    # RESERVATION ADD-ONS ENDPOINTS
    # =====================================================================
    
    @addon_bp.route('/reservation/<int:reservation_id>', methods=['GET'])
    def get_reservation_addons(reservation_id):
        """
        Get all add-ons for a specific reservation
        """
        try:
            reservation = Reservation.query.get(reservation_id)
            if not reservation:
                return jsonify({
                    'status': 'error',
                    'message': 'Reservation not found'
                }), 404
            
            addons = ReservationAddOn.query.filter_by(reservation_id=reservation_id).all()
            return jsonify({
                'status': 'success',
                'addons': [addon.to_dict() for addon in addons],
                'subtotal': sum(a.subtotal for a in addons)
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to fetch reservation add-ons: {str(e)}'
            }), 500

    @addon_bp.route('/reservation/<int:reservation_id>/add', methods=['POST'])
    def add_reservation_addon(reservation_id):
        """
        Add an add-on to a reservation
        
        Expected JSON payload:
        {
            "addon_id": 1,
            "quantity": 5
        }
        """
        try:
            reservation = Reservation.query.get(reservation_id)
            if not reservation:
                return jsonify({
                    'status': 'error',
                    'message': 'Reservation not found'
                }), 404
            
            data = request.get_json()
            addon_id = data.get('addon_id')
            quantity = int(data.get('quantity', 1))
            
            addon = AddOn.query.get(addon_id)
            if not addon:
                return jsonify({
                    'status': 'error',
                    'message': 'Add-on not found'
                }), 404
            
            # Check if add-on already exists for this reservation
            existing = ReservationAddOn.query.filter_by(
                reservation_id=reservation_id,
                addon_id=addon_id
            ).first()
            
            if existing:
                # Update quantity
                existing.quantity = quantity
                existing.calculate_subtotal()
            else:
                # Create new reservation add-on
                res_addon = ReservationAddOn(
                    reservation_id=reservation_id,
                    addon_id=addon_id,
                    quantity=quantity,
                    unit_price=addon.unit_price
                )
                res_addon.calculate_subtotal()
                db.session.add(res_addon)
            
            # Update reservation addon_subtotal
            total_addon_subtotal = db.session.query(func.sum(ReservationAddOn.subtotal)).filter_by(reservation_id=reservation_id).scalar() or 0
            reservation.addon_subtotal = total_addon_subtotal
            
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Add-on added successfully',
                'addon': existing.to_dict() if existing else res_addon.to_dict()
            }), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': f'Failed to add add-on: {str(e)}'
            }), 500

    @addon_bp.route('/reservation/<int:reservation_id>/remove/<int:addon_id>', methods=['POST'])
    def remove_reservation_addon(reservation_id, addon_id):
        """
        Remove an add-on from a reservation
        """
        try:
            res_addon = ReservationAddOn.query.filter_by(
                reservation_id=reservation_id,
                addon_id=addon_id
            ).first()
            
            if not res_addon:
                return jsonify({
                    'status': 'error',
                    'message': 'Add-on not found in reservation'
                }), 404
            
            db.session.delete(res_addon)
            
            # Update reservation addon_subtotal
            reservation = Reservation.query.get(reservation_id)
            total_addon_subtotal = db.session.query(func.sum(ReservationAddOn.subtotal)).filter_by(reservation_id=reservation_id).scalar() or 0
            reservation.addon_subtotal = total_addon_subtotal
            
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Add-on removed successfully'
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': f'Failed to remove add-on: {str(e)}'
            }), 500

    # =====================================================================
    # WALK-IN ADD-ONS ENDPOINTS
    # =====================================================================
    
    @addon_bp.route('/walkin/<int:walkin_id>', methods=['GET'])
    def get_walkin_addons(walkin_id):
        """
        Get all add-ons for a specific walk-in reservation
        """
        try:
            walkin = WalkinReservation.query.get(walkin_id)
            if not walkin:
                return jsonify({
                    'status': 'error',
                    'message': 'Walk-in reservation not found'
                }), 404
            
            addons = WalkinAddOn.query.filter_by(walkin_reservation_id=walkin_id).all()
            return jsonify({
                'status': 'success',
                'addons': [addon.to_dict() for addon in addons],
                'subtotal': sum(a.subtotal for a in addons)
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to fetch walk-in add-ons: {str(e)}'
            }), 500

    @addon_bp.route('/walkin/<int:walkin_id>/add', methods=['POST'])
    def add_walkin_addon(walkin_id):
        """
        Add an add-on to a walk-in reservation
        """
        try:
            walkin = WalkinReservation.query.get(walkin_id)
            if not walkin:
                return jsonify({
                    'status': 'error',
                    'message': 'Walk-in reservation not found'
                }), 404
            
            data = request.get_json()
            addon_id = data.get('addon_id')
            quantity = int(data.get('quantity', 1))
            
            addon = AddOn.query.get(addon_id)
            if not addon:
                return jsonify({
                    'status': 'error',
                    'message': 'Add-on not found'
                }), 404
            
            # Check if add-on already exists for this walk-in
            existing = WalkinAddOn.query.filter_by(
                walkin_reservation_id=walkin_id,
                addon_id=addon_id
            ).first()
            
            if existing:
                # Update quantity
                existing.quantity = quantity
                existing.calculate_subtotal()
            else:
                # Create new walk-in add-on
                walkin_addon = WalkinAddOn(
                    walkin_reservation_id=walkin_id,
                    addon_id=addon_id,
                    quantity=quantity,
                    unit_price=addon.unit_price
                )
                walkin_addon.calculate_subtotal()
                db.session.add(walkin_addon)
            
            # Update walk-in addon_subtotal
            total_addon_subtotal = db.session.query(func.sum(WalkinAddOn.subtotal)).filter_by(walkin_reservation_id=walkin_id).scalar() or 0
            walkin.addon_subtotal = total_addon_subtotal
            
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Add-on added successfully',
                'addon': existing.to_dict() if existing else walkin_addon.to_dict()
            }), 201
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': f'Failed to add add-on: {str(e)}'
            }), 500

    @addon_bp.route('/walkin/<int:walkin_id>/remove/<int:addon_id>', methods=['POST'])
    def remove_walkin_addon(walkin_id, addon_id):
        """
        Remove an add-on from a walk-in reservation
        """
        try:
            walkin_addon = WalkinAddOn.query.filter_by(
                walkin_reservation_id=walkin_id,
                addon_id=addon_id
            ).first()
            
            if not walkin_addon:
                return jsonify({
                    'status': 'error',
                    'message': 'Add-on not found in walk-in reservation'
                }), 404
            
            db.session.delete(walkin_addon)
            
            # Update walk-in addon_subtotal
            walkin = WalkinReservation.query.get(walkin_id)
            total_addon_subtotal = db.session.query(func.sum(WalkinAddOn.subtotal)).filter_by(walkin_reservation_id=walkin_id).scalar() or 0
            walkin.addon_subtotal = total_addon_subtotal
            
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Add-on removed successfully'
            }), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({
                'status': 'error',
                'message': f'Failed to remove add-on: {str(e)}'
            }), 500

    # =====================================================================
    # REPORTS ENDPOINTS
    # =====================================================================
    
    @addon_bp.route('/report/revenue', methods=['GET'])
    @login_required
    def get_addon_revenue_report():
        """
        Get add-on revenue report
        
        Optional query parameters:
        - start_date: YYYY-MM-DD
        - end_date: YYYY-MM-DD
        """
        if current_user.role not in ['admin', 'staff']:
            return jsonify({
                'status': 'error',
                'message': 'Access denied'
            }), 403
        
        try:
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            
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
            
            report_data = [{
                'addon_name': r[0],
                'total_quantity': r[1] or 0,
                'total_revenue': float(r[2]) if r[2] else 0.0,
                'count': r[3]
            } for r in results]
            
            total_revenue = sum(item['total_revenue'] for item in report_data)
            
            return jsonify({
                'status': 'success',
                'report': report_data,
                'total_revenue': total_revenue
            }), 200
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to generate report: {str(e)}'
            }), 500

    return addon_bp
