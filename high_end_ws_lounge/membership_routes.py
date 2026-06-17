"""
membership_routes.py
Membership management routes for admin panel - Official Members page and check-in/check-out functionality
"""

from datetime import datetime
from flask import Blueprint, render_template, jsonify, request, url_for, redirect, flash
from flask_login import login_required, current_user
from database_fixed import db, Membership, AttendanceLog, User
from admin import require_admin_or_staff, require_admin_or_staff_json

# Create a separate blueprint for membership routes to keep admin.py clean
membership_bp = Blueprint("membership", __name__, url_prefix="/admin/membership")


# ===================================================================
# Official Members Page - Card Layout View
# ===================================================================
@membership_bp.route("/official-members", methods=["GET"])
@login_required
def official_members():
    """Display all members with active memberships as cards"""
    redirect_response = require_admin_or_staff()
    if redirect_response:
        return redirect_response
    
    # Get all members with memberships
    memberships = Membership.query.all()
    
    # Organize by status
    active_members = []
    expired_members = []
    pending_members = []
    
    for membership in memberships:
        member_data = {
            'membership_id': membership.id,
            'user_id': membership.user_id,
            'user_name': membership.user.name if membership.user else 'Unknown',
            'user_email': membership.user.email if membership.user else 'Unknown',
            'user_phone': membership.user.phone if membership.user else 'N/A',
            'plan_name': membership.plan_name,
            'start_date': membership.start_date,
            'expiry_date': membership.expiry_date,
            'total_hours': membership.total_hours,
            'hours_left': membership.hours_left,
            'is_checked_in': membership.is_checked_in,
            'status': membership.status,
        }
        
        if membership.status == 'pending':
            pending_members.append(member_data)
        elif membership.is_active:
            active_members.append(member_data)
        else:
            expired_members.append(member_data)
    
    return render_template(
        'admin/official_members.html',
        active_members=active_members,
        expired_members=expired_members,
        pending_members=pending_members,
        page_title="Official Members - Membership Management"
    )


# ===================================================================
# Member History Modal Data
# ===================================================================
@membership_bp.route("/history/<int:membership_id>", methods=["GET"])
@login_required
def get_member_history(membership_id):
    """Get attendance history for a specific member"""
    redirect_response = require_admin_or_staff_json()
    if redirect_response:
        return redirect_response
    
    membership = Membership.query.get_or_404(membership_id)
    
    # Get all attendance logs for this membership, ordered by date
    logs = AttendanceLog.query.filter_by(membership_id=membership_id).order_by(
        AttendanceLog.check_in_time.desc()
    ).all()
    
    logs_data = []
    for log in logs:
        logs_data.append({
            'id': log.id,
            'date': log.check_in_time.strftime('%B %d, %Y'),
            'check_in': log.check_in_time.strftime('%I:%M %p'),
            'check_out': log.check_out_time.strftime('%I:%M %p') if log.check_out_time else 'Still checked in',
            'hours_deducted': round(log.hours_deducted, 2),
            'session_duration': round(log.session_duration_hours, 2),
        })
    
    return jsonify({
        'member_name': membership.user.name,
        'plan_name': membership.plan_name,
        'logs': logs_data
    })


# ===================================================================
# Check-In / Check-Out API Endpoints
# ===================================================================
@membership_bp.route("/check-in/<int:membership_id>", methods=["POST"])
@login_required
def check_in(membership_id):
    """Check-in a member - start their session timer"""
    redirect_response = require_admin_or_staff_json()
    if redirect_response:
        return redirect_response
    
    membership = Membership.query.get_or_404(membership_id)
    
    # Verify membership is active
    if not membership.is_active:
        return jsonify({
            'success': False,
            'message': 'Membership is not active or has expired.'
        }), 400
    
    # Verify not already checked in
    if membership.is_checked_in:
        return jsonify({
            'success': False,
            'message': 'Member is already checked in.'
        }), 400
    
    # Create new attendance log with check-in time
    now = datetime.utcnow()
    log = AttendanceLog(
        membership_id=membership_id,
        check_in_time=now,
    )
    
    # Mark membership as checked in
    membership.is_checked_in = True
    
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'{membership.user.name} has been checked in.',
        'attendance_log_id': log.id,
    })


@membership_bp.route("/check-out/<int:membership_id>/<int:attendance_log_id>", methods=["POST"])
@login_required
def check_out(membership_id, attendance_log_id):
    """Check-out a member - end their session and deduct hours"""
    redirect_response = require_admin_or_staff_json()
    if redirect_response:
        return redirect_response
    
    membership = Membership.query.get_or_404(membership_id)
    log = AttendanceLog.query.get_or_404(attendance_log_id)
    
    # Verify log belongs to this membership
    if log.membership_id != membership_id:
        return jsonify({
            'success': False,
            'message': 'Invalid attendance log.'
        }), 400
    
    # Verify not already checked out
    if log.check_out_time:
        return jsonify({
            'success': False,
            'message': 'Member is already checked out.'
        }), 400
    
    # Set check-out time
    now = datetime.utcnow()
    log.check_out_time = now
    
    # Calculate hours deducted
    hours_duration = log.session_duration_hours
    log.hours_deducted = hours_duration
    
    # Deduct from membership hours
    membership.hours_left -= hours_duration
    if membership.hours_left < 0:
        membership.hours_left = 0
    
    # Mark membership as not checked in
    membership.is_checked_in = False
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'{membership.user.name} has been checked out. {round(hours_duration, 2)} hours deducted.',
        'hours_deducted': round(hours_duration, 2),
        'hours_remaining': round(membership.hours_left, 2),
    })


@membership_bp.route("/check-out/<int:membership_id>", methods=["POST"])
@login_required
def check_out_active(membership_id):
    """Check-out a member using the current active attendance log."""
    redirect_response = require_admin_or_staff_json()
    if redirect_response:
        return redirect_response

    membership = Membership.query.get_or_404(membership_id)
    log = AttendanceLog.query.filter_by(membership_id=membership_id, check_out_time=None).first()

    if not log:
        return jsonify({
            'success': False,
            'message': 'No active session found for this member.'
        }), 400

    now = datetime.utcnow()
    log.check_out_time = now
    hours_duration = log.session_duration_hours
    log.hours_deducted = hours_duration

    membership.hours_left -= hours_duration
    if membership.hours_left < 0:
        membership.hours_left = 0
    membership.is_checked_in = False

    db.session.commit()

    return jsonify({
        'success': True,
        'message': f'{membership.user.name} has been checked out. {round(hours_duration, 2)} hours deducted.',
        'hours_deducted': round(hours_duration, 2),
        'hours_remaining': round(membership.hours_left, 2),
    })


# ===================================================================
# Approve/Activate Membership
# ===================================================================
@membership_bp.route("/approve/<int:membership_id>", methods=["POST"])
@login_required
def approve_membership(membership_id):
    """Admin approves a pending membership application"""
    redirect_response = require_admin_or_staff_json()
    if redirect_response:
        return redirect_response
    
    membership = Membership.query.get_or_404(membership_id)
    
    if membership.status != 'pending':
        return jsonify({
            'success': False,
            'message': 'Only pending memberships can be approved.'
        }), 400
    
    membership.status = 'active'
    db.session.commit()
    
    return jsonify({
        'success': True,
        'message': f'Membership for {membership.user.name} has been activated.'
    })
