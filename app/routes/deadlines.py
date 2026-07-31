import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import Deadline, Jurisdiction, FilingStatus, RiskLevel

logger = logging.getLogger(__name__)
deadlines_bp = Blueprint("deadlines", __name__)


@deadlines_bp.route("/deadlines")
@login_required
def list_deadlines():
    tid = current_user.tenant_id
    status_filter = request.args.get("status", "")
    risk_filter = request.args.get("risk", "")
    try:
        q = Deadline.query.filter_by(tenant_id=tid)
        if status_filter:
            q = q.filter(Deadline.status == FilingStatus(status_filter))
        if risk_filter:
            q = q.filter(Deadline.risk_level == RiskLevel(risk_filter))
        deadlines = q.order_by(Deadline.due_date).all()
        jurisdictions = Jurisdiction.query.filter_by(tenant_id=tid).all()
    except Exception as exc:
        logger.exception("list_deadlines: error — %s", exc)
        return render_template("errors/500.html"), 500

    return render_template("deadlines/list.html",
        deadlines=deadlines, jurisdictions=jurisdictions,
        statuses=FilingStatus, risks=RiskLevel,
        status_filter=status_filter, risk_filter=risk_filter)


@deadlines_bp.route("/deadlines/new", methods=["GET", "POST"])
@login_required
def new_deadline():
    if not current_user.can_edit():
        flash("You do not have permission to create deadlines.", "danger")
        return redirect(url_for("deadlines.list_deadlines"))
    tid = current_user.tenant_id
    try:
        jurisdictions = Jurisdiction.query.filter_by(tenant_id=tid).all()
    except Exception as exc:
        logger.exception("new_deadline: error loading jurisdictions — %s", exc)
        return render_template("errors/500.html"), 500

    if request.method == "POST":
        try:
            d = Deadline(
                tenant_id=tid,
                jurisdiction_id=int(request.form["jurisdiction_id"]),
                title=request.form["title"].strip(),
                tax_type=request.form["tax_type"].strip(),
                due_date=datetime.strptime(request.form["due_date"], "%Y-%m-%d").date(),
                status=FilingStatus(request.form.get("status", "pending")),
                risk_level=RiskLevel(request.form.get("risk_level", "medium")),
                assigned_to=request.form.get("assigned_to", "").strip(),
                notes=request.form.get("notes", "").strip(),
            )
            ext = request.form.get("extension_date", "").strip()
            if ext:
                d.extension_date = datetime.strptime(ext, "%Y-%m-%d").date()
            db.session.add(d)
            db.session.commit()
            flash("Deadline created.", "success")
            return redirect(url_for("deadlines.list_deadlines"))
        except Exception as exc:
            logger.exception("new_deadline: creation error — %s", exc)
            flash(f"Error creating deadline: {exc}", "danger")

    return render_template("deadlines/form.html", deadline=None,
        jurisdictions=jurisdictions, statuses=FilingStatus, risks=RiskLevel)


@deadlines_bp.route("/deadlines/<int:did>/edit", methods=["GET", "POST"])
@login_required
def edit_deadline(did):
    if not current_user.can_edit():
        flash("You do not have permission.", "danger")
        return redirect(url_for("deadlines.list_deadlines"))
    tid = current_user.tenant_id
    try:
        deadline = Deadline.query.filter_by(id=did, tenant_id=tid).first()
        jurisdictions = Jurisdiction.query.filter_by(tenant_id=tid).all()
    except Exception as exc:
        logger.exception("edit_deadline: error — %s", exc)
        return render_template("errors/500.html"), 500

    if deadline is None:
        flash("Deadline not found.", "warning")
        return redirect(url_for("deadlines.list_deadlines"))

    if request.method == "POST":
        try:
            deadline.jurisdiction_id = int(request.form["jurisdiction_id"])
            deadline.title = request.form["title"].strip()
            deadline.tax_type = request.form["tax_type"].strip()
            deadline.due_date = datetime.strptime(request.form["due_date"], "%Y-%m-%d").date()
            deadline.status = FilingStatus(request.form.get("status", "pending"))
            deadline.risk_level = RiskLevel(request.form.get("risk_level", "medium"))
            deadline.assigned_to = request.form.get("assigned_to", "").strip()
            deadline.notes = request.form.get("notes", "").strip()
            ext = request.form.get("extension_date", "").strip()
            deadline.extension_date = datetime.strptime(ext, "%Y-%m-%d").date() if ext else None
            filed = request.form.get("filed_date", "").strip()
            deadline.filed_date = datetime.strptime(filed, "%Y-%m-%d").date() if filed else None
            db.session.commit()
            flash("Deadline updated.", "success")
            return redirect(url_for("deadlines.list_deadlines"))
        except Exception as exc:
            logger.exception("edit_deadline: update error — %s", exc)
            flash(f"Error: {exc}", "danger")

    return render_template("deadlines/form.html", deadline=deadline,
        jurisdictions=jurisdictions, statuses=FilingStatus, risks=RiskLevel)


@deadlines_bp.route("/deadlines/<int:did>/delete", methods=["POST"])
@login_required
def delete_deadline(did):
    if not current_user.can_edit():
        flash("Permission denied.", "danger")
        return redirect(url_for("deadlines.list_deadlines"))
    try:
        d = Deadline.query.filter_by(id=did, tenant_id=current_user.tenant_id).first()
        if d:
            db.session.delete(d)
            db.session.commit()
            flash("Deadline deleted.", "success")
        else:
            flash("Deadline not found.", "warning")
    except Exception as exc:
        logger.exception("delete_deadline: error — %s", exc)
        flash("Error deleting deadline.", "danger")
    return redirect(url_for("deadlines.list_deadlines"))
