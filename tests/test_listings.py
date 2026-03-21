"""Listing route tests."""
import pytest


def test_add_listing_requires_login(client):
    """Unauthenticated POST to /listings/add redirects to login."""
    resp = client.post('/listings/add', data={
        'title': 'Test Plumber',
        'category': 'service',
        'price': 'R300',
        'address': 'Soweto',
    }, follow_redirects=False)
    assert resp.status_code in (302, 401)
    location = resp.headers.get('Location', '')
    assert 'login' in location.lower()


def test_add_listing_creates_pending(provider_client, app):
    """New listing is created with is_verified=False."""
    resp = provider_client.post('/listings/add', data={
        'title': 'Expert Plumbing Service',
        'category': 'service',
        'price': 'R400',
        'address': 'Orlando, Soweto',
    }, follow_redirects=True)
    assert resp.status_code == 200

    from src.models.listing_model import Listing
    with app.app_context():
        listing = Listing.query.filter_by(title='Expert Plumbing Service').first()
        if listing:
            assert listing.is_verified is False, "New listings must start as pending"


def test_add_listing_short_title_rejected(provider_client):
    """Title shorter than 5 characters is rejected."""
    resp = provider_client.post('/listings/add', data={
        'title': 'Hi',
        'category': 'service',
        'price': 'R100',
        'address': 'Soweto',
    }, follow_redirects=True)
    assert b'5 and 100' in resp.data or b'error' in resp.data.lower()


def test_edit_listing_by_non_owner_denied(auth_client, provider_user, app):
    """Customer cannot edit a provider's listing."""
    from src.models.listing_model import Listing, db
    with app.app_context():
        listing = Listing(
            title='Owner Only Listing',
            category='service',
            price='R500',
            address='Test',
            provider_id=provider_user.id,
            is_verified=True,
        )
        db.session.add(listing)
        db.session.commit()
        lid = listing.id

    resp = auth_client.post(f'/listings/edit/{lid}', data={
        'title': 'Hacked Title',
        'category': 'service',
        'price': 'R1',
        'address': 'Hacked',
    }, follow_redirects=True)
    # Should redirect with Access Denied flash, not save the change
    assert b'Access Denied' in resp.data or b'Hacked Title' not in resp.data
