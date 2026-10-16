import os
import uuid
from datetime import datetime, date
from pathlib import Path
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, current_app, jsonify
)
from werkzeug.utils import secure_filename
from models import (
    db, User, Applicant, LoanType, BankRequirement, LoanApplication,
    UploadedDocument, ExtractedDocumentData, FinancialAssessment,
    RequirementCheckResult, SalaryHistory
)
from routes.auth import login_required
from services.audit_service import log_action
from services.document_processor import DocumentProcessor
from services.financial_calculator import FinancialCalculator
from services.eligibility_engine import EligibilityEngine
from services.ml_scorer import MLScorer
from services.sample_generator import SampleDocGenerator

applicant_bp = Blueprint('applicant', __name__)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def get_current_applicant():
    """Retrieve applicant record for currently logged-in user"""
    if 'user_id' not in session:
        return None
    applicant = Applicant.query.filter_by(user_id=session['user_id']).first()
    if not applicant and session.get('role') == 'applicant':
        user = db.session.get(User, session['user_id'])
        if user:
            applicant = Applicant(
                user_id=user.id,
                full_name=user.full_name,
                email=user.email
            )
            db.session.add(applicant)
            db.session.commit()
    return applicant


@applicant_bp.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('applicant.dashboard'))
    return redirect(url_for('auth.login'))


# -------------------------------------------------------------------------
# Loan Type Selection Screen (Step 1 of Application Flow)
# -------------------------------------------------------------------------
@applicant_bp.route('/select-loan-type')
@login_required
def select_loan_type():
    """Display interactive loan type selection grid with 8 categories"""
    loan_types = LoanType.query.filter_by(is_active=True).all()
    return render_template('select_loan_type.html', loan_types=loan_types)


# -------------------------------------------------------------------------
# Page 2: Dashboard
# -------------------------------------------------------------------------
@applicant_bp.route('/dashboard')
@login_required
def dashboard():
    user = db.session.get(User, session['user_id'])
    role = session.get('role', 'applicant')
    loan_type_filter = request.args.get('loan_type', '').strip()

    all_loan_types = LoanType.query.filter_by(is_active=True).all()

    if role in ('admin', 'bank_officer'):
        # Global banking officer stats
        query = LoanApplication.query
        if loan_type_filter:
            query = query.filter_by(loan_type_code=loan_type_filter)

        total_apps = query.count()
        awaiting_review = query.filter(LoanApplication.status.in_(['submitted', 'manual_review'])).count()
        missing_docs = query.filter_by(status='pending_verification').count()
        docs_needing_verif = UploadedDocument.query.filter_by(verification_status='pending').count()
        meets_reqs = query.filter_by(status='meets_requirements').count()
        does_not_meet = query.filter_by(status='does_not_meet').count()
        
        recent_apps = query.order_by(LoanApplication.created_at.desc()).limit(10).all()
        
        # Loan type counts for Chart.js
        loan_type_counts = {}
        for lt in all_loan_types:
            cnt = LoanApplication.query.filter_by(loan_type_code=lt.code).count()
            loan_type_counts[lt.name] = cnt

        # Monthly salary brackets for visualization
        all_salaries = [a.declared_monthly_salary for a in LoanApplication.query.all() if a.declared_monthly_salary]
        salary_brackets = {
            "< ₹25k": sum(1 for s in all_salaries if s < 25000),
            "₹25k - ₹50k": sum(1 for s in all_salaries if 25000 <= s < 50000),
            "₹50k - ₹100k": sum(1 for s in all_salaries if 50000 <= s < 100000),
            "> ₹100k": sum(1 for s in all_salaries if s >= 100000)
        }

        status_counts = {
            "Meets Requirements": meets_reqs,
            "Does Not Meet": does_not_meet,
            "Pending Verification": missing_docs,
            "Manual Review": awaiting_review
        }

        return render_template(
            'dashboard.html',
            is_staff=True,
            total_apps=total_apps,
            awaiting_review=awaiting_review,
            missing_docs=missing_docs,
            docs_needing_verif=docs_needing_verif,
            meets_reqs=meets_reqs,
            does_not_meet=does_not_meet,
            recent_apps=recent_apps,
            loan_types=all_loan_types,
            loan_type_counts=loan_type_counts,
            status_counts=status_counts,
            salary_brackets=salary_brackets,
            current_loan_type=loan_type_filter
        )
    else:
        # Applicant personal dashboard
        applicant = get_current_applicant()
        my_apps_query = LoanApplication.query.filter_by(applicant_id=applicant.id) if applicant else None
        
        if my_apps_query and loan_type_filter:
            my_apps_query = my_apps_query.filter_by(loan_type_code=loan_type_filter)
            
        my_apps = my_apps_query.order_by(LoanApplication.created_at.desc()).all() if my_apps_query else []
        
        total_apps = len(my_apps)
        meets_reqs = sum(1 for a in my_apps if a.status == 'meets_requirements')
        pending_verif = sum(1 for a in my_apps if a.status == 'pending_verification')
        under_review = sum(1 for a in my_apps if a.status in ('submitted', 'manual_review'))

        return render_template(
            'dashboard.html',
            is_staff=False,
            applicant=applicant,
            my_apps=my_apps,
            total_apps=total_apps,
            meets_reqs=meets_reqs,
            pending_verif=pending_verif,
            under_review=under_review,
            loan_types=all_loan_types,
            current_loan_type=loan_type_filter
        )


