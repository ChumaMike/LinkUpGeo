import os
import logging
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, session, request, abort
from flask_login import login_required, current_user
from functools import wraps

from src.models.user_model import User
from src.models.listing_model import Listing, db

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash("Admin access required.", "error")
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function


# ---------------------------------------------------------
# Admin Login (master key → sets role to admin in session)
# ---------------------------------------------------------
@admin_bp.route("/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        entered_key = request.form.get("admin_key")
        master_key = os.getenv("ADMIN_SECRET")
        if entered_key and master_key and entered_key == master_key:
            session['is_admin_key_verified'] = True
            flash("Welcome back, Commander.", "success")
            return redirect(url_for('admin.admin_panel'))
        flash("Access Denied: Incorrect Key.", "error")
        logger.warning("Failed admin login attempt")
    return render_template("admin/admin_login.html")


@admin_bp.route("/logout")
def admin_logout():
    session.pop('is_admin_key_verified', None)
    flash("Session Closed.", "info")
    return redirect(url_for('admin.admin_login'))


# ---------------------------------------------------------
# Admin Panel
# ---------------------------------------------------------
@admin_bp.route("/")
@login_required
@admin_required
def admin_panel():
    total_users = User.query.filter(User.deleted_at == None).count()
    total_listings = Listing.query.filter(Listing.deleted_at == None).count()
    pending_listings = Listing.query.filter_by(is_verified=False).filter(Listing.deleted_at == None).count()

    users = User.query.filter(User.deleted_at == None).all()
    listings = Listing.query.filter(Listing.deleted_at == None).order_by(Listing.created_at.desc()).all()

    return render_template("admin/admin.html",
                           stats={
                               "users": total_users,
                               "listings": total_listings,
                               "pending": pending_listings
                           },
                           users=users,
                           listings=listings)


# ---------------------------------------------------------
# Verify Listing (POST only)
# ---------------------------------------------------------
@admin_bp.route("/verify/<int:listing_id>", methods=["POST"])
@login_required
@admin_required
def verify_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    listing.is_verified = True
    db.session.commit()
    logger.info("Admin %s verified listing %d", current_user.id, listing_id)
    flash(f"Verified '{listing.title}'!", "success")
    return redirect(url_for('admin.admin_panel'))


# ---------------------------------------------------------
# Delete Listing — soft delete (POST only)
# ---------------------------------------------------------
@admin_bp.route("/delete_listing/<int:listing_id>", methods=["POST"])
@login_required
@admin_required
def delete_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    listing.deleted_at = datetime.utcnow()
    db.session.commit()
    logger.info("Admin %s soft-deleted listing %d", current_user.id, listing_id)
    flash(f"Listing '{listing.title}' removed.", "warning")
    return redirect(url_for('admin.admin_panel'))


# ---------------------------------------------------------
# Delete User — soft delete (POST only)
# ---------------------------------------------------------
@admin_bp.route("/delete_user/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash("Cannot delete admin accounts.", "error")
        return redirect(url_for('admin.admin_panel'))
    user.deleted_at = datetime.utcnow()
    db.session.commit()
    logger.info("Admin %s soft-deleted user %d", current_user.id, user_id)
    flash(f"User {user.name} removed.", "success")
    return redirect(url_for('admin.admin_panel'))


# ---------------------------------------------------------
# Restore soft-deleted listing
# ---------------------------------------------------------
@admin_bp.route("/restore_listing/<int:listing_id>", methods=["POST"])
@login_required
@admin_required
def restore_listing(listing_id):
    listing = Listing.query.get_or_404(listing_id)
    listing.deleted_at = None
    db.session.commit()
    flash(f"Listing '{listing.title}' restored.", "success")
    return redirect(url_for('admin.admin_panel'))
