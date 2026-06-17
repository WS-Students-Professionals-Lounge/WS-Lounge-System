"""
admin.py
Contains the admin blueprint with all admin routes and daily report helpers.
"""
import os
from io import BytesIO
from datetime import datetime, timedelta

from database_fixed import AdminReservationForm, AttendanceLog, DailyReport, Membership, PaymentInfo, Reservation, \
    Room, SoloPlan, TimeLog, User, UserActivityLog, WalkinForm, WalkinReservation, db, generate_customer_id, \
    get_common_area_count, mail
from flask_mail import Message
from werkzeug.utils import secure_filename
from flask_login import current_user, login_required
from sqlalchemy import and_, func, inspect, or_, text
from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, send_file, url_for
from time_utils import format_checkin_time, format_checkout_time, format_date, decimal_hours_to_readable

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def require_super_admin():
    if current_user.role != "admin":
        flash("Access Restricted: Super Admin Account Required", "danger")
        return redirect(url_for("main.dashboard"))


def require_admin_or_staff():
    if current_user.role not in ("admin", "staff"):
        flash("Access Restricted: Super Admin Account Required", "danger")
        return redirect(url_for("main.dashboard"))


def require_super_admin_json():
    if current_user.role != "admin":
        return jsonify({"status": "error", "message": "Admin access required"}), 403


def require_admin_or_staff_json():
    if current_user.role not in ("admin", "staff"):
        return jsonify({"status": "error", "message": "Access restricted"}), 403


def _solo_plan_credit_hours(plan_name):
    plan_key = (plan_name or "").strip().upper()
    hour_mapping = {
        "INDIVIDUAL RATE": 1.0,
        "INDIVIDUAL RATE (4HRS)": 4.0,
        "DAY/NIGHT PASS": 24.0,
        "WEEKLY PASS (DAY/NIGHT)": 168.0,
        "WEEKLY PASS (24HRS)": 168.0,
        "MONTHLY PASS (DAY/NIGHT)": 720.0,
        "MONTHLY PASS (24HRS)": 720.0,
        "WORKSTATION (24HRS)": 720.0,
        "ACTIVE PLAN": 720.0,
    }
    return hour_mapping.get(plan_key, 24.0)


def _ensure_approved_solo_plan_membership(user):
    if user.membership:
        return False

    plan = SoloPlan.query.filter_by(user_id=user.id).filter(SoloPlan.status.ilike("approved")).order_by(SoloPlan.expiry_date.desc()).first()
    if not plan:
        return False

    hours = _solo_plan_credit_hours(plan.plan_name)
    membership = Membership(
        user_id=user.id,
        status="active",
        start_date=datetime.utcnow(),
        expiry_date=plan.expiry_date or datetime.utcnow() + timedelta(days=30),
        total_hours=hours,
        hours_left=hours,
        plan_name=plan.plan_name,
        is_checked_in=False,
    )
    db.session.add(membership)
    return True


def _expire_membership_if_needed(membership):
    if not membership or membership.status != "active" or not membership.expiry_date:
        return

    now = datetime.utcnow()
    if now >= membership.expiry_date:
        membership.status = "expired"
        membership.hours_left = 0.0
        membership.is_checked_in = False

        active_log = membership.attendance_logs.filter(AttendanceLog.check_out_time.is_(None)).first()
        if active_log:
            active_log.check_out_time = membership.expiry_date
            active_log.hours_deducted = round(
                (active_log.check_out_time - active_log.check_in_time).total_seconds() / 3600,
                2,
            )

        db.session.commit()


# ---------------------------------------------------------------------------
# Daily Report Helpers
# ---------------------------------------------------------------------------
@admin_bp.route("/api/rooms")
@login_required
def admin_rooms_api():
    redirect_response = require_admin_or_staff()
    if redirect_response:
        return jsonify({"status": "error", "message": "Access Restricted: Super Admin Account Required"}), 403

    rooms = Room.query.all()
    room_data = [
        {
            "id": room.id,
            "name": room.name,
            "base_rate": room.base_rate,
            "status": room.status,
            "is_common_area": room.name.strip().lower() == "common area",
        }
        for room in rooms
    ]
    return jsonify(room_data)
def get_or_create_daily_report(report_date):
    report = DailyReport.query.filter_by(report_date=report_date).first()
    if not report:
        report = DailyReport(
            report_date=report_date,
            total_check_ins=0,
            total_logins=0,
            total_timelogged=0,
        )
        db.session.add(report)
    return report


def ensure_address_column():
    try:
        inspector = inspect(db.engine)
        if inspector.has_table("reservations"):
            columns = [
                column["name"] for column in inspector.get_columns("reservations")
            ]
            if "address" not in columns:
                db.session.execute(
                    text("ALTER TABLE reservations ADD COLUMN address VARCHAR(128)")
                )
                db.session.commit()
    except Exception:
        pass


def refresh_daily_report(report_date):
    report = get_or_create_daily_report(report_date)
    start = datetime.combine(report_date, datetime.min.time())
    end = datetime.combine(report_date, datetime.max.time())

    report.total_check_ins = Reservation.query.filter(
        Reservation.end_time >= start,
        Reservation.end_time <= end,
        Reservation.status == "Checked-Out",
        Reservation.paid == True,
    ).count()

    report.total_logins = TimeLog.query.filter(
        TimeLog.time_in >= start, TimeLog.time_in <= end
    ).count()

    total_revenue = (
        db.session.query(func.coalesce(func.sum(Reservation.total_amount), 0))
        .filter(
            Reservation.end_time >= start,
            Reservation.end_time <= end,
            Reservation.status == "Checked-Out",
            Reservation.paid == True,
        )
        .scalar()
        or 0
    )

    report.total_timelogged = total_revenue
    report.generated_at = datetime.utcnow()
    db.session.add(report)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
    return report


def get_active_room_reservations(rooms):
    room_ids = [room.id for room in rooms]
    now = datetime.now()
    reservations = (
        Reservation.query.filter(
            Reservation.room_id.in_(room_ids),
            Reservation.status.in_(["Confirmed", "Walk-in", "Pending"]),
        )
        .order_by(Reservation.start_time.asc())
        .all()
    )

    def is_current(reservation):
        if reservation.start_time and reservation.end_time:
            return reservation.start_time <= now <= reservation.end_time
        if reservation.start_time and reservation.is_open_time:
            return reservation.start_time <= now
        return False

    room_reservations = {}
    for res in reservations:
        existing = room_reservations.get(res.room_id)
        if existing is None:
            room_reservations[res.room_id] = res
            continue

        existing_current = is_current(existing)
        res_current = is_current(res)

        if res_current and not existing_current:
            room_reservations[res.room_id] = res
            continue
        if existing_current and not res_current:
            continue

        if res.start_time and existing.start_time:
            if res.start_time < existing.start_time:
                room_reservations[res.room_id] = res
    return room_reservations


