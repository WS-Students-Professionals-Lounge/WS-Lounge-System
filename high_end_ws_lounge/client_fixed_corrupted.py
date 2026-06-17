"""
client.py
Contains all client-facing blueprints: auth, main, and api.
"""

import os
from datetime import datetime, timedelta

                            generate_customer_id)
                            Room, SoloPlan, TimeLog, User, db,
                            RegistrationForm, Reservation, ReservationForm,
from database_fixed import (AttendanceLog, LoginForm, Membership, PaymentInfo,
                            generate_customer_id)
from flask import (Blueprint, :, current_app, def, flash, jsonify, login,
                   redirect, try:)
        try:
def logout():
def register():
@login_required
    logout_user()
    form = LoginForm()
def get_admin_stats():
    active_timelogs = (
    now = datetime.now()
        if existing_user:
        except Exception:
@auth_bp.route("/logout")
from sqlalchemy import or_

            login_user(user)
    form = RegistrationForm()
        if not user.is_active:
        except Exception as e:
    if request.method == "GET":
    if request.method == "GET":
            db.session.commit()
            db.session.add(user)
    session.pop("user_id", None)
    if form.validate_on_submit():
    if form.validate_on_submit():
            db.session.rollback()
    session.pop("user_name", None)
    session.pop("user_role", None)
        session["user_id"] = user.id
auth_bp = Blueprint("auth", __name__)
    if current_user.is_authenticated:
    if current_user.is_authenticated:
# ===========================================================================
# Main Blueprint
# ===========================================================================
main_bp = Blueprint("main", __name__)
        session["user_name"] = user.name
        session["user_role"] = user.role
from werkzeug.utils import secure_filename

    return redirect(url_for("main.index"))
        next_page = request.args.get("next")
        email = form.email.data.strip().lower()
        email = form.email.data.strip().lower()
@auth_bp.route("/login", methods=["GET", "POST"])
            user.set_password(form.password.data)
        return redirect(url_for("main.dashboard"))
        return redirect(url_for("main.dashboard"))
        return redirect(url_for("main.dashboard"))
@auth_bp.route("/register", methods=["GET", "POST"])
        user = User.query.filter_by(email=email).first()
        login_user(user, remember=form.remember_me.data)
    return redirect(url_for("main.index", show_login="true"))
                   render_template, request, session, url_for)
        return redirect(next_page or url_for("main.dashboard"))
    total_members = User.query.filter_by(role="member").count()
    return redirect(url_for("main.index", show_register="true"))
        return redirect(url_for("main.index", show_login="true"))
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
    flash("Please enter valid credentials and try again.", "danger")
        return redirect(url_for("main.index", show_register="true"))
            return redirect(url_for("main.index", show_login="true"))
            return redirect(url_for("main.index", show_login="true"))
            return redirect(url_for("main.index", show_login="true"))
    flash("Please complete all required fields correctly.", "danger")
            flash("Registration successful! Please login.", "success")
        if user is None or not user.check_password(form.password.data):
            return redirect(url_for("main.index", show_register="true"))
            return redirect(url_for("main.index", show_register="true"))
from flask_login import current_user, login_required, login_user, logout_user

        db.session.query(TimeLog).filter(TimeLog.time_out.is_(None)).count(),
        flash("Registration successful! Welcome to your dashboard.", "success")
            user = User(name=form.name.data, email=email, phone=form.phone.data)
            flash("Registration failed. Please try again with a different email.", "danger")
            flash("Email already registered. Please login or use a different email.", "danger")
            flash("Access Restricted: Account is inactive. Contact your administrator.", "danger")
    )
    today_start = datetime(now.year, now.month, now.day)
    today_end = today_start + timedelta(days=1)
    res_today = (
        Reservation.query.filter(
            Reservation.start_time >= today_start,
            Reservation.start_time < today_end,
            Reservation.status == "Confirmed",
        ).count()
    )
    revenue_today = (
        db.session.query(func.sum(Reservation.total_amount))
        .filter(
            Reservation.start_time >= today_start,
            Reservation.start_time < today_end,
            Reservation.status == "Confirmed",
        )
        .scalar()
        or 0
    )
    return total_members, active_timelogs, res_today, revenue_today