# -------------------------------------------------------------------------
# Page 3: Applicant Details Form
# -------------------------------------------------------------------------
@applicant_bp.route('/applicant/details', methods=['GET', 'POST'])
@login_required
def applicant_details():
    applicant = get_current_applicant()
    if not applicant:
        flash("Applicant profile not found.", "danger")
        return redirect(url_for('applicant.dashboard'))

    if request.method == 'POST':
        applicant.full_name = request.form.get('full_name', '').strip()
        applicant.phone = request.form.get('phone', '').strip()
        
        dob_str = request.form.get('date_of_birth')
        if dob_str:
            try:
                applicant.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
            except ValueError:
                pass

        applicant.pan_number = request.form.get('pan_number', '').strip().upper()
        applicant.current_address = request.form.get('current_address', '').strip()
        applicant.permanent_address = request.form.get('permanent_address', '').strip()
        applicant.education_level = request.form.get('education_level', '').strip()
        
        try:
            applicant.backlog_count = int(request.form.get('backlog_count', 0))
        except ValueError:
            applicant.backlog_count = 0
            
        applicant.backlog_details = request.form.get('backlog_details', '').strip()

        db.session.commit()
        log_action("PROFILE_UPDATED", details=f"Applicant {applicant.full_name} updated profile details.")
        flash("Applicant profile details saved successfully.", "success")
        
        return redirect(url_for('applicant.select_loan_type'))

    return render_template('applicant_details.html', applicant=applicant)


