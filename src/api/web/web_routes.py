import logging
from flask import Blueprint, render_template, redirect, url_for, request, jsonify
from flask_login import login_required, current_user
from src.models.listing_model import Listing, JobRequest, Lead
from src.services.listing_service import ListingService

logger = logging.getLogger(__name__)
web_bp = Blueprint('web', __name__)
listing_service = ListingService()


def _deterministic_jitter(item_id, default_lat, default_lon):
    """Stable offset based on item id — same value on every page load."""
    seed = hash(item_id) % 1000
    lat = default_lat + seed / 50000.0
    lon = default_lon + seed / 50000.0
    return lat, lon


def attach_coordinates(item_list, default_lat=-26.2514, default_lon=27.8967):
    data = []
    for item in item_list:
        if hasattr(item, 'to_dict'):
            item_dict = item.to_dict()
        else:
            item_dict = {
                'id': item.id,
                'category': item.category,
                'description': item.description,
                'location': item.location,
                'status': getattr(item, 'status', 'open'),
            }

        lat = getattr(item, 'latitude', None)
        lon = getattr(item, 'longitude', None)

        if not lat or not lon:
            lat, lon = _deterministic_jitter(item.id, default_lat, default_lon)

        item_dict['lat'] = lat
        item_dict['lon'] = lon
        data.append(item_dict)
    return data


@web_bp.route("/")
def home():
    return render_template("web/home.html")


@web_bp.route("/map")
def map_view():
    listings = Listing.query.filter_by(is_verified=True).filter(Listing.deleted_at == None).all()
    data = attach_coordinates(listings)
    return render_template("web/map_pro.html", listings=data)


@web_bp.route("/api/listings")
def api_listings():
    """JSON endpoint for dynamic map filter — no page reload needed."""
    category = request.args.get('category')
    max_price = request.args.get('max_price')
    verified_only = request.args.get('verified', 'true').lower() == 'true'
    radius_km = request.args.get('radius')
    center_lat = request.args.get('lat')
    center_lon = request.args.get('lon')

    results = listing_service.get_all_for_map(
        category=category,
        max_price=max_price,
        verified_only=verified_only,
        radius_km=radius_km,
        center_lat=center_lat,
        center_lon=center_lon,
    )

    # Attach stable coordinates for items without GPS
    for item in results:
        if not item.get('latitude') or not item.get('longitude'):
            lat, lon = _deterministic_jitter(item['id'], -26.2514, 27.8967)
            item['latitude'] = lat
            item['longitude'] = lon
        item['lat'] = item['latitude']
        item['lon'] = item['longitude']

    return jsonify(results)


@web_bp.route("/dashboard")
@login_required
def dashboard():
    if current_user.role == 'provider':
        raw_listings = Listing.query.filter_by(
            provider_id=current_user.id
        ).filter(Listing.deleted_at == None).all()
        listings_data = [item.to_dict() for item in raw_listings]

        open_jobs = JobRequest.query.filter_by(status='open').all()
        jobs_data = [{
            'category': job.category,
            'description': job.description,
            'lat': job.latitude,
            'lon': job.longitude,
        } for job in open_jobs]

        try:
            my_leads = Lead.query.filter_by(provider_id=current_user.id).all()
        except Exception:
            my_leads = []

        return render_template("web/dashboard.html",
                               user=current_user,
                               listings=listings_data,
                               job_opportunities=jobs_data,
                               leads=my_leads)

    elif current_user.role == 'customer':
        page = request.args.get('page', 1, type=int)
        all_raw = Listing.query.filter_by(is_verified=True).filter(Listing.deleted_at == None).all()
        all_listings_data = attach_coordinates(all_raw)

        my_jobs_raw = JobRequest.query.filter_by(
            customer_id=current_user.id
        ).order_by(JobRequest.created_at.desc()).paginate(page=page, per_page=10, error_out=False)

        my_jobs_data = attach_coordinates(my_jobs_raw.items)

        return render_template("web/customer_dashboard.html",
                               user=current_user,
                               listings=all_listings_data,
                               jobs=my_jobs_data,
                               pagination=my_jobs_raw)

    elif current_user.role == 'admin':
        return redirect(url_for('admin.admin_panel'))

    return redirect(url_for('web.home'))