def _expire_membership_if_needed(membership):
    if not membership or membership.status != 'active' or not membership.expiry_date:
        return

    now = datetime.utcnow()
    if now >= membership.expiry_date:
        membership.status = 'expired'
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


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    login_form = LoginForm()
    register_form = RegistrationForm()
    show_register = request.args.get("show_register", "false").lower() == "true"
    show_login = request.args.get("show_login", "false").lower() == "true"

    return render_template(
        "landing.html",
        login_form=login_form,
        register_form=register_form,
        show_register=show_register,
        show_login=show_login,
    )


@main_bp.route("/dashboard")
@login_required
def dashboard():
    reservations = (
        Reservation.query.filter_by(user_id=current_user.id)
        .order_by(Reservation.created_at.desc())
        .limit(10)
        .all()
    )
    latest_log = (
        TimeLog.query.filter_by(user_id=current_user.id)
        .order_by(TimeLog.time_in.desc())
        .first()
    )

    # Get membership data if user has one
    membership = Membership.query.filter_by(user_id=current_user.id).first()
    attendance_logs = []
    remaining_days = None
    if membership:
        _expire_membership_if_needed(membership)
        attendance_logs = (
            AttendanceLog.query.filter_by(membership_id=membership.id)
            .order_by(AttendanceLog.check_in_time.desc())
            .limit(20)
            .all()
        )
        if membership.expiry_date:
            remaining_days = max((membership.expiry_date - datetime.now()).days, 0)

    if current_user.role in ["admin", "staff"]:
        # Redirect admins and operational staff to the dedicated admin dashboard.
        return redirect(url_for("admin.dashboard"))
    else:
        solo_plans = (
            SoloPlan.query.filter_by(user_id=current_user.id)
            .order_by(SoloPlan.created_at.desc())
            .limit(5)
            .all()
        )
        return render_template(
            "dashboard/member_dashboard.html",
            reservations=reservations,
            active_plan=latest_log,
            remaining_days=remaining_days,
            solo_plans=solo_plans,
            membership=membership,
            attendance_logs=attendance_logs,
        )


