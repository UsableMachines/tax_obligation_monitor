import logging
from datetime import date, timedelta
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import (
    Deadline, NexusExposure, PaymentObligation, Jurisdiction,
    FilingStatus, PaymentStatus, RiskLevel,
)
from app.services import kindo_agent

logger = logging.getLogger(__name__)
main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect_to_dashboard()
    return render_template("index.html")


def redirect_to_dashboard():
    from flask import redirect, url_for
    return redirect(url_for("main.dashboard"))


@main_bp.route("/dashboard")
@login_required
def dashboard():
    tid = current_user.tenant_id
    today = date.today()
    upcoming_window = today + timedelta(days=30)

    try:
        total_deadlines = Deadline.query.filter_by(tenant_id=tid).count()
        overdue_deadlines = Deadline.query.filter(
            Deadline.tenant_id == tid,
            Deadline.status != FilingStatus.FILED,
            Deadline.due_date < today
        ).count()
        upcoming_deadlines = Deadline.query.filter(
            Deadline.tenant_id == tid,
            Deadline.status != FilingStatus.FILED,
            Deadline.due_date >= today,
            Deadline.due_date <= upcoming_window
        ).order_by(Deadline.due_date).limit(10).all()

        total_nexus = NexusExposure.query.filter_by(tenant_id=tid).count()
        active_nexus = NexusExposure.query.filter_by(tenant_id=tid, has_nexus=True).count()
        high_risk_nexus = NexusExposure.query.filter(
            NexusExposure.tenant_id == tid,
            NexusExposure.risk_level.in_([RiskLevel.CRITICAL, RiskLevel.HIGH])
        ).count()

        total_payments = PaymentObligation.query.filter_by(tenant_id=tid).count()
        overdue_payments = PaymentObligation.query.filter(
            PaymentObligation.tenant_id == tid,
            PaymentObligation.status != PaymentStatus.PAID,
            PaymentObligation.due_date < today
        ).count()
        total_amount_due = db.session.query(
            db.func.coalesce(db.func.sum(PaymentObligation.amount), 0)
        ).filter(
            PaymentObligation.tenant_id == tid,
            PaymentObligation.status.in_([PaymentStatus.SCHEDULED, PaymentStatus.OVERDUE])
        ).scalar()

        jurisdictions_count = Jurisdiction.query.filter_by(tenant_id=tid).count()

        risk_counts = {}
        for rl in RiskLevel:
            risk_counts[rl.value] = Deadline.query.filter_by(
                tenant_id=tid, risk_level=rl
            ).count()

    except Exception as exc:
        logger.exception("dashboard: service error — %s", exc)
        return render_template("errors/500.html"), 500

    return render_template("dashboard.html",
        total_deadlines=total_deadlines,
        overdue_deadlines=overdue_deadlines,
        upcoming_deadlines=upcoming_deadlines,
        total_nexus=total_nexus,
        active_nexus=active_nexus,
        high_risk_nexus=high_risk_nexus,
        total_payments=total_payments,
        overdue_payments=overdue_payments,
        total_amount_due=total_amount_due,
        jurisdictions_count=jurisdictions_count,
        risk_counts=risk_counts,
        agent_configured=kindo_agent.is_configured(),
    )


@main_bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    if request.method == "POST":
        theme = request.form.get("theme", "light")
        if theme in ("light", "dark"):
            current_user.theme = theme
            db.session.commit()
    return render_template("settings.html")