@admin_bp.route("/check_availability")
@login_required
def check_availability():
    redirect_response = require_admin_or_staff()
    if redirect_response:
        return jsonify({"status": "error", "message": "Access Restricted: Super Admin Account Required"}), 403

    room_id = request.args.get("room_id", type=int)
    date_str = request.args.get("date", "")
    start_str = request.args.get("start", "")
    end_str = request.args.get("end", "")
    open_time = request.args.get("open_time", "false").lower() in ["1", "true", "yes"]

    try:
        if start_str and "T" in start_str:
            start_dt = datetime.strptime(start_str, "%Y-%m-%dT%H:%M")
        else:
            start_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else datetime.now().date()
            if start_str:
                start_time = datetime.strptime(start_str, "%H:%M").time()
                start_dt = datetime.combine(start_date, start_time)
            else:
                start_dt = datetime.now()

        if open_time:
            end_dt = start_dt + timedelta(hours=12)
        elif end_str:
            if "T" in end_str:
                end_dt = datetime.strptime(end_str, "%Y-%m-%dT%H:%M")
            else:
                end_time = datetime.strptime(end_str, "%H:%M").time()
                end_dt = datetime.combine(start_dt.date(), end_time)
                if end_dt <= start_dt:
                    end_dt += timedelta(days=1)
        else:
            end_dt = start_dt + timedelta(hours=1)

        conflict = Reservation.check_conflict(room_id, start_dt, end_dt)
        if conflict:
            return jsonify(
                {
                    "status": "conflict",
                    "message": "Selected room is not available for the requested time.",
                }
            )
    except Exception as error:
        return jsonify(
            {"status": "error", "message": f"Invalid availability check data: {error}"}
        ), 400

    return jsonify({"status": "ok"})


# ---------------------------------------------------------------------------
# Admin Routes
# ---------------------------------------------------------------------------
@admin_bp.route("/dashboard")
@login_required
def dashboard():
    redirect_response = require_admin_or_staff()
    if redirect_response:
        return redirect_response

    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    form = WalkinForm()
    rooms = Room.query.filter(~Room.name.ilike('Test Room%')).all()
    form.room_id.choices = [
        (room.id, f"{room.name} (₱{room.base_rate}/hr)") for room in rooms
    ]

    room_reservations = get_active_room_reservations(rooms)
    recent_members = (
        User.query.filter_by(role="member")
        .order_by(User.created_at.desc())
        .limit(8)
        .all()
    )
    incomplete_count = (
        User.query.filter(
            User.role == "member",
            or_(
                User.phone.is_(None),
                User.phone == "",
                User.email.is_(None),
                User.email == "",
            ),
        )
        .count()
    )

    total_members = User.query.filter_by(role="member").count()
    active_plans = (
        SoloPlan.query.filter_by(status="approved")
        .filter(SoloPlan.expiry_date >= now)
        .count()
    )

    revenue_today = (
        db.session.query(func.coalesce(func.sum(Reservation.total_amount), 0))
        .filter(
            Reservation.end_time >= today_start,
            Reservation.end_time < today_end,
            Reservation.paid == True,
            Reservation.status == "Checked-Out",
        )
        .scalar()
        or 0
    )

    updated = False
    # NOTE: Do not auto-confirm Pending reservations here. Pending (online) reservations
    # must be reviewed by staff on the confirmation page to verify receipts and payments.

    expired_sessions = Reservation.query.filter(
        Reservation.end_time <= now,
        Reservation.status.in_(["Confirmed", "Walk-in"]),
        Reservation.is_open_time == False,
    ).all()
    for res in expired_sessions:
        res.status = "Ended"
        db.session.add(res)
        updated = True

    if updated:
        db.session.commit()

    reservations_today = (
        Reservation.query.filter(
            Reservation.status.in_(["Pending", "Confirmed"]),
            Reservation.start_time >= today_start,
            Reservation.start_time < today_end,
            Reservation.end_time >= now,
        )
        .count()
    )

    all_res = Reservation.query.filter(
        Reservation.start_time <= now,
        Reservation.end_time >= today_start,
        Reservation.status.in_(["Confirmed", "Walk-in", "Ended"]),
    ).all()

    active_reservations = sorted(all_res, key=lambda x: (x.status != "Ended", x.end_time))

    pending_reservations = (
        Reservation.query.filter(
            Reservation.status.in_(["Pending", "Confirmed"]),
            Reservation.start_time >= today_start,
            Reservation.start_time < today_end,
            Reservation.end_time >= now,
        )
        .order_by(Reservation.start_time.asc())
        .limit(7)
        .all()
    )

    active_walkins = [
        r
        for r in active_reservations
        if r.status in ("Walk-in", "Ended") and r.room is not None
    ]

    common_area_reservations = [
        r
        for r in active_reservations
        if r.room and r.room.name.strip().lower() == "common area"
    ]

    common_area_occupancy = get_common_area_count()
    common_area_available_slots = max(0, 50 - common_area_occupancy)

    return render_template(
        "admin/admin_dashboard.html",
        form=form,
        total_members=total_members,
        active_plans=active_plans,
        reservations_today=reservations_today,
        revenue_today=revenue_today,
        rooms=rooms,
        room_reservations=room_reservations,
        recent_members=recent_members,
        incomplete_count=incomplete_count,
        active_reservations=active_reservations,
        pending_reservations=pending_reservations,
        active_walkins=active_walkins,
        common_area_reservations=common_area_reservations,
        common_area_occupancy=common_area_occupancy,
        common_area_available_slots=common_area_available_slots,
        now=now,
    )


@admin_bp.route('/payment_settings', methods=['GET', 'POST'])
@login_required
def payment_settings():
    redirect_response = require_super_admin()
    if redirect_response:
        return redirect_response

    payment_infos = {info.method: info for info in PaymentInfo.query.all()}

    if request.method == 'POST':
        method = request.form.get('method')
        account_name = request.form.get('account_name', '').strip()
        account_number = request.form.get('account_number', '').strip()
        instructions = request.form.get('instructions', '').strip()
        qr_file = request.files.get('qr_image')

        if method not in ['GCash', 'Maya']:
            flash('Invalid payment method.', 'danger')
            return redirect(url_for('admin.payment_settings'))

        payment_info = PaymentInfo.query.filter_by(method=method).first()
        if not payment_info:
            payment_info = PaymentInfo(method=method)

        payment_info.account_name = account_name
        payment_info.account_number = account_number
        payment_info.instructions = instructions

        if qr_file and qr_file.filename:
            filename = secure_filename(f"{method.lower()}_{int(datetime.now().timestamp())}_{qr_file.filename}")
            upload_folder = os.path.join(current_app.root_path, 'static/uploads/payment')
            os.makedirs(upload_folder, exist_ok=True)
            qr_path = os.path.join(upload_folder, filename)
            qr_file.save(qr_path)
            payment_info.qr_image = filename

        db.session.add(payment_info)
        db.session.commit()
        flash(f'{method} payment settings updated.', 'success')
        return redirect(url_for('admin.payment_settings'))

    payment_infos = {info.method: info for info in PaymentInfo.query.all()}
    return render_template('admin/payment_settings.html', payment_infos=payment_infos)


