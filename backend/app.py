import os
import secrets
from io import BytesIO
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, g, jsonify, request, send_file
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from openpyxl import Workbook
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from sqlalchemy import UniqueConstraint
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


ROLE_SUPER_ADMIN = "super_admin"
ROLE_ADMIN = "admin"
ROLE_AGENT = "agent"
ROLE_CANDIDATE = "candidate"
ALLOWED_ROLES = {ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_AGENT, ROLE_CANDIDATE}

CANDIDATE_STATUSES = {"pending", "in_review", "cleared", "flagged"}
CHECK_STATUSES = {"in_progress", "passed", "failed"}


class Employer(db.Model):
    __tablename__ = "employers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {"id": self.id, "name": self.name, "created_at": self.created_at.isoformat()}


class EmployerVerificationStep(db.Model):
    __tablename__ = "employer_verification_steps"

    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey("employers.id"), nullable=False)
    check_type = db.Column(db.String(40), nullable=False)
    default_provider = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("employer_id", "check_type", name="uq_employer_check_type"),)

    def to_dict(self):
        return {
            "id": self.id,
            "employer_id": self.employer_id,
            "check_type": self.check_type,
            "default_provider": self.default_provider,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey("employers.id"), nullable=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=True, unique=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(40), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "role": self.role,
            "employer_id": self.employer_id,
            "candidate_id": self.candidate_id,
            "is_active": self.is_active,
        }


class AuthToken(db.Model):
    __tablename__ = "auth_tokens"

    id = db.Column(db.Integer, primary_key=True)
    token = db.Column(db.String(80), nullable=False, unique=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class EmployerCandidate(db.Model):
    __tablename__ = "employer_candidates"

    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey("employers.id"), nullable=False)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class AgentEmployer(db.Model):
    __tablename__ = "agent_employers"

    id = db.Column(db.Integer, primary_key=True)
    employer_id = db.Column(db.Integer, db.ForeignKey("employers.id"), nullable=False)
    agent_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (UniqueConstraint("employer_id", "agent_user_id", name="uq_agent_employer"),)


class Candidate(db.Model):
    __tablename__ = "candidates"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)
    phone = db.Column(db.String(30), nullable=False)
    dob = db.Column(db.String(20), nullable=False)
    position = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(40), nullable=False, default="pending")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    checks = db.relationship("BackgroundCheck", backref="candidate", cascade="all,delete", lazy=True)

    def to_dict(self, include_checks=False):
        payload = {
            "id": self.id,
            "full_name": self.full_name,
            "email": self.email,
            "phone": self.phone,
            "dob": self.dob,
            "position": self.position,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }
        if include_checks:
            payload["checks"] = [check.to_dict() for check in self.checks]
        return payload


class BackgroundCheck(db.Model):
    __tablename__ = "background_checks"

    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("candidates.id"), nullable=False)
    check_type = db.Column(db.String(40), nullable=False)
    provider = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(40), nullable=False, default="in_progress")
    result_notes = db.Column(db.Text, nullable=True)
    initiated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "candidate_id": self.candidate_id,
            "check_type": self.check_type,
            "provider": self.provider,
            "status": self.status,
            "result_notes": self.result_notes,
            "initiated_at": self.initiated_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


