import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import User, Tenant, Role
from app.routes.auth import role_required

logger = logging.getLogger(__name__)
admin_bp = Blueprint("admin", __name__)


@admin_bp.route("/")
@role_required("admin")
def admin_home():
    try:
        users = User.query.filter_by(tenant_id=current_user.tenant_id).all()
        roles = Role.query.filter_by(tenant_id=current_user.tenant_id).all()
        tenants = Tenant.query.all() if current_user.tenant.slug == "default" else [current_user.tenant]
    except Exception as exc:
        logger.exception("admin_home: error — %s", exc)
        return render_template("errors/500.html"), 500
    return render_template("admin/home.html", users=users, roles=roles, tenants=tenants)


@admin_bp.route("/users/<int:uid>/role", methods=["POST"])
@role_required("admin")
def change_role(uid):
    try:
        user = User.query.filter_by(id=uid, tenant_id=current_user.tenant_id).first()
    except Exception as exc:
        logger.exception("change_role: error — %s", exc)
        flash("Error.", "danger")
        return redirect(url_for("admin.admin_home"))

    if user is None:
        flash("User not found.", "warning")
        return redirect(url_for("admin.admin_home"))

    new_role_id = request.form.get("role_id")
    if new_role_id:
        try:
            role = Role.query.filter_by(id=int(new_role_id), tenant_id=current_user.tenant_id).first()
            if role:
                user.role_id = role.id
                db.session.commit()
                flash(f"Role updated for {user.username}.", "success")
            else:
                flash("Invalid role.", "danger")
        except Exception as exc:
            logger.exception("change_role: error — %s", exc)
            flash("Error updating role.", "danger")

    return redirect(url_for("admin.admin_home"))


@admin_bp.route("/tenants/new", methods=["POST"])
@role_required("admin")
def new_tenant():
    name = request.form.get("name", "").strip()
    slug = request.form.get("slug", "").strip().lower().replace(" ", "-")
    if not name or not slug:
        flash("Name and slug are required.", "danger")
        return redirect(url_for("admin.admin_home"))
    try:
        if Tenant.query.filter_by(slug=slug).first():
            flash("Slug already in use.", "danger")
            return redirect(url_for("admin.admin_home"))
        t = Tenant(name=name, slug=slug)
        db.session.add(t)
        db.session.flush()
        for rn in ["admin", "manager", "analyst", "viewer"]:
            db.session.add(Role(name=rn, tenant_id=t.id))
        db.session.commit()
        flash(f"Tenant '{name}' created.", "success")
    except Exception as exc:
        logger.exception("new_tenant: error — %s", exc)
        flash("Error creating tenant.", "danger")
    return redirect(url_for("admin.admin_home"))
