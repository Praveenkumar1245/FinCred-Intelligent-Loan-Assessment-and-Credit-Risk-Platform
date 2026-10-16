import pytest
from datetime import date
from app import create_app
from models import db, User, Applicant, BankRequirement, LoanApplication, FinancialAssessment, UploadedDocument
from services.financial_calculator import FinancialCalculator
from services.eligibility_engine import EligibilityEngine

@pytest.fixture
def app_instance():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"
    })
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

def test_backlog_policy_education_vs_personal(app_instance):
    # Setup user and applicant with 2 backlogs
    user = User(username="test_student", email="student@test.com", full_name="Student Test", role="applicant")
    user.set_password("Pass@123")
    db.session.add(user)
    db.session.flush()

    applicant = Applicant(
        user_id=user.id,
        full_name="Student Test",
        email="student@test.com",
        date_of_birth=date(1999, 1, 1),
        backlog_count=2
    )
    db.session.add(applicant)
    db.session.flush()

    # Policy 1: Personal Loan (Backlog check disabled)
    policy_personal = BankRequirement(
        bank_name="Test Bank",
        loan_type="Personal Loan",
        policy_code="TEST-PL",
        policy_version=1,
        min_monthly_income=20000.0,
        backlog_policy_enabled=False,
        max_allowed_backlogs=0
    )
    policy_personal.required_documents_list = []

    # Policy 2: Education Loan (Backlog check enabled, max 1 backlog)
    policy_edu = BankRequirement(
        bank_name="Test Bank",
        loan_type="Education Loan",
        policy_code="TEST-EDU",
        policy_version=1,
        min_monthly_income=20000.0,
        backlog_policy_enabled=True,
        max_allowed_backlogs=1
    )
    policy_edu.required_documents_list = []

    db.session.add_all([policy_personal, policy_edu])
    db.session.flush()

    # Application 1: Under Personal Loan
    app_pl = LoanApplication(
        application_number="TEST-PL-001",
        applicant_id=applicant.id,
        bank_requirement_id=policy_personal.id,
        loan_amount_requested=100000.0,
        loan_tenure_months=24,
        company_name="Test Co",
        declared_monthly_salary=40000.0,
        credit_score=750
    )
    db.session.add(app_pl)
    db.session.flush()

    assess_pl = FinancialCalculator.compute_assessment(app_pl)
    outcome_pl, checks_pl = EligibilityEngine.run_assessment(app_pl, assess_pl)
    
    # In personal loan, backlog check should be NOT_APPLICABLE and NOT cause failure
    backlog_check_pl = next(c for c in checks_pl if c.requirement_key == 'backlog_check')
    assert backlog_check_pl.status == 'NOT_APPLICABLE'
    assert "does not evaluate academic backlogs" in backlog_check_pl.bank_rule_text

    # Application 2: Under Education Loan
    app_edu = LoanApplication(
        application_number="TEST-EDU-002",
        applicant_id=applicant.id,
        bank_requirement_id=policy_edu.id,
        loan_amount_requested=100000.0,
        loan_tenure_months=24,
        company_name="Test Co",
        declared_monthly_salary=40000.0,
        credit_score=750
    )
    db.session.add(app_edu)
    db.session.flush()

    assess_edu = FinancialCalculator.compute_assessment(app_edu)
    outcome_edu, checks_edu = EligibilityEngine.run_assessment(app_edu, assess_edu)

    # In education loan, 2 backlogs > 1 max allowed -> FAIL
    backlog_check_edu = next(c for c in checks_edu if c.requirement_key == 'backlog_check')
    assert backlog_check_edu.status == 'FAIL'
    assert outcome_edu == 'does_not_meet'
