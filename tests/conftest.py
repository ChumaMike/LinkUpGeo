import os
import pytest

os.environ.setdefault('SECRET_KEY', 'test-secret-key-for-ci')
os.environ.setdefault('FLASK_ENV', 'testing')


@pytest.fixture(scope='session')
def app():
    from src import create_app
    application = create_app('testing')
    with application.app_context():
        from src.models.listing_model import db
        db.create_all()
        yield application
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db_session(app):
    from src.models.listing_model import db
    with app.app_context():
        yield db
        db.session.rollback()


@pytest.fixture
def new_user(app):
    """Create a test customer user."""
    from src.models.listing_model import db
    from src.models.user_model import User
    with app.app_context():
        user = User(phone_number='27821000001', name='Test User', role='customer')
        user.set_password('Password1')
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def provider_user(app):
    """Create a test provider user."""
    from src.models.listing_model import db
    from src.models.user_model import User
    with app.app_context():
        user = User(phone_number='27821000002', name='Test Provider', role='provider')
        user.set_password('Password1')
        db.session.add(user)
        db.session.commit()
        yield user
        db.session.delete(user)
        db.session.commit()


@pytest.fixture
def auth_client(client, new_user):
    """Logged-in customer client."""
    client.post('/login', data={
        'phone': new_user.phone_number,
        'password': 'Password1',
    }, follow_redirects=True)
    return client


@pytest.fixture
def provider_client(client, provider_user):
    """Logged-in provider client."""
    client.post('/login', data={
        'phone': provider_user.phone_number,
        'password': 'Password1',
    }, follow_redirects=True)
    return client
