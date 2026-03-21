import logging
import os
from flask import Flask, render_template
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from src.models.listing_model import db
from src.models.user_model import User
from config import config_map

csrf = CSRFProtect()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address)


def create_app(config_name=None):
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'default')

    app = Flask(__name__)
    app.config.from_object(config_map[config_name])

    # ── Logging ────────────────────────────────────────────────────────────────
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s %(name)s %(message)s'
    )

    # ── Extensions ─────────────────────────────────────────────────────────────
    db.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)

    # Exempt Twilio webhook from CSRF (it posts with its own auth headers)
    from src.api.bot_routes import bot_bp
    csrf.exempt(bot_bp)

    # ── Login Manager ──────────────────────────────────────────────────────────
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # ── Upload folder ──────────────────────────────────────────────────────────
    upload_folder = app.config.get('UPLOAD_FOLDER', 'src/static/uploads')
    os.makedirs(upload_folder, exist_ok=True)

    # ── Blueprints ─────────────────────────────────────────────────────────────
    from src.api.auth_routes import auth_bp
    from src.api.admin_routes import admin_bp
    from src.api.web import web_bp, listings_bp, jobs_bp
    from src.api.web.profile_routes import profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(bot_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(web_bp)
    app.register_blueprint(listings_bp)
    app.register_blueprint(jobs_bp)
    app.register_blueprint(profile_bp)

    # ── Error Handlers ─────────────────────────────────────────────────────────
    @app.errorhandler(404)
    def not_found(e):
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden(e):
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def server_error(e):
        return render_template('errors/500.html'), 500

    return app
