import enum
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db


class Tenant(db.Model):
    __tablename__ = "tenants"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(100), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    users = db.relationship("User", backref="tenant", lazy="dynamic")
    roles = db.relationship("Role", backref="tenant", lazy="dynamic")


class Role(db.Model):
    __tablename__ = "roles"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)  # admin, manager, analyst, viewer
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    users = db.relationship("User", backref="role", lazy="dynamic")

    __table_args__ = (db.UniqueConstraint("name", "tenant_id"),)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(200), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    theme = db.Column(db.String(10), default="light")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, pw):
        self.password_hash = generate_password_hash(pw)

    def check_password(self, pw):
        return check_password_hash(self.password_hash, pw)

    @property
    def role_name(self):
        return self.role.name if self.role else "viewer"

    def has_role(self, *names):
        return self.role_name in names

    def can_edit(self):
        return self.role_name in ("admin", "manager", "analyst")

    def can_admin(self):
        return self.role_name == "admin"


class RiskLevel(enum.Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class FilingStatus(enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    FILED = "filed"
    OVERDUE = "overdue"
    EXTENSION = "extension"


class Jurisdiction(db.Model):
    __tablename__ = "jurisdictions"
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    code = db.Column(db.String(20), nullable=False)  # e.g. US-CA, US-NY, DE
    jurisdiction_type = db.Column(db.String(50), default="state")  # federal, state, local, international
    country = db.Column(db.String(100), default="United States")
    tax_types = db.Column(db.Text, default="")  # comma-separated: income,sales,payroll
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    deadlines = db.relationship("Deadline", backref="jurisdiction", lazy="dynamic")
    nexus_records = db.relationship("NexusExposure", backref="jurisdiction", lazy="dynamic")
    payments = db.relationship("PaymentObligation", backref="jurisdiction", lazy="dynamic")


class Deadline(db.Model):
    __tablename__ = "deadlines"
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    jurisdiction_id = db.Column(db.Integer, db.ForeignKey("jurisdictions.id"), nullable=False)
    title = db.Column(db.String(300), nullable=False)
    tax_type = db.Column(db.String(100), nullable=False)  # income, sales, payroll, franchise, etc.
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum(FilingStatus), default=FilingStatus.PENDING)
    risk_level = db.Column(db.Enum(RiskLevel), default=RiskLevel.MEDIUM)
    assigned_to = db.Column(db.String(200), default="")
    notes = db.Column(db.Text, default="")
    extension_date = db.Column(db.Date, nullable=True)
    filed_date = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_overdue(self):
        if self.status == FilingStatus.FILED:
            return False
        effective = self.extension_date or self.due_date
        return date.today() > effective

    @property
    def days_until_due(self):
        effective = self.extension_date or self.due_date
        return (effective - date.today()).days


class NexusExposure(db.Model):
    __tablename__ = "nexus_exposures"
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    jurisdiction_id = db.Column(db.Integer, db.ForeignKey("jurisdictions.id"), nullable=False)
    entity_name = db.Column(db.String(300), nullable=False)
    nexus_type = db.Column(db.String(100), nullable=False)  # physical, economic, affiliate, click-through
    has_nexus = db.Column(db.Boolean, default=False)
    revenue_in_jurisdiction = db.Column(db.Float, default=0.0)
    employee_count = db.Column(db.Integer, default=0)
    property_value = db.Column(db.Float, default=0.0)
    threshold_met = db.Column(db.Boolean, default=False)
    risk_level = db.Column(db.Enum(RiskLevel), default=RiskLevel.LOW)
    notes = db.Column(db.Text, default="")
    last_reviewed = db.Column(db.Date, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PaymentStatus(enum.Enum):
    SCHEDULED = "scheduled"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    PARTIAL = "partial"


class PaymentObligation(db.Model):
    __tablename__ = "payment_obligations"
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    jurisdiction_id = db.Column(db.Integer, db.ForeignKey("jurisdictions.id"), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    tax_type = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.SCHEDULED)
    payment_date = db.Column(db.Date, nullable=True)
    confirmation_number = db.Column(db.String(200), default="")
    risk_level = db.Column(db.Enum(RiskLevel), default=RiskLevel.MEDIUM)
    notes = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def is_overdue(self):
        if self.status == PaymentStatus.PAID:
            return False
        return date.today() > self.due_date


class AnalysisResult(db.Model):
    """Stores Kindo agent enrichment results."""
    __tablename__ = "analysis_results"
    id = db.Column(db.Integer, primary_key=True)
    tenant_id = db.Column(db.Integer, db.ForeignKey("tenants.id"), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)  # deadline, nexus, payment, jurisdiction
    entity_id = db.Column(db.Integer, nullable=False)
    operation = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="ok")
    summary = db.Column(db.Text, default="")
    score = db.Column(db.Float, default=0.0)
    risk_level = db.Column(db.String(20), default="medium")
    findings_json = db.Column(db.Text, default="[]")
    recommendations_json = db.Column(db.Text, default="[]")
    confidence = db.Column(db.Float, default=0.0)
    raw_response_json = db.Column(db.Text, default="{}")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    created_by = db.Column(db.String(80), default="")
