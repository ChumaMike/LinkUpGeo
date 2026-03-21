import logging
from flask import Blueprint, render_template, abort
from src.models.user_model import User
from src.models.listing_model import Listing, Review, db

logger = logging.getLogger(__name__)
profile_bp = Blueprint('profile', __name__, url_prefix='/provider')


@profile_bp.route("/<int:user_id>")
def view_profile(user_id):
    user = User.query.get_or_404(user_id)

    if user.role != 'provider' or user.is_deleted:
        abort(404)

    listings = Listing.query.filter_by(
        provider_id=user_id, is_verified=True
    ).filter(Listing.deleted_at == None).all()

    # Aggregate stats
    review_count = db.session.query(db.func.count(Review.id)).join(
        Listing, Review.listing_id == Listing.id
    ).filter(Listing.provider_id == user_id).scalar() or 0

    avg_rating = db.session.query(db.func.avg(Review.rating)).join(
        Listing, Review.listing_id == Listing.id
    ).filter(Listing.provider_id == user_id).scalar()
    avg_rating = round(float(avg_rating), 1) if avg_rating else 0.0

    # Fetch recent reviews with listing title
    recent_reviews = db.session.query(Review, Listing.title).join(
        Listing, Review.listing_id == Listing.id
    ).filter(Listing.provider_id == user_id).order_by(Review.created_at.desc()).limit(10).all()

    return render_template(
        "web/profile.html",
        provider=user,
        listings=listings,
        review_count=review_count,
        avg_rating=avg_rating,
        recent_reviews=recent_reviews,
    )