@main_bp.route("/rooms", methods=["GET", "POST"])
@login_required
def rooms():
    form = ReservationForm()
    rooms = Room.query.filter(~Room.name.ilike('Test Room%')).order_by(Room.id).all()
    available_rooms = (
        Room.query.filter(
            Room.status == "available",
            ~Room.name.ilike('Test Room%'),
        )
        .order_by(Room.id)
        .all()
    )
    form.room_id.choices = [
        (room.id, f"{room.name} - ₱{room.base_rate}/hr") for room in available_rooms
    ]

    payment_info = {
        info.method: {
            "account_number": info.account_number,
            "account_name": info.account_name,
            "qr_image": url_for("static", filename=f"uploads/payment/{info.qr_image}") if info.qr_image else None,
            "instructions": info.instructions,
        }
        for info in PaymentInfo.query.all()
    }

    bookings = (
        db.session.query(
            Reservation.start_time, Reservation.end_time, Reservation.status, Room.name
        )
        .join(Room)
        .filter(
            Reservation.status == "Confirmed",
            ~Room.name.ilike('Test Room%'),
        )
        .order_by(Reservation.start_time)
        .all()
    )

    if form.validate_on_submit() and current_user.role == "member":
        payment_method = request.form.get("payment_method", "")
        receipt_file = request.files.get("receipt_image")

        room = Room.query.get(form.room_id.data)
        start_time = form.start_time.data
        end_time = form.end_time.data
        is_open_time = form.is_open_time.data

        if payment_method not in ["GCash", "Maya"]:
            flash("Please select GCash or Maya as payment method.", "danger")
            return render_template("rooms.html", rooms=rooms, bookings=bookings, form=form, payment_info=payment_info)

        if not receipt_file or receipt_file.filename == "":
            flash("Please upload your payment receipt for verification.", "danger")
            return render_template("rooms.html", rooms=rooms, bookings=bookings, form=form, payment_info=payment_info)

        # Validate upload: extension and size
        allowed_ext = {'.png', '.jpg', '.jpeg', '.gif', '.pdf'}
        original_name = receipt_file.filename or ''
        ext = os.path.splitext(original_name)[1].lower()
        if ext not in allowed_ext:
            flash("Unsupported receipt file type. Allowed: PNG, JPG, GIF, PDF.", "danger")
            return render_template("rooms.html", rooms=rooms, bookings=bookings, form=form, payment_info=payment_info)

        receipt_file.seek(0, os.SEEK_END)
        size = receipt_file.tell()
        receipt_file.seek(0)
        max_bytes = 5 * 1024 * 1024
        if size > max_bytes:
            flash("Receipt file too large (max 5MB).", "danger")
            return render_template("rooms.html", rooms=rooms, bookings=bookings, form=form, payment_info=payment_info)

        # If image, do a quick magic check
        if ext in ['.png', '.jpg', '.jpeg', '.gif']:
            # Quick MIME check (best-effort)
            mimetype = receipt_file.mimetype or ''
            if not mimetype.startswith('image/'):
                flash("Uploaded file is not a valid image.", "danger")
                return render_template("rooms.html", rooms=rooms, bookings=bookings, form=form, payment_info=payment_info)

        if not room:
            flash("Please select a valid room.", "danger")
            return render_template("rooms.html", rooms=rooms, bookings=bookings, form=form, payment_info=payment_info)

        if not end_time and not is_open_time:
            flash("Please choose a valid reservation end time.", "danger")
            return render_template("rooms.html", rooms=rooms, bookings=bookings, form=form, payment_info=payment_info)

        if not end_time:
            end_time = start_time + timedelta(hours=12)

        conflict = Reservation.query.filter(
            Reservation.room_id == form.room_id.data,
            Reservation.status.in_(["Pending", "Confirmed"]),
            or_(
                (Reservation.start_time <= start_time)
                & (Reservation.end_time >= start_time),
                (Reservation.start_time <= end_time)
                & (Reservation.end_time >= end_time),
                (start_time <= Reservation.start_time)
                & (end_time >= Reservation.end_time),
            ),
        ).first()

        if conflict:
            flash("Room unavailable for selected time.", "danger")
            return render_template("rooms.html", rooms=rooms, bookings=bookings, form=form, payment_info=payment_info)

        hours = (end_time - start_time).total_seconds() / 3600
        total = max(room.base_rate * hours, room.base_rate)

        addon_name = request.form.get('addon_name', '').strip() or None
        try:
            addon_quantity = int(request.form.get('addon_quantity', 0) or 0)
        except ValueError:
            addon_quantity = 0
        try:
            addon_total = float(request.form.get('extra_fee_total', 0) or 0)
        except ValueError:
            addon_total = 0.0

        if not addon_name or addon_quantity <= 0:
            addon_name = None
            addon_quantity = 0
            addon_total = 0.0

        extra_fee_total = addon_total
        total = round(total + extra_fee_total, 2)
        
        # Calculate amount_paid based on payment_type
        payment_type = form.payment_type.data if hasattr(form, 'payment_type') else "Downpayment"
        if payment_type == "Full Payment":
            amount_paid = round(total, 2)
        else:  # Downpayment
            amount_paid = round(total * 0.5, 2)

        try:
            customer_id = generate_customer_id(
                "common area" if room.name.strip().lower() == "common area" else "other"
            )
        except ValueError as e:
            flash(str(e), "danger")
            return render_template("rooms.html", rooms=rooms, bookings=bookings, form=form, payment_info=payment_info)

        filename = secure_filename(
            f"receipt_{current_user.id}_{int(datetime.now().timestamp())}_{receipt_file.filename}"
        )
        upload_folder = os.path.join(current_app.root_path, "static/uploads/receipts")
        os.makedirs(upload_folder, exist_ok=True)
        file_path = os.path.join(upload_folder, filename)
        receipt_file.save(file_path)

        reservation = Reservation(
            user_id=current_user.id,
            customer_id=customer_id,
            room_id=form.room_id.data,
            customer_name=form.customer_name.data,
            contact_number=form.contact_number.data,
            pax_count=form.pax_count.data,
            start_time=start_time,
            end_time=end_time,
            status="Pending",
            added_by=current_user.name,
            extra_notes=form.extra_notes.data,
            extra_fee=extra_fee_total,
            addon_name=addon_name,
            addon_quantity=addon_quantity,
            addon_total=addon_total,
            total_amount=total,
            amount_paid=amount_paid,
            payment_method=payment_method,
            payment_type=form.payment_type.data,
            receipt_image=filename,
            paid=False,
        )
        room.status = "unavailable"
        db.session.add(reservation)
        db.session.commit()
        flash(
            "Reservation created and payment receipt uploaded. Awaiting admin approval.",
            "success",
        )

    return render_template(
        "rooms.html",
        rooms=rooms,
        bookings=bookings,
        form=form,
        payment_info=payment_info,
    )


