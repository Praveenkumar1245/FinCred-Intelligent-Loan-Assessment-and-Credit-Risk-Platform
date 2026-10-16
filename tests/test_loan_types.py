import uuid
import pytest
from app import create_app
from models import db, LoanType, BankRequirement, LoanApplication, FinancialAssessment, RequirementCheckResult, UploadedDocument
from services.financial_calculator import FinancialCalculator
from services.eligibility_engine import EligibilityEngine

@pytest.fixture
def test_app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        yield app

@pytest.fixture
def client(test_app):
    return test_app.test_client()


def test_eight_master_loan_types_seeded(test_app):
    """Verify all 8 mandatory loan categories are configured"""
    with test_app.app_context():
        types = LoanType.query.all()
        assert len(types) >= 8
        codes = {t.code for t in types}
        expected = {
            'home_loan', 'gold_loan', 'education_loan', 'personal_loan',
            'vehicle_loan', 'business_loan', 'loan_against_property', 'agriculture_loan'
        }
        assert expected.issubset(codes)


def test_gold_loan_collateral_math_and_underwriting(test_app):
    """Gold loan must calculate gold valuation accurately and enforce statutory 75% LTV cap"""
    with test_app.app_context():
        policy = BankRequirement.query.filter_by(loan_type_code='gold_loan').first()
        gold_lt = LoanType.query.filter_by(code='gold_loan').first()

        app_num = f"FC-TEST-GL-{uuid.uuid4().hex[:6]}"
        app_record = LoanApplication(
            application_number=app_num,
            applicant_id=1,
            bank_requirement_id=policy.id,
            loan_type_id=gold_lt.id,
            loan_type_code="gold_loan",
            policy_version_used=1,
            loan_amount_requested=200000.0,
            loan_tenure_months=12,
            company_name="Self Employed",
            declared_monthly_salary=30000.0,
            existing_monthly_emis=0.0,
            credit_score=720,
            status='submitted'
        )
        # 45 grams of 22K gold @ ₹6,800/g = ₹306,000. 75% LTV cap = ₹229,500.
        app_record.loan_specific_data = {
            "gold_weight_grams": 45.0,
            "gold_purity_karats": "22K",
            "gold_rate_per_gram": 6800.0,
            "estimated_gold_value": 306000.0,
            "gold_item_type": "Jewelry"
        }
        db.session.add(app_record)
        db.session.commit()

        assessment = FinancialCalculator.compute_assessment(app_record)
        assert assessment.collateral_valuation == 306000.0
        # 200,000 / 306,000 = 65.36% LTV
        assert assessment.calculated_ltv_ratio == 65.36

        status, checks = EligibilityEngine.run_assessment(app_record, assessment)
        ltv_check = next(c for c in checks if c.requirement_key == 'gold_ltv')
        # Requested 200k on 306k gold is below 75% LTV -> PASS
        assert ltv_check.status == 'PASS'


def test_gold_loan_exceeding_75_pct_ltv_fails(test_app):
    """Gold loan exceeding 75% LTV cap must fail the LTV check"""
    with test_app.app_context():
        policy = BankRequirement.query.filter_by(loan_type_code='gold_loan').first()
        gold_lt = LoanType.query.filter_by(code='gold_loan').first()

        app_num = f"FC-TEST-GL-{uuid.uuid4().hex[:6]}"
        app_record = LoanApplication(
            application_number=app_num,
            applicant_id=1,
            bank_requirement_id=policy.id,
            loan_type_id=gold_lt.id,
            loan_type_code="gold_loan",
            policy_version_used=1,
            loan_amount_requested=250000.0, # Exceeds 75% of 306,000 (which is 229,500)
            loan_tenure_months=12,
            company_name="Self Employed",
            declared_monthly_salary=30000.0,
            existing_monthly_emis=0.0,
            status='submitted'
        )
        app_record.loan_specific_data = {
            "gold_weight_grams": 45.0,
            "gold_purity_karats": "22K",
            "gold_rate_per_gram": 6800.0,
            "estimated_gold_value": 306000.0
        }
        db.session.add(app_record)
        db.session.commit()

        assessment = FinancialCalculator.compute_assessment(app_record)
        # 250,000 / 306,000 = 81.7% LTV
        assert assessment.calculated_ltv_ratio == 81.7

        status, checks = EligibilityEngine.run_assessment(app_record, assessment)
        ltv_check = next(c for c in checks if c.requirement_key == 'gold_ltv')
        assert ltv_check.status == 'FAIL'
        assert "exceeds" in ltv_check.simple_explanation.lower()