# -------------------------------------------------------------------------
# Page 4: Loan Application Form (Loan-Specific Questions)
# -------------------------------------------------------------------------
@applicant_bp.route('/apply', methods=['GET', 'POST'])
@login_required
def apply():
    applicant = get_current_applicant()
    if not applicant:
        flash("Please log in as an applicant to apply for a loan.", "warning")
        return redirect(url_for('applicant.dashboard'))

    all_loan_types = LoanType.query.filter_by(is_active=True).all()
    selected_lt_code = request.form.get('loan_type_code') or request.args.get('loan_type', 'personal_loan')
    selected_lt = LoanType.query.filter_by(code=selected_lt_code, is_active=True).first()
    if not selected_lt and all_loan_types:
        selected_lt = all_loan_types[0]
        selected_lt_code = selected_lt.code

    # Filter bank policies matching this loan type
    bank_policies = BankRequirement.query.filter(
        (BankRequirement.loan_type_code == selected_lt_code) | (BankRequirement.loan_type == selected_lt.name),
        BankRequirement.is_active == True
    ).all()

    # Fallback to all active policies if none specifically mapped
    if not bank_policies:
        bank_policies = BankRequirement.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        policy_id = request.form.get('bank_requirement_id')
        loan_amount = float(request.form.get('loan_amount_requested', 0) or 0)
        tenure = int(request.form.get('loan_tenure_months', 36) or 36)
        purpose = request.form.get('loan_purpose', '').strip()
        
        company = request.form.get('company_name', '').strip()
        designation = request.form.get('designation', '').strip()
        emp_type = request.form.get('employment_type', 'Salaried')
        exp_months = int(request.form.get('experience_months', 12) or 0)
        
        current_salary = float(request.form.get('declared_monthly_salary', 0) or 0)
        prev_salary_val = request.form.get('declared_previous_salary')
        prev_salary = float(prev_salary_val) if prev_salary_val and prev_salary_val.strip() else None
        
        inc_date_val = request.form.get('salary_increase_date')
        inc_date = None
        if inc_date_val:
            try:
                inc_date = datetime.strptime(inc_date_val, '%Y-%m-%d').date()
            except ValueError:
                pass

        existing_emis = float(request.form.get('existing_monthly_emis', 0) or 0)
        credit_val = request.form.get('credit_score')
        credit_score = int(credit_val) if credit_val and credit_val.strip() else None

        policy = BankRequirement.query.get_or_404(policy_id)

        # Collect loan-specific fields based on selected loan type
        loan_specific = {}
        if selected_lt_code == 'gold_loan':
            weight = float(request.form.get('gold_weight_grams', 0) or 0)
            purity = request.form.get('gold_purity_karats', '22K')
            rate_map = {'24K': 7400.0, '22K': 6800.0, '18K': 5500.0}
            gold_rate = rate_map.get(purity, 6800.0)
            loan_specific = {
                "gold_weight_grams": weight,
                "gold_purity_karats": purity,
                "gold_rate_per_gram": gold_rate,
                "estimated_gold_value": round(weight * gold_rate, 2),
                "gold_item_type": request.form.get('gold_item_type', 'Jewelry'),
                "pledge_declaration": request.form.get('pledge_declaration', '')
            }
        elif selected_lt_code == 'home_loan':
            loan_specific = {
                "property_value": float(request.form.get('property_value', 0) or 0),
                "down_payment": float(request.form.get('down_payment', 0) or 0),
                "property_type": request.form.get('property_type', 'Residential Flat'),
                "property_address": request.form.get('property_address', '').strip(),
                "is_approved_builder": 'is_approved_builder' in request.form
            }
        elif selected_lt_code == 'education_loan':
            loan_specific = {
                "course_name": request.form.get('course_name', '').strip(),
                "institution_name": request.form.get('institution_name', '').strip(),
                "study_location": request.form.get('study_location', 'Domestic'),
                "total_course_fee": float(request.form.get('total_course_fee', 0) or 0),
                "co_applicant_name": request.form.get('co_applicant_name', '').strip(),
                "co_applicant_relationship": request.form.get('co_applicant_relationship', 'Parent'),
                "co_applicant_income": float(request.form.get('co_applicant_income', 0) or 0)
            }
        elif selected_lt_code == 'vehicle_loan':
            loan_specific = {
                "vehicle_price": float(request.form.get('vehicle_price', 0) or 0),
                "vehicle_down_payment": float(request.form.get('vehicle_down_payment', 0) or 0),
                "vehicle_type": request.form.get('vehicle_type', 'Car'),
                "vehicle_make_model": request.form.get('vehicle_make_model', '').strip(),
                "is_new_vehicle": 'is_new_vehicle' in request.form
            }
        elif selected_lt_code == 'business_loan':
            loan_specific = {
                "business_name": request.form.get('business_name', '').strip(),
                "business_type": request.form.get('business_type', 'Enterprise'),
                "business_vintage_months": int(request.form.get('business_vintage_months', 24) or 0),
                "annual_turnover": float(request.form.get('annual_turnover', 0) or 0),
                "annual_net_profit": float(request.form.get('annual_net_profit', 0) or 0),
                "gst_number": request.form.get('gst_number', '').strip().upper()
            }
        elif selected_lt_code == 'loan_against_property':
            loan_specific = {
                "property_market_value": float(request.form.get('property_market_value', 0) or 0),
                "property_type": request.form.get('lap_property_type', 'Residential'),
                "property_city": request.form.get('property_city', '').strip()
            }
        elif selected_lt_code == 'agriculture_loan':
            loan_specific = {
                "crop_activity_type": request.form.get('crop_activity_type', 'Crop Cultivation'),
                "land_holding_acres": float(request.form.get('land_holding_acres', 0) or 0),
                "ownership_status": request.form.get('ownership_status', 'Owner'),
                "annual_farm_income": float(request.form.get('annual_farm_income', 0) or 0)
            }

        # Generate unique application number
        app_num = f"FC-{datetime.utcnow().strftime('%Y%m')}-{uuid.uuid4().hex[:6].upper()}"

        application = LoanApplication(
            application_number=app_num,
            applicant_id=applicant.id,
            bank_requirement_id=policy.id,
            loan_type_id=selected_lt.id if selected_lt else None,
            loan_type_code=selected_lt_code,
            policy_version_used=policy.policy_version,
            loan_amount_requested=loan_amount,
            loan_tenure_months=tenure,
            loan_purpose=purpose,
            company_name=company,
            designation=designation,
            employment_type=emp_type,
            experience_months=exp_months,
            declared_monthly_salary=current_salary,
            declared_previous_salary=prev_salary,
            salary_increase_date=inc_date,
            existing_monthly_emis=existing_emis,
            credit_score=credit_score,
            status='submitted'
        )
        application.loan_specific_data = loan_specific
        db.session.add(application)
        db.session.flush()

        # Run initial financial calculation and baseline check
        assessment = FinancialCalculator.compute_assessment(application)
        MLScorer.evaluate(application, assessment)
        EligibilityEngine.run_assessment(application, assessment)

        log_action(
            "APPLICATION_CREATED",
            application_id=application.id,
            details=f"Loan Application {app_num} ({selected_lt.name}) submitted for {policy.bank_name}."
        )

        flash(f"Application {app_num} registered for {selected_lt.name}! Please upload the required documents.", "success")
        return redirect(url_for('applicant.document_upload', app_id=application.id))

    return render_template(
        'loan_application.html',
        applicant=applicant,
        bank_policies=bank_policies,
        all_loan_types=all_loan_types,
        selected_lt=selected_lt,
        selected_lt_code=selected_lt_code
    )


