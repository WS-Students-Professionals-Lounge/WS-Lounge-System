"""
client.py
Contains all client-facing blueprints: auth, main, and api.
"""

import os
from datetime import datetime, timedelta
import pytz

from database_fixed import (
    db,
    Room,
    User,
    TimeLog,
    SoloPlan,
    LoginForm,
    Membership,
    PaymentInfo,
    ProfileForm,
    Reservation,
    AttendanceLog,
    ReservationForm,
    RegistrationForm,
    ChangePasswordForm,
    generate_customer_id,
    get_user_by_email,
)
from flask import (
    flash,
    jsonify,
    request,
    session,
    url_for,
    redirect,
    Blueprint,
    current_app,
    render_template,
)
from sqlalchemy import func, or_
from werkzeug.utils import secure_filename
from flask_login import current_user, login_required, login_user, logout_user


# Auth Blueprint
auth_bp = Blueprint("auth", __name__)
main_bp = Blueprint('main', __name__, template_folder='templates')


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "GET":
        return redirect(url_for("main.index", show_login="true"))

    form = LoginForm(meta={"csrf": False})
    if form.validate():
        email = form.email.data.strip().lower()
        user = get_user_by_email(email)
        if user is None or not user.check_password(form.password.data):
            flash("Invalid email or password", "danger")
            return redirect(url_for("main.index", show_login="true"))
        if not user.is_active:
            flash("Access Restricted: Account is inactive. Contact your administrator.", "danger")
            return redirect(url_for("main.index", show_login="true"))
        login_user(user, remember=form.remember_me.data)
        session["user_id"] = user.id
        session["user_name"] = user.name
        session["user_role"] = user.role
        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.dashboard"))

    flash("Please enter valid credentials and try again.", "danger")
    return redirect(url_for("main.index", show_login="true"))


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))

    if request.method == "GET":
        return redirect(url_for("main.index", show_register="true"))

    form = RegistrationForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        
        # Check if email already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered. Please login or use a different email.", "danger")
            return redirect(url_for("main.index", show_register="true"))
        
        try:
            user = User(name=form.name.data, email=email, phone=form.phone.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash("Registration failed. Please try again with a different email.", "danger")
            return redirect(url_for("main.index", show_register="true"))
        
        # FIX: Dulaon ang automatic login! Force user to manually log in.
        flash("Account created successfully! Please log in with your credentials.", "success")
        return redirect(url_for("main.index", show_login="true"))

    flash("Please complete all required fields correctly.", "danger")
    return redirect(url_for("main.index", show_register="true"))


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    session.pop("user_id", None)
    session.pop("user_name", None)
    session.pop("user_role", None)
    return redirect(url_for("main.index"))


# Main Blueprint
main_bp = Blueprint("main", __name__)


def get_admin_stats():
    # Fix: PHT Timezone (Asia/Manila) gamit ang pytz
    ph_tz = pytz.timezone("Asia/Manila")
    now = datetime.now(ph_tz)

    total_members = User.query.filter_by(role="member").count()
    active_timelogs = (
        db.session.query(TimeLog).filter(TimeLog.time_out.is_(None)).count()
    )
    
    # Calculate today's boundary based on PHT
    today_start = ph_tz.localize(datetime(now.year, now.month, now.day))
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

    # 1. FIX: Gamiton ang Asia/Manila Timezone sa pytz
    ph_tz = pytz.timezone("Asia/Manila")
    now = datetime.now(ph_tz)
    
    # Siguraduha nga ang membership.expiry_date kay naka-localize man o synchronized
    expiry_dt = membership.expiry_date
    if expiry_dt.tzinfo is None:
        expiry_dt = ph_tz.localize(expiry_dt)

    # 2. Compare if expired na
    if now >= expiry_dt:
        membership.status = 'expired'
        membership.hours_left = 0.0
        membership.is_checked_in = False

        active_log = membership.attendance_logs.filter(AttendanceLog.check_out_time.is_(None)).first()
        if active_log:
            # Check-out time set to expiry date
            active_log.check_out_time = membership.expiry_date
            
            # Synchronize active_log dates for subtraction if needed
            check_in = active_log.check_in_time
            check_out = active_log.check_out_time
            
            if check_in.tzinfo is None:
                check_in = ph_tz.localize(check_in)
            if check_out.tzinfo is None:
                check_out = ph_tz.localize(check_out)

            # Calculate exact hours deducted
            time_diff = check_out - check_in
            active_log.hours_deducted = round(time_diff.total_seconds() / 3600, 2)

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
    ph_tz = pytz.timezone("Asia/Manila")
    now_ph = datetime.now(ph_tz)
    now_naive = now_ph.replace(second=0, microsecond=0, tzinfo=None)

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

    if current_user.role in ["admin", "staff"]:
        return redirect(url_for("admin.dashboard"))

    # 1. Fetch Membership Data
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
            expiry_dt = membership.expiry_date
            if expiry_dt.tzinfo is None:
                expiry_dt = ph_tz.localize(expiry_dt)

            diff = expiry_dt - now_ph
            if diff.total_seconds() > 0:
                remaining_days = max(round(diff.total_seconds() / 86400, 1), 0)
            else:
                remaining_days = 0

    # 2. Fetch Solo Plans
    solo_plans = (
        SoloPlan.query.filter_by(user_id=current_user.id)
        .order_by(SoloPlan.created_at.desc())
        .limit(5)
        .all()
    )

    # CALCULATE TOTAL SOLO HOURS (Safe Join & Status Check)
    # ---------------------------------------------------------
    try:
        all_user_solo_plans = SoloPlan.query.join(Membership).filter(
            Membership.user_id == current_user.id
        ).all()
    except Exception:
        all_user_solo_plans = SoloPlan.query.filter(
            SoloPlan.user_id == current_user.id
        ).all()

    total_solo_hours = 0.0
    for plan in all_user_solo_plans:
        p_status = str(getattr(plan, 'status', '')).lower().strip()
        if p_status in ['approved', 'active', 'completed', 'ended', 'checked_out', 'checked-out', 'used', 'expired']:
            p_hours = (
                getattr(plan, 'hours', None) or 
                getattr(plan, 'duration_hours', None) or 
                getattr(plan, 'duration', None) or 
                getattr(plan, 'hours_left', 0) or 0
            )
            try:
                total_solo_hours += float(p_hours)
            except (ValueError, TypeError):
                pass

    total_solo_hours = round(total_solo_hours, 2)

    # Strict Attendance Log & Is_Checked_In Validation para sa Active Session
    open_log = None
    if membership:
        open_log = AttendanceLog.query.filter_by(
            membership_id=membership.id,
            check_out_time=None
        ).first()

    # Dynamic Validation: Matuod nga Active Session kon CHECKED IN pa gid man ang user
    is_user_checked_in = (membership and membership.is_checked_in) or (open_log is not None)

    active_solo = None
    if is_user_checked_in:
        active_solo = SoloPlan.query.filter(
            SoloPlan.user_id == current_user.id,
            SoloPlan.status.ilike("approved"),
            SoloPlan.expiry_date > now_naive,
            SoloPlan.status.notin_(["checked_out", "checked-out", "completed"])
        ).order_by(SoloPlan.created_at.desc()).first()

    active_session = None
    if is_user_checked_in:
        if active_solo:
            active_session = active_solo
        elif membership and membership.expiry_date and membership.expiry_date > now_naive and membership.status not in ["checked_out", "completed"]:
            active_session = membership
        else:
            active_session = latest_log

    return render_template(
        "dashboard/member_dashboard.html",
        reservations=reservations,
        active_plan=active_session,
        active_session=active_session,
        remaining_days=remaining_days,
        solo_plans=solo_plans,
        total_solo_hours=total_solo_hours,
        membership=membership,
        attendance_logs=attendance_logs,
        now_ph=now_ph,
    )


@main_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    profile_form = ProfileForm(obj=current_user)
    password_form = ChangePasswordForm()

    if request.method == "POST" and request.form.get("profile_submit") is not None:
        if profile_form.validate_on_submit():
            email = profile_form.email.data.strip().lower()
            existing_user = User.query.filter(func.lower(User.email) == email).first()
            if existing_user and existing_user.id != current_user.id:
                profile_form.email.errors.append("Email already in use by another account.")
            else:
                current_user.name = profile_form.name.data.strip()
                current_user.email = email
                current_user.phone = profile_form.phone.data.strip() or None
                db.session.commit()
                flash("Profile updated successfully.", "success")
                return redirect(url_for("main.profile"))

    if request.method == "POST" and request.form.get("password_submit") is not None:
        if password_form.validate_on_submit():
            if not current_user.check_password(password_form.current_password.data):
                password_form.current_password.errors.append("Current password is incorrect.")
            elif password_form.new_password.data != password_form.confirm_password.data:
                password_form.confirm_password.errors.append("Passwords do not match.")
            else:
                current_user.set_password(password_form.new_password.data)
                db.session.commit()
                flash("Password changed successfully.", "success")
                return redirect(url_for("main.profile"))

    return render_template("profile.html", profile_form=profile_form, password_form=password_form)


@main_bp.route("/rooms", methods=["GET", "POST"])
@login_required
def rooms():
    ph_tz = pytz.timezone("Asia/Manila")

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
    selected_room_id = None
    try:
        selected_room_id = int(form.room_id.data) if form.room_id.data is not None else None
    except (TypeError, ValueError):
        selected_room_id = None

    if selected_room_id is not None:
        selected_room = Room.query.get(selected_room_id)
        if selected_room and selected_room.id not in {room.id for room in available_rooms}:
            available_rooms.append(selected_room)

    available_rooms = sorted(available_rooms, key=lambda room: room.id)
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

    # FIX 1: Tanggalon ang tzinfo para sa accurate MySQL comparison (Naive Datetime)
    now_ph = datetime.now(ph_tz).replace(tzinfo=None)

    bookings = (
        db.session.query(
            Reservation.start_time, Reservation.end_time, Reservation.status, Room.name
        )
        .join(Room)
        .filter(
            Reservation.status == "Confirmed",
            ~Room.name.ilike('Test Room%'),
            Reservation.end_time >= now_ph
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
        ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.jpe', '.gif', '.webp', '.pdf'}

        original_name = receipt_file.filename or ''
        ext = os.path.splitext(original_name)[1].lower()

        if ext not in ALLOWED_EXTENSIONS:
            flash("Unsupported receipt file type. Allowed: PNG, JPG, JPEG, JPE, GIF, WEBP, PDF.", "danger")
            return render_template("rooms.html", rooms=rooms, bookings=bookings, form=form, payment_info=payment_info)
        
        receipt_file.seek(0, os.SEEK_END)
        size = receipt_file.tell()
        receipt_file.seek(0)
        max_bytes = 5 * 1024 * 1024

        if size > max_bytes:
            flash("Receipt file too large (max 5MB).", "danger")
            return render_template("rooms.html", rooms=rooms, bookings=bookings, form=form, payment_info=payment_info)

        if not room:
            flash("Please select a valid room.", "danger")
            return render_template("rooms.html", rooms=rooms, bookings=bookings, form=form, payment_info=payment_info)

        # FIX 2: DULAON ANG ph_tz.localize(...) KAY SIYA ANG NAGAGAHO SANG TIMEZONE OFFSET SA DB!
        # Dili na naton i-localize ang start_time kag end_time para timezone-naive sila.

        if not end_time and not is_open_time:
            flash("Please choose a valid reservation end time.", "danger")
            return render_template("rooms.html", rooms=rooms, bookings=bookings, form=form, payment_info=payment_info)

        if not end_time:
            end_time = start_time + timedelta(hours=8)

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

        extra_fee_total = 0.0
        try:
            extra_fee_total = float(request.form.get('extra_fee_total', 0) or 0)
        except ValueError:
            extra_fee_total = 0.0

        total = round(total + extra_fee_total, 2)
        
        payment_type = form.payment_type.data if hasattr(form, 'payment_type') else "Downpayment"
        if payment_type == "Full Payment":
            amount_paid = round(total, 2)
        else:
            amount_paid = round(total * 0.5, 2)

        try:
            customer_id = generate_customer_id(
                "common area" if room.name.strip().lower() == "common area" else "other"
            )
        except ValueError as e:
            flash(str(e), "danger")
            return render_template("rooms.html", rooms=rooms, bookings=bookings, form=form, payment_info=payment_info)

        now_timestamp = int(datetime.now(ph_tz).timestamp())
        filename = secure_filename(
            f"receipt_{current_user.id}_{now_timestamp}_{receipt_file.filename}"
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
            total_amount=total,
            amount_paid=amount_paid,
            payment_method=payment_method,
            payment_type=form.payment_type.data,
            receipt_image=filename,
            paid=False,
        )
        db.session.add(reservation)
        db.session.commit()
        
        # Pag-redirect lang para makuha na ang bag-o nga state
        flash(
            "Reservation created and payment receipt uploaded. Awaiting admin approval.",
            "success",
        )
        return redirect(url_for("main.rooms"))

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
    ph_tz = pytz.timezone("Asia/Manila")
    now_ph = datetime.now(ph_tz)
    now_naive = now_ph.replace(second=0, microsecond=0, tzinfo=None)
    month_start = ph_tz.localize(datetime(now_ph.year, now_ph.month, 1))

    # 1. FETCH MEMBERSHIP & ATTENDANCE LOGS
    membership = Membership.query.filter_by(user_id=current_user.id).first()

    # 2. DYNAMIC ACTIVE SESSION CHECK (Checked-In Validation)
    open_log = None
    if membership:
        open_log = AttendanceLog.query.filter_by(
            membership_id=membership.id,
            check_out_time=None
        ).first()

    # Dapa checked in gid man sa Membership flag O may nabilin nga open AttendanceLog
    is_checked_in = (membership and membership.is_checked_in) or (open_log is not None)

    active_session = None
    if is_checked_in:
        active_solo = SoloPlan.query.filter(
            SoloPlan.user_id == current_user.id,
            SoloPlan.status.ilike("approved"),
            SoloPlan.expiry_date > now_naive,
            SoloPlan.status.notin_(["checked_out", "checked-out", "completed"])
        ).order_by(SoloPlan.id.desc()).first()

        if active_solo:
            active_session = active_solo
        elif membership and membership.expiry_date and membership.expiry_date > now_naive and membership.status not in ["checked_out", "completed"]:
            active_session = membership

    logs = []
    completed_sessions_count = 0
    total_time_all = 0
    total_time_month = 0
    today_logs = 0
    plan_counts = {}

    # 3. COMPUTE ATTENDANCE LOGS (If exists)
    if membership:
        raw_logs = (
            AttendanceLog.query.filter_by(membership_id=membership.id)
            .order_by(AttendanceLog.check_in_time.desc())
            .limit(10)
            .all()
        )

        for l in raw_logs:
            check_in = l.check_in_time
            if check_in and check_in.tzinfo is None:
                check_in = ph_tz.localize(check_in)

            if l.check_out_time:
                check_out = l.check_out_time
                if check_out.tzinfo is None:
                    check_out = ph_tz.localize(check_out)
                duration_hours = l.session_duration_hours or ((check_out - check_in).total_seconds() / 3600)
            else:
                duration_hours = max((now_ph - check_in).total_seconds() / 3600, 0)

            p_name = membership.plan_name or 'INDIVIDUAL RATE'
            plan_counts[p_name] = plan_counts.get(p_name, 0) + 1

            logs.append({
                'time_in': check_in,
                'time_out': l.check_out_time,
                'status': 'Ended' if l.check_out_time else 'Active',
                'plan': p_name,
                'total_time': int(duration_hours * 60),
            })

        completed_sessions_count = AttendanceLog.query.filter(
            AttendanceLog.membership_id == membership.id,
            AttendanceLog.check_out_time != None
        ).count()

        all_attendance_logs = AttendanceLog.query.filter_by(membership_id=membership.id).all()

        for log in all_attendance_logs:
            c_in = log.check_in_time
            if c_in and c_in.tzinfo is None:
                c_in = ph_tz.localize(c_in)

            if log.check_out_time:
                c_out = log.check_out_time
                if c_out.tzinfo is None:
                    c_out = ph_tz.localize(c_out)
                dur = (c_out - c_in).total_seconds() / 3600
            else:
                dur = max((now_ph - c_in).total_seconds() / 3600, 0)

            dur_minutes = int(dur * 60)
            total_time_all += dur_minutes

            if c_in >= month_start:
                total_time_month += dur_minutes

            if c_in.date() == now_ph.date():
                today_logs += dur_minutes

    # 4. COMPUTE SOLO PLANS (If Attendance Logs are empty or to complement history)
    solo_history = SoloPlan.query.filter_by(user_id=current_user.id).order_by(SoloPlan.created_at.desc()).all()
    
    for sp in solo_history:
        p_name = sp.plan_name or 'INDIVIDUAL RATE'
        plan_counts[p_name] = plan_counts.get(p_name, 0) + 1

        if not logs:  # Populated lang kun wala pa ma-populate sang AttendanceLog
            is_ended = sp.status in ['completed', 'ended', 'checked_out'] or (sp.expiry_date and sp.expiry_date <= now_naive)
            logs.append({
                'time_in': getattr(sp, 'created_at', None) or getattr(sp, 'start_time', None),
                'time_out': sp.expiry_date if is_ended else None,
                'status': 'Ended' if is_ended else 'Active',
                'plan': p_name,
                'total_time': 0,
            })

    if not membership and solo_history:
        completed_sessions_count = SoloPlan.query.filter(
            SoloPlan.user_id == current_user.id,
            SoloPlan.status.in_(['completed', 'ended', 'checked_out'])
        ).count()

    # A. COMPUTE MOST USED PLAN (Querying directly from completed SoloPlan history)
    most_frequent_plan = db.session.query(
        SoloPlan.plan_name, 
        func.count(SoloPlan.id).label('plan_count')
    ).filter(
        SoloPlan.user_id == current_user.id
    ).group_by(
        SoloPlan.plan_name
    ).order_by(
        db.desc('plan_count')
    ).first()

    if most_frequent_plan:
        most_used_room = most_frequent_plan.plan_name
    else:
        # Fallback sa plan_counts dict kon walang query match
        most_used_room = max(plan_counts, key=plan_counts.get) if plan_counts else "None"

    # CALCULATE AVG SESSION LENGTH (Safe Join sa Membership)
    all_user_logs = AttendanceLog.query.join(Membership).filter(
        Membership.user_id == current_user.id
    ).all()

    completed_session_minutes = []
    for log in all_user_logs:
        c_in = getattr(log, 'check_in_time', None)
        c_out = getattr(log, 'check_out_time', None)

        if c_in and c_out:
            diff_seconds = (c_out - c_in).total_seconds()
            if diff_seconds > 0:
                completed_session_minutes.append(diff_seconds / 60)
        elif getattr(log, 'duration_minutes', 0) and getattr(log, 'duration_minutes', 0) > 0:
            completed_session_minutes.append(float(log.duration_minutes))
        elif getattr(log, 'duration', 0) and getattr(log, 'duration', 0) > 0:
            completed_session_minutes.append(float(log.duration))

    if len(completed_session_minutes) > 0:
        avg_session_length = round(sum(completed_session_minutes) / len(completed_session_minutes))
    else:
        avg_session_length = 0

    totals = {
        "all_time_minutes": total_time_all,
        "month_time_minutes": total_time_month,
        "today_time_minutes": today_logs,
        "plan_totals": plan_counts,
        "most_used_room": most_used_room,
        "avg_session_length": avg_session_length
    }

    return render_template(
        "timelog.html",
        logs=logs[:10],
        current_plan=membership,
        totals=totals,
        active_session=active_session,
        completed_sessions=completed_sessions_count
    )


@main_bp.route("/timein", methods=["POST"])
@login_required
def time_in():
    ph_tz = pytz.timezone("Asia/Manila")
    now_ph = datetime.now(ph_tz)
    
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
            SoloPlan.expiry_date > now_ph.replace(tzinfo=None),
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
        time_in=now_ph,
    )
    db.session.add(timelog)
    db.session.commit()
    flash(f"Timed in with {approved_plan.plan_name}!", "success")
    return redirect(url_for("main.timelog"))


@main_bp.route("/timeout", methods=["POST"])
@login_required
def time_out():
    ph_tz = pytz.timezone("Asia/Manila")
    now_ph = datetime.now(ph_tz)

    active = (
        TimeLog.query.filter_by(user_id=current_user.id)
        .filter(TimeLog.time_out.is_(None))
        .first()
    )
    if not active:
        flash("No active time session found. Time in first.", "warning")
        return redirect(url_for("main.timelog"))

    # Synchronize active.time_in timezone if naive
    time_in_dt = active.time_in
    if time_in_dt and time_in_dt.tzinfo is None:
        time_in_dt = ph_tz.localize(time_in_dt)

    # Calculate exact duration in minutes based on PHT
    duration_seconds = (now_ph - time_in_dt).total_seconds()
    duration = max(int(duration_seconds / 60), 0)

    # Save exact Philippine Time on time_out (stripped of tzinfo for DB safety)
    active.time_out = now_ph.replace(tzinfo=None)
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

    ph_tz = pytz.timezone("Asia/Manila")
    now_ph = datetime.now(ph_tz)

    reservations = (
        db.session.query(Reservation)
        .join(Room)
        .filter(Reservation.user_id == current_user.id)
        .order_by(Reservation.start_time.desc())
        .all()
    )

    for res in reservations:
        end_time_dt = res.end_time
        if end_time_dt and end_time_dt.tzinfo is None:
            end_time_dt = ph_tz.localize(end_time_dt)
        
        # Attach dynamic property for template rendering if needed
        res.is_past = end_time_dt < now_ph if end_time_dt else False

    return render_template("reservations.html", reservations=reservations)


@main_bp.route("/get_time_inside")
@login_required
def get_time_inside():
    ph_tz = pytz.timezone("Asia/Manila")
    now_ph = datetime.now(ph_tz)

    latest = (
        TimeLog.query.filter_by(user_id=current_user.id)
        .order_by(TimeLog.time_in.desc())
        .first()
    )

    if latest and latest.time_out is None:
        # Localize time_in if timezone-naive
        time_in_dt = latest.time_in
        if time_in_dt.tzinfo is None:
            time_in_dt = ph_tz.localize(time_in_dt)

        # Compute exact elapsed seconds based on PHT
        diff = int((now_ph - time_in_dt).total_seconds())
        diff = max(diff, 0)  # Prevent negative values

        return jsonify({"status": "inside", "seconds": diff})

    return jsonify({"status": "outside", "seconds": 0})


@main_bp.route("/solo_rates", methods=["GET", "POST"])
@login_required
def solo_rates():
    if current_user.role != "member":
        flash("Unauthorized. Members only.", "warning")
        return redirect(url_for("main.dashboard"))

    ph_tz = pytz.timezone("Asia/Manila")
    now_ph = datetime.now(ph_tz)
    now_naive = now_ph.replace(tzinfo=None)

    plans = Plan.query.all() if 'Plan' in globals() else []

    # Check attendance / check-in flag sang membership
    membership_record = Membership.query.filter_by(user_id=current_user.id).first()
    
    open_log = None
    if membership_record:
        open_log = AttendanceLog.query.filter_by(
            membership_id=membership_record.id,
            check_out_time=None
        ).first()

    # User is only considered checked-in if flag is true or open log exists
    is_user_checked_in = (membership_record and membership_record.is_checked_in) or (open_log is not None)

    # 1. Fetch Membership - Check condition kon naka Check-In gid man
    active_membership = None
    if is_user_checked_in:
        active_membership = (
            Membership.query.filter(
                Membership.user_id == current_user.id,
                Membership.status.ilike("active"),
                Membership.status.notin_(["checked_out", "checked-out", "completed"]),
                Membership.expiry_date > now_naive
            )
            .order_by(Membership.start_date.desc())
            .first()
        )

    active_plan = active_membership
    remaining_days = expiration = None

    if active_plan and active_plan.expiry_date:
        expiration = active_plan.expiry_date
        if expiration.tzinfo is None:
            expiration = ph_tz.localize(expiration)

        diff = expiration - now_ph
        remaining_days = round(diff.total_seconds() / 86400, 1) if diff.total_seconds() > 0 else 0

    # 2. Fetch SoloPlan - Filter validation kon naka Check-In ang user
    active_solo_plan = None
    if is_user_checked_in:
        active_solo_plan = (
            SoloPlan.query.filter(
                SoloPlan.user_id == current_user.id,
                SoloPlan.status.ilike("approved"),
                SoloPlan.expiry_date > now_naive,
                SoloPlan.status.notin_(["checked_out", "checked-out", "completed", "CHECKED_OUT"])
            )
            .order_by(SoloPlan.created_at.desc())
            .first()
        )

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

    # 3. Query has_pending
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
                    "You currently have an active plan. Please wait for it to expire before purchasing a new one.",
                    "warning",
                )
            elif has_pending:
                flash(
                    "You already have a pending plan application. Please wait for admin approval.",
                    "warning",
                )
            else:
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
                    created_at=now_naive,
                )
                db.session.add(solo_plan)
                db.session.commit()

                message = (
                    f"Plan '{selected_plan}' selected! Waiting for admin approval. Your plan ID is: {customer_id}"
                )
                flash(message, "success")

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

