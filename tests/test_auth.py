"""Auth route tests — signup, login, validation."""
import pytest


def test_signup_valid_phone(client):
    """Valid SA phone number creates an account."""
    resp = client.post('/signup', data={
        'phone': '27831000099',
        'name': 'Thabo Nkosi',
        'password': 'Password1',
        'role': 'customer',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Account created' in resp.data or b'log in' in resp.data.lower()


def test_signup_invalid_phone(client):
    """Non-SA phone number is rejected."""
    resp = client.post('/signup', data={
        'phone': '1234567890',
        'name': 'John',
        'password': 'Password1',
        'role': 'customer',
    }, follow_redirects=True)
    assert b'valid South African' in resp.data or b'error' in resp.data.lower()


def test_signup_short_password(client):
    """Password shorter than 8 chars is rejected."""
    resp = client.post('/signup', data={
        'phone': '27831000098',
        'name': 'Sipho',
        'password': 'abc12',
        'role': 'customer',
    }, follow_redirects=True)
    assert b'8 characters' in resp.data or b'error' in resp.data.lower()


def test_signup_duplicate_phone(client, new_user):
    """Duplicate phone number is rejected."""
    resp = client.post('/signup', data={
        'phone': new_user.phone_number,
        'name': 'Another Person',
        'password': 'Password1',
        'role': 'customer',
    }, follow_redirects=True)
    assert b'already registered' in resp.data


def test_login_correct_credentials(client, new_user):
    """Correct credentials redirect to dashboard."""
    resp = client.post('/login', data={
        'phone': new_user.phone_number,
        'password': 'Password1',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Dashboard' in resp.data or b'dashboard' in resp.data.lower()


def test_login_wrong_password(client, new_user):
    """Wrong password stays on login page."""
    resp = client.post('/login', data={
        'phone': new_user.phone_number,
        'password': 'WrongPass9',
    }, follow_redirects=True)
    assert b'Invalid' in resp.data or b'error' in resp.data.lower()


def test_login_normalises_phone_format(client, new_user):
    """0xx format is accepted and matched to 27xx stored number."""
    local_format = '0' + new_user.phone_number[2:]  # 27821000001 → 0821000001
    resp = client.post('/login', data={
        'phone': local_format,
        'password': 'Password1',
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b'Invalid' not in resp.data