@main_bp.route("/timelog")
@login_required
def timelog():
    now = datetime.now()
    month_start = now.replace(day=1)
    membership = Membership.query.filter_by(user_id=current_user.id).first()
    active_session = None
    logs = []

    if membership:
        raw_logs = (
            AttendanceLog.query.filter_by(membership_id=membership.id)
            .order_by(AttendanceLog.check_in_time.desc())
            .limit(10)
            .all()
        )
        # Do not expose AttendanceLog objects directly to the timelog template
        # which expects TimeLog-like fields (`time_in`, `time_out`, `plan`, `total_time`).
        logs = []
        for l in raw_logs:
            logs.append({
                'time_in': l.check_in_time,
                'time_out': l.check_out_time,
                'status': 'Ended' if l.check_out_time else 'Active',
                'plan': membership.plan_name or 'Lounge Area',
                'total_time': int(l.session_duration_hours * 60),
            })

        # For membership-based sessions we don't have a reservation `end_time`,
        # so avoid passing an AttendanceLog as `active_session` to the template.
        active_session = None

        all_attendance_logs = AttendanceLog.query.filter_by(membership_id=membership.id).all()
        total_time_all = int(
            sum((log.session_duration_hours * 60) for log in all_attendance_logs)
        )
        total_time_month = int(
            sum(
                (log.session_duration_hours * 60)
                for log in AttendanceLog.query.filter(
                    AttendanceLog.membership_id == membership.id,
                    AttendanceLog.check_in_time >= month_start,
                ).all()
            )
        )
        today_logs = int(
            sum(
                (log.session_duration_hours * 60)
                for log in AttendanceLog.query.filter(
                    AttendanceLog.membership_id == membership.id,
                    func.date(AttendanceLog.check_in_time) == now.date(),
                ).all()
            )
        )
        plan_totals = {
            membership.plan_name: total_time_all
        }
    else:
        logs = (
            TimeLog.query.filter_by(user_id=current_user.id)
            .order_by(TimeLog.id.desc())
            .limit(10)
            .all()
        )
        total_time_all = current_user.total_timelogged or 0
        total_time_month = (
            db.session.query(func.sum(TimeLog.total_time))
            .filter(TimeLog.user_id == current_user.id, TimeLog.time_in >= month_start)
            .scalar()
            or 0
        )
        today_logs = (
            db.session.query(func.sum(TimeLog.total_time))
            .filter(
                TimeLog.user_id == current_user.id,
                func.date(TimeLog.time_in) == now.date(),
            )
            .scalar()
            or 0
        )
        plan_totals = (
            db.session.query(TimeLog.plan, func.sum(TimeLog.total_time))
            .filter_by(user_id=current_user.id)
            .group_by(TimeLog.plan)
            .all()
        )
        plan_totals = dict(plan_totals)

    totals = {
        "all_time_minutes": total_time_all,
        "month_time_minutes": total_time_month,
        "today_time_minutes": today_logs,
        "plan_totals": plan_totals,
    }

    return render_template(
        "timelog.html",
        logs=logs,
        current_plan=membership,
        totals=totals,
        active_session=active_session,
    )


@main_bp.route("/timein", methods=["POST"])
@login_required
def time_in():
    active = (
        TimeLog.query.filter_by(user_id=current_user.id)
        .filter(TimeLog.time_out.is_(None))
        .first()
    )
    if active:
        flash("You are already timed in. Time out first.", "warning")
        return redirect(url_for("main.timelog"))

    approved_plan = (
        SoloPlan.query.filter(
            SoloPlan.user_id == current_user.id,
            SoloPlan.status == "approved",
            SoloPlan.expiry_date > datetime.now(),
        )
        .order_by(SoloPlan.created_at.desc())
        .first()
    )

    if not approved_plan:
        flash(
            "No active approved solo plan found. Please select, get approval, and check expiry.",
            "danger",
        )
        return redirect(url_for("main.solo_rates"))

    timelog = TimeLog(
        user_id=current_user.id,
        plan=approved_plan.plan_name,
        time_in=datetime.now(),
    )
    db.session.add(timelog)
    db.session.commit()
    flash(f"Timed in with {approved_plan.plan_name}!", "success")
    return redirect(url_for("main.timelog"))


