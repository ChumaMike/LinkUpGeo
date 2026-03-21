import json
import logging
from flask import Blueprint, request
from twilio.twiml.messaging_response import MessagingResponse

from src.services.ai_service import ai_brain
from src.services.listing_service import ListingService
from src.models.listing_model import db, BotSession
from src import limiter

logger = logging.getLogger(__name__)
bot_bp = Blueprint('bot', __name__)
listing_service = ListingService()

MAX_HISTORY = 10


def _get_session(sender_id):
    """Load chat history from DB, return as list."""
    session = BotSession.query.filter_by(sender_id=sender_id).first()
    if not session:
        return []
    try:
        return json.loads(session.history_json)
    except (json.JSONDecodeError, TypeError):
        return []


def _save_session(sender_id, history):
    """Persist chat history to DB, capped at MAX_HISTORY messages."""
    history = history[-MAX_HISTORY:]
    session = BotSession.query.filter_by(sender_id=sender_id).first()
    if session:
        session.history_json = json.dumps(history)
    else:
        session = BotSession(sender_id=sender_id, history_json=json.dumps(history))
        db.session.add(session)
    db.session.commit()


@bot_bp.route("/whatsapp", methods=['POST'])
@limiter.limit("30 per minute")
def whatsapp_reply():
    sender_id = request.values.get('From', '')
    incoming_msg = request.values.get('Body', '').strip()

    logger.info("WhatsApp message from %s: %s", sender_id, incoming_msg[:80])

    # Load persistent session
    history = _get_session(sender_id)
    history.append({"role": "user", "text": incoming_msg})

    reply = ""

    # ── Location pin shared by user ────────────────────────────────────────────
    user_lat = request.values.get('Latitude')
    user_lon = request.values.get('Longitude')

    if user_lat and user_lon:
        try:
            lat = float(user_lat)
            lon = float(user_lon)
            results = listing_service.get_listings_near_me(
                category='service', user_lat=lat, user_lon=lon, radius_km=10
            )
            if results:
                reply = "📍 *Services near you:*\n\n"
                for i, item in enumerate(results[:5], 1):
                    dist = item.get('distance', '?')
                    reply += (
                        f"*{i}. {item['title']}* ✅\n"
                        f"   💰 {item['price']}\n"
                        f"   📍 {item['address']} ({dist}km away)\n"
                        f"   📞 {item['contact']}\n\n"
                    )
                reply += "Reply with a service name to search further."
            else:
                reply = "😕 No services found within 10km of your location. Try expanding your search."
        except (ValueError, TypeError) as e:
            logger.warning("Invalid coordinates from %s: %s", sender_id, e)
            reply = "Could not process your location. Please try again."

    else:
        # ── AI intent parsing ──────────────────────────────────────────────────
        analysis = ai_brain.parse_intent(incoming_msg, history=history)
        intent = analysis.get('intent')

        if intent == "greeting":
            reply = (
                "👋 *Welcome to LinkUp!*\n\n"
                "I connect you with the best services in the Kasi. "
                "I can help you find a *Plumber*, *Electrician*, *Room to Rent*, or even a *Job*.\n\n"
                "📍 *Tip:* Share your location pin for instant nearby results!\n\n"
                "How can I help you today?"
            )

        elif intent == "search_listings":
            category = analysis.get("category", "service")
            location = analysis.get("location", "Soweto")
            keywords = analysis.get("keywords", "")
            results = listing_service.get_listings_simple(location, category, keyword=keywords, limit=5)
            reply = listing_service.format_listings_response(results, f"{keywords or category} in {location}")

        elif intent == "clear_memory":
            history = []
            _save_session(sender_id, history)
            reply = "🧹 Memory cleared! We can start fresh."

        else:
            reply = analysis.get(
                "chat_response",
                "I'm not sure how to help with that. Try asking for a service like 'Plumber near Soweto'."
            )

    # Save bot reply to history and persist
    history.append({"role": "model", "text": reply})
    _save_session(sender_id, history)

    resp = MessagingResponse()
    resp.message(reply)
    return str(resp)
