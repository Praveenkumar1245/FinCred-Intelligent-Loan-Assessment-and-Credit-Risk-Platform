from datetime import datetime
import json
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(30), nullable=False, default='applicant') # 'admin', 'bank_officer', 'applicant'
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)

    # Relationships
    applicant_profile = db.relationship('Applicant', backref='user', uselist=False, cascade='all, delete-orphan')
    uploaded_documents = db.relationship('UploadedDocument', foreign_keys='UploadedDocument.user_id', backref='uploader')
    audit_logs = db.relationship('AuditLog', backref='user')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_admin(self):
        return self.role == 'admin'

    def is_officer(self):
        return self.role in ('bank_officer', 'admin')

    def is_applicant(self):
        return self.role == 'applicant'


class Applicant(db.Model):
    __tablename__ = 'applicants'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(25), nullable=True)
    date_of_birth = db.Column(db.Date, nullable=True)
    pan_number = db.Column(db.String(20), nullable=True)
    current_address = db.Column(db.Text, nullable=True)
    permanent_address = db.Column(db.Text, nullable=True)
    education_level = db.Column(db.String(100), nullable=True) # e.g. "B.Tech / Bachelor's", "Master's"
    backlog_count = db.Column(db.Integer, default=0)
    backlog_details = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    applications = db.relationship('LoanApplication', backref='applicant', cascade='all, delete-orphan')


