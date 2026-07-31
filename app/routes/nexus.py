import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import NexusExposure, Jurisdiction, RiskLevel

logger = logging.getLogger(__name__)
nexus_bp = Blueprint("nexus", __name__)


@nexus_bp.route("/nexus")
@login_required
def list_nexus():
    tid = current_user.tenant_id
    try:
        records = NexusExposure.query.filter_by(tenant_id=tid).order_by(NexusExposure.updated_at.desc()).all()
        jurisdictions = Jurisdiction.query.filter_by(tenant_id=tid).all()
    except Exception as exc:
        logger.exception("list_nexus: error — %s", exc)
        return render_template("errors/500.html"), 500
    return render_template("nexus/list.html", records=records, jurisdictions=jurisdictions, risks=RiskLevel)


@nexus_bp.route("/nexus/new", methods=["GET", "POST"])
@login_required
def new_nexus():
    if not current_user.can_edit():
        flash("Permission denied.", "danger")
        return redirect(url_for("nexus.list_nexus"))
    tid = current_user.tenant_id
    try:
        jurisdictions = Jurisdiction.query.filter_by(tenant_id=tid).all()
    except Exception as exc:
        logger.exception("new_nexus: error — %s", exc)
        return render_template("errors/500.html"), 500

    if request.method == "POST":
        try:
            n = NexusExposure(
                tenant_id=tid,
                jurisdiction_id=int(request.form["jurisdiction_id"]),
                entity_name=request.form["entity_name"].strip(),
                nexus_type=request.form["nexus_type"].strip(),
                has_nexus="has_nexus" in request.form,
                revenue_in_jurisdiction=float(request.form.get("revenue_in_jurisdiction", 0) or 0),
                employee_count=int(request.form.get("employee_count", 0) or 0),
                property_value=float(request.form.get("property_value", 0) or 0),
                threshold_met="threshold_met" in request.form,
                risk_level=RiskLevel(request.form.get("risk_level", "low")),
                notes=request.form.get("notes", "").strip(),
            )
            lr = request.form.get("last_reviewed", "").strip()
            if lr:
                n.last_reviewed = datetime.strptime(lr, "%Y-%m-%d").date()
            db.session.add(n)
            db.session.commit()
            flash("Nexus exposure record created.", "success")
            return redirect(url_for("nexus.list_nexus"))
        except Exception as exc:
            logger.exception("new_nexus: error — %s", exc)
            flash(f"Error: {exc}", "danger")

    return render_template("nexus/form.html", record=None, jurisdictions=jurisdictions, risks=RiskLevel)


@nexus_bp.route("/nexus/<int:nid>/edit", methods=["GET", "POST"])
@login_required
def edit_nexus(nid):
    if not current_user.can_edit():
        flash("Permission denied.", "danger")
        return redirect(url_for("nexus.list_nexus"))
    tid = current_user.tenant_id
    try:
        record = NexusExposure.query.filter_by(id=nid, tenant_id=tid).first()
        jurisdictions = Jurisdiction.query.filter_by(tenant_id=tid).all()
    except Exception as exc:
        logger.exception("edit_nexus: error — %s", exc)
        return render_template("errors/500.html"), 500

    if record is None:
        flash("Record not found.", "warning")
        return redirect(url_for("nexus.list_nexus"))

    if request.method == "POST":
        try:
            record.jurisdiction_id = int(request.form["jurisdiction_id"])
            record.entity_name = request.form["entity_name"].strip()
            record.nexus_type = request.form["nexus_type"].strip()
            record.has_nexus = "has_nexus" in request.form
            record.revenue_in_jurisdiction = float(request.form.get("revenue_in_jurisdiction", 0) or 0)
            record.employee_count = int(request.form.get("employee_count", 0) or 0)
            record.property_value = float(request.form.get("property_value", 0) or 0)
            record.threshold_met = "threshold_met" in request.form
            record.risk_level = RiskLevel(request.form.get("risk_level", "low"))
            record.notes = request.form.get("notes", "").strip()
            lr = request.form.get("last_reviewed", "").strip()
            record.last_reviewed = datetime.strptime(lr, "%Y-%m-%d").date() if lr else None
            db.session.commit()
            flash("Nexus exposure updated.", "success")
            return redirect(url_for("nexus.list_nexus"))
        except Exception as exc:
            logger.exception("edit_nexus: error — %s", exc)
            flash(f"Error: {exc}", "danger")

    return render_template("nexus/form.html", record=record, jurisdictions=jurisdictions, risks=RiskLevel)


@nexus_bp.route("/nexus/<int:nid>/delete", methods=["POST"])
@login_required
def delete_nexus(nid):
    if not current_user.can_edit():
        flash("Permission denied.", "danger")
        return redirect(url_for("nexus.list_nexus"))
    try:
        r = NexusExposure.query.filter_by(id=nid, tenant_id=current_user.tenant_id).first()
        if r:
            db.session.delete(r)
            db.session.commit()
            flash("Record deleted.", "success")
        else:
            flash("Not found.", "warning")
    except Exception as exc:
        logger.exception("delete_nexus: error — %s", exc)
        flash("Error deleting record.", "danger")
    return redirect(url_for("nexus.list_nexus"))
