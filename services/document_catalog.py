"""
FinCred AI — Loan-Specific Document Catalog & Verification Rules
Defines dynamic document requirements, condition evaluators, and checklists
for all 8 supported loan categories:
1. Home Loan
2. Gold Loan
3. Education Loan
4. Personal Loan
5. Vehicle Loan
6. Business Loan
7. Loan Against Property (LAP)
8. Agriculture Loan
"""

import json
from pathlib import Path


LOAN_DOCUMENT_CATALOG = {
    # =========================================================================
    # 1. HOME LOAN
    # =========================================================================
    'home_loan': [
        {
            'doc_type': 'id_proof',
            'name': 'Identity Proof',
            'purpose': 'To verify applicant identity, date of birth, and legal name against government records.',
            'level': 'required',
            'condition_desc': 'Mandatory for all loan applicants.',
            'condition_func': lambda app: (True, 'Mandatory government identity verification.'),
            'demo_key': 'id_proof',
            'aliases': ['id_proof', 'identity_proof', 'pan_mock']
        },
        {
            'doc_type': 'address_proof',
            'name': 'Address Proof',
            'purpose': 'To establish current and permanent residential address verification.',
            'level': 'required',
            'condition_desc': 'Mandatory residential address verification.',
            'condition_func': lambda app: (True, 'Mandatory residential address proof.'),
            'demo_key': 'address_proof',
            'aliases': ['address_proof', 'aadhaar_mock']
        },
        {
            'doc_type': 'pan_card',
            'name': 'PAN / Tax Identification Document',
            'purpose': 'Required for credit bureau reporting, tax compliance, and KYC regulatory checks.',
            'level': 'required',
            'condition_desc': 'Mandatory for Indian credit underwriting and CIBIL reporting.',
            'condition_func': lambda app: (True, 'Mandatory tax identification document.'),
            'demo_key': 'pan_card',
            'aliases': ['pan_card', 'pan_doc', 'pan_mock', 'tax_id']
        },
        {
            'doc_type': 'salary_slip',
            'name': 'Recent Salary Slips (Last 3 Months)',
            'purpose': 'To verify recurring employment income, allowances, and statutory payroll deductions.',
            'level': 'conditional',
            'condition_desc': 'Required for salaried applicants; self-employed applicants provide business financials.',
            'condition_func': lambda app: (
                app.employment_type == 'Salaried',
                'Required for Salaried applicants to substantiate monthly payroll.'
                if app.employment_type == 'Salaried'
                else 'Not required for self-employed applicant; business tax returns are evaluated instead.'
            ),
            'demo_key': 'salary_slip',
            'aliases': ['salary_slip', 'payslips', 'salary_slips']
        },
        {
            'doc_type': 'bank_statement',
            'name': 'Bank Account Statements (Last 6 Months)',
            'purpose': 'To inspect monthly salary credits, banking conduct, recurring commitments, and average balance.',
            'level': 'required',
            'condition_desc': 'Mandatory banking track record for the past 6 months.',
            'condition_func': lambda app: (True, 'Mandatory 6-month primary bank account statements.'),
            'demo_key': 'bank_statement',
            'aliases': ['bank_statement', 'bank_statements']
        },
        {
            'doc_type': 'employment_proof',
            'name': 'Employment Proof / Salary Revision Letter',
            'purpose': 'To confirm current employment tenure, official designation, and salary progression trajectory.',
            'level': 'conditional',
            'condition_desc': 'Required if applicant declared a recent salary hike or has less than 24 months total experience.',
            'condition_func': lambda app: (
                bool(app.declared_previous_salary or (app.experience_months and app.experience_months < 24)),
                'Required to corroborate declared salary progression (+45.45%) and employer tenure.'
                if (app.declared_previous_salary or (app.experience_months and app.experience_months < 24))
                else 'Optional for seasoned borrowers with stable long-term employment tenure.'
            ),
            'demo_key': 'increment_letter',
            'aliases': ['increment_letter', 'employment_proof', 'appointment_letter']
        },
        {
            'doc_type': 'tax_doc',
            'name': 'Income Tax Returns / Form 16',
            'purpose': 'To corroborate annual income consistency and official tax return acknowledgments.',
            'level': 'required',
            'condition_desc': 'Mandatory Form 16 / ITR for the preceding financial year.',
            'condition_func': lambda app: (True, 'Mandatory Form 16 / ITR assessment order.'),
            'demo_key': 'tax_doc',
            'aliases': ['tax_doc', 'form16', 'itr', 'form16_tax_returns']
        },
        {
            'doc_type': 'property_sale_agreement',
            'name': 'Property Sale Agreement / Title Deeds',
            'purpose': 'To verify property ownership, chain of title, carpet area, and purchase consideration.',
            'level': 'required',
            'condition_desc': 'Mandatory registered conveyance deed, sale agreement, or allotment letter.',
            'condition_func': lambda app: (True, 'Mandatory legal agreement and title documentation.'),
            'demo_key': 'property_docs',
            'aliases': ['property_docs', 'property_documents', 'property_sale_agreement', 'title_deed']
        },
        {
            'doc_type': 'property_valuation',
            'name': 'Property Valuation / Technical Inspection Report',
            'purpose': 'To verify fair market value, construction progress, and enforce regulatory 80%-90% LTV caps.',
            'level': 'conditional',
            'condition_desc': 'Required for home loans exceeding ₹25,00,000 or pre-owned independent properties.',
            'condition_func': lambda app: (
                (app.loan_amount_requested or 0) >= 2500000,
                'Required by lender policy for high-value housing credit exceeding ₹25 Lakhs.'
                if (app.loan_amount_requested or 0) >= 2500000
                else 'Optional for standard builder-approved projects below ₹25 Lakhs.'
            ),
            'demo_key': 'property_docs',
            'aliases': ['property_valuation', 'valuation_report', 'technical_inspection']
        },
        {
            'doc_type': 'existing_loan_statements',
            'name': 'Existing Loan / EMI Repayment Statements',
            'purpose': 'To verify active debt burden, remaining balance, and punctual EMI repayment history.',
            'level': 'conditional',
            'condition_desc': 'Required if applicant declared existing monthly debt obligations.',
            'condition_func': lambda app: (
                (app.existing_monthly_emis or 0) > 0,
                f'Required because applicant declared ongoing EMI obligations of ₹{app.existing_monthly_emis:,.2f}/mo.'
                if (app.existing_monthly_emis or 0) > 0
                else 'Not required since applicant declared zero existing monthly loan obligations.'
            ),
            'demo_key': 'bank_statement',
            'aliases': ['existing_loan_statements', 'loan_statement', 'emi_records']
        },
        {
            'doc_type': 'co_applicant_docs',
            'name': 'Co-Applicant KYC & Income Documents',
            'purpose': 'To assess creditworthiness of the secondary borrower or property co-owner.',
            'level': 'optional',
            'condition_desc': 'Optional unless needed to enhance DTI debt servicing capacity.',
            'condition_func': lambda app: (False, 'Optional document to enhance borrowing eligibility with joint income.'),
            'demo_key': 'id_proof',
            'aliases': ['co_applicant_docs', 'coapplicant_kyc']
        }
    ],

    # =========================================================================
    # 2. GOLD LOAN
    # =========================================================================
    'gold_loan': [
        {
            'doc_type': 'id_proof',
            'name': 'Identity Proof',
            'purpose': 'To establish borrower identity and fulfill mandatory KYC statutory requirements.',
            'level': 'required',
            'condition_desc': 'Mandatory KYC identification for gold pledge.',
            'condition_func': lambda app: (True, 'Mandatory borrower identification.'),
            'demo_key': 'id_proof',
            'aliases': ['id_proof', 'identity_proof', 'pan_mock']
        },
        {
            'doc_type': 'address_proof',
            'name': 'Address Proof',
            'purpose': 'To verify current residential address for pledge custody records.',
            'level': 'required',
            'condition_desc': 'Required for bullion collateral registration.',
            'condition_func': lambda app: (True, 'Required borrower address verification.'),
            'demo_key': 'address_proof',
            'aliases': ['address_proof', 'aadhaar_mock']
        },
        {
            'doc_type': 'pan_card',
            'name': 'PAN / Form 60 Tax Identification',
            'purpose': 'Statutory requirement under RBI bullion guidelines for high-value pledges.',
            'level': 'conditional',
            'condition_desc': 'Mandatory by regulatory guidelines for gold loan disbursements of ₹5,00,000 and above.',
            'condition_func': lambda app: (
                (app.loan_amount_requested or 0) >= 500000,
                'Mandatory under RBI guidelines for loan amounts of ₹5,00,000 and above.'
                if (app.loan_amount_requested or 0) >= 500000
                else 'Optional for gold loan requests below ₹5,00,000 threshold.'
            ),
            'demo_key': 'pan_card',
            'aliases': ['pan_card', 'pan_doc', 'tax_id']
        },
        {
            'doc_type': 'gold_valuation_appraisal',
            'name': 'Gold Valuation & Appraisal Certificate',
            'purpose': 'To certify hallmark purity (22K/24K), net gram weight, and benchmark collateral market value under 75% LTV.',
            'level': 'required',
            'condition_desc': 'Mandatory certified appraiser bullion assessment report.',
            'condition_func': lambda app: (True, 'Mandatory certified assayer valuation report enforcing 75% LTV cap.'),
            'demo_key': 'gold_valuation',
            'aliases': ['gold_valuation_appraisal', 'gold_valuation_cert', 'gold_valuation', 'gold_appraisal']
        },
        {
            'doc_type': 'gold_ownership_receipt',
            'name': 'Gold Purchase Invoice / Ownership Declaration',
            'purpose': 'To verify legitimate acquisition and unencumbered ownership of pledged ornaments.',
            'level': 'conditional',
            'condition_desc': 'Recommended for all pledges; mandatory for jewel weight exceeding 50 grams.',
            'condition_func': lambda app: (
                float((app.loan_specific_data or {}).get('gold_weight_grams', 0) or 0) >= 50.0,
                'Mandatory proof of purchase or family heirloom declaration for pledges >= 50 grams.'
                if float((app.loan_specific_data or {}).get('gold_weight_grams', 0) or 0) >= 50.0
                else 'Optional self-declaration for standard retail gold jewelry under 50 grams.'
            ),
            'demo_key': 'gold_ownership_receipt',
            'aliases': ['gold_ownership_receipt', 'gold_ownership_declaration', 'gold_invoice']
        },
        {
            'doc_type': 'pledge_declaration',
            'name': 'Lender Bullion Pledge & Safe Custody Form',
            'purpose': 'Legal covenant governing vault safe custody, insurance, and statutory auction terms.',
            'level': 'required',
            'condition_desc': 'Mandatory collateral pledge covenant.',
            'condition_func': lambda app: (True, 'Mandatory signed bullion pledge agreement.'),
            'demo_key': 'pledge_declaration',
            'aliases': ['pledge_declaration', 'pledge_form']
        }
    ],

    # =========================================================================
    # 3. EDUCATION LOAN
    # =========================================================================
    'education_loan': [
        {
            'doc_type': 'id_proof',
            'name': 'Student Identity Proof',
            'purpose': 'To verify student identity and age eligibility.',
            'level': 'required',
            'condition_desc': 'Mandatory student identity verification.',
            'condition_func': lambda app: (True, 'Mandatory student identity proof.'),
            'demo_key': 'id_proof',
            'aliases': ['id_proof', 'student_id_proof']
        },
        {
            'doc_type': 'address_proof',
            'name': 'Student & Family Address Proof',
            'purpose': 'To confirm permanent residential address of the student applicant.',
            'level': 'required',
            'condition_desc': 'Mandatory permanent address verification.',
            'condition_func': lambda app: (True, 'Mandatory address verification.'),
            'demo_key': 'address_proof',
            'aliases': ['address_proof']
        },
        {
            'doc_type': 'pan_card',
            'name': 'PAN / Tax Identification Document',
            'purpose': 'Required for student / co-applicant credit bureau record opening.',
            'level': 'required',
            'condition_desc': 'Mandatory tax identification document.',
            'condition_func': lambda app: (True, 'Mandatory PAN card verification.'),
            'demo_key': 'pan_card',
            'aliases': ['pan_card', 'tax_id']
        },
        {
            'doc_type': 'admission_letter',
            'name': 'University Admission Offer Letter',
            'purpose': 'To confirm accredited university admission, course duration, and matriculation commencement.',
            'level': 'required',
            'condition_desc': 'Mandatory official university admission letter.',
            'condition_func': lambda app: (True, 'Mandatory unconditional or conditional admission letter.'),
            'demo_key': 'admission_letter',
            'aliases': ['admission_letter', 'offer_letter']
        },
        {
            'doc_type': 'course_fee_structure',
            'name': 'Institutional Course Fee Structure Breakdown',
            'purpose': 'To calculate tuition, laboratory, library, exam, and living expense loan components.',
            'level': 'required',
            'condition_desc': 'Mandatory fee schedule issued by the educational institution.',
            'condition_func': lambda app: (True, 'Mandatory breakdown of tuition and campus hostel fees.'),
            'demo_key': 'fee_structure',
            'aliases': ['course_fee_structure', 'fee_schedule']
        },
        {
            'doc_type': 'mark_sheets',
            'name': 'Academic Mark Sheets (10th, 12th & Degree)',
            'purpose': 'To evaluate scholastic merit, GPA/percentage, and inspect academic backlogs.',
            'level': 'required',
            'condition_desc': 'Mandatory transcripts for academic policy appraisal.',
            'condition_func': lambda app: (True, 'Mandatory academic transcripts and backlog policy verification.'),
            'demo_key': 'education_cert',
            'aliases': ['mark_sheets', 'education_cert', 'transcripts']
        },
        {
            'doc_type': 'educational_certificates',
            'name': 'Passing Certificates / Degree Diplomas',
            'purpose': 'To substantiate completion of prerequisite qualifying examinations.',
            'level': 'required',
            'condition_desc': 'Mandatory qualifying degree or diploma certificate.',
            'condition_func': lambda app: (True, 'Mandatory graduation / passing certificates.'),
            'demo_key': 'education_cert',
            'aliases': ['educational_certificates', 'degree_certificate']
        },
        {
            'doc_type': 'entrance_exam_results',
            'name': 'Entrance Exam Scorecard (GRE / GMAT / CAT / NEET / JEE)',
            'purpose': 'To verify standardized entrance examination ranking and percentile qualifications.',
            'level': 'conditional',
            'condition_desc': 'Required for competitive professional and overseas university programs.',
            'condition_func': lambda app: (
                'overseas' in (app.loan_purpose or '').lower() or 'master' in ((app.applicant.education_level or '').lower()),
                'Required for competitive overseas or postgraduate degree programs.'
                if ('overseas' in (app.loan_purpose or '').lower() or 'master' in ((app.applicant.education_level or '').lower()))
                else 'Optional for direct merit-based domestic degree admissions.'
            ),
            'demo_key': 'entrance_exam',
            'aliases': ['entrance_exam_results', 'exam_scorecard']
        },
        {
            'doc_type': 'student_bank_statement',
            'name': 'Student Savings Bank Statement',
            'purpose': 'To inspect student savings history where available.',
            'level': 'optional',
            'condition_desc': 'Optional student savings account statement.',
            'condition_func': lambda app: (False, 'Optional savings bank account statement for student.'),
            'demo_key': 'bank_statement',
            'aliases': ['student_bank_statement']
        },
        {
            'doc_type': 'parent_id_proof',
            'name': 'Parent / Co-Borrower Identity Proof',
            'purpose': 'Education loans require an earning parent or guardian as primary financial co-applicant.',
            'level': 'required',
            'condition_desc': 'Mandatory parent / guardian co-borrower identification.',
            'condition_func': lambda app: (True, 'Mandatory parent / co-applicant KYC identification.'),
            'demo_key': 'id_proof',
            'aliases': ['parent_id_proof', 'coapplicant_id']
        },
        {
            'doc_type': 'parent_income_proof',
            'name': 'Parent / Co-Borrower Salary Slips or ITR',
            'purpose': 'To establish co-borrower repayment capacity for during-study simple interest service.',
            'level': 'required',
            'condition_desc': 'Mandatory co-borrower income documentation (3 months salary slips or 2 years ITR).',
            'condition_func': lambda app: (True, 'Mandatory parent / guardian income verification.'),
            'demo_key': 'salary_slip',
            'aliases': ['parent_income_proof', 'parent_salary_slip', 'coapplicant_income']
        },
        {
            'doc_type': 'parent_bank_statement',
            'name': 'Parent / Co-Borrower Bank Statement (6 Months)',
            'purpose': 'To verify regular cash flow and banking conduct of the primary guarantor.',
            'level': 'required',
            'condition_desc': 'Mandatory 6-month bank statement of the parent / co-applicant.',
            'condition_func': lambda app: (True, 'Mandatory parent / guarantor 6-month bank statements.'),
            'demo_key': 'bank_statement',
            'aliases': ['parent_bank_statement', 'coapplicant_bank_statement']
        },
        {
            'doc_type': 'collateral_docs',
            'name': 'Collateral Security / Property Documents',
            'purpose': 'Tangible security (property / fixed deposit) for high-value education loans under RBI guidelines.',
            'level': 'conditional',
            'condition_desc': 'Mandatory under banking regulations for education loan amounts exceeding ₹7.5 Lakhs.',
            'condition_func': lambda app: (
                (app.loan_amount_requested or 0) > 750000,
                'Mandatory under banking regulations for education credit exceeding ₹7,50,000.'
                if (app.loan_amount_requested or 0) > 750000
                else 'Not required for unsecured education credit under ₹7,50,000 ceiling.'
            ),
            'demo_key': 'property_docs',
            'aliases': ['collateral_docs', 'education_collateral', 'property_docs']
        },
        {
            'doc_type': 'scholarship_proof',
            'name': 'Scholarship or Financial Grant Award Letter',
            'purpose': 'To incorporate external institutional fee subsidies into margin money calculation.',
            'level': 'optional',
            'condition_desc': 'Optional grant or university scholarship award proof.',
            'condition_func': lambda app: (False, 'Optional document to reduce required borrower margin contribution.'),
            'demo_key': 'scholarship_proof',
            'aliases': ['scholarship_proof', 'grant_letter']
        }
    ],

    # =========================================================================
    # 4. PERSONAL LOAN
    # =========================================================================
    'personal_loan': [
        {
            'doc_type': 'id_proof',
            'name': 'Identity Proof',
            'purpose': 'To verify identity, full name, and date of birth.',
            'level': 'required',
            'condition_desc': 'Mandatory government identity document.',
            'condition_func': lambda app: (True, 'Mandatory identity verification.'),
            'demo_key': 'id_proof',
            'aliases': ['id_proof', 'identity_proof', 'pan_mock']
        },
        {
            'doc_type': 'address_proof',
            'name': 'Address Proof',
            'purpose': 'To confirm current residential location and utility billing address.',
            'level': 'required',
            'condition_desc': 'Mandatory residential address verification.',
            'condition_func': lambda app: (True, 'Mandatory address verification.'),
            'demo_key': 'address_proof',
            'aliases': ['address_proof', 'aadhaar_mock']
        },
        {
            'doc_type': 'pan_card',
            'name': 'PAN Card / Tax Identification',
            'purpose': 'Required for automated credit underwriting, CIBIL pull, and regulatory KYC.',
            'level': 'required',
            'condition_desc': 'Mandatory tax identification document.',
            'condition_func': lambda app: (True, 'Mandatory PAN verification.'),
            'demo_key': 'pan_card',
            'aliases': ['pan_card', 'tax_id']
        },
        {
            'doc_type': 'salary_slip',
            'name': 'Recent Salary Slips (Last 3 Months)',
            'purpose': 'To verify net monthly take-home pay, allowances, and compute salary growth delta (+45.45%).',
            'level': 'required',
            'condition_desc': 'Mandatory salary slips for consecutive 3 months.',
            'condition_func': lambda app: (True, 'Mandatory 3-month salary slips for unsecured credit underwriting.'),
            'demo_key': 'salary_slip',
            'aliases': ['salary_slip', 'payslips', 'salary_slips']
        },
        {
            'doc_type': 'bank_statement',
            'name': 'Salary Bank Account Statements (Last 6 Months)',
            'purpose': 'To verify automated ACH/NEFT employer salary credits and compute monthly expense patterns.',
            'level': 'required',
            'condition_desc': 'Mandatory 6-month primary salary bank account statement.',
            'condition_func': lambda app: (True, 'Mandatory bank statement verifying regular salary credits.'),
            'demo_key': 'bank_statement',
            'aliases': ['bank_statement', 'bank_statements']
        },
        {
            'doc_type': 'employment_proof',
            'name': 'Employment ID / Experience / Appraisal Letter',
            'purpose': 'To corroborate company tenure, designation, and recent promotion or increment.',
            'level': 'conditional',
            'condition_desc': 'Required if applicant declared salary progression or has < 24 months total experience.',
            'condition_func': lambda app: (
                bool(app.declared_previous_salary or (app.experience_months and app.experience_months < 24)),
                'Required to corroborate declared salary increase and official employment vintage.'
                if (app.declared_previous_salary or (app.experience_months and app.experience_months < 24))
                else 'Optional for established applicants with tenured employment records.'
            ),
            'demo_key': 'increment_letter',
            'aliases': ['increment_letter', 'employment_proof', 'appointment_letter']
        },
        {
            'doc_type': 'tax_doc',
            'name': 'Form 16 / Annual Tax Return',
            'purpose': 'To verify annual earnings consistency across financial assessment years.',
            'level': 'conditional',
            'condition_desc': 'Required for personal loan requests exceeding ₹5,00,000.',
            'condition_func': lambda app: (
                (app.loan_amount_requested or 0) >= 500000,
                'Required by lender underwriting policy for personal loan amounts >= ₹5 Lakhs.'
                if (app.loan_amount_requested or 0) >= 500000
                else 'Optional for standard personal loans below ₹5 Lakhs.'
            ),
            'demo_key': 'tax_doc',
            'aliases': ['tax_doc', 'form16', 'itr']
        },
        {
            'doc_type': 'existing_loan_statements',
            'name': 'Existing Loan or EMI Statements',
            'purpose': 'To verify debt servicing track record and accurately compute DTI debt-to-income ratio.',
            'level': 'conditional',
            'condition_desc': 'Required if applicant declared existing monthly debt obligations.',
            'condition_func': lambda app: (
                (app.existing_monthly_emis or 0) > 0,
                f'Required because applicant declared monthly EMI obligations of ₹{app.existing_monthly_emis:,.2f}.'
                if (app.existing_monthly_emis or 0) > 0
                else 'Not required since applicant declared zero existing monthly loan obligations.'
            ),
            'demo_key': 'bank_statement',
            'aliases': ['existing_loan_statements', 'loan_statement']
        }
    ],

    # =========================================================================
    # 5. VEHICLE LOAN
    # =========================================================================
    'vehicle_loan': [
        {
            'doc_type': 'id_proof',
            'name': 'Identity Proof',
            'purpose': 'To verify borrower identity and driving license eligibility.',
            'level': 'required',
            'condition_desc': 'Mandatory identity verification.',
            'condition_func': lambda app: (True, 'Mandatory borrower identification.'),
            'demo_key': 'id_proof',
            'aliases': ['id_proof', 'identity_proof', 'pan_mock']
        },
        {
            'doc_type': 'address_proof',
            'name': 'Address Proof',
            'purpose': 'To verify RTO jurisdictional registration address.',
            'level': 'required',
            'condition_desc': 'Mandatory local address proof for vehicle registration.',
            'condition_func': lambda app: (True, 'Mandatory address verification for regional transport authority.'),
            'demo_key': 'address_proof',
            'aliases': ['address_proof', 'aadhaar_mock']
        },
        {
            'doc_type': 'pan_card',
            'name': 'PAN / Tax Identification',
            'purpose': 'Mandatory for vehicle purchase invoicing and credit bureau reporting.',
            'level': 'required',
            'condition_desc': 'Mandatory tax identification document.',
            'condition_func': lambda app: (True, 'Mandatory PAN card verification.'),
            'demo_key': 'pan_card',
            'aliases': ['pan_card', 'tax_id']
        },
        {
            'doc_type': 'salary_slip',
            'name': 'Salary Slips or Business Income Proof',
            'purpose': 'To verify regular monthly income for monthly auto installment servicing.',
            'level': 'required',
            'condition_desc': 'Mandatory income proof (salary slips or audited business returns).',
            'condition_func': lambda app: (True, 'Mandatory income documentation.'),
            'demo_key': 'salary_slip',
            'aliases': ['salary_slip', 'payslips', 'income_proof']
        },
        {
            'doc_type': 'bank_statement',
            'name': 'Bank Account Statements (Last 6 Months)',
            'purpose': 'To verify regular cash flow and healthy account turnover.',
            'level': 'required',
            'condition_desc': 'Mandatory 6-month bank statements.',
            'condition_func': lambda app: (True, 'Mandatory 6-month bank statement.'),
            'demo_key': 'bank_statement',
            'aliases': ['bank_statement']
        },
        {
            'doc_type': 'vehicle_quotation',
            'name': 'Authorized Dealer Proforma Invoice / Quotation',
            'purpose': 'To verify ex-showroom price, RTO road tax, insurance, and enforce 85% vehicle LTV cap.',
            'level': 'required',
            'condition_desc': 'Mandatory official quotation from an authorized automobile dealership.',
            'condition_func': lambda app: (True, 'Mandatory dealership proforma invoice establishing on-road price.'),
            'demo_key': 'vehicle_quotation',
            'aliases': ['vehicle_quotation', 'proforma_invoice', 'dealer_quotation']
        },
        {
            'doc_type': 'down_payment_proof',
            'name': 'Down Payment Advance Receipt',
            'purpose': 'To substantiate borrower minimum 15% equity contribution towards vehicle purchase.',
            'level': 'conditional',
            'condition_desc': 'Required prior to loan sanction for dealer booking confirmation.',
            'condition_func': lambda app: (
                bool((app.loan_specific_data or {}).get('down_payment_amount', 0)),
                'Required to verify customer advance payment receipt to the dealership.'
                if (app.loan_specific_data or {}).get('down_payment_amount', 0)
                else 'Optional at pre-approval; mandatory before final vehicle delivery.'
            ),
            'demo_key': 'down_payment_proof',
            'aliases': ['down_payment_proof', 'booking_receipt']
        },
        {
            'doc_type': 'existing_loan_statements',
            'name': 'Existing Loan Statements',
            'purpose': 'To check existing obligations.',
            'level': 'conditional',
            'condition_desc': 'Required if existing debts were declared.',
            'condition_func': lambda app: (
                (app.existing_monthly_emis or 0) > 0,
                f'Required because applicant declared monthly EMI obligations of ₹{app.existing_monthly_emis:,.2f}.'
                if (app.existing_monthly_emis or 0) > 0
                else 'Not required since applicant declared zero existing monthly loan obligations.'
            ),
            'demo_key': 'bank_statement',
            'aliases': ['existing_loan_statements']
        },
        {
            'doc_type': 'co_applicant_docs',
            'name': 'Co-Applicant / Guarantor Documents',
            'purpose': 'To enhance vehicle finance eligibility with household income.',
            'level': 'optional',
            'condition_desc': 'Optional co-applicant documentation.',
            'condition_func': lambda app: (False, 'Optional co-applicant records.'),
            'demo_key': 'id_proof',
            'aliases': ['co_applicant_docs']
        }
    ],

    # =========================================================================
    # 6. BUSINESS LOAN
    # =========================================================================
    'business_loan': [
        {
            'doc_type': 'id_proof',
            'name': 'Identity Proof of Proprietor / Partners / Directors',
            'purpose': 'To verify identity of the key promoter and beneficial business owners.',
            'level': 'required',
            'condition_desc': 'Mandatory promoter identity proof.',
            'condition_func': lambda app: (True, 'Mandatory key managerial personnel identity verification.'),
            'demo_key': 'id_proof',
            'aliases': ['id_proof', 'promoter_id']
        },
        {
            'doc_type': 'business_registration',
            'name': 'Business Registration Certificate / Udyam / Certificate of Incorporation',
            'purpose': 'To verify official enterprise vintage (min 24 months) and legal operational entity status.',
            'level': 'required',
            'condition_desc': 'Mandatory government business registration certificate.',
            'condition_func': lambda app: (True, 'Mandatory enterprise registration proving business vintage.'),
            'demo_key': 'business_reg',
            'aliases': ['business_registration', 'udyam_cert', 'cin_cert', 'business_pan']
        },
        {
            'doc_type': 'pan_card',
            'name': 'Entity & Promoter PAN Cards',
            'purpose': 'Required for commercial credit bureau (CIBIL Commercial) reporting and tax verification.',
            'level': 'required',
            'condition_desc': 'Mandatory entity and promoter PAN records.',
            'condition_func': lambda app: (True, 'Mandatory corporate and promoter PAN verification.'),
            'demo_key': 'pan_card',
            'aliases': ['pan_card', 'business_pan']
        },
        {
            'doc_type': 'business_bank_statement',
            'name': 'Current Account Business Bank Statements (Last 12 Months)',
            'purpose': 'To verify cash flow liquidity, banking credits, and calculate business turnover underwriting metrics.',
            'level': 'required',
            'condition_desc': 'Mandatory 12-month current account operating statement.',
            'condition_func': lambda app: (True, 'Mandatory 12-month operating business bank account statements.'),
            'demo_key': 'bank_statement',
            'aliases': ['business_bank_statement', 'bank_statement']
        },
        {
            'doc_type': 'personal_bank_statement',
            'name': 'Proprietor / Director Personal Bank Statement',
            'purpose': 'To inspect promoter personal banking discipline and drawings.',
            'level': 'optional',
            'condition_desc': 'Optional personal bank statement of the key promoter.',
            'condition_func': lambda app: (False, 'Optional secondary personal banking statement.'),
            'demo_key': 'bank_statement',
            'aliases': ['personal_bank_statement']
        },
        {
            'doc_type': 'tax_doc',
            'name': 'Audited Income Tax Returns (Last 2-3 Years)',
            'purpose': 'To substantiate annual turnover compliance (min ₹20 Lakhs) and taxable profit generation.',
            'level': 'required',
            'condition_desc': 'Mandatory 2 years audited ITR with computation of income.',
            'condition_func': lambda app: (True, 'Mandatory audited business income tax returns.'),
            'demo_key': 'tax_doc',
            'aliases': ['tax_doc', 'business_itr']
        },
        {
            'doc_type': 'financial_statements',
            'name': 'Audited Financial Statements (P&L and Balance Sheet)',
            'purpose': 'To analyze Debt Service Coverage Ratio (DSCR), current ratio, and net operating margin.',
            'level': 'required',
            'condition_desc': 'Mandatory chartered accountant certified Balance Sheet and Profit & Loss statement.',
            'condition_func': lambda app: (True, 'Mandatory audited balance sheet and profit & loss statements.'),
            'demo_key': 'tax_doc',
            'aliases': ['financial_statements', 'balance_sheet', 'pnl_statement']
        },
        {
            'doc_type': 'gst_returns',
            'name': 'GST Filing Returns (GSTR-3B / GSTR-1)',
            'purpose': 'To cross-verify active monthly turnover against audited financial declarations.',
            'level': 'required',
            'condition_desc': 'Mandatory recent 6-12 months GST returns.',
            'condition_func': lambda app: (True, 'Mandatory GST returns verifying reported commercial revenue.'),
            'demo_key': 'tax_doc',
            'aliases': ['gst_returns', 'gstr3b']
        },
        {
            'doc_type': 'business_address_proof',
            'name': 'Commercial Business Premise Proof / Lease Deed',
            'purpose': 'To verify commercial operational facility ownership or registered tenancy.',
            'level': 'required',
            'condition_desc': 'Mandatory commercial premises address proof or registered lease.',
            'condition_func': lambda app: (True, 'Mandatory enterprise operating facility proof.'),
            'demo_key': 'address_proof',
            'aliases': ['business_address_proof', 'commercial_lease']
        },
        {
            'doc_type': 'ownership_partnership_docs',
            'name': 'Partnership Deed / MOA & AOA / Shareholding Pattern',
            'purpose': 'To establish governing authority and authorized borrowing signatories.',
            'level': 'conditional',
            'condition_desc': 'Required for Partnership firms, LLPs, and Private Limited companies.',
            'condition_func': lambda app: (
                (app.loan_specific_data or {}).get('business_type', '') in ('Partnership', 'Private Limited', 'LLP'),
                'Required for entity structures with multiple partners or corporate shareholding.'
                if (app.loan_specific_data or {}).get('business_type', '') in ('Partnership', 'Private Limited', 'LLP')
                else 'Optional for Sole Proprietorship enterprises.'
            ),
            'demo_key': 'business_reg',
            'aliases': ['ownership_partnership_docs', 'partnership_deed', 'moa_aoa']
        },
        {
            'doc_type': 'existing_loan_statements',
            'name': 'Existing Business Loan & Credit Facility Statements',
            'purpose': 'To audit active working capital limits, term loans, and credit exposure.',
            'level': 'conditional',
            'condition_desc': 'Required if enterprise holds active external credit facilities.',
            'condition_func': lambda app: (
                (app.existing_monthly_emis or 0) > 0,
                f'Required because applicant declared ongoing business debt of ₹{app.existing_monthly_emis:,.2f}/mo.'
                if (app.existing_monthly_emis or 0) > 0
                else 'Not required since enterprise declared zero existing debt obligations.'
            ),
            'demo_key': 'bank_statement',
            'aliases': ['existing_loan_statements', 'facility_statement']
        },
        {
            'doc_type': 'collateral_docs',
            'name': 'Collateral Security Documents (For Secured Lines)',
            'purpose': 'Property or asset pledge documents for secured commercial credit.',
            'level': 'conditional',
            'condition_desc': 'Required for secured business loans or credit limits exceeding ₹50 Lakhs.',
            'condition_func': lambda app: (
                (app.loan_amount_requested or 0) >= 5000000,
                'Required for high-value business loans exceeding ₹50 Lakhs collateral threshold.'
                if (app.loan_amount_requested or 0) >= 5000000
                else 'Optional for unsecured working capital business loans under ₹50 Lakhs.'
            ),
            'demo_key': 'property_docs',
            'aliases': ['collateral_docs', 'property_docs']
        }
    ],

    # =========================================================================
    # 7. LOAN AGAINST PROPERTY (LAP)
    # =========================================================================
    'loan_against_property': [
        {
            'doc_type': 'id_proof',
            'name': 'Identity Proof',
            'purpose': 'To verify legal identity and match applicant name with property title documents.',
            'level': 'required',
            'condition_desc': 'Mandatory property owner identity proof.',
            'condition_func': lambda app: (True, 'Mandatory title holder identity verification.'),
            'demo_key': 'id_proof',
            'aliases': ['id_proof', 'identity_proof', 'pan_mock']
        },
        {
            'doc_type': 'address_proof',
            'name': 'Address Proof',
            'purpose': 'To verify residential address of the title owner.',
            'level': 'required',
            'condition_desc': 'Mandatory residential address verification.',
            'condition_func': lambda app: (True, 'Mandatory address verification.'),
            'demo_key': 'address_proof',
            'aliases': ['address_proof', 'aadhaar_mock']
        },
        {
            'doc_type': 'pan_card',
            'name': 'PAN / Tax Identification',
            'purpose': 'Required for credit bureau reporting, mortgage registration, and tax filings.',
            'level': 'required',
            'condition_desc': 'Mandatory tax identification document.',
            'condition_func': lambda app: (True, 'Mandatory PAN card verification.'),
            'demo_key': 'pan_card',
            'aliases': ['pan_card', 'tax_id']
        },
        {
            'doc_type': 'salary_slip',
            'name': 'Recent Salary Slips or Business Income Proof',
            'purpose': 'To verify cash flow liquidity for monthly mortgage interest and principal repayment.',
            'level': 'required',
            'condition_desc': 'Mandatory monthly earnings proof (salary slips or audited business returns).',
            'condition_func': lambda app: (True, 'Mandatory applicant cash flow and income proof.'),
            'demo_key': 'salary_slip',
            'aliases': ['salary_slip', 'payslips', 'income_proof']
        },
        {
            'doc_type': 'bank_statement',
            'name': 'Bank Account Statements (Last 6-12 Months)',
            'purpose': 'To audit regular cash flow, account balance, and credit turnovers.',
            'level': 'required',
            'condition_desc': 'Mandatory primary bank account statements.',
            'condition_func': lambda app: (True, 'Mandatory banking operational history.'),
            'demo_key': 'bank_statement',
            'aliases': ['bank_statement']
        },
        {
            'doc_type': 'tax_doc',
            'name': 'Income Tax Returns (Last 2 Years)',
            'purpose': 'To verify income consistency and tax assessments.',
            'level': 'required',
            'condition_desc': 'Mandatory 2 years ITR with computation of income.',
            'condition_func': lambda app: (True, 'Mandatory tax returns assessment.'),
            'demo_key': 'tax_doc',
            'aliases': ['tax_doc', 'itr']
        },
        {
            'doc_type': 'property_ownership_docs',
            'name': 'Registered Property Title Deed & Chain Documents',
            'purpose': 'To verify absolute registered ownership, 13-30 year chain of title, and unencumbered title.',
            'level': 'required',
            'condition_desc': 'Mandatory registered conveyance/sale deed proving clear title.',
            'condition_func': lambda app: (True, 'Mandatory registered title deed and legal chain documents.'),
            'demo_key': 'property_docs',
            'aliases': ['property_ownership_docs', 'property_docs', 'property_documents', 'title_deed']
        },
        {
            'doc_type': 'property_tax_receipts',
            'name': 'Latest Property Tax Paid Receipts & Khata Certificate',
            'purpose': 'To confirm zero municipality tax arrears and municipal plan sanction compliance.',
            'level': 'required',
            'condition_desc': 'Mandatory municipal tax receipt for current assessment year.',
            'condition_func': lambda app: (True, 'Mandatory property tax paid challan and municipal Khata extract.'),
            'demo_key': 'property_docs',
            'aliases': ['property_tax_receipts', 'tax_receipt', 'khata_extract', 'property_docs']
        },
        {
            'doc_type': 'property_valuation',
            'name': 'Property Valuation & Technical Inspection Report',
            'purpose': 'To determine fair market valuation and enforce mandatory 60%-70% LAP LTV regulatory limit.',
            'level': 'required',
            'condition_desc': 'Mandatory independent technical valuation report.',
            'condition_func': lambda app: (True, 'Mandatory technical valuation establishing collateral value.'),
            'demo_key': 'property_docs',
            'aliases': ['property_valuation', 'valuation_report', 'property_docs']
        },
        {
            'doc_type': 'existing_loan_statements',
            'name': 'Existing Property Loan / Encumbrance Statements',
            'purpose': 'To verify existing debt obligations.',
            'level': 'conditional',
            'condition_desc': 'Required if applicant declared existing loans.',
            'condition_func': lambda app: (
                (app.existing_monthly_emis or 0) > 0,
                f'Required because applicant declared monthly EMI obligations of ₹{app.existing_monthly_emis:,.2f}.'
                if (app.existing_monthly_emis or 0) > 0
                else 'Not required since applicant declared zero existing monthly debt obligations.'
            ),
            'demo_key': 'bank_statement',
            'aliases': ['existing_loan_statements']
        },
        {
            'doc_type': 'co_applicant_docs',
            'name': 'Co-Owner / Co-Applicant KYC Documents',
            'purpose': 'All joint title holders of the mortgaged property must join as co-applicants.',
            'level': 'conditional',
            'condition_desc': 'Mandatory for all registered joint property owners.',
            'condition_func': lambda app: (
                'joint' in ((app.loan_specific_data or {}).get('ownership_status', '')).lower(),
                'Mandatory for all co-owners listed on the property title deed.'
                if 'joint' in ((app.loan_specific_data or {}).get('ownership_status', '')).lower()
                else 'Optional for sole individual property owners.'
            ),
            'demo_key': 'id_proof',
            'aliases': ['co_applicant_docs']
        }
    ],

    # =========================================================================
    # 8. AGRICULTURE LOAN
    # =========================================================================
    'agriculture_loan': [
        {
            'doc_type': 'id_proof',
            'name': 'Farmer Identity Proof',
            'purpose': 'To verify farmer borrower identity and Kisan registry credentials.',
            'level': 'required',
            'condition_desc': 'Mandatory farmer identity verification.',
            'condition_func': lambda app: (True, 'Mandatory farmer identity proof.'),
            'demo_key': 'id_proof',
            'aliases': ['id_proof', 'identity_proof', 'pan_mock']
        },
        {
            'doc_type': 'address_proof',
            'name': 'Rural Residential Address Proof',
            'purpose': 'To confirm village panchayat / rural residential jurisdiction.',
            'level': 'required',
            'condition_desc': 'Mandatory residential address verification.',
            'condition_func': lambda app: (True, 'Mandatory rural residential address proof.'),
            'demo_key': 'address_proof',
            'aliases': ['address_proof', 'aadhaar_mock']
        },
        {
            'doc_type': 'pan_card',
            'name': 'PAN Card / Form 60 Agricultural Declaration',
            'purpose': 'Required for statutory credit bureau reporting and agricultural KYC.',
            'level': 'conditional',
            'condition_desc': 'Required for loan limits exceeding ₹2,00,000.',
            'condition_func': lambda app: (
                (app.loan_amount_requested or 0) >= 200000,
                'Required for agricultural loan limits of ₹2,00,000 and above.'
                if (app.loan_amount_requested or 0) >= 200000
                else 'Optional Form 60 agricultural self-declaration for small loans under ₹2 Lakhs.'
            ),
            'demo_key': 'pan_card',
            'aliases': ['pan_card', 'form60']
        },
        {
            'doc_type': 'land_records',
            'name': 'Land Ownership Records (Patta / 7/12 Extract / Khasra / Khatoni)',
            'purpose': 'To verify cultivable landholding acreage (min 2.0 acres) and clear agricultural title.',
            'level': 'required',
            'condition_desc': 'Mandatory revenue land ownership record or registered tenancy agreement.',
            'condition_func': lambda app: (True, 'Mandatory revenue records certifying cultivable acreage.'),
            'demo_key': 'land_records',
            'aliases': ['land_records', 'land_records_patta', 'patta', 'khasra']
        },
        {
            'doc_type': 'crop_activity_details',
            'name': 'Crop Sowing Pattern & Seasonal Activity Declaration',
            'purpose': 'To calculate scale of finance per acre (Kharif, Rabi, Horticulture) and harvest cash flow cycles.',
            'level': 'required',
            'condition_desc': 'Mandatory declaration of cultivated crop varieties and harvest schedule.',
            'condition_func': lambda app: (True, 'Mandatory crop cultivation schedule determining Scale of Finance.'),
            'demo_key': 'crop_declaration',
            'aliases': ['crop_activity_details', 'crop_declaration', 'sowing_certificate']
        },
        {
            'doc_type': 'bank_statement',
            'name': 'Bank Account Statements / Kisan Credit Card (KCC) Passbook',
            'purpose': 'To audit prior seasonal credit repayments and agricultural subsidy credits.',
            'level': 'required',
            'condition_desc': 'Mandatory 12-month agricultural or savings bank account statement.',
            'condition_func': lambda app: (True, 'Mandatory 12-month banking passbook records.'),
            'demo_key': 'bank_statement',
            'aliases': ['bank_statement', 'kcc_passbook']
        },
        {
            'doc_type': 'income_crop_records',
            'name': 'Crop Sale Receipts / APMC Mandi Invoices',
            'purpose': 'To corroborate agricultural harvest revenue and crop yield pricing.',
            'level': 'optional',
            'condition_desc': 'Optional APMC mandi sale slips or sugar mill payment receipts.',
            'condition_func': lambda app: (False, 'Optional crop sale vouchers to corroborate farm income.'),
            'demo_key': 'income_crop_records',
            'aliases': ['income_crop_records', 'mandi_receipts']
        },
        {
            'doc_type': 'equipment_quotation',
            'name': 'Farm Equipment / Tractor / Solar Pump Quotation',
            'purpose': 'Required for term loans financing agricultural machinery, implements, or micro-irrigation.',
            'level': 'conditional',
            'condition_desc': 'Mandatory if loan is sought for tractor or agricultural machinery financing.',
            'condition_func': lambda app: (
                'equipment' in (app.loan_purpose or '').lower() or 'tractor' in (app.loan_purpose or '').lower() or 'machinery' in (app.loan_purpose or '').lower(),
                'Mandatory dealer proforma invoice for agricultural machinery purchase.'
                if ('equipment' in (app.loan_purpose or '').lower() or 'tractor' in (app.loan_purpose or '').lower() or 'machinery' in (app.loan_purpose or '').lower())
                else 'Not required for seasonal crop cultivation loans.'
            ),
            'demo_key': 'vehicle_quotation',
            'aliases': ['equipment_quotation', 'tractor_quotation']
        },
        {
            'doc_type': 'existing_loan_statements',
            'name': 'Existing Agricultural / Cooperative Loan Records',
            'purpose': 'To check existing institutional or cooperative society debt obligations.',
            'level': 'conditional',
            'condition_desc': 'Required if applicant declared existing loans.',
            'condition_func': lambda app: (
                (app.existing_monthly_emis or 0) > 0,
                f'Required because applicant declared monthly debt obligations of ₹{app.existing_monthly_emis:,.2f}.'
                if (app.existing_monthly_emis or 0) > 0
                else 'Not required since applicant declared zero existing loan obligations.'
            ),
            'demo_key': 'bank_statement',
            'aliases': ['existing_loan_statements']
        },
        {
            'doc_type': 'co_applicant_guarantor',
            'name': 'Co-Applicant / Guarantor Documents',
            'purpose': 'To verify secondary cultivator or family member co-obligant.',
            'level': 'optional',
            'condition_desc': 'Optional guarantor records.',
            'condition_func': lambda app: (False, 'Optional agricultural co-obligant documentation.'),
            'demo_key': 'id_proof',
            'aliases': ['co_applicant_guarantor']
        }
    ]
}


