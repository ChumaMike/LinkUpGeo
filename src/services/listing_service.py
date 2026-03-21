import logging
import math
from src.models.listing_model import Listing
from src.utils.geo_utils import calculate_distance

logger = logging.getLogger(__name__)

# Bounding box padding in degrees (~50km at SA latitude)
GEO_PAD = 0.5


class ListingService:

    def get_listings_near_me(self, category, user_lat, user_lon, radius_km=50):
        """
        Finds verified listings within radius_km of the user's GPS coordinates.
        Uses a SQL bounding-box pre-filter to avoid loading the entire table into RAM.
        """
        lat_min = user_lat - GEO_PAD
        lat_max = user_lat + GEO_PAD
        lon_min = user_lon - GEO_PAD
        lon_max = user_lon + GEO_PAD

        query = Listing.query.filter(
            Listing.is_verified == True,
            Listing.deleted_at == None,
            Listing.latitude.between(lat_min, lat_max),
            Listing.longitude.between(lon_min, lon_max),
        )

        if category and category != 'service':
            query = query.filter(Listing.category == category)

        candidates = query.all()
        nearby = []

        for item in candidates:
            dist = calculate_distance(user_lat, user_lon, item.latitude, item.longitude)
            if dist <= radius_km:
                item_data = item.to_dict()
                item_data['distance'] = round(dist, 1)
                nearby.append(item_data)

        nearby.sort(key=lambda x: x['distance'])
        return nearby

    def get_listings(self, location, category, keyword=None, page=1, per_page=10):
        """
        Keyword + location search. Returns paginated results.
        For WhatsApp, use per_page=5.
        """
        try:
            from sqlalchemy import or_
            query = Listing.query.filter(
                Listing.is_verified == True,
                Listing.deleted_at == None,
            )

            if category and category != 'service':
                query = query.filter(Listing.category == category)

            if location and isinstance(location, str) and location.lower() != 'near me':
                query = query.filter(Listing.address.ilike(f"%{location}%"))

            if keyword:
                search_terms = [k.strip() for k in keyword.split(',') if k.strip()]
                conditions = []
                for term in search_terms:
                    pattern = f"%{term}%"
                    conditions.append(Listing.title.ilike(pattern))
                    conditions.append(Listing.keywords.ilike(pattern))
                if conditions:
                    query = query.filter(or_(*conditions))

            pagination = query.paginate(page=page, per_page=per_page, error_out=False)
            return pagination

        except Exception as e:
            logger.error("Search error: %s", e)
            return None

    def get_listings_simple(self, location, category, keyword=None, limit=5):
        """Flat list version for WhatsApp bot — no pagination object."""
        pagination = self.get_listings(location, category, keyword=keyword, per_page=limit)
        if pagination is None:
            return []
        return [item.to_dict() for item in pagination.items]

    def get_all_for_map(self, category=None, max_price=None, verified_only=True, radius_km=None,
                        center_lat=None, center_lon=None):
        """Filtered listing fetch for the map view JSON endpoint."""
        query = Listing.query.filter(Listing.deleted_at == None)

        if verified_only:
            query = query.filter(Listing.is_verified == True)
        if category and category != 'all':
            query = query.filter(Listing.category == category)
        if max_price:
            try:
                query = query.filter(Listing.price_numeric <= int(max_price))
            except (ValueError, TypeError):
                pass

        listings = query.all()

        if radius_km and center_lat and center_lon:
            try:
                r = float(radius_km)
                listings = [
                    l for l in listings
                    if l.latitude and l.longitude and
                    calculate_distance(float(center_lat), float(center_lon), l.latitude, l.longitude) <= r
                ]
            except (ValueError, TypeError):
                pass

        return [l.to_dict() for l in listings]

    def format_listings_response(self, listings, context):
        """Format listing list for WhatsApp response."""
        if not listings:
            return (
                f"😕 I couldn't find any *{context}*.\n\n"
                "Try searching for something else, or reply *'Menu'* to see options."
            )

        message = f"🔍 *Here is what I found for {context}:*\n\n"

        for i, item in enumerate(listings, 1):
            verified = "✅" if item['is_verified'] else ""
            dist = f" ({item['distance']}km)" if 'distance' in item else ""
            message += (
                f"*{i}. {item['title']}* {verified}\n"
                f"   💰 {item['price']}\n"
                f"   📍 {item['address']}{dist}\n"
                f"   📞 {item['contact']}\n\n"
            )

        message += (
            "💡 *Tip:* Share your 📍 location pin for nearest results.\n"
            "Reply *'New Search'* to look for something else."
        )
        return message
