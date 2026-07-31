import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf import CSRFProtect
from werkzeug.middleware.proxy_fix import ProxyFix

db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
csrf = CSRFProtect()

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")

    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///tax_monitor.db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", os.urandom(32).hex())

    cookie_slug = "tax_obligation_monitor"
    app.config["SESSION_COOKIE_NAME"]     = f"{cookie_slug}_session"
    app.config["SESSION_COOKIE_PATH"]     = os.environ.get("SESSION_COOKIE_PATH", "/")
    app.config["SESSION_COOKIE_SECURE"]   = os.environ.get("SESSION_COOKIE_SECURE", "false").lower() == "true"
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    logging.basicConfig(level=logging.INFO)

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"
    migrate.init_app(app, db)
    csrf.init_app(app)

    from app.models import User
    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.deadlines import deadlines_bp
    from app.routes.nexus import nexus_bp
    from app.routes.payments import payments_bp
    from app.routes.jurisdictions import jurisdictions_bp
    from app.routes.api import api_bp
    from app.routes.admin import admin_bp
    from app.routes.getting_started import gs_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(deadlines_bp)
    app.register_blueprint(nexus_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(jurisdictions_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(gs_bp)

    with app.app_context():
        db.create_all()
        _seed_defaults(app)

    return app


def _seed_defaults(app):
    """Create default admin tenant and user if DB is empty."""
    from app.models import Tenant, User, Role
    if Tenant.query.first():
        return

    tenant = Tenant(name="Default Organization", slug="default")
    db.session.add(tenant)
    db.session.flush()

    for role_name in ["admin", "manager", "analyst", "viewer"]:
        db.session.add(Role(name=role_name, tenant_id=tenant.id))
    db.session.flush()

    admin_role = Role.query.filter_by(name="admin", tenant_id=tenant.id).first()
    admin = User(username="admin", email="admin@example.com", tenant_id=tenant.id, role_id=admin_role.id)
    admin.set_password("admin")
    db.session.add(admin)
    db.session.commit()
    app.logger.info("Seeded default tenant + admin user (admin / admin)")
