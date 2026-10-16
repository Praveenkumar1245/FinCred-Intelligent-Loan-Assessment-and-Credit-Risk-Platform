import os
from datetime import datetime
from pathlib import Path
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, send_file, jsonify
)
from models import (
    db, User, LoanApplication, UploadedDocument, ExtractedDocumentData,
    ReviewNote, SalaryHistory
)
from routes.auth import login_required, roles_required
from services.audit_service import log_action
from services.financial_calculator import FinancialCalculator
from services.eligibility_engine import EligibilityEngine
from services.ml_scorer import MLScorer

officer_bp = Blueprint('officer', __name__)

# -------------------------------------------------------------------------
# Page 10: Bank Officer Review Queue & Single Application Review
# -------------------------------------------------------------------------
@officer_bp.route('/officer/queue')
@login_required
@roles_required('bank_officer', 'admin')
def officer_queue():
    """List of applications requiring bank officer scrutiny"""
    status_filter = request.args.get('status')
    query = LoanApplication.query

    if status_filter:
        query = query.filter_by(status=status_filter)
    
    applications = query.order_by(LoanApplication.created_at.desc()).all()
    return render_template('officer_queue.html', applications=applications, current_filter=status_filter)


@officer_bp.route('/officer/review/<int:app_id>')
@login_required
@roles_required('bank_officer', 'admin')
def review_application(app_id):
    """Detailed bank officer review workbench for an application"""
    application = LoanApplication.query.get_or_404(app_id)
    assessment = application.financial_assessment
    if not assessment:
        assessment = FinancialCalculator.compute_assessment(application)
        MLScorer.evaluate(application, assessment)
        EligibilityEngine.run_assessment(application, assessment)

    checks = application.requirement_checks
    notes = application.review_notes

    return render_template(
        'officer_review.html',
        application=application,
        assessment=assessment,
        checks=checks,
        notes=notes
    )


# -------------------------------------------------------------------------
# Document File Serving / Preview
# -------------------------------------------------------------------------
@officer_bp.route('/document/<int:doc_id>/preview')
@login_required
def preview_document(doc_id):
    """Secure document file preview with role validation"""
    doc = UploadedDocument.query.get_or_404(doc_id)
    
    # Restrict applicant to their own docs
    if session.get('role') == 'applicant' and doc.user_id != session['user_id']:
        flash("Unauthorized document access.", "danger")
        return redirect(url_for('applicant.dashboard'))

    if not Path(doc.file_path).exists():
        flash("Document file not found on disk.", "warning")
        return redirect(request.referrer or url_for('applicant.dashboard'))

    mimetypes = {
        'pdf': 'application/pdf',
        'png': 'image/png',
        'jpg': 'image/jpeg',
        'jpeg': 'image/jpeg'
    }
    mime = mimetypes.get(doc.file_type.lower(), 'application/octet-stream')
    return send_file(doc.file_path, mimetype=mime)


# -------------------------------------------------------------------------
# Officer Action: Verify or Reject Document
# -------------------------------------------------------------------------
@officer_bp.route('/officer/document/<int:doc_id>/verify', methods=['POST'])
@login_required
@roles_required('bank_officer', 'admin')
def verify_document_status(doc_id):
    doc = UploadedDocument.query.get_or_404(doc_id)
    new_status = request.form.get('verification_status', 'verified')
    notes = request.form.get('verification_notes', '').strip()

    doc.verification_status = new_status
    doc.verification_notes = notes
    doc.verified_at = datetime.utcnow()
    doc.verified_by_id = session['user_id']
    
    # If verified salary slip, verify corresponding salary history entry
    if doc.document_type == 'salary_slip' and new_status == 'verified':
        srec = SalaryHistory.query.filter_by(source_document_id=doc.id).first()
        if srec:
            srec.is_verified = True

    db.session.commit()

    # Re-evaluate application calculations & requirements
    app_obj = doc.application
    assessment = FinancialCalculator.compute_assessment(app_obj)
    MLScorer.evaluate(app_obj, assessment)
    EligibilityEngine.run_assessment(app_obj, assessment)

    log_action(
        "DOCUMENT_VERIFIED",
        application_id=app_obj.id,
        details=f"Officer marked document #{doc.id} ({doc.document_type}) as '{new_status}'. Notes: {notes}"
    )

    flash(f"Document marked as '{new_status}'. Financial calculations updated.", "success")
    return redirect(url_for('officer.review_application', app_id=doc.application_id))