@admin_bp.route("/manage_staff", methods=["GET", "POST"])
@login_required
def manage_staff():
    redirect_response = require_super_admin()
    if redirect_response:
        return redirect_response

    message = None
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        role = request.form.get("role", "staff")

        if not name or not email or not password or role not in ["admin", "staff"]:
            message = "Please fill in all fields and select a valid role."
        elif User.query.filter(func.lower(User.email) == email).first():
            message = "A staff account with that email already exists."
        else:
            new_user = User(name=name, email=email, phone=phone, role=role, is_active=True)
            new_user.set_password(password)
            db.session.add(new_user)
            try:
                db.session.commit()
                flash(f"{role.title()} account created for {name}.", "success")
                return redirect(url_for("admin.manage_staff"))
            except Exception as err:
                db.session.rollback()
                message = "Failed to create staff account. Check server logs for details."
                flash(message, "danger")

    staff_users = User.query.filter(User.role.in_(["admin", "staff"]))
    staff_users = staff_users.order_by(User.role.desc(), User.name).all()
    return render_template(
        "admin/manage_staff.html",
        staff_users=staff_users,
        message=message,
    )


@admin_bp.route("/toggle_staff_status/<int:user_id>", methods=["POST"])
@login_required
def toggle_staff_status(user_id):
    redirect_response = require_super_admin()
    if redirect_response:
        return redirect_response

    user = User.query.get_or_404(user_id)
    if user.role not in ["admin", "staff"]:
        return jsonify({"status": "error", "message": "Unsupported user type."}), 400
    if user.id == current_user.id:
        return jsonify({"status": "error", "message": "You cannot change your own status."}), 400

    user.is_active = not user.is_active
    action = "reactivated" if user.is_active else "deactivated"
    log_message = f"{action} by {current_user.name}"
    log = UserActivityLog(
        user_id=user.id,
        activity_type=log_message,
        ip_address=request.remote_addr or "unknown",
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"status": "success", "message": f"Staff account {action}."})


@admin_bp.route("/walkin_checkin", methods=["POST"])
@login_required
def walkin_checkin_modal():
    form = WalkinForm()
    rooms = Room.query.filter(~Room.name.ilike('Test Room%')).all()
    form.room_id.choices = [(room.id, room.name) for room in rooms]

    current_app.logger.debug("walkin_checkin request.form at entry: %s", request.form.to_dict())
    current_app.logger.debug("csrf_token present: %s", 'csrf_token' in request.form)

    if form.validate_on_submit():
        room = Room.query.get(form.room_id.data)
        if not room:
            flash("Please select a valid room.")
            return redirect(url_for("admin.dashboard"))

        now = datetime.now()
        is_open_time = form.open_time.data

        if is_open_time:
            start_time = now
        else:
            if form.start_time.data:
                if isinstance(form.start_time.data, str):
                    try:
                        start_time = datetime.strptime(form.start_time.data, "%Y-%m-%dT%H:%M")
                    except ValueError:
                        start_time = now
                else:
                    start_time = form.start_time.data
            else:
                start_time = now

        if is_open_time:
            end_time = start_time + timedelta(hours=12)
        else:
            if form.end_time.data:
                if isinstance(form.end_time.data, str):
                    try:
                        end_time = datetime.strptime(form.end_time.data, "%Y-%m-%dT%H:%M")
                    except ValueError:
                        end_time = start_time + timedelta(hours=1)
                else:
                    end_time = form.end_time.data
                if end_time <= start_time:
                    end_time += timedelta(days=1)
            else:
                end_time = start_time + timedelta(hours=1)

        if room.name.strip().lower() != "common area":
            conflict = Reservation.query.filter(
                Reservation.room_id == room.id,
                Reservation.status.in_( ["Confirmed", "Walk-in", "Pending"] ),
                Reservation.start_time < end_time,
                Reservation.end_time > start_time,
            ).first()

            if conflict:
                flash(
                    f"Conflict! {room.name} is already occupied or reserved by {conflict.customer_name} from {conflict.start_time.strftime('%I:%M %p')} to {conflict.end_time.strftime('%I:%M %p')}."
                )
                return redirect(url_for("admin.dashboard"))
        else:
            # Check Common Area capacity
            if get_common_area_count() >= 50:
                flash("Common Area has reached maximum capacity of 50 people.")
                return redirect(url_for("admin.dashboard"))

        # Generate customer_id based on room type
        room_type = "common area" if room.name.strip().lower() == "common area" else "other"
        try:
            customer_id = generate_customer_id(room_type)
        except ValueError as e:
            flash(str(e))
            return redirect(url_for("admin.dashboard"))

        total_from_js = request.form.get("total_price")
        total_amount = (
            float(total_from_js) if total_from_js and not is_open_time else 0.0
        )

        new_walkin = Reservation(
            user_id=current_user.id,
            customer_id=customer_id,
            room_id=form.room_id.data,
            customer_name=form.customer_name.data,
            contact_number=form.contact_number.data or "N/A",
            pax_count=form.pax_count.data,
            extra_notes=form.extra_notes.data,
            extra_fee=float(form.extra_fee.data) if form.extra_fee.data else 0.0,
            start_time=start_time,
            end_time=end_time,
            is_open_time=is_open_time,
            status="Walk-in",
            added_by=current_user.name,
            total_amount=round(total_amount, 2),
            paid=False,
        )

        if room and room.name.strip().lower() != "common area" and start_time <= now:
            room.status = "unavailable"

        db.session.add(new_walkin)
        db.session.commit()

        walkin_entry = WalkinReservation(
            reservation_id=new_walkin.id,
            user_id=new_walkin.user_id,
            room_id=new_walkin.room_id,
            customer_name=new_walkin.customer_name,
            contact_number=new_walkin.contact_number,
            pax_count=new_walkin.pax_count,
            start_time=new_walkin.start_time,
            end_time=new_walkin.end_time,
            status="Walk-in",
            total_amount=new_walkin.total_amount,
            extra_fee=new_walkin.extra_fee,
            paid=False,
            added_by=new_walkin.added_by,
        )
        db.session.add(walkin_entry)
        db.session.commit()

        current_app.logger.debug("Walk-in created: %s", new_walkin.customer_name)
        flash(f"Walk-in {new_walkin.customer_name} added successfully!")
        return redirect(url_for("admin.dashboard"))

    current_app.logger.debug("WalkinForm validation failed: %s", form.errors)
    current_app.logger.debug("walkin_checkin request.form at failure: %s", request.form.to_dict())
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/walkin_checkout/<int:res_id>", methods=["GET", "POST"])
@login_required
def walkin_checkout(res_id):
    res = Reservation.query.get_or_404(res_id)
    now = datetime.now()

    final_bill_arg = request.args.get("final_bill") or request.form.get("final_bill")
    final_bill = None
    if final_bill_arg:
        try:
            final_bill = float(final_bill_arg)
        except (TypeError, ValueError):
            final_bill = None

    if final_bill is not None and final_bill > 0:
        res.total_amount = round(final_bill, 2)
        res.end_time = now
    elif res.is_open_time:
        duration_seconds = (now - res.start_time).total_seconds()
        duration_minutes = max(1, int(duration_seconds / 60))
        room_rate = res.room.base_rate or 0
        res.total_amount = round(
            ((duration_minutes / 60) * room_rate) + (res.extra_fee or 0), 2
        )
        res.end_time = now
    else:
        if not res.total_amount or res.total_amount == 0:
            try:
                room_rate = res.room.base_rate or 0
                if res.end_time and res.start_time:
                    diff_hours = (res.end_time - res.start_time).total_seconds() / 3600
                    diff_hours = max(diff_hours, 0)
                    discount = getattr(res, "discount_rate", 0) or 0
                    room_cost = room_rate * diff_hours
                    room_cost = room_cost * (1 - (discount or 0))
                    res.total_amount = round(room_cost + (res.extra_fee or 0), 2)
            except Exception:
                pass
        res.end_time = now

    report_date = res.end_time.date()

    res.status = "Checked-Out"
    res.paid = True

    if res.room and res.room.name.strip().lower() != "common area":
        res.room.status = "available"

    walkin_entry = WalkinReservation.query.filter_by(reservation_id=res.id).first()
    if walkin_entry:
        walkin_entry.status = "Checked-Out"
        walkin_entry.paid = True
        walkin_entry.total_amount = res.total_amount
        walkin_entry.end_time = res.end_time

    db.session.commit()
    refresh_daily_report(report_date)

    if (
        request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or request.is_json
    ):
        return jsonify(
            {
                "status": "success",
                "message": f"Payment of ₱{res.total_amount:.2f} received from {res.customer_name}.",
            }
        )

    flash(f"Payment of ₱{res.total_amount:.2f} received from {res.customer_name}.")
    return redirect(url_for("admin.dashboard"))