def create_app():
    app = Flask(__name__)

    database_url = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/background_verification")
    if database_url.startswith("postgres://"):
        database_url = database_url.replace("postgres://", "postgresql://", 1)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    CORS(app)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        ensure_default_super_admin()

    def parse_json():
        return request.get_json(silent=True) or {}

    def unauthorized(message="Authentication required"):
        return jsonify({"error": message}), 401

    def forbidden(message="Forbidden"):
        return jsonify({"error": message}), 403

    def get_user_from_request():
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return None

        token_value = auth_header.split(" ", 1)[1].strip()
        if not token_value:
            return None

        auth_token = AuthToken.query.filter_by(token=token_value).first()
        if not auth_token or auth_token.expires_at < datetime.utcnow():
            return None

        user = User.query.get(auth_token.user_id)
        if not user or not user.is_active:
            return None
        return user

    def require_auth(roles=None):
        allowed_roles = set(roles or [])

        def decorator(fn):
            @wraps(fn)
            def wrapped(*args, **kwargs):
                user = get_user_from_request()
                if not user:
                    return unauthorized()

                if allowed_roles and user.role not in allowed_roles:
                    return forbidden("Insufficient role access")

                g.current_user = user
                return fn(*args, **kwargs)

            return wrapped

        return decorator

    def candidate_employer_id(candidate_id):
        link = EmployerCandidate.query.filter_by(candidate_id=candidate_id).first()
        return link.employer_id if link else None

    def agent_has_employer_access(agent_user_id, employer_id):
        if employer_id is None:
            return False
        return (
            AgentEmployer.query.filter_by(agent_user_id=agent_user_id, employer_id=employer_id).first()
            is not None
        )

    def user_can_access_employer(user, employer_id):
        if user.role == ROLE_SUPER_ADMIN:
            return True
        if user.role == ROLE_ADMIN:
            return user.employer_id == employer_id
        if user.role == ROLE_AGENT:
            return agent_has_employer_access(user.id, employer_id)
        if user.role == ROLE_CANDIDATE:
            return user.employer_id == employer_id
        return False

    def user_can_access_candidate(user, candidate):
        employer_id = candidate_employer_id(candidate.id)
        if user.role == ROLE_SUPER_ADMIN:
            return True
        if user.role == ROLE_ADMIN:
            return user.employer_id == employer_id
        if user.role == ROLE_AGENT:
            return agent_has_employer_access(user.id, employer_id)
        if user.role == ROLE_CANDIDATE:
            return user.candidate_id == candidate.id
        return False

    def scoped_candidate_query(user):
        if user.role == ROLE_SUPER_ADMIN:
            return Candidate.query

        if user.role == ROLE_ADMIN:
            subq = db.session.query(EmployerCandidate.candidate_id).filter_by(employer_id=user.employer_id)
            return Candidate.query.filter(Candidate.id.in_(subq))

        if user.role == ROLE_AGENT:
            employer_ids = db.session.query(AgentEmployer.employer_id).filter_by(agent_user_id=user.id)
            subq = db.session.query(EmployerCandidate.candidate_id).filter(EmployerCandidate.employer_id.in_(employer_ids))
            return Candidate.query.filter(Candidate.id.in_(subq))

        return Candidate.query.filter_by(id=user.candidate_id)

    def recompute_candidate_status(candidate):
        statuses = {item.status for item in candidate.checks}
        if "failed" in statuses:
            candidate.status = "flagged"
        elif statuses and statuses.issubset({"passed"}):
            candidate.status = "cleared"
        elif statuses:
            candidate.status = "in_review"
        else:
            candidate.status = "pending"

    def validate_status(value, allowed, field_name):
        if value not in allowed:
            return jsonify({"error": f"Invalid {field_name}"}), 400
        return None

    def parse_iso_date(value, field_name):
        if not value:
            return None, jsonify({"error": f"{field_name} is required"}), 400
        try:
            return datetime.strptime(value, "%Y-%m-%d"), None, None
        except ValueError:
            return None, jsonify({"error": f"{field_name} must be YYYY-MM-DD"}), 400

    @app.post("/api/auth/login")
    def login():
        data = parse_json()
        email = (data.get("email") or "").strip().lower()
        password = data.get("password") or ""
        if not email or not password:
            return jsonify({"error": "email and password are required"}), 400

        user = User.query.filter_by(email=email).first()
        if not user or not user.is_active or not check_password_hash(user.password_hash, password):
            return unauthorized("Invalid credentials")

        token = AuthToken(
            token=secrets.token_urlsafe(32),
            user_id=user.id,
            expires_at=datetime.utcnow() + timedelta(hours=12),
        )
        db.session.add(token)
        db.session.commit()
        return jsonify({"token": token.token, "user": user.to_dict()})

    @app.get("/api/auth/me")
    @require_auth()
    def me():
        return jsonify(g.current_user.to_dict())

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "employment-background-verification-api"})

    @app.get("/api/dashboard/summary")
    @require_auth()
    def dashboard_summary():
        if g.current_user.role == ROLE_ADMIN:
            total_employers = Employer.query.count()
            companies_with_candidates = db.session.query(EmployerCandidate.employer_id).distinct().count()
            return jsonify(
                {
                    "total_employers": total_employers,
                    "companies_with_candidates": companies_with_candidates,
                }
            )

        query = scoped_candidate_query(g.current_user)
        total_candidates = query.count()
        pending = query.filter_by(status="pending").count()
        in_review = query.filter_by(status="in_review").count()
        cleared = query.filter_by(status="cleared").count()
        flagged = query.filter_by(status="flagged").count()

        return jsonify(
            {
                "total_candidates": total_candidates,
                "pending": pending,
                "in_review": in_review,
                "cleared": cleared,
                "flagged": flagged,
            }
        )

    @app.get("/api/candidates")
    @require_auth({ROLE_SUPER_ADMIN, ROLE_AGENT, ROLE_CANDIDATE})
    def list_candidates():
        status = request.args.get("status")
        query = scoped_candidate_query(g.current_user)
        if status:
            query = query.filter_by(status=status)

        candidates = query.order_by(Candidate.created_at.desc()).all()
        return jsonify([candidate.to_dict() for candidate in candidates])

    @app.post("/api/candidates")
    @require_auth({ROLE_SUPER_ADMIN})
    def create_candidate():
        data = parse_json()
        required_fields = [
            "full_name",
            "email",
            "phone",
            "dob",
            "position",
            "credential_email",
            "credential_password",
        ]
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

        existing = Candidate.query.filter_by(email=data["email"].strip().lower()).first()
        if existing:
            return jsonify({"error": "Candidate email already exists"}), 409

        credential_email = data["credential_email"].strip().lower()
        if User.query.filter_by(email=credential_email).first():
            return jsonify({"error": "credential_email already exists"}), 409

        if len(data["credential_password"]) < 8:
            return jsonify({"error": "credential_password must be at least 8 characters"}), 400

        user = g.current_user
        employer_id = data.get("employer_id")
        if user.role == ROLE_ADMIN:
            employer_id = user.employer_id

        if not employer_id:
            return jsonify({"error": "employer_id is required"}), 400

        employer = Employer.query.get(employer_id)
        if not employer:
            return jsonify({"error": "Employer not found"}), 404

        if not user_can_access_employer(user, employer_id):
            return forbidden()

        candidate = Candidate(
            full_name=data["full_name"].strip(),
            email=data["email"].strip().lower(),
            phone=data["phone"].strip(),
            dob=data["dob"].strip(),
            position=data["position"].strip(),
            status="pending",
        )
        db.session.add(candidate)
        db.session.flush()

        candidate_user = User(
            full_name=candidate.full_name,
            email=credential_email,
            password_hash=generate_password_hash(data["credential_password"]),
            role=ROLE_CANDIDATE,
            employer_id=employer.id,
            candidate_id=candidate.id,
        )
        db.session.add(candidate_user)

        link = EmployerCandidate(employer_id=employer.id, candidate_id=candidate.id)
        db.session.add(link)

        active_steps = EmployerVerificationStep.query.filter_by(employer_id=employer.id, is_active=True).all()
        if active_steps:
            for step in active_steps:
                db.session.add(
                    BackgroundCheck(
                        candidate_id=candidate.id,
                        check_type=step.check_type,
                        provider=step.default_provider,
                        status="in_progress",
                    )
                )
            candidate.status = "in_review"

        db.session.commit()

        return jsonify(candidate.to_dict()), 201

    @app.get("/api/candidates/<int:candidate_id>")
    @require_auth({ROLE_SUPER_ADMIN, ROLE_AGENT, ROLE_CANDIDATE})
    def get_candidate(candidate_id):
        candidate = Candidate.query.get_or_404(candidate_id)
        if not user_can_access_candidate(g.current_user, candidate):
            return forbidden()
        return jsonify(candidate.to_dict(include_checks=True))

    @app.patch("/api/candidates/<int:candidate_id>")
    @require_auth({ROLE_SUPER_ADMIN})
    def update_candidate(candidate_id):
        candidate = Candidate.query.get_or_404(candidate_id)
        if not user_can_access_candidate(g.current_user, candidate):
            return forbidden()
        data = parse_json()

        if "status" in data:
            status_validation = validate_status(data["status"], CANDIDATE_STATUSES, "candidate status")
            if status_validation:
                return status_validation
            candidate.status = data["status"]

        db.session.commit()
        return jsonify(candidate.to_dict(include_checks=True))

    @app.post("/api/candidates/<int:candidate_id>/checks")
    @require_auth({ROLE_SUPER_ADMIN})
    def create_check(candidate_id):
        candidate = Candidate.query.get_or_404(candidate_id)
        if not user_can_access_candidate(g.current_user, candidate):
            return forbidden()
        data = parse_json()

        required_fields = ["check_type", "provider"]
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

        check = BackgroundCheck(
            candidate_id=candidate.id,
            check_type=data["check_type"].strip(),
            provider=data["provider"].strip(),
            status="in_progress",
        )

        candidate.status = "in_review"
        db.session.add(check)
        db.session.commit()

        return jsonify(check.to_dict()), 201

    @app.patch("/api/checks/<int:check_id>")
    @require_auth({ROLE_SUPER_ADMIN, ROLE_AGENT})
    def update_check(check_id):
        check = BackgroundCheck.query.get_or_404(check_id)
        if not user_can_access_candidate(g.current_user, check.candidate):
            return forbidden()
        data = parse_json()

        if "status" in data:
            status_validation = validate_status(data["status"], CHECK_STATUSES, "check status")
            if status_validation:
                return status_validation
            check.status = data["status"]
            if data["status"] in {"passed", "failed"}:
                check.completed_at = datetime.utcnow()

        if "result_notes" in data:
            check.result_notes = data["result_notes"]

        candidate = check.candidate
        recompute_candidate_status(candidate)

        db.session.commit()
        return jsonify(check.to_dict())

    @app.get("/api/employers")
    @require_auth({ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_AGENT, ROLE_CANDIDATE})
    def list_employers():
        user = g.current_user
        if user.role == ROLE_SUPER_ADMIN:
            employers = Employer.query.order_by(Employer.name.asc()).all()
        elif user.role == ROLE_ADMIN:
            employers = Employer.query.filter_by(id=user.employer_id).all()
        elif user.role == ROLE_CANDIDATE:
            employers = Employer.query.filter_by(id=user.employer_id).all()
        else:
            ids = db.session.query(AgentEmployer.employer_id).filter_by(agent_user_id=user.id)
            employers = Employer.query.filter(Employer.id.in_(ids)).order_by(Employer.name.asc()).all()
        return jsonify([employer.to_dict() for employer in employers])

    @app.post("/api/employers")
    @require_auth({ROLE_SUPER_ADMIN, ROLE_ADMIN})
    def create_employer():
        data = parse_json()
        name = (data.get("name") or "").strip()
        if not name:
            return jsonify({"error": "name is required"}), 400

        existing = Employer.query.filter_by(name=name).first()
        if existing:
            return jsonify({"error": "Employer name already exists"}), 409

        employer = Employer(name=name)
        db.session.add(employer)
        db.session.commit()
        return jsonify(employer.to_dict()), 201

    @app.get("/api/reports/candidates")
    @require_auth({ROLE_SUPER_ADMIN, ROLE_ADMIN})
    def export_candidate_report():
        start_date_raw = request.args.get("start_date", "")
        end_date_raw = request.args.get("end_date", "")
        format_raw = (request.args.get("format", "xlsx") or "xlsx").strip().lower()

        start_date, error_response, status_code = parse_iso_date(start_date_raw, "start_date")
        if error_response:
            return error_response, status_code

        end_date, error_response, status_code = parse_iso_date(end_date_raw, "end_date")
        if error_response:
            return error_response, status_code

        if end_date < start_date:
            return jsonify({"error": "end_date must be on or after start_date"}), 400

        if format_raw not in {"xlsx", "pdf"}:
            return jsonify({"error": "format must be xlsx or pdf"}), 400

        end_of_day = end_date + timedelta(days=1)
        rows = (
            db.session.query(Candidate, Employer)
            .join(EmployerCandidate, EmployerCandidate.candidate_id == Candidate.id)
            .join(Employer, Employer.id == EmployerCandidate.employer_id)
            .filter(Candidate.created_at >= start_date)
            .filter(Candidate.created_at < end_of_day)
            .order_by(Candidate.created_at.asc())
            .all()
        )

        if format_raw == "xlsx":
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "Candidate Report"
            sheet.append(["Candidate", "Employer", "Email", "Position", "Status", "Created At"])
            for candidate, employer in rows:
                sheet.append(
                    [
                        candidate.full_name,
                        employer.name,
                        candidate.email,
                        candidate.position,
                        candidate.status,
                        candidate.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    ]
                )

            output = BytesIO()
            workbook.save(output)
            output.seek(0)
            return send_file(
                output,
                as_attachment=True,
                download_name="candidate_report.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )

        output = BytesIO()
        pdf = canvas.Canvas(output, pagesize=letter)
        width, height = letter
        y = height - 40

        pdf.setFont("Helvetica-Bold", 12)
        pdf.drawString(40, y, f"Candidate Report ({start_date_raw} to {end_date_raw})")
        y -= 24

        pdf.setFont("Helvetica", 9)
        if not rows:
            pdf.drawString(40, y, "No records for selected date range.")
        else:
            for candidate, employer in rows:
                line = (
                    f"{candidate.created_at.strftime('%Y-%m-%d')} | {candidate.full_name} | "
                    f"{employer.name} | {candidate.status}"
                )
                pdf.drawString(40, y, line[:120])
                y -= 14
                if y < 40:
                    pdf.showPage()
                    pdf.setFont("Helvetica", 9)
                    y = height - 40

        pdf.save()
        output.seek(0)
        return send_file(
            output,
            as_attachment=True,
            download_name="candidate_report.pdf",
            mimetype="application/pdf",
        )

    @app.get("/api/employers/<int:employer_id>/steps")
    @require_auth({ROLE_SUPER_ADMIN, ROLE_ADMIN, ROLE_AGENT, ROLE_CANDIDATE})
    def list_steps(employer_id):
        if not user_can_access_employer(g.current_user, employer_id):
            return forbidden()

        steps = (
            EmployerVerificationStep.query.filter_by(employer_id=employer_id)
            .order_by(EmployerVerificationStep.check_type.asc())
            .all()
        )
        return jsonify([step.to_dict() for step in steps])

    @app.post("/api/employers/<int:employer_id>/steps")
    @require_auth({ROLE_SUPER_ADMIN})
    def create_step(employer_id):
        employer = Employer.query.get_or_404(employer_id)
        data = parse_json()
        required_fields = ["check_type", "default_provider"]
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

        check_type = data["check_type"].strip().lower()
        default_provider = data["default_provider"].strip()
        if check_type not in {"employment", "criminal", "education", "identity"}:
            return jsonify({"error": "Invalid check_type"}), 400

        existing = EmployerVerificationStep.query.filter_by(employer_id=employer.id, check_type=check_type).first()
        if existing:
            return jsonify({"error": "Step already exists for employer"}), 409

        step = EmployerVerificationStep(
            employer_id=employer.id,
            check_type=check_type,
            default_provider=default_provider,
            is_active=bool(data.get("is_active", True)),
        )
        db.session.add(step)
        db.session.commit()
        return jsonify(step.to_dict()), 201

    @app.post("/api/users")
    @require_auth({ROLE_SUPER_ADMIN})
    def create_user():
        data = parse_json()
        required_fields = ["full_name", "email", "password", "role"]
        missing = [field for field in required_fields if not data.get(field)]
        if missing:
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400

        role = (data.get("role") or "").strip()
        if role not in {ROLE_ADMIN, ROLE_AGENT}:
            return jsonify({"error": "role must be admin or agent"}), 400

        employer_id = data.get("employer_id")
        if not employer_id:
            return jsonify({"error": "employer_id is required"}), 400

        employer = Employer.query.get(employer_id)
        if not employer:
            return jsonify({"error": "Employer not found"}), 404

        email = data["email"].strip().lower()
        if User.query.filter_by(email=email).first():
            return jsonify({"error": "Email already exists"}), 409

        password = data["password"]
        if len(password) < 8:
            return jsonify({"error": "password must be at least 8 characters"}), 400

        user = User(
            full_name=data["full_name"].strip(),
            email=email,
            password_hash=generate_password_hash(password),
            role=role,
            employer_id=employer.id,
        )
        db.session.add(user)
        db.session.flush()

        if role == ROLE_AGENT:
            db.session.add(AgentEmployer(employer_id=employer.id, agent_user_id=user.id))

        db.session.commit()
        return jsonify(user.to_dict()), 201

    @app.post("/api/seed")
    @require_auth({ROLE_SUPER_ADMIN})
    def seed_data():
        if Candidate.query.count() > 0:
            return jsonify({"message": "Seed data already exists"})

        employer = Employer.query.filter_by(name="Acme Corp").first()
        if not employer:
            employer = Employer(name="Acme Corp")
            db.session.add(employer)
            db.session.flush()

        step_templates = [
            {"check_type": "employment", "default_provider": "VerifierOps"},
            {"check_type": "criminal", "default_provider": "SecureScreen"},
            {"check_type": "education", "default_provider": "EduValidate"},
            {"check_type": "identity", "default_provider": "TrustID"},
        ]
        for template in step_templates:
            existing = EmployerVerificationStep.query.filter_by(
                employer_id=employer.id, check_type=template["check_type"]
            ).first()
            if not existing:
                db.session.add(
                    EmployerVerificationStep(
                        employer_id=employer.id,
                        check_type=template["check_type"],
                        default_provider=template["default_provider"],
                    )
                )
        db.session.flush()

        seed_candidates = [
            Candidate(
                full_name="Ava Thompson",
                email="ava.thompson@example.com",
                phone="+1-415-555-0141",
                dob="1994-08-22",
                position="Senior Backend Engineer",
                status="pending",
            ),
            Candidate(
                full_name="Liam Carter",
                email="liam.carter@example.com",
                phone="+1-332-555-0189",
                dob="1991-01-12",
                position="Product Manager",
                status="pending",
            ),
        ]
        db.session.add_all(seed_candidates)
        db.session.flush()

        for candidate in seed_candidates:
            db.session.add(EmployerCandidate(employer_id=employer.id, candidate_id=candidate.id))
            credential_email = f"{candidate.full_name.lower().replace(' ', '.')}@candidate.acme.local"
            db.session.add(
                User(
                    full_name=candidate.full_name,
                    email=credential_email,
                    password_hash=generate_password_hash("Candidate123!"),
                    role=ROLE_CANDIDATE,
                    employer_id=employer.id,
                    candidate_id=candidate.id,
                )
            )
            active_steps = EmployerVerificationStep.query.filter_by(employer_id=employer.id, is_active=True).all()
            for step in active_steps:
                db.session.add(
                    BackgroundCheck(
                        candidate_id=candidate.id,
                        check_type=step.check_type,
                        provider=step.default_provider,
                        status="in_progress",
                    )
                )
            candidate.status = "in_review"

        admin = User.query.filter_by(email="admin@acme.local").first()
        if not admin:
            db.session.add(
                User(
                    full_name="Acme Admin",
                    email="admin@acme.local",
                    password_hash=generate_password_hash("Admin123!"),
                    role=ROLE_ADMIN,
                    employer_id=employer.id,
                )
            )

        agent = User.query.filter_by(email="agent@acme.local").first()
        if not agent:
            agent = User(
                full_name="Acme Agent",
                email="agent@acme.local",
                password_hash=generate_password_hash("Agent123!"),
                role=ROLE_AGENT,
                employer_id=employer.id,
            )
            db.session.add(agent)
            db.session.flush()
            db.session.add(AgentEmployer(employer_id=employer.id, agent_user_id=agent.id))

        db.session.commit()

        return jsonify({"message": "Seeded demo candidates", "count": len(seed_candidates)}), 201

    return app


def ensure_default_super_admin():
    existing = User.query.filter_by(role=ROLE_SUPER_ADMIN).first()
    if existing:
        return

    email = os.getenv("DEFAULT_SUPERADMIN_EMAIL", "superadmin@system.local").strip().lower()
    password = os.getenv("DEFAULT_SUPERADMIN_PASSWORD", "SuperAdmin123!")
    full_name = os.getenv("DEFAULT_SUPERADMIN_NAME", "Platform Super Admin").strip()
    user = User(
        full_name=full_name,
        email=email,
        password_hash=generate_password_hash(password),
        role=ROLE_SUPER_ADMIN,
    )
    db.session.add(user)
    db.session.commit()


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port, debug=True)