# -------------------------------------------------------------------------
# Page 5: Dedicated Loan-Specific Document Upload & Ingestion
# -------------------------------------------------------------------------
@applicant_bp.route('/application/<int:app_id>/documents', methods=['GET', 'POST'])
@login_required
def document_upload(app_id):
    application = LoanApplication.query.get_or_404(app_id)
    
    # Access control
    if session.get('role') == 'applicant' and application.applicant.user_id != session['user_id']:
        flash("You do not have access to this application.", "danger")
        return redirect(url_for('applicant.dashboard'))

    from services.document_catalog import evaluate_application_document_slots
    policy = application.bank_requirement
    required_docs = policy.required_documents_list
    loan_type = application.loan_type_rel

    # Handle legacy general POST upload (backward compatibility)
    if request.method == 'POST':
        doc_type = request.form.get('document_type', 'salary_slip')
        file = request.files.get('file')

        if not file or file.filename == '':
            flash("No file selected for upload.", "warning")
            return redirect(url_for('applicant.document_upload', app_id=app_id))

        if not allowed_file(file.filename):
            flash("Invalid file type. Only PDF, JPG, and PNG files are accepted.", "danger")
            return redirect(url_for('applicant.document_upload', app_id=app_id))

        orig_filename = secure_filename(file.filename)
        file_ext = orig_filename.rsplit('.', 1)[1].lower()
        storage_filename = f"app_{app_id}_{uuid.uuid4().hex[:8]}_{orig_filename}"
        
        app_upload_dir = Path(current_app.config['UPLOAD_FOLDER']) / f"app_{app_id}"
        app_upload_dir.mkdir(parents=True, exist_ok=True)
        file_dest = app_upload_dir / storage_filename
        
        file.save(str(file_dest))
        file_size = file_dest.stat().st_size

        uploaded_doc = UploadedDocument(
            application_id=application.id,
            user_id=session['user_id'],
            document_type=doc_type,
            slot_key=doc_type,
            original_filename=orig_filename,
            stored_filename=storage_filename,
            file_path=str(file_dest),
            file_size=file_size,
            file_type=file_ext,
            verification_status='pending',
            verification_notes="Uploaded by applicant. Automated OCR extraction completed."
        )
        db.session.add(uploaded_doc)
        db.session.flush()

        raw_text, method, success, error_msg = DocumentProcessor.extract_raw_text(str(file_dest))
        structured = DocumentProcessor.extract_structured_fields(raw_text, doc_type)

        extracted_record = ExtractedDocumentData(
            document_id=uploaded_doc.id,
            application_id=application.id,
            extraction_method=method,
            raw_text=raw_text,
            applicant_name_extracted=structured.get("applicant_name"),
            company_name_extracted=structured.get("company_name"),
            salary_amount_extracted=structured.get("salary_amount"),
            salary_month_extracted=structured.get("salary_month"),
            deductions_extracted=structured.get("deductions"),
            bank_credits_extracted=structured.get("bank_credits"),
            document_date_extracted=structured.get("document_date"),
            confidence_score=structured.get("confidence_score", 0.0)
        )
        db.session.add(extracted_record)

        if doc_type == 'salary_slip' and structured.get("salary_amount"):
            srec = SalaryHistory(
                application_id=application.id,
                month_year=structured.get("salary_month") or datetime.utcnow().strftime("%b %Y"),
                net_salary=structured.get("salary_amount"),
                deductions=structured.get("deductions", 0.0) or 0.0,
                employer_name=structured.get("company_name") or application.company_name,
                bank_credit_amount=structured.get("bank_credits"),
                is_verified=False,
                source_document_id=uploaded_doc.id
            )
            db.session.add(srec)

        db.session.commit()

        assessment = FinancialCalculator.compute_assessment(application)
        MLScorer.evaluate(application, assessment)
        EligibilityEngine.run_assessment(application, assessment)

        log_action(
            "DOCUMENT_UPLOADED",
            application_id=application.id,
            details=f"Uploaded {doc_type} ({orig_filename}). Confidence: {structured.get('confidence_score')}%."
        )

        flash(f"'{orig_filename}' uploaded and parsed successfully!", "success")
        return redirect(url_for('applicant.document_upload', app_id=app_id))

    slots, doc_progress = evaluate_application_document_slots(application)
    uploaded_types = {d.document_type: d for d in application.documents}

    return render_template(
        'document_upload.html',
        application=application,
        policy=policy,
        loan_type=loan_type,
        slots=slots,
        doc_progress=doc_progress,
        required_docs=required_docs,
        uploaded_types=uploaded_types
    )