class LoanType(db.Model):
    __tablename__ = 'loan_types'

    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True) # 'home_loan', 'gold_loan', 'education_loan', etc.
    name = db.Column(db.String(80), nullable=False) # 'Home Loan', 'Gold Loan', etc.
    icon = db.Column(db.String(40), default='bi-cash-coin')
    description = db.Column(db.Text, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    default_ltv_cap = db.Column(db.Float, default=75.0)
    default_interest_rate = db.Column(db.Float, default=10.5)
    required_documents_json = db.Column(db.Text, default='["id_proof"]')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bank_requirements = db.relationship('BankRequirement', backref='loan_type_rel', lazy=True)
    applications = db.relationship('LoanApplication', backref='loan_type_rel', lazy=True)

    @property
    def required_documents_list(self):
        try:
            return json.loads(self.required_documents_json or '[]')
        except Exception:
            return ['id_proof']

    @required_documents_list.setter
    def required_documents_list(self, doc_list):
        self.required_documents_json = json.dumps(doc_list)


class BankRequirement(db.Model):
    __tablename__ = 'bank_requirements'

    id = db.Column(db.Integer, primary_key=True)
    bank_name = db.Column(db.String(120), nullable=False)
    loan_type_id = db.Column(db.Integer, db.ForeignKey('loan_types.id'), nullable=True)
    loan_type_code = db.Column(db.String(50), default='personal_loan', index=True)
    loan_type = db.Column(db.String(80), nullable=False) # Display name
    policy_code = db.Column(db.String(50), nullable=False) # e.g. "APEX-PL-2026"
    policy_version = db.Column(db.Integer, default=1)
    description = db.Column(db.Text, nullable=True)
    
    # General Configurable limits
    min_age = db.Column(db.Integer, default=21)
    max_age = db.Column(db.Integer, default=65)
    min_monthly_income = db.Column(db.Float, default=25000.0) # In INR
    min_employment_months = db.Column(db.Integer, default=12) # Current or total
    max_dti_ratio = db.Column(db.Float, default=50.0) # Percentage (e.g. 50%)
    min_credit_score = db.Column(db.Integer, default=680)
    max_loan_amount = db.Column(db.Float, default=1500000.0)
    max_loan_tenure_months = db.Column(db.Integer, default=60)
    interest_rate_pct = db.Column(db.Float, default=10.5)
    
    # Loan-Specific Configurable Parameters
    max_ltv_ratio = db.Column(db.Float, default=75.0) # For Gold (75%), Home (80%), LAP (60%), Vehicle (85%)
    min_down_payment_pct = db.Column(db.Float, default=15.0) # Vehicle / Home loan
    min_business_vintage_months = db.Column(db.Integer, default=24) # Business Loan
    min_annual_turnover = db.Column(db.Float, default=2000000.0) # Business Loan
    min_land_acres = db.Column(db.Float, default=2.0) # Agriculture Loan
    scale_of_finance_per_acre = db.Column(db.Float, default=50000.0) # Agriculture Loan
    gold_price_per_gram_22k = db.Column(db.Float, default=6800.0) # Gold Loan benchmarks
    gold_price_per_gram_24k = db.Column(db.Float, default=7400.0)
    gold_price_per_gram_18k = db.Column(db.Float, default=5500.0)

    # Backlog rule (specific to education/policy loans)
    backlog_policy_enabled = db.Column(db.Boolean, default=False)
    max_allowed_backlogs = db.Column(db.Integer, default=0)
    backlog_policy_note = db.Column(db.Text, nullable=True)

    # Required documents stored as JSON string
    required_documents_json = db.Column(db.Text, default='["salary_slip", "bank_statement", "id_proof"]')
    
    is_active = db.Column(db.Boolean, default=True)
    is_sample_policy = db.Column(db.Boolean, default=True) # Labels sample demo policies
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def min_monthly_salary(self):
        return self.min_monthly_income or 0.0

    @property
    def required_documents_list(self):
        try:
            return json.loads(self.required_documents_json or '[]')
        except Exception:
            return ['salary_slip', 'bank_statement', 'id_proof']

    @required_documents_list.setter
    def required_documents_list(self, doc_list):
        self.required_documents_json = json.dumps(doc_list)


class LoanApplication(db.Model):
    __tablename__ = 'loan_applications'

    id = db.Column(db.Integer, primary_key=True)
    application_number = db.Column(db.String(40), unique=True, nullable=False, index=True)
    applicant_id = db.Column(db.Integer, db.ForeignKey('applicants.id', ondelete='CASCADE'), nullable=False)
    bank_requirement_id = db.Column(db.Integer, db.ForeignKey('bank_requirements.id'), nullable=False)
    loan_type_id = db.Column(db.Integer, db.ForeignKey('loan_types.id', ondelete='SET NULL'), nullable=True)
    loan_type_code = db.Column(db.String(50), default='personal_loan', index=True)
    policy_version_used = db.Column(db.Integer, default=1)
    
    # Loan details
    loan_amount_requested = db.Column(db.Float, nullable=False)
    loan_tenure_months = db.Column(db.Integer, nullable=False)
    loan_purpose = db.Column(db.String(200), nullable=True)
    
    # Declared Financials
    declared_monthly_salary = db.Column(db.Float, nullable=False, default=0.0)
    declared_previous_salary = db.Column(db.Float, nullable=True)
    salary_increase_date = db.Column(db.Date, nullable=True)
    existing_monthly_emis = db.Column(db.Float, default=0.0)
    credit_score = db.Column(db.Integer, nullable=True)
    
    # Employment / Business info
    company_name = db.Column(db.String(150), nullable=True)
    designation = db.Column(db.String(100), nullable=True)
    employment_type = db.Column(db.String(50), default='Salaried') # Salaried, Self-employed, Business, Farmer
    experience_months = db.Column(db.Integer, default=12)

    # Loan-Specific Applicant Details (Stored as JSON)
    loan_specific_data_json = db.Column(db.Text, default='{}')

    # Status & Workflow
    # 'draft', 'submitted', 'pending_verification', 'manual_review', 'meets_requirements', 'does_not_meet'
    status = db.Column(db.String(40), default='submitted', index=True)
    officer_decision = db.Column(db.String(40), default='pending') # 'approved', 'rejected', 'more_info_needed', 'pending'
    decision_reason = db.Column(db.Text, nullable=True)
    decision_date = db.Column(db.DateTime, nullable=True)
    assigned_officer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bank_requirement = db.relationship('BankRequirement', backref='applications')
    assigned_officer = db.relationship('User', foreign_keys=[assigned_officer_id])
    documents = db.relationship('UploadedDocument', backref='application', cascade='all, delete-orphan')
    extracted_data = db.relationship('ExtractedDocumentData', backref='application', cascade='all, delete-orphan')
    financial_assessment = db.relationship('FinancialAssessment', backref='application', uselist=False, cascade='all, delete-orphan')
    requirement_checks = db.relationship('RequirementCheckResult', backref='application', cascade='all, delete-orphan', order_by='RequirementCheckResult.order_index')
    review_notes = db.relationship('ReviewNote', backref='application', cascade='all, delete-orphan', order_by='ReviewNote.created_at.desc()')
    salary_records = db.relationship('SalaryHistory', backref='application', cascade='all, delete-orphan')

    @property
    def loan_specific_data(self):
        try:
            return json.loads(self.loan_specific_data_json or '{}')
        except Exception:
            return {}

    @loan_specific_data.setter
    def loan_specific_data(self, data_dict):
        self.loan_specific_data_json = json.dumps(data_dict or {})


class UploadedDocument(db.Model):
    __tablename__ = 'uploaded_documents'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('loan_applications.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Document categories
    document_type = db.Column(db.String(60), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, default=0) # Bytes
    file_type = db.Column(db.String(20), nullable=False) # 'pdf', 'jpg', 'png'
    
    # Status: 'pending', 'verified', 'discrepancy_detected', 'rejected', 'unreadable'
    verification_status = db.Column(db.String(40), default='pending')
    verification_notes = db.Column(db.Text, nullable=True)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    verified_at = db.Column(db.DateTime, nullable=True)
    verified_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)

    verified_by = db.relationship('User', foreign_keys=[verified_by_id])
    extracted_record = db.relationship('ExtractedDocumentData', backref='source_document', uselist=False, cascade='all, delete-orphan')


class ExtractedDocumentData(db.Model):
    __tablename__ = 'extracted_document_data'

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey('uploaded_documents.id', ondelete='CASCADE'), nullable=False)
    application_id = db.Column(db.Integer, db.ForeignKey('loan_applications.id', ondelete='CASCADE'), nullable=False)
    
    extraction_method = db.Column(db.String(40), default='pymupdf') # 'pymupdf', 'tesseract_ocr', 'manual_entry'
    raw_text = db.Column(db.Text, nullable=True)
    
    # Structured extracted attributes
    applicant_name_extracted = db.Column(db.String(150), nullable=True)
    company_name_extracted = db.Column(db.String(150), nullable=True)
    salary_amount_extracted = db.Column(db.Float, nullable=True)
    salary_month_extracted = db.Column(db.String(50), nullable=True)
    deductions_extracted = db.Column(db.Float, nullable=True)
    bank_credits_extracted = db.Column(db.Float, nullable=True)
    document_date_extracted = db.Column(db.String(50), nullable=True)
    
    # Confidence and discrepancies
    confidence_score = db.Column(db.Float, default=0.0) # 0 to 100%
    discrepancy_detected = db.Column(db.Boolean, default=False)
    discrepancy_details = db.Column(db.Text, nullable=True)
    
    # Officer Manual Override / Correction
    is_overridden_by_officer = db.Column(db.Boolean, default=False)
    officer_override_notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class FinancialAssessment(db.Model):
    __tablename__ = 'financial_assessments'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('loan_applications.id', ondelete='CASCADE'), nullable=False, unique=True)
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Income metrics
    current_verified_income = db.Column(db.Float, default=0.0)
    declared_income = db.Column(db.Float, default=0.0)
    income_verification_status = db.Column(db.String(40), default='unverified') # 'fully_verified', 'partially_verified', 'unverified'
    
    # Salary progression
    previous_salary = db.Column(db.Float, nullable=True)
    salary_increase_amount = db.Column(db.Float, default=0.0)
    salary_increase_pct = db.Column(db.Float, default=0.0)
    salary_increase_supported = db.Column(db.Boolean, default=False) # Backed by document
    average_verified_salary = db.Column(db.Float, default=0.0)
    
    # Obligations & Debt-to-income
    existing_monthly_emis = db.Column(db.Float, default=0.0)
    estimated_new_emi = db.Column(db.Float, default=0.0)
    projected_total_emi = db.Column(db.Float, default=0.0)
    current_dti_ratio = db.Column(db.Float, default=0.0)
    projected_dti_ratio = db.Column(db.Float, default=0.0)
    
    # Disposable income
    living_expense_estimate = db.Column(db.Float, default=0.0)
    estimated_disposable_income = db.Column(db.Float, default=0.0)

    # Loan-Specific Metrics & Collateral Valuation
    collateral_valuation = db.Column(db.Float, default=0.0) # Gold value, Property value, Vehicle price
    calculated_ltv_ratio = db.Column(db.Float, default=0.0) # Loan-to-Value percentage
    down_payment_amount = db.Column(db.Float, default=0.0)
    down_payment_pct = db.Column(db.Float, default=0.0)
    business_turnover_ratio = db.Column(db.Float, default=0.0)
    loan_specific_metrics_json = db.Column(db.Text, default='{}')

    # ML Scorer values
    ml_risk_score = db.Column(db.Float, default=0.0) # 0 to 100
    ml_risk_tier = db.Column(db.String(20), default='Moderate') # 'Low', 'Moderate', 'High'
    ml_approval_probability = db.Column(db.Float, default=0.0) # %
    ml_risk_factors_json = db.Column(db.Text, default='[]')

    @property
    def proposed_loan_emi(self):
        return self.estimated_new_emi or 0.0

    @property
    def total_projected_obligations(self):
        return self.projected_total_emi or ((self.existing_monthly_emis or 0.0) + (self.estimated_new_emi or 0.0))

    @property
    def ml_risk_factors(self):
        try:
            return json.loads(self.ml_risk_factors_json or '[]')
        except Exception:
            return []

    @property
    def loan_specific_metrics(self):
        try:
            return json.loads(self.loan_specific_metrics_json or '{}')
        except Exception:
            return {}

    @loan_specific_metrics.setter
    def loan_specific_metrics(self, metrics_dict):
        self.loan_specific_metrics_json = json.dumps(metrics_dict or {})