def test_business_loan_vintage_and_turnover_underwriting(test_app):
    """Business loan must verify operational vintage and annual turnover"""
    with test_app.app_context():
        policy = BankRequirement.query.filter_by(loan_type_code='business_loan').first()
        biz_lt = LoanType.query.filter_by(code='business_loan').first()

        app_num = f"FC-TEST-BL-{uuid.uuid4().hex[:6]}"
        app_record = LoanApplication(
            application_number=app_num,
            applicant_id=1,
            bank_requirement_id=policy.id,
            loan_type_id=biz_lt.id,
            loan_type_code="business_loan",
            policy_version_used=1,
            loan_amount_requested=1000000.0,
            loan_tenure_months=36,
            company_name="Apex Logistics Ltd",
            declared_monthly_salary=80000.0,
            status='submitted'
        )
        app_record.loan_specific_data = {
            "business_vintage_months": 36, # >= 24 required
            "annual_turnover": 5000000.0,   # >= 2,000,000 required
            "annual_net_profit": 600000.0
        }
        db.session.add(app_record)
        db.session.commit()

        assessment = FinancialCalculator.compute_assessment(app_record)
        assert assessment.business_turnover_ratio == 20.0 # 1,000,000 / 5,000,000 = 20%

        status, checks = EligibilityEngine.run_assessment(app_record, assessment)
        vintage_checks = [c for c in checks if 'Vintage' in c.requirement_label]
        turnover_checks = [c for c in checks if 'Turnover' in c.requirement_label]

        assert len(vintage_checks) == 1
        assert vintage_checks[0].status == 'PASS'
        assert len(turnover_checks) == 1
        assert turnover_checks[0].status == 'PASS'


def test_loan_selection_and_dashboard_filters(client):
    """Test HTTP endpoints for loan type selection and dashboard filtering"""
    # 1. Login as applicant
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['email'] = 'rajesh.sharma@example.com'
        sess['role'] = 'applicant'
        sess['full_name'] = 'Rajesh Sharma'

    # 2. Access select loan type screen
    res = client.get('/select-loan-type')
    assert res.status_code == 200
    assert b"Home Loan" in res.data
    assert b"Gold Loan" in res.data
    assert b"Education Loan" in res.data
    assert b"Business Loan" in res.data
    assert b"Agriculture Loan" in res.data

    # 3. Access apply with specific loan type
    res_apply = client.get('/apply?loan_type=gold_loan')
    assert res_apply.status_code == 200
    assert b"Gold Weight (Grams)" in res_apply.data
    assert b"Gold Purity (Karats)" in res_apply.data

    # 4. Access apply for Home Loan
    res_home = client.get('/apply?loan_type=home_loan')
    assert res_home.status_code == 200
    assert b"Property Purchase / Agreement Value" in res_home.data
    assert b"Down Payment" in res_home.data

    # 5. Dashboard filtering
    res_dash = client.get('/dashboard?loan_type=gold_loan')
    assert res_dash.status_code == 200


def test_property_docs_upload_and_verification(test_app, client):
    """Test property documents upload option, extraction, and underwriting compliance"""
    # 1. Login as applicant
    client.post('/login', data={'username': 'rajesh', 'password': 'Applicant@123'})

    with test_app.app_context():
        # Find Rajesh's Home Loan application (seeded app #2)
        home_app = LoanApplication.query.filter_by(loan_type_code='home_loan').first()
        assert home_app is not None
        app_id = home_app.id

    # 2. Check document upload page contains property_docs in dropdown
    res = client.get(f'/application/{app_id}/documents')
    assert res.status_code == 200
    assert b'value="property_docs"' in res.data
    assert b"Property Documents (Title Deed / Sale Agreement / Tax Receipt)" in res.data
    assert b"Attach Demo Property Docs" in res.data

    # 3. Attach synthetic property doc
    res_attach = client.post(f'/application/{app_id}/attach-demo-doc', data={'demo_doc_type': 'property_docs'}, follow_redirects=True)
    assert res_attach.status_code == 200
    assert b"Property Documents" in res_attach.data

    with test_app.app_context():
        # Verify uploaded document was saved
        prop_doc = UploadedDocument.query.filter_by(application_id=app_id, document_type='property_docs').first()
        assert prop_doc is not None
        assert prop_doc.extracted_record is not None
        assert prop_doc.extracted_record.applicant_name_extracted == "Rajesh Sharma"
        assert prop_doc.extracted_record.salary_amount_extracted == 5500000.0 # Property consideration

        # Verify eligibility engine marks mandatory property documents as uploaded
        active_home_app = db.session.get(LoanApplication, app_id)
        assessment = FinancialCalculator.compute_assessment(active_home_app)
        status, checks = EligibilityEngine.run_assessment(active_home_app, assessment)
        doc_check = next(c for c in checks if c.requirement_key == 'mandatory_docs')
        # Check that property_docs is not in missing list
        assert "property" not in doc_check.simple_explanation.lower()