# Individual Slot Upload & Replace Route
@applicant_bp.route('/application/<int:app_id>/upload-slot', methods=['POST'])
@login_required
def upload_document_slot(app_id):
    """Uploads or replaces a document specifically for a designated loan checklist slot"""
    application = LoanApplication.query.get_or_404(app_id)
    if session.get('role') == 'applicant' and application.applicant.user_id != session['user_id']:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('applicant.dashboard'))

    slot_key = request.form.get('slot_key', 'salary_slip')
    file = request.files.get('file')

    if not file or file.filename == '':
        flash("Please select a file to upload.", "warning")
        return redirect(url_for('applicant.document_upload', app_id=app_id))

    if not allowed_file(file.filename):
        flash("Invalid file format. Only PDF, JPG, and PNG documents are allowed.", "danger")
        return redirect(url_for('applicant.document_upload', app_id=app_id))

    orig_filename = secure_filename(file.filename)
    file_ext = orig_filename.rsplit('.', 1)[1].lower()
    storage_filename = f"app_{app_id}_{slot_key}_{uuid.uuid4().hex[:8]}_{orig_filename}"

    app_upload_dir = Path(current_app.config['UPLOAD_FOLDER']) / f"app_{app_id}"
    app_upload_dir.mkdir(parents=True, exist_ok=True)
    file_dest = app_upload_dir / storage_filename
    file.save(str(file_dest))
    file_size = file_dest.stat().st_size

    # Check if a document already exists for this slot
    existing_doc = UploadedDocument.query.filter_by(
        application_id=application.id
    ).filter(
        (UploadedDocument.slot_key == slot_key) | (UploadedDocument.document_type == slot_key)
    ).first()

    if existing_doc:
        # Archive into replacement history
        history = existing_doc.replacement_history
        history.append({
            'replaced_filename': existing_doc.original_filename,
            'replaced_at': datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
            'previous_status': existing_doc.verification_status,
            'reviewer_notes': existing_doc.reviewer_comments or existing_doc.verification_notes
        })
        existing_doc.replacement_history = history
        existing_doc.replacement_count = (existing_doc.replacement_count or 0) + 1
        existing_doc.original_filename = orig_filename
        existing_doc.stored_filename = storage_filename
        existing_doc.file_path = str(file_dest)
        existing_doc.file_size = file_size
        existing_doc.file_type = file_ext
        existing_doc.verification_status = 'pending'
        existing_doc.verification_notes = "Replacement document uploaded by applicant. Pending verification."
        existing_doc.uploaded_at = datetime.utcnow()
        doc_record = existing_doc
    else:
        doc_record = UploadedDocument(
            application_id=application.id,
            user_id=session['user_id'],
            document_type=slot_key,
            slot_key=slot_key,
            original_filename=orig_filename,
            stored_filename=storage_filename,
            file_path=str(file_dest),
            file_size=file_size,
            file_type=file_ext,
            verification_status='pending',
            verification_notes="Uploaded by applicant. Pending verification."
        )
        db.session.add(doc_record)
        db.session.flush()

    # Automated PyMuPDF & OCR extraction
    raw_text, method, success, error_msg = DocumentProcessor.extract_raw_text(str(file_dest))
    structured = DocumentProcessor.extract_structured_fields(raw_text, slot_key)

    if doc_record.extracted_record:
        ext = doc_record.extracted_record
        ext.extraction_method = method
        ext.raw_text = raw_text
        ext.applicant_name_extracted = structured.get("applicant_name")
        ext.company_name_extracted = structured.get("company_name")
        ext.salary_amount_extracted = structured.get("salary_amount")
        ext.salary_month_extracted = structured.get("salary_month")
        ext.deductions_extracted = structured.get("deductions")
        ext.bank_credits_extracted = structured.get("bank_credits")
        ext.document_date_extracted = structured.get("document_date")
        ext.confidence_score = structured.get("confidence_score", 0.0)
        ext.updated_at = datetime.utcnow()
    else:
        ext = ExtractedDocumentData(
            document_id=doc_record.id,
            application_id=application.id,
            extraction_method=method,
            raw_text=raw_text,
            applicant_name_extracted=structured.get("applicant_name"),
            company_name_extracted=structured.get("company_name"),
            salary_amount_extracted=structured.get("salary_amount"),
            salary_month_extracted=structured.get("salary_month"),
            deductions_extracted=structured.get("deductions"),
            bank_credits_extracted=structured.get("bank_credits"),
            document_date_extracted=structured.get("document_date"),
            confidence_score=structured.get("confidence_score", 0.0)
        )
        db.session.add(ext)

    if slot_key == 'salary_slip' and structured.get("salary_amount"):
        srec = SalaryHistory.query.filter_by(source_document_id=doc_record.id).first()
        if not srec:
            srec = SalaryHistory(
                application_id=application.id,
                month_year=structured.get("salary_month") or datetime.utcnow().strftime("%b %Y"),
                net_salary=structured.get("salary_amount"),
                deductions=structured.get("deductions", 0.0) or 0.0,
                employer_name=structured.get("company_name") or application.company_name,
                bank_credit_amount=structured.get("bank_credits"),
                is_verified=False,
                source_document_id=doc_record.id
            )
            db.session.add(srec)
        else:
            srec.net_salary = structured.get("salary_amount")
            srec.deductions = structured.get("deductions", 0.0) or 0.0
            srec.employer_name = structured.get("company_name") or application.company_name

    db.session.commit()

    # Recalculate assessment
    assessment = FinancialCalculator.compute_assessment(application)
    MLScorer.evaluate(application, assessment)
    EligibilityEngine.run_assessment(application, assessment)

    action_label = "replaced" if existing_doc and existing_doc.replacement_count > 0 else "uploaded"
    log_action(
        "DOCUMENT_UPLOADED",
        application_id=application.id,
        details=f"Document '{orig_filename}' {action_label} for slot '{slot_key}'."
    )
    flash(f"Document '{orig_filename}' successfully {action_label} and parsed!", "success")
    return redirect(url_for('applicant.document_upload', app_id=app_id))