@admin_bp.route("/process_payment/<int:reservation_id>", methods=["GET", "POST"])
@login_required
def process_payment(reservation_id):
    res = Reservation.query.get_or_404(reservation_id)
    now = datetime.now()

    amount_passed = request.form.get("total_bill") or request.args.get("total_bill")

    if amount_passed and float(amount_passed) > 0:
        res.total_amount = round(float(amount_passed), 2)
        if res.is_open_time or not res.end_time:
            res.end_time = now
    elif res.is_open_time:
        duration_minutes = max(
            1, int((now - res.start_time).total_seconds() / 60)
        )
        room_rate = res.room.base_rate or 0
        res.total_amount = round(
            ((duration_minutes / 60) * room_rate) + (res.extra_fee or 0), 2
        )
        res.end_time = now

    if not res.is_open_time and (not res.total_amount or res.total_amount == 0):
        try:
            room_rate = res.room.base_rate or 0
            if res.end_time and res.start_time:
                diff_hours = (res.end_time - res.start_time).total_seconds() / 3600
                diff_hours = max(diff_hours, 0)
                discount = getattr(res, "discount_rate", 0) or 0
                room_cost = room_rate * diff_hours
                room_cost = room_cost * (1 - (discount or 0))
                res.total_amount = round(room_cost + (res.extra_fee or 0), 2)
        except Exception:
            pass

    report_date = res.end_time.date()

    res.status = "Checked-Out"
    res.paid = True

    if res.room and res.room.name.strip().lower() != "common area":
        res.room.status = "available"

    walkin_entry = WalkinReservation.query.filter_by(reservation_id=res.id).first()
    if walkin_entry:
        walkin_entry.status = "Checked-Out"
        walkin_entry.paid = True
        walkin_entry.total_amount = res.total_amount
        walkin_entry.end_time = res.end_time

    db.session.commit()
    refresh_daily_report(report_date)

    flash(
        f"Payment of ₱{res.total_amount:.2f} received from {res.customer_name}. Dashboard updated!"
    )

    return redirect(url_for("admin.dashboard"))


@admin_bp.route('/extend_time/<int:res_id>', methods=['POST'])
@login_required
def extend_time(res_id):
    redirect_response = require_admin_or_staff_json()
    if redirect_response:
        return redirect_response

    res = Reservation.query.get_or_404(res_id)
    data = request.get_json(silent=True) or {}
    try:
        added_hours = int(data.get('added_hours', 0))
    except (TypeError, ValueError):
        added_hours = 0

    if added_hours <= 0:
        return jsonify({"status": "error", "message": "Please add at least 1 hour."}), 400

    if not res.end_time:
        return jsonify({"status": "error", "message": "Reservation end time is missing."}), 400

    if res.status == 'Ended':
        res.status = 'Walk-in'

    room_rate = res.room.base_rate or 0
    added_cost = round(room_rate * added_hours, 2)

    if res.is_open_time:
        res.extra_fee = (res.extra_fee or 0.0) + added_cost
        res.total_amount = round((res.total_amount or 0.0) + added_cost, 2)
    else:
        previous_end = res.end_time
        current_total = res.total_amount or 0.0
        if current_total == 0 and res.start_time and previous_end:
            original_duration = max(0, (previous_end - res.start_time).total_seconds() / 3600)
            current_total = round(original_duration * room_rate + (res.extra_fee or 0), 2)

        new_end = previous_end + timedelta(hours=added_hours)
        res.end_time = new_end
        res.total_amount = round(current_total + added_cost, 2)

    if res.room and res.room.name.strip().lower() != 'common area':
        res.room.status = 'unavailable'

    walkin_entry = WalkinReservation.query.filter_by(reservation_id=res.id).first()
    if walkin_entry:
        walkin_entry.end_time = res.end_time
        walkin_entry.total_amount = res.total_amount
        walkin_entry.status = 'Walk-in'

    db.session.commit()

    return jsonify(
        {
            "status": "success",
            "message": f"Extended {added_hours} hour(s) for {res.customer_name}. New total is ₱{res.total_amount:.2f}.",
            "new_total": res.total_amount,
            "new_end_time": res.end_time.isoformat(),
            "new_extra_fee": res.extra_fee or 0.0,
        }
    )


