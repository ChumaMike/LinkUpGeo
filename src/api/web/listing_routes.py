import os
import re
import logging
from flask import Blueprint, request, redirect, url_for, flash, render_template, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from geopy.geocoders import Nominatim

from src.models.listing_model import db, Listing, Review
from src.services.ai_service import ai_brain

logger = logging.getLogger(__name__)
listings_bp = Blueprint('listings', __name__, url_prefix='/listings')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


def _allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _validate_listing_form(title, price, address):
    """Returns an error message string or None if valid."""
    if not title or len(title.strip()) < 5 or len(title.strip()) > 100:
        return "Service title must be between 5 and 100 characters."
    if not address or not address.strip():
        return "Address is required."
    if not price or not price.strip():
        return "Price is required."
    return None


def _geocode(address):
    lat, lon = -26.2514, 27.8967  # Default: Soweto
    try:
        geolocator = Nominatim(user_agent="linkup_geo_app")
        location = geolocator.geocode(f"{address}, South Africa")
        if location:
            lat, lon = location.latitude, location.longitude
    except Exception as e:
        logger.warning("Geocoding failed for '%s': %s", address, e)
    return lat, lon


def _extract_price_numeric(price_str):
    """Extract integer from price string like 'R450/hr' → 450."""
    match = re.search(r'\d+', str(price_str))
    return int(match.group()) if match else 0


def _save_image(file):
    if not file or file.filename == '':
        return None
    if not _allowed_file(file.filename):
        return None
    filename = secure_filename(file.filename)
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'src/static/uploads')
    os.makedirs(upload_folder, exist_ok=True)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)
    return f"uploads/{filename}"


@listings_bp.route("/add", methods=["POST"])
@login_required
def add():
    title = request.form.get("title", "").strip()
    category = request.form.get("category", "service")
    price = request.form.get("price", "").strip()
    address = request.form.get("address", "").strip()

    # Input validation
    error = _validate_listing_form(title, price, address)
    if error:
        flash(error, "error")
        return redirect(url_for("web.dashboard"))

    # Category whitelist
    if category not in ('service', 'house', 'job'):
        category = 'service'

    # Duplicate check
    existing = Listing.query.filter_by(title=title, provider_id=current_user.id).first()
    if existing:
        flash("You already posted this service.", "warning")
        return redirect(url_for("web.dashboard"))

    lat, lon = _geocode(address)

    # AI Tagging
    try:
        tags = ai_brain.generate_keywords(title, category)
    except Exception:
        tags = title.lower()

    # Image upload
    image_url = None
    if 'image' in request.files:
        image_url = _save_image(request.files['image'])

    new_listing = Listing(
        title=title,
        category=category,
        price=price,
        price_numeric=_extract_price_numeric(price),
        contact=current_user.phone_number,
        address=address,
        provider_id=current_user.id,
        is_verified=False,  # all listings start pending admin review
        rating=0.0,
        latitude=lat,
        longitude=lon,
        keywords=tags,
        image_url=image_url,
    )

    db.session.add(new_listing)
    db.session.commit()
    logger.info("New listing %d created by user %d (pending verification)", new_listing.id, current_user.id)

    flash("Listing submitted! An admin will review and publish it shortly.", "success")
    return redirect(url_for("web.dashboard"))


@listings_bp.route("/edit/<int:listing_id>", methods=["GET", "POST"])
@login_required
def edit(listing_id):
    listing = Listing.query.get_or_404(listing_id)

    if listing.provider_id != current_user.id and current_user.role != 'admin':
        flash("Access Denied", "error")
        return redirect(url_for("web.dashboard"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        price = request.form.get("price", "").strip()
        address = request.form.get("address", "").strip()

        error = _validate_listing_form(title, price, address)
        if error:
            flash(error, "error")
            return render_template("web/edit_listing.html", listing=listing)

        listing.title = title
        listing.category = request.form.get("category", listing.category)
        listing.price = price
        listing.price_numeric = _extract_price_numeric(price)
        listing.address = address

        if 'image' in request.files and request.files['image'].filename:
            image_url = _save_image(request.files['image'])
            if image_url:
                listing.image_url = image_url

        db.session.commit()
        flash("Listing updated!", "success")
        return redirect(url_for("web.dashboard"))

    return render_template("web/edit_listing.html", listing=listing)


@listings_bp.route("/<int:listing_id>/review", methods=["POST"])
@login_required
def submit_review(listing_id):
    if current_user.role != 'customer':
        flash("Only customers can leave reviews.", "error")
        return redirect(url_for("web.dashboard"))

    listing = Listing.query.get_or_404(listing_id)

    if listing.provider_id == current_user.id:
        flash("You cannot review your own listing.", "error")
        return redirect(url_for("web.dashboard"))

    existing = Review.query.filter_by(listing_id=listing_id, reviewer_id=current_user.id).first()
    if existing:
        flash("You have already reviewed this listing.", "warning")
        return redirect(url_for("web.dashboard"))

    try:
        rating = int(request.form.get("rating", 0))
        if not (1 <= rating <= 5):
            raise ValueError
    except (ValueError, TypeError):
        flash("Rating must be between 1 and 5.", "error")
        return redirect(url_for("web.dashboard"))

    comment = request.form.get("comment", "").strip()[:300]

    review = Review(
        listing_id=listing_id,
        reviewer_id=current_user.id,
        rating=rating,
        comment=comment,
    )
    db.session.add(review)

    # Recompute listing average rating
    db.session.flush()
    avg = db.session.query(db.func.avg(Review.rating)).filter_by(listing_id=listing_id).scalar()
    listing.rating = round(float(avg), 1) if avg else 0.0

    db.session.commit()
    flash("Review submitted!", "success")
    return redirect(url_for("web.dashboard"))
