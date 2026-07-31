import logging
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User, Tenant, Role

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        try:
            user = User.query.filter_by(username=username).first()
        except Exception as exc:
            logger.exception("login: DB error — %s", exc)
            flash("An error occurred. Please try again.", "danger")
            return render_template("auth/login.html"), 500

        if user is None or not user.check_password(password):
            flash("Invalid username or password.", "danger")
            return render_template("auth/login.html")
        login_user(user)
        next_page = request.args.get("next")
        return redirect(next_page or url_for("main.dashboard"))
    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("main.dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        tenant_slug = request.form.get("tenant_slug", "default").strip()

        if not username or not email or not password:
            flash("All fields are required.", "danger")
            return render_template("auth/register.html")

        try:
            tenant = Tenant.query.filter_by(slug=tenant_slug).first()
        except Exception as exc:
            logger.exception("register: DB error — %s", exc)
            flash("An error occurred.", "danger")
            return render_template("auth/register.html"), 500

        if tenant is None:
            flash("Organization not found. Contact your administrator.", "danger")
            return render_template("auth/register.html")

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already registered.", "danger")
            return render_template("auth/register.html")

        viewer_role = Role.query.filter_by(name="viewer", tenant_id=tenant.id).first()
        user = User(username=username, email=email, tenant_id=tenant.id, role_id=viewer_role.id)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html")


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))


def role_required(*roles):
    """Decorator to restrict route to certain roles."""
    def decorator(f):
        @wraps(f)
        @login_required
        def decorated(*args, **kwargs):
            if not current_user.has_role(*roles):
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for("main.dashboard"))
            return f(*args, **kwargs)
        return decorated
    return decorator