@admin_bp.route("/reservations", methods=["GET", "POST"])
@login_required
def admin_reservations():
    redirect_response = require_admin_or_staff()
    if redirect_response:
        return redirect_response

    rooms = Room.query.filter(~Room.name.ilike('Test Room%')).all()
    form = AdminReservationForm()
    form.room_id.choices = [
        (r.id, f"{r.name} (₱{r.base_rate}/hr)") for r in rooms
    ]

    ensure_address_column()

    if request.method == "POST":
        selected_room_id = request.form.get("room_id")
        if selected_room_id:
            try:
                selected_room_id = int(selected_room_id)
            except (TypeError, ValueError):
                selected_room_id = None
        if selected_room_id and selected_room_id not in [choice[0] for choice in form.room_id.choices]:
            selected_room = Room.query.get(selected_room_id)
            if selected_room:
                form.room_id.choices.append(
                    (selected_room.id, f"{selected_room.name} (₱{selected_room.base_rate}/hr)")
                )

        total_from_js = request.form.get("total_price")
        is_open_time = form.open_time.data

        if form.validate_on_submit():
            room = Room.query.get(form.room_id.data)
            if not room:
                flash("Please select a valid room.")
                return render_template(
                    "admin/admin_reservations.html", form=form, rooms=rooms
                )

            try:
                if is_open_time:
                    full_start = datetime.now()
                    full_end = full_start + timedelta(hours=12)
                else:
                    if form.start_time.data:
                        if isinstance(form.start_time.data, str):
                            full_start = datetime.strptime(form.start_time.data, "%Y-%m-%dT%H:%M")
                        else:
                            full_start = form.start_time.data
                    else:
                        full_start = datetime.now()

                    if form.end_time.data:
                        if isinstance(form.end_time.data, str):
                            full_end = datetime.strptime(form.end_time.data, "%Y-%m-%dT%H:%M")
                        else:
                            full_end = form.end_time.data
                        if full_end <= full_start:
                            full_end += timedelta(days=1)
                    else:
                        full_end = full_start + timedelta(hours=1)

                if room.name.strip().lower() != "common area":
                    conflict = Reservation.query.filter(
                        Reservation.room_id == room.id,
                        Reservation.status.in_(["Confirmed", "Walk-in", "Pending"]),
                        Reservation.start_time < full_end,
                        Reservation.end_time > full_start,
                    ).first()

                    if conflict:
                        flash(
                            f"Cannot book: {room.name} is already reserved by {conflict.customer_name} from {conflict.start_time.strftime('%I:%M %p')} to {conflict.end_time.strftime('%I:%M %p')}."
                        )
                        return render_template(
                            "admin/admin_reservations.html", form=form, rooms=rooms
                        )

            except Exception as e:
                flash(f"Time Format Error: {str(e)}")
                return render_template(
                    "admin/admin_reservations.html", form=form, rooms=rooms
                )

            # Generate customer_id based on room type
            room_type = "common area" if room.name.strip().lower() == "common area" else "other"
            try:
                customer_id = generate_customer_id(room_type)
            except ValueError as e:
                flash(str(e))
                return render_template(
                    "admin/admin_reservations.html", form=form, rooms=rooms
                )

            reservation = Reservation(
                user_id=current_user.id,
                customer_id=customer_id,
                room_id=form.room_id.data,
                customer_name=form.customer_name.data,
                contact_number=request.form.get("contact_number", "N/A"),
                pax_count=form.pax_count.data,
                start_time=full_start,
                end_time=full_end,
                is_open_time=is_open_time,
                status="Pending",
                added_by=current_user.name,
                extra_notes=form.extra_notes.data,
                extra_fee=float(form.extra_fee.data) if form.extra_fee.data else 0.0,
                total_amount=round(float(total_from_js or 0), 2),
                discount_rate=(
                    float(form.discount.data)
                    if getattr(form, "discount", None)
                    else 0.0
                ),
                paid=False,
            )

            now = datetime.now()
            if (
                room
                and room.name.strip().lower() != "common area"
                and full_start <= now
            ):
                room.status = "unavailable"

            db.session.add(reservation)
            if not is_open_time and (
                not reservation.total_amount or reservation.total_amount == 0
            ):
                try:
                    base_rate = room.base_rate or 0
                    diff_hours = (
                        reservation.end_time - reservation.start_time
                    ).total_seconds() / 3600
                    diff_hours = max(diff_hours, 0)
                    discount = reservation.discount_rate or 0.0
                    room_cost = base_rate * diff_hours
                    room_cost = room_cost * (1 - (discount or 0))
                    reservation.total_amount = round(
                        room_cost + (reservation.extra_fee or 0), 2
                    )
                except Exception:
                    reservation.total_amount = round(float(total_from_js or 0), 2)

            db.session.commit()

            flash("Reservation added! It will appear on dashboard once it starts.")
            return redirect(url_for("admin.dashboard"))

    return render_template("admin/admin_reservations.html", form=form, rooms=rooms)


@admin_bp.route("/reservations_list")
@login_required
def admin_reservations_list():
    redirect_response = require_admin_or_staff()
    if redirect_response:
        return redirect_response
    search = request.args.get("search", "")
    # Only show reservations that are clearly legitimate in the main list:
    # - Walk-ins (staff-registered in-person)
    # - On Hold (clients who paid a downpayment and were placed on hold)
    # - Confirmed & paid reservations created by staff (not online full-pay clients)

    base_query = Reservation.query
    # Build filter: include Walk-in and On Hold always; include Confirmed+paid only if created by staff or no user
    query = base_query.filter(
        or_(
            Reservation.status == "On Hold",
            Reservation.status == "Walk-in",
            and_(
                Reservation.status == "Confirmed",
                Reservation.paid == True,
                or_(
                    Reservation.user_id.is_(None),
                    Reservation.user.has(User.role.in_(["admin", "staff"])),
                ),
            ),
        )
    )

    if search:
        query = query.filter(
            or_(
                Reservation.customer_name.ilike(f"%{search}%"),
                Reservation.added_by.ilike(f"%{search}%"),
                Reservation.status.ilike(f"%{search}%"),
            )
        )

    reservations = query.order_by(Reservation.start_time.asc()).all()
    return render_template(
        "admin/admin_reservations_list.html",
        reservations=reservations,
        search=search,
    )


@admin_bp.route("/confirm_reservations")
@login_required
def admin_confirm_reservations():
    redirect_response = require_admin_or_staff()
    if redirect_response:
        return redirect_response

    pending_reservations = (
        Reservation.query.filter_by(status="Pending")
        .order_by(Reservation.start_time.asc())
        .all()
    )
    return render_template(
        "admin/confirm_reservations.html",
        reservations=pending_reservations,
    )