# Remove Document Route
@applicant_bp.route('/application/<int:app_id>/document/<int:doc_id>/remove', methods=['POST'])
@login_required
def remove_document(app_id, doc_id):
    """Removes an uploaded document from its slot and recalculates assessment"""
    application = LoanApplication.query.get_or_404(app_id)
    doc = UploadedDocument.query.get_or_404(doc_id)

    if session.get('role') == 'applicant' and application.applicant.user_id != session['user_id']:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('applicant.dashboard'))

    filename = doc.original_filename
    doc_type = doc.document_type

    # Delete physical file if exists
    try:
        p = Path(doc.file_path)
        if p.exists() and "sample_docs" not in str(p):
            p.unlink(missing_ok=True)
    except Exception:
        pass

    db.session.delete(doc)
    db.session.commit()

    # Recalculate assessment
    assessment = FinancialCalculator.compute_assessment(application)
    MLScorer.evaluate(application, assessment)
    EligibilityEngine.run_assessment(application, assessment)

    log_action(
        "DOCUMENT_REMOVED",
        application_id=application.id,
        details=f"Removed document #{doc_id} ({doc_type}: {filename})."
    )
    flash(f"Document '{filename}' was removed from the application.", "info")
    return redirect(url_for('applicant.document_upload', app_id=app_id))


# Submit All Documents for Underwriting Route
@applicant_bp.route('/application/<int:app_id>/submit-documents', methods=['POST'])
@login_required
def submit_application_documents(app_id):
    """Validates that all mandatory documents are uploaded and submits application for final underwriting"""
    application = LoanApplication.query.get_or_404(app_id)
    if session.get('role') == 'applicant' and application.applicant.user_id != session['user_id']:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('applicant.dashboard'))

    from services.document_catalog import evaluate_application_document_slots
    slots, doc_progress = evaluate_application_document_slots(application)

    if not doc_progress['can_submit']:
        missing_count = len(doc_progress['missing_required'])
        flash(
            f"Cannot submit yet: {missing_count} mandatory document(s) are still pending. Please upload all required files.",
            "warning"
        )
        return redirect(url_for('applicant.document_upload', app_id=app_id))

    # Recalculate full underwriting
    assessment = FinancialCalculator.compute_assessment(application)
    MLScorer.evaluate(application, assessment)
    overall_outcome, checks = EligibilityEngine.run_assessment(application, assessment)

    log_action(
        "DOCUMENTS_SUBMITTED",
        application_id=application.id,
        details=f"Applicant submitted all {doc_progress['uploaded_required']} required documents for underwriting. Outcome: {overall_outcome}."
    )
    flash("All required documents have been uploaded! Your application has been submitted for automated underwriting.", "success")
    return redirect(url_for('applicant.eligibility_results', app_id=app_id))


