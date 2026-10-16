import os
from datetime import date, datetime
from pathlib import Path
from models import (
    db, User, Applicant, LoanType, BankRequirement, LoanApplication,
    UploadedDocument, ExtractedDocumentData, SalaryHistory,
    AuditLog
)
from services.document_processor import DocumentProcessor
from services.financial_calculator import FinancialCalculator
from services.eligibility_engine import EligibilityEngine
from services.ml_scorer import MLScorer
from services.sample_generator import SampleDocGenerator

def init_db(app):
    """Initialize database tables and seed baseline data"""
    with app.app_context():
        # Ensure instance and upload directories exist
        instance_dir = Path(app.config.get('SQLALCHEMY_DATABASE_URI').replace('sqlite:///', '')).parent
        instance_dir.mkdir(parents=True, exist_ok=True)
        
        upload_dir = Path(app.config['UPLOAD_FOLDER'])
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Ensure sample documents exist
        sample_dir = upload_dir / "sample_docs"
        sample_files = SampleDocGenerator.ensure_sample_documents(sample_dir)

        db.create_all()

        # Seed initial demo data if empty
        if not User.query.first():
            seed_demo_data(sample_files)
        else:
            # Ensure LoanType master table is populated if missing
            ensure_loan_types()


def ensure_loan_types():
    """Ensure all 8 supported loan types exist in DB"""
    existing_codes = {lt.code for lt in LoanType.query.all()}
    all_loan_types = get_standard_loan_types()
    for lt_data in all_loan_types:
        if lt_data['code'] not in existing_codes:
            lt = LoanType(
                code=lt_data['code'],
                name=lt_data['name'],
                icon=lt_data['icon'],
                description=lt_data['description'],
                default_ltv_cap=lt_data['default_ltv_cap'],
                default_interest_rate=lt_data['default_interest_rate'],
                is_active=True
            )
            lt.required_documents_list = lt_data['required_docs']
            db.session.add(lt)
    db.session.commit()


def get_standard_loan_types():
    return [
        {
            "code": "home_loan",
            "name": "Home Loan",
            "icon": "bi-house-heart",
            "description": "For purchasing, constructing, or renovating a house.",
            "default_ltv_cap": 80.0,
            "default_interest_rate": 8.5,
            "required_docs": ["salary_slip", "bank_statement", "id_proof", "property_docs", "tax_doc"]
        },
        {
            "code": "gold_loan",
            "name": "Gold Loan",
            "icon": "bi-gem",
            "description": "For borrowing against pledged gold jewelry or bullion.",
            "default_ltv_cap": 75.0,
            "default_interest_rate": 9.2,
            "required_docs": ["id_proof", "gold_ownership_declaration", "bank_statement"]
        },
        {
            "code": "education_loan",
            "name": "Education Loan",
            "icon": "bi-mortarboard",
            "description": "For tuition fees, educational expenses, and higher studies.",
            "default_ltv_cap": 100.0,
            "default_interest_rate": 9.5,
            "required_docs": ["id_proof", "education_cert", "admission_letter", "bank_statement"]
        },
        {
            "code": "personal_loan",
            "name": "Personal Loan",
            "icon": "bi-person-badge",
            "description": "For personal expenses without a specific asset as collateral, subject to lender rules.",
            "default_ltv_cap": 0.0,
            "default_interest_rate": 10.5,
            "required_docs": ["salary_slip", "bank_statement", "id_proof"]
        },
        {
            "code": "vehicle_loan",
            "name": "Vehicle Loan",
            "icon": "bi-car-front",
            "description": "For purchasing a car, motorcycle, or other eligible vehicle.",
            "default_ltv_cap": 85.0,
            "default_interest_rate": 8.9,
            "required_docs": ["salary_slip", "bank_statement", "id_proof", "vehicle_quotation"]
        },
        {
            "code": "business_loan",
            "name": "Business Loan",
            "icon": "bi-briefcase",
            "description": "For business expenses, expansion, or working capital.",
            "default_ltv_cap": 0.0,
            "default_interest_rate": 11.5,
            "required_docs": ["business_pan", "gst_returns", "bank_statement", "tax_doc", "id_proof"]
        },
        {
            "code": "loan_against_property",
            "name": "Loan Against Property",
            "icon": "bi-building",
            "description": "For borrowing against eligible residential or commercial property.",
            "default_ltv_cap": 60.0,
            "default_interest_rate": 9.8,
            "required_docs": ["property_docs", "salary_slip", "bank_statement", "id_proof", "tax_doc"]
        },
        {
            "code": "agriculture_loan",
            "name": "Agriculture Loan",
            "icon": "bi-flower1",
            "description": "For eligible farming, cultivation, and agricultural needs.",
            "default_ltv_cap": 70.0,
            "default_interest_rate": 7.0,
            "required_docs": ["land_records_patta", "id_proof", "bank_statement", "crop_declaration"]
        }
    ]