# -------------------------------------------------------------------------
# Officer Action: Correct / Override Extracted Data
# -------------------------------------------------------------------------
@officer_bp.route('/officer/extraction/<int:ext_id>/override', methods=['POST'])
@login_required
@roles_required('bank_officer', 'admin')
def override_extraction(ext_id):
    ext = ExtractedDocumentData.query.get_or_404(ext_id)
    
    # Get form values
    corrected_salary = request.form.get('salary_amount_extracted')
    corrected_company = request.form.get('company_name_extracted', '').strip()
    corrected_name = request.form.get('applicant_name_extracted', '').strip()
    override_notes = request.form.get('officer_override_notes', '').strip()

    old_salary = ext.salary_amount_extracted
    if corrected_salary and corrected_salary.strip():
        try:
            ext.salary_amount_extracted = float(corrected_salary)
        except ValueError:
            pass

    if corrected_company:
        ext.company_name_extracted = corrected_company
    if corrected_name:
        ext.applicant_name_extracted = corrected_name

    ext.is_overridden_by_officer = True
    ext.officer_override_notes = override_notes
    ext.updated_at = datetime.utcnow()

    # Update linked salary history record if exists
    srec = SalaryHistory.query.filter_by(source_document_id=ext.document_id).first()
    if srec and ext.salary_amount_extracted:
        srec.net_salary = ext.salary_amount_extracted
        srec.employer_name = ext.company_name_extracted

    db.session.commit()

    # Recalculate assessment
    app_obj = ext.application
    assessment = FinancialCalculator.compute_assessment(app_obj)
    MLScorer.evaluate(app_obj, assessment)
    EligibilityEngine.run_assessment(app_obj, assessment)

    log_action(
        "EXTRACTION_OVERRIDDEN",
        application_id=app_obj.id,
        details=(
            f"Officer corrected extraction for doc #{ext.document_id}. "
            f"Salary changed from {old_salary} to {ext.salary_amount_extracted}. Notes: {override_notes}"
        )
    )

    flash("Extracted data corrected and updated. System recalculation finished.", "success")
    return redirect(url_for('officer.review_application', app_id=ext.application_id))


# -------------------------------------------------------------------------
# Officer Action: Record Final Decision
# -------------------------------------------------------------------------
@officer_bp.route('/officer/application/<int:app_id>/decision', methods=['POST'])
@login_required
@roles_required('bank_officer', 'admin')
def record_decision(app_id):
    application = LoanApplication.query.get_or_404(app_id)
    decision = request.form.get('officer_decision') # 'approved', 'rejected', 'more_info_needed'
    reason = request.form.get('decision_reason', '').strip()

    if not decision or not reason:
        flash("Please provide both a decision outcome and a formal justification reason.", "danger")
        return redirect(url_for('officer.review_application', app_id=app_id))

    application.officer_decision = decision
    application.decision_reason = reason
    application.decision_date = datetime.utcnow()
    application.assigned_officer_id = session['user_id']

    # Update status accordingly
    if decision == 'approved':
        application.status = 'meets_requirements'
    elif decision == 'rejected':
        application.status = 'does_not_meet'
    elif decision == 'more_info_needed':
        application.status = 'pending_verification'

    # Append to review notes
    note = ReviewNote(
        application_id=application.id,
        officer_id=session['user_id'],
        note_type='decision',
        content=f"Formal Decision Recorded: [{decision.upper()}] - {reason}"
    )
    db.session.add(note)
    db.session.commit()

    log_action(
        "DECISION_RECORDED",
        application_id=application.id,
        details=f"Officer recorded decision: {decision}. Reason: {reason}"
    )

    flash(f"Final decision '{decision.replace('_', ' ').title()}' recorded with audit log.", "success")
    return redirect(url_for('officer.review_application', app_id=app_id))


# -------------------------------------------------------------------------
# Officer Action: Add Review Note / Request Documents
# -------------------------------------------------------------------------
@officer_bp.route('/officer/application/<int:app_id>/add-note', methods=['POST'])
@login_required
@roles_required('bank_officer', 'admin')
def add_note(app_id):
    application = LoanApplication.query.get_or_404(app_id)
    content = request.form.get('note_content', '').strip()
    note_type = request.form.get('note_type', 'general')

    if content:
        note = ReviewNote(
            application_id=application.id,
            officer_id=session['user_id'],
            note_type=note_type,
            content=content
        )
        db.session.add(note)
        
        # If requesting missing document, update status to pending_verification
        if note_type == 'verification_query':
            application.status = 'pending_verification'
            
        db.session.commit()

        log_action(
            "REVIEW_NOTE_ADDED",
            application_id=application.id,
            details=f"Officer added {note_type} note: {content[:100]}"
        )
        flash("Officer note recorded.", "info")

    return redirect(url_for('officer.review_application', app_id=app_id))