# Quick Demo Document Attacher
@applicant_bp.route('/application/<int:app_id>/attach-demo-doc', methods=['POST'])
@login_required
def attach_demo_doc(app_id):
    """Convenience helper to attach synthetic sample PDF for immediate testing"""
    application = LoanApplication.query.get_or_404(app_id)
    doc_type = request.form.get('demo_doc_type', 'salary_slip')
    slot_key = request.form.get('slot_key', doc_type)

    sample_dir = Path(current_app.config['UPLOAD_FOLDER']) / "sample_docs"
    sample_files = SampleDocGenerator.ensure_sample_documents(sample_dir)

    target_file = sample_files.get(doc_type)
    if not target_file or not Path(target_file).exists():
        target_file = sample_files.get(slot_key)
    if not target_file or not Path(target_file).exists():
        target_file = sample_files.get("salary_slip")

    if not target_file or not Path(target_file).exists():
        flash("Synthetic sample file not found on disk.", "warning")
        return redirect(url_for('applicant.document_upload', app_id=app_id))

    orig_name = Path(target_file).name
    file_size = Path(target_file).stat().st_size

    # Check if document already exists for this slot
    existing_doc = UploadedDocument.query.filter_by(
        application_id=application.id
    ).filter(
        (UploadedDocument.slot_key == slot_key) | (UploadedDocument.document_type == slot_key) | (UploadedDocument.document_type == doc_type)
    ).first()

    if existing_doc:
        existing_doc.original_filename = orig_name
        existing_doc.stored_filename = orig_name
        existing_doc.file_path = str(target_file)
        existing_doc.file_size = file_size
        existing_doc.file_type = "pdf"
        existing_doc.verification_status = 'verified'
        existing_doc.verification_notes = "Synthetic demo document attached for automated verification."
        uploaded_doc = existing_doc
    else:
        uploaded_doc = UploadedDocument(
            application_id=application.id,
            user_id=session['user_id'],
            document_type=doc_type,
            slot_key=slot_key,
            original_filename=orig_name,
            stored_filename=orig_name,
            file_path=str(target_file),
            file_size=file_size,
            file_type="pdf",
            verification_status='verified',
            verification_notes="Synthetic demo document attached for automated verification."
        )
        db.session.add(uploaded_doc)
        db.session.flush()

    raw_text, method, _, _ = DocumentProcessor.extract_raw_text(str(target_file))
    structured = DocumentProcessor.extract_structured_fields(raw_text, doc_type)

    if uploaded_doc.extracted_record:
        ext = uploaded_doc.extracted_record
        ext.extraction_method = method
        ext.raw_text = raw_text
        ext.applicant_name_extracted = structured.get("applicant_name")
        ext.company_name_extracted = structured.get("company_name")
        ext.salary_amount_extracted = structured.get("salary_amount")
        ext.salary_month_extracted = structured.get("salary_month")
        ext.deductions_extracted = structured.get("deductions")
        ext.bank_credits_extracted = structured.get("bank_credits")
        ext.document_date_extracted = structured.get("document_date")
        ext.confidence_score = structured.get("confidence_score", 0.0)
    else:
        ext = ExtractedDocumentData(
            document_id=uploaded_doc.id,
            application_id=application.id,
            extraction_method=method,
            raw_text=raw_text,
            applicant_name_extracted=structured.get("applicant_name"),
            company_name_extracted=structured.get("company_name"),
            salary_amount_extracted=structured.get("salary_amount"),
            salary_month_extracted=structured.get("salary_month"),
            deductions_extracted=structured.get("deductions"),
            bank_credits_extracted=structured.get("bank_credits"),
            document_date_extracted=structured.get("document_date"),
            confidence_score=structured.get("confidence_score", 0.0)
        )
        db.session.add(ext)

    if doc_type == 'salary_slip' and structured.get("salary_amount"):
        srec = SalaryHistory.query.filter_by(source_document_id=uploaded_doc.id).first()
        if not srec:
            srec = SalaryHistory(
                application_id=application.id,
                month_year=structured.get("salary_month") or "Aug 2024",
                net_salary=structured.get("salary_amount"),
                deductions=structured.get("deductions", 0.0) or 0.0,
                employer_name=structured.get("company_name") or application.company_name,
                is_verified=True,
                source_document_id=uploaded_doc.id
            )
            db.session.add(srec)
        else:
            srec.net_salary = structured.get("salary_amount")
            srec.is_verified = True

    db.session.commit()

    assessment = FinancialCalculator.compute_assessment(application)
    MLScorer.evaluate(application, assessment)
    EligibilityEngine.run_assessment(application, assessment)

    flash(f"Sample {doc_type.replace('_', ' ').title()} attached and analyzed automatically!", "success")
    return redirect(url_for('applicant.document_upload', app_id=app_id))