def seed_demo_data(sample_files):
    """Seed initial sample users, bank policies, demo applications, and documents"""
    print("[FinCred AI] Seeding database with initial users, 8 loan types, and bank policies...")

    # 1. Users
    admin_user = User(
        username="admin",
        email="admin@fincred.ai",
        full_name="System Administrator",
        role="admin"
    )
    admin_user.set_password("Admin@123")

    officer_user = User(
        username="officer",
        email="officer.verma@fincred.ai",
        full_name="Pooja Verma (Chief Credit Officer)",
        role="bank_officer"
    )
    officer_user.set_password("Officer@123")

    applicant_user = User(
        username="rajesh",
        email="rajesh.sharma@example.com",
        full_name="Rajesh Sharma",
        role="applicant"
    )
    applicant_user.set_password("Applicant@123")

    priya_user = User(
        username="priya",
        email="priya.nair@example.com",
        full_name="Priya Nair",
        role="applicant"
    )
    priya_user.set_password("Applicant@123")

    vikram_user = User(
        username="vikram",
        email="vikram.patel@example.com",
        full_name="Vikram Patel",
        role="applicant"
    )
    vikram_user.set_password("Applicant@123")

    db.session.add_all([admin_user, officer_user, applicant_user, priya_user, vikram_user])
    db.session.flush()

    # 2. Applicant Profiles
    rajesh_profile = Applicant(
        user_id=applicant_user.id,
        full_name="Rajesh Sharma",
        email="rajesh.sharma@example.com",
        phone="+91 98765 43210",
        date_of_birth=date(1994, 5, 14),
        pan_number="ABCPS1234F",
        current_address="Flat 402, Green Valley Apts, Sector 62, Noida, UP",
        permanent_address="House 12, Civil Lines, Jaipur, Rajasthan",
        education_level="B.Tech (Computer Science)",
        backlog_count=0,
        backlog_details="Nil. Graduated with First Class Honors."
    )

    priya_profile = Applicant(
        user_id=priya_user.id,
        full_name="Priya Nair",
        email="priya.nair@example.com",
        phone="+91 98111 22334",
        date_of_birth=date(1998, 9, 21),
        pan_number="BKRPN9876K",
        current_address="A-12, Indiranagar, Bengaluru, Karnataka",
        permanent_address="TC 4/108, Kowdiar, Thiruvananthapuram, Kerala",
        education_level="B.Sc (Data Analytics) - Final Year",
        backlog_count=2,
        backlog_details="2 active backlogs: Advanced Statistics, Operating Systems."
    )

    vikram_profile = Applicant(
        user_id=vikram_user.id,
        full_name="Vikram Patel",
        email="vikram.patel@example.com",
        phone="+91 97234 56789",
        date_of_birth=date(1988, 3, 10),
        pan_number="ABCVP5678M",
        current_address="14, Shanti Nagar, SG Highway, Ahmedabad, Gujarat",
        permanent_address="14, Shanti Nagar, SG Highway, Ahmedabad, Gujarat",
        education_level="Bachelor of Commerce",
        backlog_count=0,
        backlog_details="None"
    )

    db.session.add_all([rajesh_profile, priya_profile, vikram_profile])
    db.session.flush()

    # 3. Seed Master Loan Types (All 8 Required Categories)
    loan_type_instances = {}
    for lt_data in get_standard_loan_types():
        lt = LoanType(
            code=lt_data['code'],
            name=lt_data['name'],
            icon=lt_data['icon'],
            description=lt_data['description'],
            default_ltv_cap=lt_data['default_ltv_cap'],
            default_interest_rate=lt_data['default_interest_rate'],
            is_active=True
        )
        lt.required_documents_list = lt_data['required_docs']
        db.session.add(lt)
        db.session.flush()
        loan_type_instances[lt_data['code']] = lt

    # 4. Bank Requirements / Policies for All 8 Categories
    policies = []

    # 4.1 Personal Loan
    p_personal = BankRequirement(
        bank_name="Apex National Bank",
        loan_type_id=loan_type_instances['personal_loan'].id,
        loan_type_code="personal_loan",
        loan_type="Personal Loan",
        policy_code="APEX-PL-2026",
        policy_version=1,
        description="Prime Personal Loan for salaried professionals in Tier-1 & Tier-2 corporate firms.",
        min_age=21,
        max_age=58,
        min_monthly_income=30000.0,
        min_employment_months=12,
        max_dti_ratio=50.0,
        min_credit_score=700,
        max_loan_amount=1500000.0,
        max_loan_tenure_months=60,
        interest_rate_pct=10.5,
        backlog_policy_enabled=False,
        max_allowed_backlogs=0,
        backlog_policy_note="Academic backlogs are not evaluated for personal loans.",
        is_sample_policy=True
    )
    p_personal.required_documents_list = ["salary_slip", "bank_statement", "id_proof"]
    policies.append(p_personal)

    # 4.2 Home Loan
    p_home = BankRequirement(
        bank_name="Metro Heritage Bank",
        loan_type_id=loan_type_instances['home_loan'].id,
        loan_type_code="home_loan",
        loan_type="Home Loan",
        policy_code="METRO-HL-2026",
        policy_version=1,
        description="Premium residential mortgage facility with competitive reducing interest rates.",
        min_age=23,
        max_age=65,
        min_monthly_income=45000.0,
        min_employment_months=24,
        max_dti_ratio=55.0,
        min_credit_score=720,
        max_loan_amount=7500000.0,
        max_loan_tenure_months=240,
        interest_rate_pct=8.4,
        max_ltv_ratio=80.0,
        min_down_payment_pct=20.0,
        backlog_policy_enabled=False,
        is_sample_policy=True
    )
    p_home.required_documents_list = ["salary_slip", "bank_statement", "id_proof", "property_docs", "tax_doc"]
    policies.append(p_home)

    # 4.3 Gold Loan
    p_gold = BankRequirement(
        bank_name="Muthoot & Apex Bullion Bank",
        loan_type_id=loan_type_instances['gold_loan'].id,
        loan_type_code="gold_loan",
        loan_type="Gold Loan",
        policy_code="APEX-GL-2026",
        policy_version=1,
        description="Instant liquidity against pledged gold ornaments. Fast verification with minimal income documentation.",
        min_age=18,
        max_age=70,
        min_monthly_income=10000.0, # Nominal baseline
        min_employment_months=0,
        max_dti_ratio=65.0,
        min_credit_score=600,
        max_loan_amount=3500000.0,
        max_loan_tenure_months=24,
        interest_rate_pct=9.2,
        max_ltv_ratio=75.0, # Statutory RBI gold LTV cap
        gold_price_per_gram_22k=6800.0,
        gold_price_per_gram_24k=7400.0,
        gold_price_per_gram_18k=5500.0,
        backlog_policy_enabled=False,
        is_sample_policy=True
    )
    p_gold.required_documents_list = ["id_proof", "gold_ownership_declaration", "bank_statement"]
    policies.append(p_gold)

    # 4.4 Education Loan
    p_edu = BankRequirement(
        bank_name="Horizon Career & Education Bank",
        loan_type_id=loan_type_instances['education_loan'].id,
        loan_type_code="education_loan",
        loan_type="Education Loan",
        policy_code="HORIZON-EDU-2026",
        policy_version=1,
        description="Higher education financing. Strict academic performance and backlog caps apply.",
        min_age=18,
        max_age=32,
        min_monthly_income=20000.0,
        min_employment_months=0,
        max_dti_ratio=60.0,
        min_credit_score=620,
        max_loan_amount=2500000.0,
        max_loan_tenure_months=84,
        interest_rate_pct=9.5,
        backlog_policy_enabled=True,
        max_allowed_backlogs=1,
        backlog_policy_note="Documented academic eligibility: Candidates may have at most 1 active backlog.",
        is_sample_policy=True
    )
    p_edu.required_documents_list = ["id_proof", "education_cert", "admission_letter", "bank_statement"]
    policies.append(p_edu)

    # 4.5 Vehicle Loan
    p_vehicle = BankRequirement(
        bank_name="Apex Wheels Commercial Bank",
        loan_type_id=loan_type_instances['vehicle_loan'].id,
        loan_type_code="vehicle_loan",
        loan_type="Vehicle Loan",
        policy_code="APEX-VL-2026",
        policy_version=1,
        description="Automotive financing for new and certified pre-owned passenger vehicles.",
        min_age=21,
        max_age=60,
        min_monthly_income=25000.0,
        min_employment_months=12,
        max_dti_ratio=50.0,
        min_credit_score=680,
        max_loan_amount=2000000.0,
        max_loan_tenure_months=84,
        interest_rate_pct=8.9,
        max_ltv_ratio=85.0,
        min_down_payment_pct=15.0,
        backlog_policy_enabled=False,
        is_sample_policy=True
    )
    p_vehicle.required_documents_list = ["salary_slip", "bank_statement", "id_proof", "vehicle_quotation"]
    policies.append(p_vehicle)

    # 4.6 Business Loan
    p_biz = BankRequirement(
        bank_name="TrustFin Commercial Bank",
        loan_type_id=loan_type_instances['business_loan'].id,
        loan_type_code="business_loan",
        loan_type="Business Loan",
        policy_code="TRUST-BIZ-2026",
        policy_version=1,
        description="Unsecured business expansion and working capital facility for established enterprises.",
        min_age=25,
        max_age=65,
        min_monthly_income=40000.0,
        min_employment_months=24,
        max_dti_ratio=55.0,
        min_credit_score=700,
        max_loan_amount=5000000.0,
        max_loan_tenure_months=48,
        interest_rate_pct=11.5,
        min_business_vintage_months=24,
        min_annual_turnover=2500000.0, # 25 Lakhs minimum turnover
        backlog_policy_enabled=False,
        is_sample_policy=True
    )
    p_biz.required_documents_list = ["business_pan", "gst_returns", "bank_statement", "tax_doc", "id_proof"]
    policies.append(p_biz)

    # 4.7 Loan Against Property (LAP)
    p_lap = BankRequirement(
        bank_name="Apex Premier Bank",
        loan_type_id=loan_type_instances['loan_against_property'].id,
        loan_type_code="loan_against_property",
        loan_type="Loan Against Property",
        policy_code="APEX-LAP-2026",
        policy_version=1,
        description="High-value secured mortgage against residential or commercial real estate collateral.",
        min_age=23,
        max_age=65,
        min_monthly_income=35000.0,
        min_employment_months=24,
        max_dti_ratio=60.0,
        min_credit_score=680,
        max_loan_amount=10000000.0,
        max_loan_tenure_months=180,
        interest_rate_pct=9.8,
        max_ltv_ratio=60.0, # 60% LTV on property
        backlog_policy_enabled=False,
        is_sample_policy=True
    )
    p_lap.required_documents_list = ["property_docs", "salary_slip", "bank_statement", "id_proof", "tax_doc"]
    policies.append(p_lap)

    # 4.8 Agriculture Loan
    p_agri = BankRequirement(
        bank_name="Kisan Apex Rural Bank",
        loan_type_id=loan_type_instances['agriculture_loan'].id,
        loan_type_code="agriculture_loan",
        loan_type="Agriculture Loan",
        policy_code="KISAN-AGRI-2026",
        policy_version=1,
        description="Crop cultivation and agricultural equipment finance supported by landholding and seasonal yield.",
        min_age=18,
        max_age=70,
        min_monthly_income=15000.0,
        min_employment_months=0,
        max_dti_ratio=55.0,
        min_credit_score=620,
        max_loan_amount=2000000.0,
        max_loan_tenure_months=60,
        interest_rate_pct=7.0,
        min_land_acres=2.0, # Minimum 2 acres
        scale_of_finance_per_acre=50000.0,
        backlog_policy_enabled=False,
        is_sample_policy=True
    )
    p_agri.required_documents_list = ["land_records_patta", "id_proof", "bank_statement", "crop_declaration"]
    policies.append(p_agri)

    db.session.add_all(policies)
    db.session.flush()

    # 5. Prepopulated Demo Applications
    # 5.1 Rajesh Sharma: Personal Loan
    app1 = LoanApplication(
        application_number="FC-2026-00101",
        applicant_id=rajesh_profile.id,
        bank_requirement_id=p_personal.id,
        loan_type_id=loan_type_instances['personal_loan'].id,
        loan_type_code="personal_loan",
        policy_version_used=1,
        loan_amount_requested=500000.0,
        loan_tenure_months=36,
        loan_purpose="Home renovation and furniture purchase",
        declared_monthly_salary=32000.0,
        declared_previous_salary=22000.0,
        salary_increase_date=date(2024, 7, 1),
        existing_monthly_emis=4500.0,
        credit_score=740,
        company_name="Apex Tech Solutions Pvt Ltd",
        designation="Senior Software Engineer",
        employment_type="Salaried",
        experience_months=36,
        status="submitted"
    )
    app1.loan_specific_data = {}
    db.session.add(app1)
    db.session.flush()

    # Attach demo documents for App1
    if sample_files:
        if sample_files.get("salary_slip") and Path(sample_files["salary_slip"]).exists():
            slip_path = sample_files["salary_slip"]
            doc1 = UploadedDocument(
                application_id=app1.id,
                user_id=applicant_user.id,
                document_type="salary_slip",
                original_filename="Sample_Salary_Slip_Aug2024.pdf",
                stored_filename="Sample_Salary_Slip_Aug2024.pdf",
                file_path=str(slip_path),
                file_size=Path(slip_path).stat().st_size,
                file_type="pdf",
                verification_status="verified",
                verification_notes="Verified by automated extraction and officer review."
            )
            db.session.add(doc1)
            db.session.flush()

            raw_txt, method, _, _ = DocumentProcessor.extract_raw_text(str(slip_path))
            fields = DocumentProcessor.extract_structured_fields(raw_txt, "salary_slip")
            ext1 = ExtractedDocumentData(
                document_id=doc1.id,
                application_id=app1.id,
                extraction_method=method,
                raw_text=raw_txt,
                applicant_name_extracted=fields["applicant_name"],
                company_name_extracted=fields["company_name"],
                salary_amount_extracted=fields["salary_amount"],
                salary_month_extracted=fields["salary_month"],
                deductions_extracted=fields["deductions"],
                bank_credits_extracted=fields["bank_credits"],
                document_date_extracted=fields["document_date"],
                confidence_score=fields["confidence_score"]
            )
            db.session.add(ext1)

            srec = SalaryHistory(
                application_id=app1.id,
                month_year="Aug 2024",
                gross_salary=34600.0,
                net_salary=32000.0,
                deductions=2600.0,
                employer_name="Apex Tech Solutions Pvt Ltd",
                bank_credit_amount=32000.0,
                is_verified=True,
                source_document_id=doc1.id
            )
            db.session.add(srec)

        if sample_files.get("bank_statement") and Path(sample_files["bank_statement"]).exists():
            stmt_path = sample_files["bank_statement"]
            doc2 = UploadedDocument(
                application_id=app1.id,
                user_id=applicant_user.id,
                document_type="bank_statement",
                original_filename="Sample_Bank_Statement.pdf",
                stored_filename="Sample_Bank_Statement.pdf",
                file_path=str(stmt_path),
                file_size=Path(stmt_path).stat().st_size,
                file_type="pdf",
                verification_status="verified",
                verification_notes="3 consecutive monthly salary credits verified."
            )
            db.session.add(doc2)
            db.session.flush()

            raw_txt2, method2, _, _ = DocumentProcessor.extract_raw_text(str(stmt_path))
            fields2 = DocumentProcessor.extract_structured_fields(raw_txt2, "bank_statement")
            ext2 = ExtractedDocumentData(
                document_id=doc2.id,
                application_id=app1.id,
                extraction_method=method2,
                raw_text=raw_txt2,
                applicant_name_extracted=fields2["applicant_name"],
                company_name_extracted=fields2["company_name"],
                salary_amount_extracted=fields2["salary_amount"],
                bank_credits_extracted=fields2["bank_credits"],
                document_date_extracted=fields2["document_date"],
                confidence_score=fields2["confidence_score"]
            )
            db.session.add(ext2)

        if sample_files.get("increment_letter") and Path(sample_files["increment_letter"]).exists():
            inc_path = sample_files["increment_letter"]
            doc3 = UploadedDocument(
                application_id=app1.id,
                user_id=applicant_user.id,
                document_type="increment_letter",
                original_filename="Sample_Increment_Letter.pdf",
                stored_filename="Sample_Increment_Letter.pdf",
                file_path=str(inc_path),
                file_size=Path(inc_path).stat().st_size,
                file_type="pdf",
                verification_status="verified",
                verification_notes="Official promotion & appraisal letter corroborated."
            )
            db.session.add(doc3)
            db.session.flush()

            raw_txt3, method3, _, _ = DocumentProcessor.extract_raw_text(str(inc_path))
            fields3 = DocumentProcessor.extract_structured_fields(raw_txt3, "increment_letter")
            ext3 = ExtractedDocumentData(
                document_id=doc3.id,
                application_id=app1.id,
                extraction_method=method3,
                raw_text=raw_txt3,
                applicant_name_extracted=fields3["applicant_name"],
                company_name_extracted=fields3["company_name"],
                salary_amount_extracted=fields3["salary_amount"],
                document_date_extracted=fields3["document_date"],
                confidence_score=fields3["confidence_score"]
            )
            db.session.add(ext3)

    db.session.commit()

    # Calculate assessment for App 1
    assessment1 = FinancialCalculator.compute_assessment(app1)
    MLScorer.evaluate(app1, assessment1)
    EligibilityEngine.run_assessment(app1, assessment1)

    # 5.2 Priya Nair: Education Loan with 2 active backlogs
    app2 = LoanApplication(
        application_number="FC-2026-00102",
        applicant_id=priya_profile.id,
        bank_requirement_id=p_edu.id,
        loan_type_id=loan_type_instances['education_loan'].id,
        loan_type_code="education_loan",
        policy_version_used=1,
        loan_amount_requested=1200000.0,
        loan_tenure_months=60,
        loan_purpose="Master's in Data Science tuition and campus boarding",
        declared_monthly_salary=25000.0,
        existing_monthly_emis=2000.0,
        credit_score=680,
        company_name="Apex Data Labs (Internship / Stipend)",
        designation="Data Analyst Trainee",
        employment_type="Contract",
        experience_months=8,
        status="submitted"
    )
    app2.loan_specific_data = {
        "course_name": "M.Sc Data Science & Artificial Intelligence",
        "institution_name": "Indian Institute of Information Technology",
        "study_location": "Domestic",
        "total_course_fee": 1500000.0,
        "co_applicant_name": "K. Nair (Parent)",
        "co_applicant_relationship": "Father",
        "co_applicant_income": 45000.0
    }
    db.session.add(app2)
    db.session.flush()

    assessment2 = FinancialCalculator.compute_assessment(app2)
    MLScorer.evaluate(app2, assessment2)
    EligibilityEngine.run_assessment(app2, assessment2)

    # 5.3 Vikram Patel: Gold Loan (45 grams 22K pledged gold, requested 2,00,000, LTV 65.3% -> Meets Requirements)
    app3 = LoanApplication(
        application_number="FC-2026-00103",
        applicant_id=vikram_profile.id,
        bank_requirement_id=p_gold.id,
        loan_type_id=loan_type_instances['gold_loan'].id,
        loan_type_code="gold_loan",
        policy_version_used=1,
        loan_amount_requested=200000.0,
        loan_tenure_months=12,
        loan_purpose="Urgent inventory purchasing for retail store",
        declared_monthly_salary=35000.0,
        existing_monthly_emis=0.0,
        credit_score=710,
        company_name="Patel General Stores",
        designation="Proprietor",
        employment_type="Self-Employed",
        experience_months=48,
        status="submitted"
    )
    app3.loan_specific_data = {
        "gold_weight_grams": 45.0,
        "gold_purity_karats": "22K",
        "estimated_gold_value": 306000.0, # 45g * 6800 = 3,06,000
        "gold_item_type": "Gold bangles and necklace",
        "pledge_declaration": "Self-owned family jewelry, purchased with receipt."
    }
    db.session.add(app3)
    db.session.flush()

    assessment3 = FinancialCalculator.compute_assessment(app3)
    MLScorer.evaluate(app3, assessment3)
    EligibilityEngine.run_assessment(app3, assessment3)

    # 5.4 Rajesh Sharma: Home Loan (Property 60 Lakhs, Down Payment 15 Lakhs, Loan 45 Lakhs -> Meets Requirements)
    app4 = LoanApplication(
        application_number="FC-2026-00104",
        applicant_id=rajesh_profile.id,
        bank_requirement_id=p_home.id,
        loan_type_id=loan_type_instances['home_loan'].id,
        loan_type_code="home_loan",
        policy_version_used=1,
        loan_amount_requested=4500000.0,
        loan_tenure_months=180,
        loan_purpose="Purchase of 3BHK Residential Flat in Sector 75 Noida",
        declared_monthly_salary=85000.0,
        existing_monthly_emis=4500.0,
        credit_score=760,
        company_name="Apex Tech Solutions Pvt Ltd",
        designation="Lead Architect",
        employment_type="Salaried",
        experience_months=48,
        status="submitted"
    )
    app4.loan_specific_data = {
        "property_value": 6000000.0,
        "down_payment": 1500000.0,
        "property_type": "Residential Apartment",
        "property_address": "Tower 4, Flat 1202, Royal Palms, Sector 75, Noida",
        "is_approved_builder": True
    }
    db.session.add(app4)
    db.session.flush()

    assessment4 = FinancialCalculator.compute_assessment(app4)
    MLScorer.evaluate(app4, assessment4)
    EligibilityEngine.run_assessment(app4, assessment4)

    # 6. Seed Audit Log
    db.session.add(AuditLog(
        user_id=admin_user.id,
        user_role="admin",
        action="SYSTEM_INITIALIZED",
        details="FinCred AI initialized with 8 distinct loan types, lender policies, and sample applications."
    ))

    db.session.commit()
    print("[FinCred AI] Seeded successfully with all 8 loan types.")