class RequirementCheckResult(db.Model):
    __tablename__ = 'requirement_check_results'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('loan_applications.id', ondelete='CASCADE'), nullable=False)
    requirement_key = db.Column(db.String(60), nullable=False)
    requirement_label = db.Column(db.String(120), nullable=False)
    bank_rule_text = db.Column(db.Text, nullable=False)
    applicant_actual_value = db.Column(db.String(200), nullable=False)
    
    # 'PASS', 'FAIL', 'PENDING_VERIFICATION', 'MANUAL_REVIEW', 'NOT_APPLICABLE'
    status = db.Column(db.String(40), nullable=False)
    simple_explanation = db.Column(db.Text, nullable=False)
    supporting_document_info = db.Column(db.String(255), nullable=True)
    next_steps = db.Column(db.Text, nullable=False)
    order_index = db.Column(db.Integer, default=0)


class SalaryHistory(db.Model):
    __tablename__ = 'salary_histories'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('loan_applications.id', ondelete='CASCADE'), nullable=False)
    month_year = db.Column(db.String(30), nullable=False) # e.g. "Aug 2024"
    gross_salary = db.Column(db.Float, default=0.0)
    net_salary = db.Column(db.Float, default=0.0)
    deductions = db.Column(db.Float, default=0.0)
    employer_name = db.Column(db.String(150), nullable=True)
    bank_credit_amount = db.Column(db.Float, nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    source_document_id = db.Column(db.Integer, db.ForeignKey('uploaded_documents.id', ondelete='SET NULL'), nullable=True)


class ReviewNote(db.Model):
    __tablename__ = 'review_notes'

    id = db.Column(db.Integer, primary_key=True)
    application_id = db.Column(db.Integer, db.ForeignKey('loan_applications.id', ondelete='CASCADE'), nullable=False)
    officer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    note_type = db.Column(db.String(40), default='general') # 'general', 'verification_query', 'discrepancy', 'decision'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    officer = db.relationship('User', foreign_keys=[officer_id])


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    user_role = db.Column(db.String(30), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    application_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
