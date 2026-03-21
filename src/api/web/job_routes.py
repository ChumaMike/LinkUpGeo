import logging
from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_required, current_user
from geopy.geocoders import Nominatim

from src.models.listing_model import db, JobRequest, Listing
from src.services.notification_service import notification_service

logger = logging.getLogger(__name__)
jobs_bp = Blueprint('jobs', __name__, url_prefix='/jobs')

VALID_CATEGORIES = {'service', 'house', 'job'}


@jobs_bp.route("/create", methods=["POST"])
@login_required
def create():
    category = request.form.get("category", "").strip().lower()
    description = request.form.get("description", "").strip()
    location_text = request.form.get("location", "").strip()

    # Input validation
    if category not in VALID_CATEGORIES:
        flash("Invalid category. Choose service, house, or job.", "error")
        return redirect(url_for("web.dashboard"))
    if len(description) < 10 or len(description) > 500:
        flash("Description must be between 10 and 500 characters.", "error")
        return redirect(url_for("web.dashboard"))
    if not location_text:
        flash("Location is required.", "error")
        return redirect(url_for("web.dashboard"))

    # Geocode once — stored permanently
    lat, lon = -26.2514, 27.8967
    try:
        geolocator = Nominatim(user_agent="linkup_geo_app")
        loc = geolocator.geocode(f"{location_text}, South Africa")
        if loc:
            lat = loc.latitude
            lon = loc.longitude
        else:
            # Deterministic jitter so the default pin doesn't move on reload
            seed = hash(location_text) % 1000
            lat += seed / 50000.0
            lon += seed / 50000.0
    except Exception as e:
        logger.warning("Geocoding failed for job location '%s': %s", location_text, e)

    new_job = JobRequest(
        customer_id=current_user.id,
        category=category,
        description=description,
        location=location_text,
        latitude=lat,
        longitude=lon,
    )
    db.session.add(new_job)
    db.session.commit()
    logger.info("Job request %d created by user %d", new_job.id, current_user.id)

    # Real Twilio broadcast to matching providers
    potential_matches = Listing.query.filter(
        Listing.category.ilike(f"%{category}%"),
        Listing.is_verified == True,
        Listing.deleted_at == None,
    ).all()
    provider_phones = {l.contact for l in potential_matches if l.contact}

    sent = notification_service.broadcast_job(new_job, provider_phones)

    if sent > 0:
        flash(f"Request posted! {sent} provider(s) notified via WhatsApp.", "success")
    elif provider_phones:
        flash(f"Request saved. Attempting to notify {len(provider_phones)} provider(s).", "warning")
    else:
        flash("Request saved. Waiting for providers in your area.", "warning")

    # Update notification count
    new_job.notifications_sent = sent
    db.session.commit()

    return redirect(url_for("web.dashboard"))