# API Blueprint
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
    ph_tz = pytz.timezone("Asia/Manila")
    now_ph = datetime.now(ph_tz)

    total_members = User.query.filter_by(role="member").count()
    active_plans = (
        db.session.query(TimeLog).filter(TimeLog.time_out.is_(None)).count()
    )

    today_start = ph_tz.localize(datetime(now_ph.year, now_ph.month, now_ph.day))
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
    ph_tz = pytz.timezone("Asia/Manila")
    now_ph = datetime.now(ph_tz)

    plan_name = request.form.get('plan_name')
    payment_method = request.form.get('payment_method')
    receipt_file = request.files.get('receipt_image')

    if not receipt_file or not plan_name:
        return jsonify({'success': False, 'message': 'Missing data or receipt.'}), 400

    allowed_ext = ['.png', '.jpg', '.jpeg', '.jpe', '.webp', '.gif', '.pdf']
    original_name = receipt_file.filename or ''
    ext = os.path.splitext(original_name)[1].lower() or '.png'

    if ext not in allowed_ext:
        return jsonify({'success': False, 'message': 'Unsupported file type.'}), 400

    receipt_file.seek(0, os.SEEK_END)
    size = receipt_file.tell()
    receipt_file.seek(0)
    if size > 5 * 1024 * 1024:
        return jsonify({'success': False, 'message': 'File too large (max 5MB).'}), 400

    # MIME check (gina-allow lang ang image/ o application/pdf)
    mimetype = receipt_file.mimetype or ''
    if ext == '.pdf':
        if mimetype != 'application/pdf':
            return jsonify({'success': False, 'message': 'Uploaded file is not a valid PDF.'}), 400
    else:
        if not mimetype.startswith('image/'):
            return jsonify({'success': False, 'message': 'Uploaded file is not a valid image.'}), 400

    try:
        # Use PHT timestamp for unique filename
        timestamp = int(now_ph.timestamp())
        filename = secure_filename(f"receipt_{current_user.id}_{timestamp}{ext}")
        upload_folder = os.path.join(current_app.root_path, 'static/uploads/receipts')
        
        if not os.path.exists(upload_folder):
            os.makedirs(upload_folder)
            
        file_path = os.path.join(upload_folder, filename)
        receipt_file.save(file_path)

        # Generate Customer ID for the Solo Plan
        customer_id = generate_customer_id("monthly")  # Defaulting to monthly pattern for solo plans

        # Create SoloPlan record with explicit Philippine Time
        new_plan = SoloPlan(
            user_id=current_user.id,
            customer_id=customer_id,
            plan_name=plan_name,
            status="pending",
            receipt_image=filename, 
            payment_method=payment_method,
            created_at=now_ph
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
    
    ph_tz = pytz.timezone("Asia/Manila")
    now_ph = datetime.now(ph_tz)

    data = request.json or {}
    amount = int(data.get('amount', 0) * 100)
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
            # 2. FIX: Include Philippine Time metadata for precise server log tracking
            metadata={
                'user_id': current_user.id, 
                'plan': plan_name,
                'created_at_pht': now_ph.strftime('%Y-%m-%d %H:%M:%S'),
                'timestamp_pht': int(now_ph.timestamp())
            }
        )
        return jsonify({'id': session.id})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@main_bp.route("/checkout_solo_plan", methods=["POST"])