@admin_bp.route("/solo_applications")
@login_required
def solo_applications():
    redirect_response = require_super_admin()
    if redirect_response:
        return redirect_response

    pending_plans = (
        SoloPlan.query.filter_by(status="pending")
        .order_by(SoloPlan.created_at.desc())
        .all()
    )
    return render_template(
        "admin/solo_applications.html", pending_plans=pending_plans
    )


@admin_bp.route("/approve_membership/<int:req_id>", methods=["POST"])
@login_required
def approve_membership(req_id):
    redirect_response = require_super_admin()
    if redirect_response:
        return redirect_response

    plan = SoloPlan.query.get_or_404(req_id)
    plan.approved_by_id = current_user.id
    plan.status = "approved"
    plan.set_expiry_date(datetime.utcnow())
    if not plan.customer_id:
        plan.customer_id = generate_customer_id("other")

    # Ensure approved solo plan users receive a matching active membership record.
    _ensure_approved_solo_plan_membership(plan.user)

    db.session.commit()
    flash(f"Membership approved for {plan.user.name}")
    return redirect(url_for("admin.members", tab="list"))


@admin_bp.route("/reject_membership/<int:req_id>", methods=["POST"])
@login_required
def reject_membership(req_id):
    redirect_response = require_super_admin()
    if redirect_response:
        return redirect_response

    plan = SoloPlan.query.get_or_404(req_id)
    plan.status = "rejected"
    db.session.commit()
    flash(f"Membership rejected for {plan.user.name}")
    return redirect(url_for("admin.members", tab="requests"))


@admin_bp.route("/renew_member", methods=["POST"])
@login_required
def renew_member():
    redirect_response = require_super_admin_json()
    if redirect_response:
        return redirect_response

    data = request.get_json(silent=True) or request.form
    user_id = data.get("user_id") or request.form.get("user_id")

    if not user_id:
        return jsonify({"status": "error", "message": "Missing user ID."}), 400

    user = User.query.get(int(user_id))
    if not user:
        return jsonify({"status": "error", "message": "Member not found."}), 404

    latest_plan = (
        SoloPlan.query.filter_by(user_id=user.id, status="approved")
        .order_by(SoloPlan.expiry_date.desc())
        .first()
    )
    if not latest_plan:
        return jsonify({"status": "error", "message": "No active membership plan to renew."}), 400

    now = datetime.now()
    if latest_plan.expiry_date and latest_plan.expiry_date > now:
        latest_plan.expiry_date += timedelta(days=30)
    else:
        latest_plan.expiry_date = now + timedelta(days=30)
    db.session.commit()

    return jsonify({"status": "success", "message": "Membership renewed successfully."})


@admin_bp.route("/deactivate_member", methods=["POST"])
@login_required
def deactivate_member():
    redirect_response = require_super_admin_json()
    if redirect_response:
        return redirect_response

    data = request.get_json(silent=True) or request.form
    user_id = data.get("user_id") or request.form.get("user_id")

    if not user_id:
        return jsonify({"status": "error", "message": "Missing user ID."}), 400

    user = User.query.get(int(user_id))
    if not user:
        return jsonify({"status": "error", "message": "Member not found."}), 404

    if user.role == "admin":
        return jsonify({"status": "error", "message": "Cannot deactivate admin account."}), 400

    user.is_active = False
    log = UserActivityLog(
        user_id=user.id,
        activity_type=f"deactivated|Manual soft deactivation by {current_user.name}",
        ip_address=request.remote_addr or "unknown",
    )
    db.session.add(log)
    db.session.commit()
    return jsonify({"status": "success", "message": "Member account deactivated."})


@admin_bp.route("/reactivate_member", methods=["POST"])
@login_required
def reactivate_member():
    redirect_response = require_super_admin_json()
    if redirect_response:
        return redirect_response

    data = request.get_json(silent=True) or request.form
    user_id = data.get("user_id") or request.form.get("user_id")

    if not user_id:
        return jsonify({"status": "error", "message": "Missing user ID."}), 400

    user = User.query.get(int(user_id))
    if not user:
        return jsonify({"status": "error", "message": "Member not found."}), 404

    if user.role == "admin":
        return jsonify({"status": "error", "message": "Cannot reactivate admin account."}), 400

    if user.is_active:
        return jsonify({"status": "error", "message": "Account is already active."}), 400

    user.is_active = True
    log = UserActivityLog(
        user_id=user.id,
        activity_type=f"reactivated by {current_user.name}",
        ip_address=request.remote_addr or "unknown",
    )
    db.session.add(log)
    db.session.commit()

    sender = current_app.config.get("MAIL_DEFAULT_SENDER") or current_app.config.get("MAIL_USERNAME") or "no-reply@lounge.com"
    if user.email and current_app.config.get("MAIL_SERVER"):
        try:
            msg = Message(
                subject="Your lounge account has been reactivated",
                sender=sender,
                recipients=[user.email],
                body=(
                    f"Hello {user.name},\n\n"
                    f"Your account has been reactivated by {current_user.name}. You may now log in again.\n\n"
                    "If you did not request this change, please contact support immediately.\n\n"
                    "Thank you,\nThe Lounge Team"
                ),
            )
            mail.send(msg)
        except Exception as exc:
            current_app.logger.warning("Failed to send reactivation email: %s", exc)

    return jsonify({"status": "success", "message": "Member account reactivated."})


@admin_bp.route("/approve_solo_plan/<int:plan_id>", methods=["POST"])
@login_required
def approve_solo_plan(plan_id):
    redirect_response = require_super_admin()
    if redirect_response:
        return redirect_response

    plan = SoloPlan.query.get_or_404(plan_id)
    plan.status = "approved"
    plan.approved_by_id = current_user.id
    plan.set_expiry_date()
    db.session.commit()
    flash(f"Plan approved for {plan.user.name}")
    return redirect(url_for("admin.solo_applications"))


@admin_bp.route("/reject_solo_plan/<int:plan_id>", methods=["POST"])
@login_required
def reject_solo_plan(plan_id):
    redirect_response = require_super_admin()
    if redirect_response:
        return redirect_response

    plan = SoloPlan.query.get_or_404(plan_id)
    plan.status = "rejected"
    db.session.commit()
    flash(f"Plan rejected for {plan.user.name}")
    return redirect(url_for("admin.solo_applications"))


@admin_bp.route("/confirm_reservation/<int:res_id>", methods=["POST"])
@login_required
def confirm_reservation(res_id):
    redirect_response = require_admin_or_staff()
    if redirect_response:
        return redirect_response

    res = Reservation.query.get_or_404(res_id)
    res.status = "Confirmed"
    res.approved_by_id = current_user.id
    if res.room and res.room.name.strip().lower() != "common area":
        now = datetime.now()
        if res.start_time <= now <= res.end_time:
            res.room.status = "unavailable"
    db.session.commit()
    flash(f"Reservation confirmed for {res.customer_name}")
    return redirect(url_for("admin.admin_reservations_list"))


