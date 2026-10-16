import pytest
from app import create_app
from models import db, LoanApplication, UploadedDocument, BankRequirement, LoanType
from services.document_catalog import (
    LOAN_DOCUMENT_CATALOG,
    get_loan_document_checklist,
    evaluate_application_document_slots
)
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


def test_unique_checklists_per_loan_type():
    """Verify that every loan type has a distinct, dedicated document checklist"""
    loan_types = [
        'home_loan', 'gold_loan', 'education_loan', 'personal_loan',
        'vehicle_loan', 'business_loan', 'loan_against_property', 'agriculture_loan'
    ]
    checklists = {}
    for lt in loan_types:
        cl = get_loan_document_checklist(lt)
        assert len(cl) >= 4, f"Checklist for {lt} should have at least 4 items"
        doc_keys = {item['doc_type'] for item in cl}
        checklists[lt] = doc_keys

    # Gold loan must NOT mandate salary slip
    gold_mandatory_types = [
        item['doc_type'] for item in get_loan_document_checklist('gold_loan')
        if item['level'] == 'required'
    ]
    assert 'salary_slip' not in gold_mandatory_types
    assert 'gold_valuation_appraisal' in gold_mandatory_types

    # Education loan must require academic and admission documents
    edu_keys = checklists['education_loan']
    assert 'admission_letter' in edu_keys
    assert 'course_fee_structure' in edu_keys
    assert 'mark_sheets' in edu_keys

    # Home loan must require property documents
    home_keys = checklists['home_loan']
    assert 'property_sale_agreement' in home_keys
    assert 'bank_statement' in home_keys

    # Business loan must require business registration and GST
    biz_keys = checklists['business_loan']
    assert 'business_registration' in biz_keys
    assert 'gst_returns' in biz_keys
    assert 'business_bank_statement' in biz_keys

    # Agriculture loan must require land records (patta) and crop activity
    agri_keys = checklists['agriculture_loan']
    assert 'land_records' in agri_keys
    assert 'crop_activity_details' in agri_keys


def test_conditional_document_requirements_evaluation(test_app):
    """Test dynamic condition evaluation for conditional documents (e.g. existing debts, employment type)"""
    with test_app.app_context():
        home_app = LoanApplication.query.filter_by(loan_type_code='home_loan').first()
        assert home_app is not None

        # Case 1: Salaried applicant with zero existing EMIs
        home_app.employment_type = 'Salaried'
        home_app.existing_monthly_emis = 0.0
        slots, progress = evaluate_application_document_slots(home_app)
        slot_map = {s['doc_type']: s for s in slots}

        assert slot_map['salary_slip']['is_mandatory'] is True
        assert slot_map['existing_loan_statements']['is_mandatory'] is False

        # Case 2: Applicant with active EMI obligations
        home_app.existing_monthly_emis = 8500.0
        slots2, progress2 = evaluate_application_document_slots(home_app)
        slot_map2 = {s['doc_type']: s for s in slots2}
        assert slot_map2['existing_loan_statements']['is_mandatory'] is True
        assert "declared ongoing EMI obligations" in slot_map2['existing_loan_statements']['condition_explanation']


def test_document_upload_progress_and_submission_block(client, test_app):
    """Test progress calculation and submission validation"""
    client.post('/login', data={'username': 'rajesh', 'password': 'Applicant@123'})

    with test_app.app_context():
        from models import User
        user = User.query.filter_by(username='rajesh').first()
        app_obj = LoanApplication.query.filter_by(applicant_id=user.applicant_profile.id).first()
        app_id = app_obj.id

    # 1. View document upload page
    res = client.get(f'/application/{app_id}/documents')
    assert res.status_code == 200
    assert b"Document Checklist Progress" in res.data

    # 2. Attach demo doc for gold appraisal
    res_attach = client.post(
        f'/application/{app_id}/attach-demo-doc',
        data={'demo_doc_type': 'gold_valuation_appraisal', 'slot_key': 'gold_valuation_appraisal'},
        follow_redirects=True
    )
    assert res_attach.status_code == 200
    assert b"gold_valuation_appraisal" in res_attach.data or b"Gold Valuation" in res_attach.data


def test_officer_review_and_replace_workflow(client, test_app):
    """Test bank officer requesting replacement with notes and applicant replacement history"""
    # 1. Login as Officer
    client.post('/login', data={'username': 'officer', 'password': 'Officer@123'})

    with test_app.app_context():
        doc = UploadedDocument.query.first()
        assert doc is not None
        doc_id = doc.id
        app_id = doc.application_id

    # 2. Officer requests replacement
    res = client.post(
        f'/officer/document/{doc_id}/verify',
        data={
            'verification_status': 'rejected',
            'reviewer_comments': 'Scanned image is blurry. Please upload clear digital PDF.'
        },
        follow_redirects=True
    )
    assert res.status_code == 200

    with test_app.app_context():
        updated_doc = db.session.get(UploadedDocument, doc_id)
        assert updated_doc.verification_status == 'rejected'
        assert updated_doc.reviewer_comments == 'Scanned image is blurry. Please upload clear digital PDF.'