@main_bp.route("/timeout", methods=["POST"])
@login_required
def time_out():
    active = (
        TimeLog.query.filter_by(user_id=current_user.id)
        .filter(TimeLog.time_out.is_(None))
        .first()
    )
    if not active:
        flash("No active time session found. Time in first.", "warning")
        return redirect(url_for("main.timelog"))

    now = datetime.now()
    duration = int((now - active.time_in).total_seconds() / 60)
    active.time_out = now
    active.total_time = duration
    db.session.commit()
    flash(f"Timed out. Session duration: {duration} minutes", "info")
    return redirect(url_for("main.timelog"))


@main_bp.route("/reservations")
@login_required
def reservations():
    if current_user.role != "member":
        flash("Members only")
        return redirect(url_for("main.dashboard"))

    reservations = (
        db.session.query(Reservation)
        .join(Room)
        .filter(Reservation.user_id == current_user.id)
        .order_by(Reservation.start_time.desc())
        .all()
    )

    return render_template("reservations.html", reservations=reservations)


@main_bp.route("/get_time_inside")
@login_required
def get_time_inside():
    latest = (
        TimeLog.query.filter_by(user_id=current_user.id)
        .order_by(TimeLog.time_in.desc())
        .first()
    )
    if latest and latest.time_out is None:
        diff = int((datetime.now() - latest.time_in).total_seconds())
        return jsonify({"status": "inside", "seconds": diff})
    return jsonify({"status": "outside", "seconds": 0})


@main_bp.route("/solo_rates", methods=["GET", "POST"])
@login_required
def solo_rates():
    if current_user.role != "member":
        flash("Unauthorized. Members only.")
        return redirect(url_for("main.dashboard"))

    now = datetime.now()

    active_membership = (
        Membership.query.filter_by(user_id=current_user.id, status="active")
        .order_by(Membership.start_date.desc())
        .first()
    )

    if active_membership and not active_membership.is_active:
        active_membership = None

    active_plan = active_membership
    remaining_days = expiration = None
    if active_plan and active_plan.expiry_date:
        expiration = active_plan.expiry_date
        remaining_days = max((expiration - now).days, 0)

    plans = [
        {
            "title": "INDIVIDUAL RATE",
            "price": "P35/HR",
            "details": ["Hourly common area usage", "WiFi / Charging"],
        },
        {
            "title": "INDIVIDUAL RATE (4HRS)",
            "price": "P100",
            "details": ["4hrs common area usage", "WiFi & Charging"],
        },
        {
            "title": "DAY/NIGHT PASS",
            "price": "P200",
            "details": [
                "Choice of Day (7AM – 10PM) or Night (6PM – 9AM) common area usage",
                "WiFi & Charging",
            ],
        },
        {
            "title": "WEEKLY PASS (DAY/NIGHT)",
            "price": "P800",
            "details": [
                "1 Week (7DAYS) common area usage",
                "Choice of Day (7AM – 10PM) or Night (6PM – 9AM)",
                "WiFi & Charging",
                "Gold Card",
            ],
        },
        {
            "title": "WEEKLY PASS (24HRS)",
            "price": "P1000",
            "details": [
                "1 Week (7DAYS) common area usage",
                "24/7 Usage",
                "WiFi & Charging",
                "Platinum Card",
            ],
        },
        {
            "title": "MONTHLY PASS (DAY/NIGHT)",
            "price": "P1999",
            "details": [
                "1 Month (30 DAYS) unlimited common area usage",
                "Choice of Day (7AM – 10PM) or Night (6PM – 9AM)",
                "WiFi, Charging & Exclusive Locker",
                "Gold Card",
            ],
        },
        {
            "title": "MONTHLY PASS (24HRS)",
            "price": "P2500",
            "details": [
                "24/7 Access to All Branches in Iloilo",
                "1 Month (30 days) unlimited common area usage",
                "WiFi & Charging, Exclusive Locker",
                "1hr Sleeping pod & Shower Room use per day (City Proper Branch only)",
                "Platinum Card",
            ],
        },
        {
            "title": "WORKSTATION (24HRS)",
            "price": "P3000",
            "details": [
                "24/7 Access to dedicated Workstation (Lapaz)",
                "24/7 Common area access to all Branches",
                "1 Dedicated Workstation",
                "WiFi & Charging & Exclusive Locker",
                "1hr Sleeping pod & Shower Room use per day (City Proper Branch only)",
                "Platinum Card",
            ],
        },
    ]

    active_solo_plan = (
        SoloPlan.query.filter(
            SoloPlan.user_id == current_user.id,
            SoloPlan.status == "approved",
            SoloPlan.expiry_date > datetime.now(),
        )
        .order_by(SoloPlan.created_at.desc())
        .first()
    )

    has_pending = (
        SoloPlan.query.filter_by(user_id=current_user.id, status="pending").first()
        is not None
    )

    message = None
    if request.method == "POST":
        selected_plan = request.form.get("plan_name")
        if selected_plan:
            if active_plan or active_solo_plan:
                flash(
                    "You already have an active membership or active plan. Wait for expiry to select a new one.",
                    "warning",
                )
            else:
                # Generate customer_id for monthly passes (3-digit numbers)
                try:
                    customer_id = generate_customer_id("monthly")
                except ValueError as e:
                    flash(str(e), "danger")
                    return redirect(url_for("main.solo_rates"))
                
                solo_plan = SoloPlan(
                    user_id=current_user.id,
                    customer_id=customer_id,
                    plan_name=selected_plan,
                    status="pending",
                )
                db.session.add(solo_plan)
                db.session.commit()
                message = (
                    f"Plan '{selected_plan}' selected! Waiting for admin approval. Your plan ID is: {customer_id}"
                )
                flash(message)

    return render_template(
        "solo_rates.html",
        plans=plans,
        active_plan=active_plan,
        remaining_days=remaining_days,
        expiration=expiration,
        message=message,
        active_solo_plan=active_solo_plan,
        has_pending=has_pending,
    )




