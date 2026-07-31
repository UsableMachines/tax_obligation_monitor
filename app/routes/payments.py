import logging
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.models import PaymentObligation, Jurisdiction, PaymentStatus, RiskLevel

logger = logging.getLogger(__name__)
payments_bp = Blueprint("payments", __name__)


@payments_bp.route("/payments")
@login_required
def list_payments():
    tid = current_user.tenant_id
    status_filter = request.args.get("status", "")
    try:
        q = PaymentObligation.query.filter_by(tenant_id=tid)
        if status_filter:
            q = q.filter(PaymentObligation.status == PaymentStatus(status_filter))
        payments = q.order_by(PaymentObligation.due_date).all()
        jurisdictions = Jurisdiction.query.filter_by(tenant_id=tid).all()
    except Exception as exc:
        logger.exception("list_payments: error — %s", exc)
        return render_template("errors/500.html"), 500
    return render_template("payments/list.html",
        payments=payments, jurisdictions=jurisdictions,
        statuses=PaymentStatus, risks=RiskLevel, status_filter=status_filter)


@payments_bp.route("/payments/new", methods=["GET", "POST"])
@login_required
def new_payment():
    if not current_user.can_edit():
        flash("Permission denied.", "danger")
        return redirect(url_for("payments.list_payments"))
    tid = current_user.tenant_id
    try:
        jurisdictions = Jurisdiction.query.filter_by(tenant_id=tid).all()
    except Exception as exc:
        logger.exception("new_payment: error — %s", exc)
        return render_template("errors/500.html"), 500

    if request.method == "POST":
        try:
            p = PaymentObligation(
                tenant_id=tid,
                jurisdiction_id=int(request.form["jurisdiction_id"]),
                description=request.form["description"].strip(),
                tax_type=request.form["tax_type"].strip(),
                amount=float(request.form["amount"]),
                due_date=datetime.strptime(request.form["due_date"], "%Y-%m-%d").date(),
                status=PaymentStatus(request.form.get("status", "scheduled")),
                risk_level=RiskLevel(request.form.get("risk_level", "medium")),
                confirmation_number=request.form.get("confirmation_number", "").strip(),
                notes=request.form.get("notes", "").strip(),
            )
            pd_str = request.form.get("payment_date", "").strip()
            if pd_str:
                p.payment_date = datetime.strptime(pd_str, "%Y-%m-%d").date()
            db.session.add(p)
            db.session.commit()
            flash("Payment obligation created.", "success")
            return redirect(url_for("payments.list_payments"))
        except Exception as exc:
            logger.exception("new_payment: error — %s", exc)
            flash(f"Error: {exc}", "danger")

    return render_template("payments/form.html", payment=None,
        jurisdictions=jurisdictions, statuses=PaymentStatus, risks=RiskLevel)


@payments_bp.route("/payments/<int:pid>/edit", methods=["GET", "POST"])
@login_required
def edit_payment(pid):
    if not current_user.can_edit():
        flash("Permission denied.", "danger")
        return redirect(url_for("payments.list_payments"))
    tid = current_user.tenant_id
    try:
        payment = PaymentObligation.query.filter_by(id=pid, tenant_id=tid).first()
        jurisdictions = Jurisdiction.query.filter_by(tenant_id=tid).all()
    except Exception as exc:
        logger.exception("edit_payment: error — %s", exc)
        return render_template("errors/500.html"), 500

    if payment is None:
        flash("Payment not found.", "warning")
        return redirect(url_for("payments.list_payments"))

    if request.method == "POST":
        try:
            payment.jurisdiction_id = int(request.form["jurisdiction_id"])
            payment.description = request.form["description"].strip()
            payment.tax_type = request.form["tax_type"].strip()
            payment.amount = float(request.form["amount"])
            payment.due_date = datetime.strptime(request.form["due_date"], "%Y-%m-%d").date()
            payment.status = PaymentStatus(request.form.get("status", "scheduled"))
            payment.risk_level = RiskLevel(request.form.get("risk_level", "medium"))
            payment.confirmation_number = request.form.get("confirmation_number", "").strip()
            payment.notes = request.form.get("notes", "").strip()
            pd_str = request.form.get("payment_date", "").strip()
            payment.payment_date = datetime.strptime(pd_str, "%Y-%m-%d").date() if pd_str else None
            db.session.commit()
            flash("Payment updated.", "success")
            return redirect(url_for("payments.list_payments"))
        except Exception as exc:
            logger.exception("edit_payment: error — %s", exc)
            flash(f"Error: {exc}", "danger")

    return render_template("payments/form.html", payment=payment,
        jurisdictions=jurisdictions, statuses=PaymentStatus, risks=RiskLevel)


@payments_bp.route("/payments/<int:pid>/delete", methods=["POST"])
@login_required
def delete_payment(pid):
    if not current_user.can_edit():
        flash("Permission denied.", "danger")
        return redirect(url_for("payments.list_payments"))
    try:
        p = PaymentObligation.query.filter_by(id=pid, tenant_id=current_user.tenant_id).first()
        if p:
            db.session.delete(p)
            db.session.commit()
            flash("Payment deleted.", "success")
        else:
            flash("Not found.", "warning")
    except Exception as exc:
        logger.exception("delete_payment: error — %s", exc)
        flash("Error.", "danger")
    return redirect(url_for("payments.list_payments"))