@login_required
def checkout_solo_plan():
    ph_tz = pytz.timezone("Asia/Manila")
    now_ph = datetime.now(ph_tz)
    now_naive = now_ph.replace(second=0, microsecond=0, tzinfo=None)

    # 1. Update Membership Check-in status
    membership = Membership.query.filter_by(user_id=current_user.id).first()
    if membership:
        
        membership.is_checked_in = False
        membership.is_checked_out = True
        membership.is_status = "active"

        # Close open attendance log
        open_log = AttendanceLog.query.filter(
            AttendanceLog.membership_id == membership.id,
            AttendanceLog.check_out_time.is_(None)
        ).order_by(AttendanceLog.check_in_time.desc()).first()

        if open_log:
            open_log.check_out_time = now_naive
            c_in = open_log.check_in_time
            if c_in and c_in.tzinfo is None:
                c_in = ph_tz.localize(c_in)
            dur_hours = max((now_ph - c_in).total_seconds() / 3600, 0) if c_in else 0.0
            open_log.hours_deducted = round(dur_hours, 2)

    # 2. DUGANG FIX: Bag-uhon gid ang STATUS sang tanan nga Active/Approved Solo Plans sang user
    user_plans = SoloPlan.query.filter(
        SoloPlan.user_id == current_user.id,
        SoloPlan.status.in_(["Approved", "approved", "APPROVED", "Pending", "pending"])
    ).all()

    for plan in user_plans:
        plan.status = "checked_out"

    db.session.commit()
    flash("Successfully checked out!", "success")
    return redirect(url_for("main.solo_rates"))