# ===========================================================================
# API Blueprint
# ===========================================================================
api_bp = Blueprint("api", __name__)


@api_bp.route('/payment-info')
def payment_info():
    payment_data = {
        info.method: {
            'account_name': info.account_name,
            'account_number': info.account_number,
            'qr_image': url_for('static', filename=f'uploads/payment/{info.qr_image}') if info.qr_image else None,
            'instructions': info.instructions,
        }
        for info in PaymentInfo.query.all()
    }
    return jsonify(payment_data)


@api_bp.route("/stats")
def stats():
    now = datetime.now()
    total_members = User.query.filter_by(role="member").count()
    active_plans = (
        db.session.query(TimeLog).filter(TimeLog.time_out.is_(None)).count()
    )
    today_start = datetime(now.year, now.month, now.day)
    today_end = today_start + timedelta(days=1)
    res_today = Reservation.query.filter(
        Reservation.start_time >= today_start,
        Reservation.start_time < today_end,
        Reservation.status == "Confirmed",
    ).count()
    revenue_today = (
        db.session.query(func.sum(Reservation.total_amount))
        .filter(
            Reservation.start_time >= today_start,
            Reservation.start_time < today_end,
            Reservation.status == "Confirmed",
        )
        .scalar()
        or 0
    )
    return jsonify(
        {
            "total_members": total_members,
            "active_timelogs": active_plans,
            "reservations_today": res_today,
            "revenue_today": float(revenue_today),
        }
    )