@admin_bp.route("/hold_reservation/<int:res_id>", methods=["POST"])
@login_required
def hold_reservation(res_id):
    redirect_response = require_admin_or_staff()
    if redirect_response:
        return redirect_response

    res = Reservation.query.get_or_404(res_id)
    if res.status not in ["Pending", "Confirmed"]:
        flash("Reservation cannot be held in its current state.")
        return redirect(url_for("admin.admin_reservations_list"))

    res.status = "On Hold"
    if res.room and res.room.name.strip().lower() != "common area":
        res.room.status = "available"
    db.session.commit()
    flash(f"Reservation for {res.customer_name} has been placed on hold.")
    return redirect(url_for("admin.admin_reservations_list"))


@admin_bp.route("/cancel_reservation/<int:res_id>", methods=["POST"])
@login_required
def cancel_reservation(res_id):
    redirect_response = require_admin_or_staff()
    if redirect_response:
        return redirect_response

    res = Reservation.query.get_or_404(res_id)
    if res.status == "Confirmed":
        res.room.status = "available"
    res.status = "Cancelled"
    db.session.commit()
    flash(f"Reservation cancelled for {res.customer_name}")
    return redirect(url_for("admin.admin_reservations_list"))


@admin_bp.route("/delete_reservation/<int:res_id>", methods=["POST"])
@login_required
def delete_reservation(res_id):
    redirect_response = require_admin_or_staff()
    if redirect_response:
        return redirect_response

    res = Reservation.query.get_or_404(res_id)
    # If reservation has associated walkin entries, delete them first to avoid FK constraint errors
    try:
        walkin_entries = WalkinReservation.query.filter_by(reservation_id=res.id).all()
        for w in walkin_entries:
            db.session.delete(w)
    except Exception:
        # ignore if table or relation unavailable; will surface on commit if real problem
        pass

    if res.status in ["Pending", "Confirmed", "Walk-in", "Ended"]:
        if res.room and res.room.name.strip().lower() != "common area":
            res.room.status = "available"

    next_url = request.form.get("next") or request.args.get("next") or request.referrer
    db.session.delete(res)
    db.session.commit()
    flash(f"Reservation for {res.customer_name} has been permanently deleted.")
    return redirect(next_url or url_for("admin.dashboard"))


@admin_bp.route("/reports", methods=["GET", "POST"])
@login_required
def reports():
    redirect_response = require_super_admin()
    if redirect_response:
        return redirect_response

    start_date = datetime.utcnow().date()
    end_date = datetime.utcnow().date()

    if request.method == "POST":
        start_date_str = request.form.get("start_date")
        end_date_str = request.form.get("end_date")
        try:
            if start_date_str:
                start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
            if end_date_str:
                end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            flash("Invalid date format.")

    query = DailyReport.query.filter(
        DailyReport.report_date >= start_date, DailyReport.report_date <= end_date
    )
    daily_reports = query.order_by(DailyReport.report_date.desc()).all()

    reports_with_member = []
    for report in daily_reports:
        member_log = (
            TimeLog.query.join(User)
            .filter(
                TimeLog.time_in >= datetime.combine(
                    report.report_date, datetime.min.time()
                ),
                TimeLog.time_in <= datetime.combine(
                    report.report_date, datetime.max.time()
                ),
                User.role == "member",
            )
            .first()
        )
        reports_with_member.append(
            {
                "report_date": report.report_date,
                "total_logins": report.total_logins,
                "total_check_ins": report.total_check_ins,
                "total_revenue": report.total_timelogged,
                "generated_at": report.generated_at,
                "member_name": member_log.user.name if member_log else "N/A",
            }
        )

    customer_sessions = (
        Reservation.query.filter(
            func.date(Reservation.end_time) >= start_date,
            func.date(Reservation.end_time) <= end_date,
            Reservation.status.in_(["Checked-Out", "Cancelled"]),
        )
        .order_by(Reservation.end_time.desc())
        .all()
    )

    return render_template(
        "admin/reports.html",
        daily_reports=reports_with_member,
        customer_sessions=customer_sessions,
        start_date=start_date,
        end_date=end_date,
    )


@admin_bp.route("/generate_pdf")
@login_required
def generate_pdf():
    redirect_response = require_super_admin()
    if redirect_response:
        return redirect_response

    flash("PDF Generation feature is being initialized.")
    return redirect(url_for("admin.reports"))


@admin_bp.route("/generate_completed_sessions_pdf")
@login_required
def generate_completed_sessions_pdf():
    redirect_response = require_super_admin()
    if redirect_response:
        return redirect_response

    start_date = request.args.get("start_date", "")
    end_date = request.args.get("end_date", "")

    if start_date or end_date:
        flash(
            f"PDF generation for completed sessions from {start_date or 'the beginning'} to {end_date or 'today'} is being initialized."
        )
    else:
        flash("PDF generation for completed sessions is being initialized.")

    return redirect(url_for("admin.reports", start_date=start_date, end_date=end_date))


@admin_bp.route("/members")
@login_required
def members():
    redirect_response = require_admin_or_staff()
    if redirect_response:
        return redirect_response

    active_tab = request.args.get("tab", "requests")
    search = request.args.get("search", "")
    # Include users with explicit role 'member' OR users who have an active/approved SoloPlan
    approved_solo_users = db.session.query(SoloPlan.user_id).filter(SoloPlan.status.ilike('approved'))
    query = User.query.filter(
        or_(User.role == "member", User.id.in_(approved_solo_users))
    )
    if search:
        search_pattern = f"%{search}%"
        filters = [
            User.name.ilike(search_pattern),
            User.email.ilike(search_pattern),
            User.phone.ilike(search_pattern),
        ]
        if search.isdigit():
            filters.append(User.id == int(search))
        query = query.filter(or_(*filters))

    approved_solo_user_ids = [r[0] for r in approved_solo_users.distinct().all()]
    approved_solo_user_ids_set = set(approved_solo_user_ids)

    all_members = query.order_by(User.created_at.desc()).all()

    # Ensure any approved solo-plan user without an explicit membership record can still be checked in.
    created_membership = False
    for member in all_members:
        if member.id in approved_solo_user_ids_set:
            created_membership = created_membership or _ensure_approved_solo_plan_membership(member)
    if created_membership:
        db.session.commit()
        all_members = query.order_by(User.created_at.desc()).all()

    membership_requests = (
        SoloPlan.query.filter_by(status="pending")
        .order_by(SoloPlan.created_at.desc())
        .all()
    )
    return render_template(
        "admin/members.html",
        members=all_members,
        search=search,
        membership_requests=membership_requests,
        active_tab=active_tab,
        approved_solo_user_ids=approved_solo_user_ids,
    )


