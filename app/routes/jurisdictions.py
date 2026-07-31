import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Jurisdiction

logger = logging.getLogger(__name__)
jurisdictions_bp = Blueprint("jurisdictions", __name__)


@jurisdictions_bp.route("/jurisdictions")
@login_required
def list_jurisdictions():
    tid = current_user.tenant_id
    try:
        jurisdictions = Jurisdiction.query.filter_by(tenant_id=tid).order_by(Jurisdiction.name).all()
    except Exception as exc:
        logger.exception("list_jurisdictions: error — %s", exc)
        return render_template("errors/500.html"), 500
    return render_template("jurisdictions/list.html", jurisdictions=jurisdictions)


@jurisdictions_bp.route("/jurisdictions/new", methods=["GET", "POST"])
@login_required
def new_jurisdiction():
    if not current_user.can_edit():
        flash("Permission denied.", "danger")
        return redirect(url_for("jurisdictions.list_jurisdictions"))

    if request.method == "POST":
        try:
            j = Jurisdiction(
                tenant_id=current_user.tenant_id,
                name=request.form["name"].strip(),
                code=request.form["code"].strip().upper(),
                jurisdiction_type=request.form.get("jurisdiction_type", "state").strip(),
                country=request.form.get("country", "United States").strip(),
                tax_types=request.form.get("tax_types", "").strip(),
                notes=request.form.get("notes", "").strip(),
            )
            db.session.add(j)
            db.session.commit()
            flash("Jurisdiction created.", "success")
            return redirect(url_for("jurisdictions.list_jurisdictions"))
        except Exception as exc:
            logger.exception("new_jurisdiction: error — %s", exc)
            flash(f"Error: {exc}", "danger")

    return render_template("jurisdictions/form.html", jurisdiction=None)


@jurisdictions_bp.route("/jurisdictions/<int:jid>/edit", methods=["GET", "POST"])
@login_required
def edit_jurisdiction(jid):
    if not current_user.can_edit():
        flash("Permission denied.", "danger")
        return redirect(url_for("jurisdictions.list_jurisdictions"))
    tid = current_user.tenant_id
    try:
        j = Jurisdiction.query.filter_by(id=jid, tenant_id=tid).first()
    except Exception as exc:
        logger.exception("edit_jurisdiction: error — %s", exc)
        return render_template("errors/500.html"), 500

    if j is None:
        flash("Jurisdiction not found.", "warning")
        return redirect(url_for("jurisdictions.list_jurisdictions"))

    if request.method == "POST":
        try:
            j.name = request.form["name"].strip()
            j.code = request.form["code"].strip().upper()
            j.jurisdiction_type = request.form.get("jurisdiction_type", "state").strip()
            j.country = request.form.get("country", "United States").strip()
            j.tax_types = request.form.get("tax_types", "").strip()
            j.notes = request.form.get("notes", "").strip()
            db.session.commit()
            flash("Jurisdiction updated.", "success")
            return redirect(url_for("jurisdictions.list_jurisdictions"))
        except Exception as exc:
            logger.exception("edit_jurisdiction: error — %s", exc)
            flash(f"Error: {exc}", "danger")

    return render_template("jurisdictions/form.html", jurisdiction=j)


@jurisdictions_bp.route("/jurisdictions/<int:jid>/delete", methods=["POST"])
@login_required
def delete_jurisdiction(jid):
    if not current_user.can_edit():
        flash("Permission denied.", "danger")
        return redirect(url_for("jurisdictions.list_jurisdictions"))
    try:
        j = Jurisdiction.query.filter_by(id=jid, tenant_id=current_user.tenant_id).first()
        if j:
            db.session.delete(j)
            db.session.commit()
            flash("Jurisdiction deleted.", "success")
        else:
            flash("Not found.", "warning")
    except Exception as exc:
        logger.exception("delete_jurisdiction: error — %s", exc)
        flash("Error.", "danger")
    return redirect(url_for("jurisdictions.list_jurisdictions"))