@api_bp.route("/submit-solo-payment", methods=["POST"])
@login_required
def submit_solo_payment():
    """Handle GCash/Maya Receipt Uploads for Solo Plans"""
    plan_name = request.form.get('plan_name')
    payment_method = request.form.get('payment_method')
    receipt_file = request.files.get('receipt_image')

    if not receipt_file or not plan_name:
        return jsonify({'success': False, 'message': 'Missing data or receipt.'}), 400

    # Basic validation
    allowed_ext = ['.png', '.jpg', '.jpeg', '.gif', '.pdf']
    original_name = receipt_file.filename or ''
    ext = os.path.splitext(original_name)[1].lower() or '.png'
    if ext not in allowed_ext:
        return jsonify({'success': False, 'message': 'Unsupported file type.'}), 400

    # Size limit 5MB
    receipt_file.seek(0, os.SEEK_END)
    size = receipt_file.tell()
    receipt_file.seek(0)
    if size > 5 * 1024 * 1024:
        return jsonify({'success': False, 'message': 'File too large (max 5MB).'}), 400

    # If image, quick MIME check (best effort)
    if ext in ['.png', '.jpg', '.jpeg', '.gif']:
        mimetype = receipt_file.mimetype or ''
        if not mimetype.startswith('image/'):
            return jsonify({'success': False, 'message': 'Uploaded file is not a valid image.'}), 400

    try:
        # 1. Save Receipt Image
        original_name = receipt_file.filename or ''
        ext = os.path.splitext(original_name)[1].lower() or '.png'
        if ext not in ['.png', '.jpg', '.jpeg', '.gif', '.pdf']:
            ext = '.png'
        filename = secure_filename(f"receipt_{current_user.id}_{int(datetime.now().timestamp())}{ext}")
        upload_folder = os.path.join(current_app.root_path, 'static/uploads/receipts')
        
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            
        file_path = os.path.join(upload_folder, filename)
        receipt_file.save(file_path)

        # 2. Generate Customer ID for the Solo Plan
        customer_id = generate_customer_id("monthly")  # Defaulting to monthly pattern for solo plans

        # 3. Create SoloPlan record with Pending Status
        new_plan = SoloPlan(
            user_id=current_user.id,
            customer_id=customer_id,
            plan_name=plan_name,
            status="pending",
            receipt_image=filename, 
            payment_method=payment_method
        )
        
        db.session.add(new_plan)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Payment submitted for verification.'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@api_bp.route("/create-checkout-session", methods=["POST"])
@login_required
def create_checkout_session():
    import stripe
    from database_fixed import Config
    stripe.api_key = Config.STRIPE_SECRET_KEY
    
    data = request.json
    amount = int(data['amount'] * 100)  # PHP to cents
    plan_name = data.get('plan_name', 'Reservation')
    customer_email = current_user.email
    
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'php',
                    'product_data': {
                        'name': f"{plan_name} Payment"
                    },
                    'unit_amount': amount,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=url_for('main.solo_rates', _external=True) + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=url_for('main.solo_rates', _external=True),
            customer_email=customer_email,
            metadata={'user_id': current_user.id, 'plan': plan_name}
        )
        return jsonify({'id': session.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@api_bp.route("/membership/status", methods=["GET"])
@login_required
def membership_status():
    """Get current user's membership status"""
    membership = Membership.query.filter_by(user_id=current_user.id).first()
    
    if not membership:
        return jsonify({"status": "error", "message": "No membership found"})

    _expire_membership_if_needed(membership)
    
    return jsonify({
        "status": "success",
        "hours_left": membership.hours_left,
        "is_checked_in": membership.is_checked_in,
        "is_active": membership.is_active,
        "plan_name": membership.plan_name,
        "expiry_date": membership.expiry_date.isoformat() if membership.expiry_date else None
    })


@api_bp.route("/membership/current-session", methods=["GET"])
@login_required
def membership_current_session():
    """Get current user's active session (check-in time)"""
    membership = Membership.query.filter_by(user_id=current_user.id).first()
    
    if not membership:
        return jsonify({"status": "error", "message": "No membership found"})

    _expire_membership_if_needed(membership)
    
    if not membership.is_checked_in:
        return jsonify({"status": "error", "message": "No active session"})
    
    # Get the most recent attendance log that doesn't have a check_out_time
    current_session = (
        AttendanceLog.query.filter(
            AttendanceLog.membership_id == membership.id,
            AttendanceLog.check_out_time.is_(None)
        )
        .order_by(AttendanceLog.check_in_time.desc())
        .first()
    )
    
    if not current_session:
        return jsonify({"status": "error", "message": "No active session found"})
    
    return jsonify({
        "status": "success",
        "check_in_time": current_session.check_in_time.isoformat(),
        "membership_id": membership.id,
        "hours_left": membership.hours_left
    })