# -------------------------------------------------------------------------
# Page 6: Salary & Asset Financial Analysis
# -------------------------------------------------------------------------
@applicant_bp.route('/application/<int:app_id>/salary-analysis')
@login_required
def salary_analysis(app_id):
    application = LoanApplication.query.get_or_404(app_id)
    assessment = application.financial_assessment
    if not assessment:
        assessment = FinancialCalculator.compute_assessment(application)
        MLScorer.evaluate(application, assessment)

    growth = FinancialCalculator.evaluate_salary_growth(
        assessment.current_verified_income,
        assessment.previous_salary
    )

    return render_template(
        'salary_analysis.html',
        application=application,
        assessment=assessment,
        growth=growth
    )


# -------------------------------------------------------------------------
# Page 7: Document Verification & Discrepancy Cross-Check
# -------------------------------------------------------------------------
@applicant_bp.route('/application/<int:app_id>/verify-documents')
@login_required
def verify_documents(app_id):
    application = LoanApplication.query.get_or_404(app_id)
    
    extracted_records = [
        doc.extracted_record for doc in application.documents
        if doc.extracted_record
    ]
    
    cross_check = DocumentProcessor.cross_check_application(
        application, extracted_records
    )

    return render_template(
        'document_verification.html',
        application=application,
        documents=application.documents,
        cross_check=cross_check
    )


# -------------------------------------------------------------------------
# Page 8: Explainable Eligibility Results
# -------------------------------------------------------------------------
@applicant_bp.route('/application/<int:app_id>/results')
@login_required
def eligibility_results(app_id):
    application = LoanApplication.query.get_or_404(app_id)
    assessment = application.financial_assessment
    if not assessment:
        assessment = FinancialCalculator.compute_assessment(application)
        MLScorer.evaluate(application, assessment)
        EligibilityEngine.run_assessment(application, assessment)

    checks = RequirementCheckResult.query.filter_by(application_id=app_id).order_by(RequirementCheckResult.order_index).all()
    if not checks:
        _, checks = EligibilityEngine.run_assessment(application, assessment)

    pass_count = sum(1 for c in checks if c.status == 'PASS')
    fail_count = sum(1 for c in checks if c.status == 'FAIL')
    pending_count = sum(1 for c in checks if c.status == 'PENDING_VERIFICATION')
    review_count = sum(1 for c in checks if c.status == 'MANUAL_REVIEW')

    uploaded_doc_types = {d.document_type for d in application.documents}
    required_docs = application.bank_requirement.required_documents_list
    missing_docs = [d for d in required_docs if d not in uploaded_doc_types]

    extracted_records = [d.extracted_record for d in application.documents if d.extracted_record]
    cross_check = DocumentProcessor.cross_check_application(application, extracted_records)

    return render_template(
        'eligibility_results.html',
        application=application,
        assessment=assessment,
        checks=checks,
        pass_count=pass_count,
        fail_count=fail_count,
        pending_count=pending_count,
        review_count=review_count,
        required_docs=required_docs,
        missing_docs=missing_docs,
        cross_check=cross_check
    )


# -------------------------------------------------------------------------
# Page 11: Application History
# -------------------------------------------------------------------------
@applicant_bp.route('/applications')
@login_required
def application_history():
    role = session.get('role', 'applicant')
    loan_type_filter = request.args.get('loan_type', '').strip()
    all_loan_types = LoanType.query.filter_by(is_active=True).all()

    query = LoanApplication.query
    if role == 'applicant':
        applicant = get_current_applicant()
        query = query.filter_by(applicant_id=applicant.id) if applicant else query.filter_by(id=-1)

    if loan_type_filter:
        query = query.filter_by(loan_type_code=loan_type_filter)

    apps = query.order_by(LoanApplication.created_at.desc()).all()

    return render_template(
        'application_history.html',
        applications=apps,
        is_staff=(role in ('admin', 'bank_officer')),
        loan_types=all_loan_types,
        current_loan_type=loan_type_filter
    )
