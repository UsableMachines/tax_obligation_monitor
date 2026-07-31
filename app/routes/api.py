import json
import logging
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from app import db
from app.models import (
    Deadline, NexusExposure, PaymentObligation, Jurisdiction,
    AnalysisResult, RiskLevel,
)
from app.services import kindo_agent

logger = logging.getLogger(__name__)
api_bp = Blueprint("api", __name__)


def _is_ajax(req):
    return req.headers.get("X-Requested-With") == "XMLHttpRequest" or \
           "application/json" in req.headers.get("Accept", "")


@api_bp.route("/analyze", methods=["POST"])
@login_required
def analyze():
    """Run Kindo agent analysis on a given entity."""
    if not kindo_agent.is_configured():
        return jsonify({
            "status": "error",
            "summary": "Kindo agent is not configured. Please set KINDO_API_TOKEN and KINDO_AGENT_ID environment variables."
        }), 422

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "summary": "Invalid request body."}), 400

    entity_type = data.get("entity_type", "")
    entity_id = data.get("entity_id")
    operation = data.get("operation", "analyze")
    tid = current_user.tenant_id

    # Build input_data from the entity
    try:
        input_data = _build_input_data(entity_type, entity_id, tid)
    except Exception as exc:
        logger.exception("analyze: error building input — %s", exc)
        return jsonify({"status": "error", "summary": f"Failed to load entity: {exc}"}), 500

    if input_data is None:
        return jsonify({"status": "error", "summary": "Entity not found."}), 404

    tenant_name = current_user.tenant.name if current_user.tenant else ""
    payload = kindo_agent.build_request_payload(
        operation=operation,
        entity_id=entity_id,
        input_data=input_data,
        organization=tenant_name,
    )

    try:
        result = kindo_agent.run_agent(payload)
    except Exception as exc:
        logger.exception("analyze: agent error — %s", exc)
        return jsonify({"status": "error", "summary": f"Agent call failed: {exc}"}), 500

    # Save analysis result
    try:
        ar = AnalysisResult(
            tenant_id=tid,
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            status=result.get("status", "ok"),
            summary=result.get("summary", ""),
            score=float(result.get("score", 0)),
            risk_level=result.get("risk_level", "medium"),
            findings_json=json.dumps(result.get("findings", [])),
            recommendations_json=json.dumps(result.get("recommendations", [])),
            confidence=float(result.get("confidence", 0)),
            raw_response_json=json.dumps(result),
            created_by=current_user.username,
        )
        db.session.add(ar)
        db.session.commit()
    except Exception as exc:
        logger.warning("analyze: failed to persist result — %s", exc)

    return jsonify(result)


@api_bp.route("/analysis-history")
@login_required
def analysis_history():
    tid = current_user.tenant_id
    entity_type = request.args.get("entity_type", "")
    entity_id = request.args.get("entity_id", "")
    try:
        q = AnalysisResult.query.filter_by(tenant_id=tid)
        if entity_type:
            q = q.filter_by(entity_type=entity_type)
        if entity_id:
            q = q.filter_by(entity_id=int(entity_id))
        results = q.order_by(AnalysisResult.created_at.desc()).limit(50).all()
    except Exception as exc:
        logger.exception("analysis_history: error — %s", exc)
        return jsonify({"error": "Failed to load history.", "detail": str(exc)}), 500

    items = []
    for r in results:
        items.append({
            "id": r.id,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "operation": r.operation,
            "status": r.status,
            "summary": r.summary,
            "score": r.score,
            "risk_level": r.risk_level,
            "confidence": r.confidence,
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "created_by": r.created_by,
        })
    return jsonify(items)


@api_bp.route("/dashboard-stats")
@login_required
def dashboard_stats():
    """Return live dashboard stats as JSON for refresh."""
    from datetime import date, timedelta
    tid = current_user.tenant_id
    today = date.today()
    try:
        from app.models import FilingStatus, PaymentStatus
        overdue_d = Deadline.query.filter(
            Deadline.tenant_id == tid,
            Deadline.status != FilingStatus.FILED,
            Deadline.due_date < today
        ).count()
        overdue_p = PaymentObligation.query.filter(
            PaymentObligation.tenant_id == tid,
            PaymentObligation.status != PaymentStatus.PAID,
            PaymentObligation.due_date < today
        ).count()
        high_risk = NexusExposure.query.filter(
            NexusExposure.tenant_id == tid,
            NexusExposure.risk_level.in_([RiskLevel.CRITICAL, RiskLevel.HIGH])
        ).count()
    except Exception as exc:
        logger.exception("dashboard_stats: error — %s", exc)
        return jsonify({"error": "Failed to load stats.", "detail": str(exc)}), 500

    return jsonify({
        "overdue_deadlines": overdue_d,
        "overdue_payments": overdue_p,
        "high_risk_nexus": high_risk,
    })


def _build_input_data(entity_type, entity_id, tenant_id):
    """Build input_data dict from entity for the Kindo agent."""
    if entity_type == "deadline":
        d = Deadline.query.filter_by(id=entity_id, tenant_id=tenant_id).first()
        if not d:
            return None
        j = d.jurisdiction
        return {
            "description": f"Tax filing deadline: {d.title}",
            "records": [
                f"Tax type: {d.tax_type}",
                f"Due date: {d.due_date.isoformat()}",
                f"Status: {d.status.value}",
                f"Risk level: {d.risk_level.value}",
                f"Jurisdiction: {j.name} ({j.code})" if j else "Jurisdiction: Unknown",
                f"Assigned to: {d.assigned_to}" if d.assigned_to else "",
                f"Notes: {d.notes}" if d.notes else "",
            ],
        }
    elif entity_type == "nexus":
        n = NexusExposure.query.filter_by(id=entity_id, tenant_id=tenant_id).first()
        if not n:
            return None
        j = n.jurisdiction
        return {
            "description": f"Nexus exposure analysis: {n.entity_name}",
            "records": [
                f"Nexus type: {n.nexus_type}",
                f"Has nexus: {n.has_nexus}",
                f"Revenue in jurisdiction: ${n.revenue_in_jurisdiction:,.2f}",
                f"Employee count: {n.employee_count}",
                f"Property value: ${n.property_value:,.2f}",
                f"Threshold met: {n.threshold_met}",
                f"Risk level: {n.risk_level.value}",
                f"Jurisdiction: {j.name} ({j.code})" if j else "Jurisdiction: Unknown",
            ],
        }
    elif entity_type == "payment":
        p = PaymentObligation.query.filter_by(id=entity_id, tenant_id=tenant_id).first()
        if not p:
            return None
        j = p.jurisdiction
        return {
            "description": f"Payment obligation: {p.description}",
            "records": [
                f"Tax type: {p.tax_type}",
                f"Amount: ${p.amount:,.2f}",
                f"Due date: {p.due_date.isoformat()}",
                f"Status: {p.status.value}",
                f"Risk level: {p.risk_level.value}",
                f"Jurisdiction: {j.name} ({j.code})" if j else "Jurisdiction: Unknown",
            ],
        }
    elif entity_type == "jurisdiction":
        j = Jurisdiction.query.filter_by(id=entity_id, tenant_id=tenant_id).first()
        if not j:
            return None
        return {
            "description": f"Jurisdiction compliance review: {j.name} ({j.code})",
            "records": [
                f"Type: {j.jurisdiction_type}",
                f"Country: {j.country}",
                f"Tax types: {j.tax_types}",
                f"Active deadlines: {j.deadlines.count()}",
                f"Nexus records: {j.nexus_records.count()}",
                f"Payment obligations: {j.payments.count()}",
            ],
        }
    return None