@api_bp.route("/membership/status", methods=["GET"])
@login_required
def membership_status():
    """Get current user's membership status"""
    ph_tz = pytz.timezone("Asia/Manila")
    now_ph = datetime.now(ph_tz)

    membership = Membership.query.filter_by(user_id=current_user.id).first()
    
    if not membership:
        return jsonify({"status": "error", "message": "No membership found"})

    _expire_membership_if_needed(membership)
    
    expiry_iso = None
    if membership.expiry_date:
        expiry_dt = membership.expiry_date
        if expiry_dt.tzinfo is None:
            expiry_dt = ph_tz.localize(expiry_dt)
        expiry_iso = expiry_dt.isoformat()

    return jsonify({
        "status": "success",
        "hours_left": membership.hours_left,
        "is_checked_in": membership.is_checked_in,
        "is_active": membership.is_active,
        "plan_name": membership.plan_name,
        "expiry_date": expiry_iso,
        "accumulated_hours": membership.accumulated_hours
    })


@api_bp.route("/membership/current-session", methods=["GET"])
@login_required
def membership_current_session():
    """Get current user's active session (check-in time)"""
    ph_tz = pytz.timezone("Asia/Manila")
    now_ph = datetime.now(ph_tz)

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
    
    # Localize check_in_time and compute exact live duration in seconds
    check_in_dt = current_session.check_in_time
    if check_in_dt and check_in_dt.tzinfo is None:
        check_in_dt = ph_tz.localize(check_in_dt)

    elapsed_seconds = int((now_ph - check_in_dt).total_seconds())
    elapsed_seconds = max(elapsed_seconds, 0)
    
    return jsonify({
        "status": "success",
        "check_in_time": check_in_dt.isoformat(),
        "elapsed_seconds": elapsed_seconds,
        "membership_id": membership.id,
        "hours_left": membership.hours_left
    })