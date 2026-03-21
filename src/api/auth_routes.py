import re
import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from src.models.user_model import User
from src.models.listing_model import db
from src import limiter

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)

SA_PHONE_RE = re.compile(r'^27[6-8][0-9]{8}$')
PASSWORD_MIN = 8

VALID_ROLES = {'customer', 'provider'}


def _validate_phone(phone):
    """Accept 27xxxxxxxxx or 0xxxxxxxxx format, normalize to 27xxx."""
    phone = re.sub(r'\s+', '', phone or '')
    if phone.startswith('0') and len(phone) == 10:
        phone = '27' + phone[1:]
    if not SA_PHONE_RE.match(phone):
        return None, "Enter a valid South African mobile number (e.g. 0821234567 or 27821234567)."
    return phone, None


def _validate_password(password):
    if not password or len(password) < PASSWORD_MIN:
        return f"Password must be at least {PASSWORD_MIN} characters."
    if not re.search(r'\d', password):
        return "Password must contain at least one number."
    return None


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def login():
    if current_user.is_authenticated:
        return redirect(url_for('web.dashboard'))

    if request.method == 'POST':
        phone_raw = request.form.get('phone', '').strip()
        password = request.form.get('password', '')

        phone, phone_error = _validate_phone(phone_raw)
        if phone_error:
            flash(phone_error, 'error')
            return render_template('auth/login.html')

        user = User.query.filter_by(phone_number=phone).first()

        if user and not user.is_deleted and user.check_password(password):
            login_user(user)
            logger.info("User %d logged in", user.id)
            flash(f'Welcome back, {user.name}!', 'success')
            if user.role == 'admin':
                return redirect(url_for('admin.admin_panel'))
            return redirect(url_for('web.dashboard'))
        else:
            logger.warning("Failed login attempt for phone %s", phone)
            flash('Invalid phone number or password.', 'error')

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logger.info("User %d logged out", current_user.id)
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/signup', methods=['GET', 'POST'])
@limiter.limit("10 per minute")
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('web.dashboard'))

    if request.method == 'POST':
        phone_raw = request.form.get('phone', '').strip()
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'customer')

        # Validate phone
        phone, phone_error = _validate_phone(phone_raw)
        if phone_error:
            flash(phone_error, 'error')
            return render_template('auth/signup.html')

        # Validate name
        if not name or len(name) < 2 or len(name) > 50:
            flash("Name must be between 2 and 50 characters.", 'error')
            return render_template('auth/signup.html')

        # Validate password
        pwd_error = _validate_password(password)
        if pwd_error:
            flash(pwd_error, 'error')
            return render_template('auth/signup.html')

        # Validate role
        if role not in VALID_ROLES:
            role = 'customer'

        if User.query.filter_by(phone_number=phone).first():
            flash('Phone number already registered.', 'error')
            return redirect(url_for('auth.signup'))

        new_user = User(phone_number=phone, name=name, role=role)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        logger.info("New user %d created (role: %s)", new_user.id, role)

        flash('Account created! Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/signup.html')