def get_loan_document_checklist(loan_type_code):
    """Retrieve raw document specifications for a loan type"""
    return LOAN_DOCUMENT_CATALOG.get(loan_type_code, LOAN_DOCUMENT_CATALOG['personal_loan'])


def find_uploaded_doc_for_slot(application, slot_def):
    """
    Locates the most appropriate uploaded document for a given slot.
    Checks exact slot_key match, exact document_type match, and alias matches.
    """
    slot_type = slot_def['doc_type']
    aliases = set(slot_def.get('aliases', [])) | {slot_type}

    # First priority: matching slot_key or document_type that is not rejected
    valid_docs = [d for d in application.documents if d.verification_status != 'rejected']
    for d in valid_docs:
        if hasattr(d, 'slot_key') and d.slot_key in aliases:
            return d
        if d.document_type in aliases:
            return d

    # Second priority: any uploaded doc matching alias (even if rejected, for display purposes)
    for d in application.documents:
        if hasattr(d, 'slot_key') and d.slot_key in aliases:
            return d
        if d.document_type in aliases:
            return d

    return None


def evaluate_application_document_slots(application):
    """
    Evaluates all document slots for an application dynamically.
    Returns:
    - slots: list of enriched slot dicts for the UI
    - progress: summary stats (total_required, uploaded_required, progress_pct, can_submit)
    """
    loan_type_code = application.loan_type_code or 'personal_loan'
    catalog = get_loan_document_checklist(loan_type_code)

    slots = []
    total_required = 0
    uploaded_required = 0
    total_uploaded = 0
    missing_required = []

    for item in catalog:
        # Evaluate condition dynamically
        cond_func = item.get('condition_func')
        if cond_func:
            is_active_for_app, condition_explanation = cond_func(application)
        else:
            is_active_for_app = (item['level'] == 'required')
            condition_explanation = item.get('condition_desc', '')

        # Determine effective requirement tier
        if item['level'] == 'required':
            is_mandatory = True
            badge_type = 'required'
            badge_label = 'Required'
        elif item['level'] == 'conditional':
            is_mandatory = is_active_for_app
            badge_type = 'conditional-active' if is_active_for_app else 'conditional-inactive'
            badge_label = 'Conditional — Required' if is_active_for_app else 'Conditional — Not Required'
        else:
            is_mandatory = False
            badge_type = 'optional'
            badge_label = 'Optional'

        if is_mandatory:
            total_required += 1

        # Look for existing uploaded file for this slot
        uploaded_doc = find_uploaded_doc_for_slot(application, item)

        if uploaded_doc:
            total_uploaded += 1
            has_file = True
            file_status = uploaded_doc.verification_status or 'uploaded'
            if is_mandatory and file_status != 'rejected':
                uploaded_required += 1
            elif is_mandatory and file_status == 'rejected':
                missing_required.append(item['name'])
        else:
            has_file = False
            file_status = 'not_uploaded'
            if is_mandatory:
                missing_required.append(item['name'])

        slot_data = {
            'doc_type': item['doc_type'],
            'name': item['name'],
            'purpose': item['purpose'],
            'level': item['level'],
            'is_mandatory': is_mandatory,
            'badge_type': badge_type,
            'badge_label': badge_label,
            'condition_explanation': condition_explanation,
            'accepted_formats': 'PDF, JPG, PNG (Max 16MB)',
            'demo_key': item.get('demo_key', 'id_proof'),
            'has_file': has_file,
            'file_status': file_status,
            'uploaded_doc': uploaded_doc,
            'reviewer_comments': (
                getattr(uploaded_doc, 'reviewer_comments', None) or uploaded_doc.verification_notes
                if uploaded_doc else None
            ),
            'needs_replacement': (
                uploaded_doc is not None and (
                    uploaded_doc.verification_status == 'rejected' or
                    'replace' in (uploaded_doc.verification_notes or '').lower() or
                    'replace' in (getattr(uploaded_doc, 'reviewer_comments', '') or '').lower()
                )
            )
        }
        slots.append(slot_data)

    progress_pct = int(round((uploaded_required / total_required) * 100)) if total_required > 0 else 100
    can_submit = (uploaded_required >= total_required)

    progress = {
        'total_required': total_required,
        'uploaded_required': uploaded_required,
        'total_uploaded': total_uploaded,
        'total_slots': len(slots),
        'progress_pct': progress_pct,
        'can_submit': can_submit,
        'missing_required': missing_required
    }

    return slots, progress