@admin_bp.route("/delete_member/<int:user_id>", methods=["POST"])
@login_required
def delete_member(user_id):
    if request.is_json:
        redirect_response = require_super_admin_json()
        if redirect_response:
            return redirect_response
    else:
        redirect_response = require_super_admin()
        if redirect_response:
            return redirect_response

    user = User.query.get_or_404(user_id)
    if user.role == "admin":
        if request.is_json:
            return jsonify({"status": "error", "message": "Cannot delete admin account."}), 400
        flash("Cannot delete admin account.")
        return redirect(url_for("admin.members"))

    db.session.delete(user)
    db.session.commit()
    if request.is_json:
        return jsonify({"status": "success", "message": "Member deleted permanently."})

    flash(f"Member {user.name} has been deleted.")
    return redirect(url_for("admin.members"))


# ---------------------------------------------------------------------------
# Membership Management Routes
# ---------------------------------------------------------------------------
@admin_bp.route("/official_members")
@login_required
def official_members():
    """Display all members with active/expired memberships in card layout."""
    redirect_response = require_admin_or_staff()
    if redirect_response:
        return redirect_response

    search = request.args.get("search", "")
    
    # Get all memberships with their user info
    query = Membership.query.join(User).order_by(Membership.status.desc(), User.name.asc())
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(or_(
            User.name.ilike(search_pattern),
            User.email.ilike(search_pattern),
            User.phone.ilike(search_pattern)
        ))
    
    memberships = query.all()
    
    # Separate active, pending, and expired
    active_memberships = [m for m in memberships if m.is_active]
    pending_memberships = [m for m in memberships if m.status == "pending"]
    expired_memberships = [m for m in memberships if m.status == "expired"]
    
    return render_template(
        "admin/official_members.html",
        active_memberships=active_memberships,
        pending_memberships=pending_memberships,
        expired_memberships=expired_memberships,
        search=search
    )


@admin_bp.route("/api/member/<int:membership_id>/check-in", methods=["POST"])
@login_required
def membership_check_in(membership_id):
    """Check in a member and start their session timer."""
    redirect_response = require_admin_or_staff_json()
    if redirect_response:
        return redirect_response

    membership = Membership.query.get_or_404(membership_id)
    
    if not membership.is_active:
        return jsonify({"status": "error", "message": "Membership is not active"}), 400
    
    if membership.is_checked_in:
        return jsonify({"status": "error", "message": "Member is already checked in"}), 400
    
    if membership.hours_left <= 0:
        return jsonify({"status": "error", "message": "No hours remaining"}), 400
    
    # Create attendance log
    now = datetime.utcnow()
    log = AttendanceLog(
        membership_id=membership.id,
        check_in_time=now
    )
    membership.is_checked_in = True
    membership.updated_at = now
    
    db.session.add(log)
    db.session.commit()
    
    return jsonify({
        "status": "success",
        "message": f"{membership.user.name} checked in",
        "check_in_time": now.isoformat(),
        "hours_left": membership.hours_left
    })


@admin_bp.route("/api/member/<int:membership_id>/check-out", methods=["POST"])
@login_required
def membership_check_out(membership_id):
    """Check out a member, end session, and deduct hours."""
    redirect_response = require_admin_or_staff_json()
    if redirect_response:
        return redirect_response

    membership = Membership.query.get_or_404(membership_id)
    
    if not membership.is_checked_in:
        return jsonify({"status": "error", "message": "Member is not checked in"}), 400
    
    # Get the current attendance log
    current_log = membership.attendance_logs.filter(
        AttendanceLog.check_out_time.is_(None)
    ).first()
    
    if not current_log:
        return jsonify({"status": "error", "message": "No active session found"}), 400
    
    now = datetime.utcnow()
    current_log.check_out_time = now
    
    # Calculate hours spent
    duration = (now - current_log.check_in_time).total_seconds() / 3600
    hours_deducted = round(duration, 2)
    
    # Ensure we don't deduct more than available
    if hours_deducted > membership.hours_left:
        hours_deducted = membership.hours_left
    
    current_log.hours_deducted = hours_deducted
    membership.hours_left = round(membership.hours_left - hours_deducted, 2)
    membership.is_checked_in = False
    membership.updated_at = now
    
    # Check if membership should expire
    if membership.hours_left <= 0:
        membership.status = "expired"
    
    db.session.commit()
    
    return jsonify({
        "status": "success",
        "message": f"{membership.user.name} checked out - {hours_deducted} hours deducted",
        "hours_deducted": hours_deducted,
        "hours_left": membership.hours_left,
        "check_out_time": now.isoformat()
    })


@admin_bp.route("/api/member/<int:membership_id>/attendance", methods=["GET"])
@login_required
def member_attendance_history(membership_id):
    """Get attendance history for a member."""
    redirect_response = require_admin_or_staff_json()
    if redirect_response:
        return redirect_response

    membership = Membership.query.get_or_404(membership_id)
    
    logs = membership.attendance_logs.order_by(AttendanceLog.check_in_time.desc()).all()
    
    attendance_data = []
    for log in logs:
        attendance_data.append({
            "id": log.id,
            "date": format_date(log.check_in_time),
            "check_in": format_checkin_time(log.check_in_time),
            "check_out": format_checkout_time(log.check_out_time),
            "hours": decimal_hours_to_readable(log.hours_deducted) if log.hours_deducted > 0 else "-"
        })
    
    return jsonify({
        "status": "success",
        "member_name": membership.user.name,
        "total_hours": membership.total_hours,
        "hours_left": membership.hours_left,
        "attendance": attendance_data
    })


@admin_bp.route("/api/dashboard/common-area-occupants", methods=["GET"])
@login_required
def common_area_occupants():
    """Get list of members currently checked in (for Common Area display on dashboard)."""
    redirect_response = require_admin_or_staff_json()
    if redirect_response:
        return redirect_response

    # Get all members currently checked in
    checked_in = db.session.query(Membership).filter(
        Membership.is_checked_in == True
    ).all()
    
    occupants = []
    for membership in checked_in:
        _expire_membership_if_needed(membership)
        if membership.status != "active" or not membership.is_checked_in:
            continue

        # Get the current active log
        active_log = membership.attendance_logs.filter(
            AttendanceLog.check_out_time.is_(None)
        ).first()
        
        if active_log:
            elapsed = (datetime.utcnow() - active_log.check_in_time).total_seconds() / 3600
            occupants.append({
                "id": membership.id,
                "name": membership.user.name,
                "check_in_time": active_log.check_in_time.isoformat(),
                "formatted_check_in": format_checkin_time(active_log.check_in_time),
                "elapsed_hours": round(elapsed, 2),
                "hours_left": membership.hours_left
            })
    
    return jsonify({
        "status": "success",
        "count": len(occupants),
        "occupants": occupants
    })
