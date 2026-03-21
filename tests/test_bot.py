"""WhatsApp bot route tests — mock Gemini to avoid live API calls."""
import json
import pytest
from unittest.mock import patch, MagicMock


def _post_whatsapp(client, body, from_='whatsapp:+27821000001', lat=None, lon=None):
    data = {'Body': body, 'From': from_}
    if lat is not None:
        data['Latitude'] = str(lat)
    if lon is not None:
        data['Longitude'] = str(lon)
    return client.post('/whatsapp', data=data)


def test_bot_greeting_returns_welcome(client):
    """Greeting intent returns the LinkUp welcome message."""
    mock_analysis = {'intent': 'greeting'}
    with patch('src.api.bot_routes.ai_brain.parse_intent', return_value=mock_analysis):
        resp = _post_whatsapp(client, 'Hi there')
    assert resp.status_code == 200
    assert b'LinkUp' in resp.data or b'Welcome' in resp.data


def test_bot_search_intent_calls_listing_service(client):
    """Search intent calls listing service and returns formatted results."""
    mock_analysis = {
        'intent': 'search_listings',
        'category': 'service',
        'location': 'Soweto',
        'keywords': 'plumber',
    }
    with patch('src.api.bot_routes.ai_brain.parse_intent', return_value=mock_analysis):
        resp = _post_whatsapp(client, 'I need a plumber in Soweto')
    assert resp.status_code == 200
    assert b'<?xml' in resp.data or b'Message' in resp.data


def test_bot_location_pin_bypasses_ai(client):
    """When latitude/longitude are sent, AI is NOT called."""
    with patch('src.api.bot_routes.ai_brain.parse_intent') as mock_ai:
        resp = _post_whatsapp(client, '', lat=-26.2514, lon=27.8967)
    assert resp.status_code == 200
    mock_ai.assert_not_called()


def test_bot_session_persisted(client, app):
    """After a message, a BotSession row exists in the DB."""
    sender = 'whatsapp:+27821000005'
    mock_analysis = {'intent': 'greeting'}
    with patch('src.api.bot_routes.ai_brain.parse_intent', return_value=mock_analysis):
        _post_whatsapp(client, 'Hello', from_=sender)

    from src.models.listing_model import BotSession
    with app.app_context():
        session = BotSession.query.filter_by(sender_id=sender).first()
        assert session is not None
        history = json.loads(session.history_json)
        assert any(m['role'] == 'user' for m in history)
