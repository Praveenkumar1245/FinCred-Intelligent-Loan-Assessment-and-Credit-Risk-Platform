import json
from datetime import datetime
from flask import (
    Blueprint, render_template, request, redirect, url_for,
    flash, session, jsonify
)
from models import db, User, LoanType, BankRequirement, AuditLog
from routes.auth import login_required, roles_required
from services.audit_service import log_action

admin_bp = Blueprint('admin', __name__)

# -------------------------------------------------------------------------
# Admin: Loan Types Configuration (New Feature 1)
# -------------------------------------------------------------------------
@admin_bp.route('/admin/loan-types')
@login_required
@roles_required('admin')
def loan_types():
    all_types = LoanType.query.order_by(LoanType.id).all()
    return render_template('admin_loan_types.html', loan_types=all_types)


@admin_bp.route('/admin/loan-types/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def create_loan_type():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().lower().replace(' ', '_')
        icon = request.form.get('icon', 'bi-cash-coin').strip()
        desc = request.form.get('description', '').strip()
        ltv = float(request.form.get('default_ltv_cap', 75.0) or 75.0)
        rate = float(request.form.get('default_interest_rate', 10.5) or 10.5)
        docs = request.form.getlist('required_documents')

        if LoanType.query.filter_by(code=code).first():
            flash(f"A loan category with code '{code}' already exists.", "warning")
            return redirect(url_for('admin.create_loan_type'))

        lt = LoanType(
            code=code,
            name=name,
            icon=icon,
            description=desc,
            default_ltv_cap=ltv,
            default_interest_rate=rate,
            is_active=True
        )
        lt.required_documents_list = docs if docs else ['id_proof', 'bank_statement']
        db.session.add(lt)
        db.session.commit()

        log_action("LOAN_TYPE_CREATED", details=f"Admin created new loan type '{name}' ({code}).")
        flash(f"Loan category '{name}' created successfully.", "success")
        return redirect(url_for('admin.loan_types'))

    return render_template('admin_loan_type_form.html', loan_type=None)


@admin_bp.route('/admin/loan-types/<int:lt_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def edit_loan_type(lt_id):
    lt = LoanType.query.get_or_404(lt_id)

    if request.method == 'POST':
        lt.name = request.form.get('name', '').strip()
        lt.icon = request.form.get('icon', 'bi-cash-coin').strip()
        lt.description = request.form.get('description', '').strip()
        lt.default_ltv_cap = float(request.form.get('default_ltv_cap', 75.0) or 75.0)
        lt.default_interest_rate = float(request.form.get('default_interest_rate', 10.5) or 10.5)
        lt.is_active = 'is_active' in request.form
        docs = request.form.getlist('required_documents')
        if docs:
            lt.required_documents_list = docs

        lt.updated_at = datetime.utcnow()
        db.session.commit()

        log_action("LOAN_TYPE_UPDATED", details=f"Admin updated loan category '{lt.name}'.")
        flash(f"Loan category '{lt.name}' updated.", "success")
        return redirect(url_for('admin.loan_types'))

    return render_template('admin_loan_type_form.html', loan_type=lt)


@admin_bp.route('/admin/loan-types/<int:lt_id>/toggle', methods=['POST'])
@login_required
@roles_required('admin')
def toggle_loan_type(lt_id):
    lt = LoanType.query.get_or_404(lt_id)
    lt.is_active = not lt.is_active
    db.session.commit()
    log_action("LOAN_TYPE_STATUS_TOGGLED", details=f"Loan category '{lt.name}' active status set to {lt.is_active}.")
    flash(f"Loan category '{lt.name}' is now {'Active' if lt.is_active else 'Disabled'}.", "info")
    return redirect(url_for('admin.loan_types'))


# -------------------------------------------------------------------------
# Page 9: Bank Requirements Configuration
# -------------------------------------------------------------------------
@admin_bp.route('/admin/bank-requirements')
@login_required
@roles_required('admin')
def bank_requirements():
    policies = BankRequirement.query.order_by(BankRequirement.bank_name, BankRequirement.loan_type).all()
    all_loan_types = LoanType.query.all()
    return render_template('bank_requirements.html', policies=policies, loan_types=all_loan_types)


@admin_bp.route('/admin/bank-requirements/new', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def create_bank_requirement():
    loan_types = LoanType.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        bank_name = request.form.get('bank_name', '').strip()
        loan_type_code = request.form.get('loan_type_code', 'personal_loan').strip()
        policy_code = request.form.get('policy_code', '').strip().upper()
        description = request.form.get('description', '').strip()
        
        lt_obj = LoanType.query.filter_by(code=loan_type_code).first()
        loan_type_name = lt_obj.name if lt_obj else loan_type_code.replace('_', ' ').title()

        min_age = int(request.form.get('min_age', 21))
        max_age = int(request.form.get('max_age', 65))
        min_monthly_income = float(request.form.get('min_monthly_income', 25000.0))
        min_employment_months = int(request.form.get('min_employment_months', 12))
        max_dti_ratio = float(request.form.get('max_dti_ratio', 50.0))
        min_credit_score = int(request.form.get('min_credit_score', 680))
        max_loan_amount = float(request.form.get('max_loan_amount', 1500000.0))
        max_loan_tenure_months = int(request.form.get('max_loan_tenure_months', 60))
        interest_rate_pct = float(request.form.get('interest_rate_pct', 10.5))
        
        # Loan-specific thresholds
        max_ltv = float(request.form.get('max_ltv_ratio', 75.0) or 75.0)
        min_down_pct = float(request.form.get('min_down_payment_pct', 15.0) or 15.0)
        min_vintage = int(request.form.get('min_business_vintage_months', 24) or 24)
        min_turnover = float(request.form.get('min_annual_turnover', 2000000.0) or 2000000.0)
        min_acres = float(request.form.get('min_land_acres', 2.0) or 2.0)

        backlog_enabled = 'backlog_policy_enabled' in request.form
        max_backlogs = int(request.form.get('max_allowed_backlogs', 0))
        backlog_note = request.form.get('backlog_policy_note', '').strip()
        
        selected_docs = request.form.getlist('required_documents')
        if not selected_docs:
            selected_docs = lt_obj.required_documents_list if lt_obj else ['salary_slip', 'bank_statement', 'id_proof']

        new_policy = BankRequirement(
            bank_name=bank_name,
            loan_type_id=lt_obj.id if lt_obj else None,
            loan_type_code=loan_type_code,
            loan_type=loan_type_name,
            policy_code=policy_code,
            policy_version=1,
            description=description,
            min_age=min_age,
            max_age=max_age,
            min_monthly_income=min_monthly_income,
            min_employment_months=min_employment_months,
            max_dti_ratio=max_dti_ratio,
            min_credit_score=min_credit_score,
            max_loan_amount=max_loan_amount,
            max_loan_tenure_months=max_loan_tenure_months,
            interest_rate_pct=interest_rate_pct,
            max_ltv_ratio=max_ltv,
            min_down_payment_pct=min_down_pct,
            min_business_vintage_months=min_vintage,
            min_annual_turnover=min_turnover,
            min_land_acres=min_acres,
            backlog_policy_enabled=backlog_enabled,
            max_allowed_backlogs=max_backlogs,
            backlog_policy_note=backlog_note,
            is_sample_policy=False,
            is_active=True
        )
        new_policy.required_documents_list = selected_docs

        db.session.add(new_policy)
        db.session.commit()

        log_action("POLICY_CREATED", details=f"Admin created bank requirement policy '{policy_code}' for {bank_name} ({loan_type_name}).")
        flash(f"Policy '{bank_name} - {loan_type_name}' created successfully.", "success")
        return redirect(url_for('admin.bank_requirements'))

    return render_template('bank_requirement_form.html', policy=None, loan_types=loan_types)


@admin_bp.route('/admin/bank-requirements/<int:policy_id>/edit', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def edit_bank_requirement(policy_id):
    policy = BankRequirement.query.get_or_404(policy_id)
    loan_types = LoanType.query.filter_by(is_active=True).all()

    if request.method == 'POST':
        policy.bank_name = request.form.get('bank_name', '').strip()
        loan_type_code = request.form.get('loan_type_code', policy.loan_type_code).strip()
        policy.loan_type_code = loan_type_code
        
        lt_obj = LoanType.query.filter_by(code=loan_type_code).first()
        if lt_obj:
            policy.loan_type_id = lt_obj.id
            policy.loan_type = lt_obj.name

        policy.description = request.form.get('description', '').strip()
        
        policy.min_age = int(request.form.get('min_age', 21))
        policy.max_age = int(request.form.get('max_age', 65))
        policy.min_monthly_income = float(request.form.get('min_monthly_income', 25000.0))
        policy.min_employment_months = int(request.form.get('min_employment_months', 12))
        policy.max_dti_ratio = float(request.form.get('max_dti_ratio', 50.0))
        policy.min_credit_score = int(request.form.get('min_credit_score', 680))
        policy.max_loan_amount = float(request.form.get('max_loan_amount', 1500000.0))
        policy.max_loan_tenure_months = int(request.form.get('max_loan_tenure_months', 60))
        policy.interest_rate_pct = float(request.form.get('interest_rate_pct', 10.5))

        policy.max_ltv_ratio = float(request.form.get('max_ltv_ratio', 75.0) or 75.0)
        policy.min_down_payment_pct = float(request.form.get('min_down_payment_pct', 15.0) or 15.0)
        policy.min_business_vintage_months = int(request.form.get('min_business_vintage_months', 24) or 24)
        policy.min_annual_turnover = float(request.form.get('min_annual_turnover', 2000000.0) or 2000000.0)
        policy.min_land_acres = float(request.form.get('min_land_acres', 2.0) or 2.0)
        
        policy.backlog_policy_enabled = 'backlog_policy_enabled' in request.form
        policy.max_allowed_backlogs = int(request.form.get('max_allowed_backlogs', 0))
        policy.backlog_policy_note = request.form.get('backlog_policy_note', '').strip()
        policy.is_active = 'is_active' in request.form

        selected_docs = request.form.getlist('required_documents')
        if selected_docs:
            policy.required_documents_list = selected_docs

        # Increment policy version for audit integrity
        policy.policy_version += 1
        policy.updated_at = datetime.utcnow()

        db.session.commit()

        log_action(
            "POLICY_UPDATED",
            details=f"Admin updated policy '{policy.policy_code}' to version {policy.policy_version}."
        )
        flash(f"Policy '{policy.bank_name}' updated to Version {policy.policy_version}.", "success")
        return redirect(url_for('admin.bank_requirements'))

    return render_template('bank_requirement_form.html', policy=policy, loan_types=loan_types)


# -------------------------------------------------------------------------
# Page 12: User Management
# -------------------------------------------------------------------------
@admin_bp.route('/admin/users', methods=['GET', 'POST'])
@login_required
@roles_required('admin')
def user_management():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip().lower()
        full_name = request.form.get('full_name', '').strip()
        role = request.form.get('role', 'applicant')
        password = request.form.get('password', 'User@123')

        if User.query.filter((User.username == username) | (User.email == email)).first():
            flash("A user with this username or email already exists.", "warning")
        else:
            new_u = User(
                username=username,
                email=email,
                full_name=full_name,
                role=role
            )
            new_u.set_password(password)
            db.session.add(new_u)
            db.session.commit()
            log_action("USER_CREATED_BY_ADMIN", details=f"Admin created user {username} with role {role}.")
            flash(f"User '{username}' created successfully.", "success")

        return redirect(url_for('admin.user_management'))

    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('user_management.html', users=users)


@admin_bp.route('/admin/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@roles_required('admin')
def toggle_user_status(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == session.get('user_id'):
        flash("You cannot deactivate your own administrative account.", "warning")
        return redirect(url_for('admin.user_management'))

    user.is_active = not user.is_active
    db.session.commit()
    log_action("USER_STATUS_TOGGLED", details=f"User {user.username} active status set to {user.is_active}.")
    flash(f"Status for {user.username} updated to {'Active' if user.is_active else 'Deactivated'}.", "info")
    return redirect(url_for('admin.user_management'))


@admin_bp.route('/admin/users/<int:user_id>/change-role', methods=['POST'])
@login_required
@roles_required('admin')
def change_user_role(user_id):
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role', 'applicant')
    
    if user.id == session.get('user_id') and new_role != 'admin':
        flash("You cannot demote your own account.", "warning")
        return redirect(url_for('admin.user_management'))

    old_role = user.role
    user.role = new_role
    db.session.commit()
    log_action("USER_ROLE_CHANGED", details=f"User {user.username} role changed from {old_role} to {new_role}.")
    flash(f"Role for {user.username} updated to '{new_role}'.", "success")
    return redirect(url_for('admin.user_management'))


# -------------------------------------------------------------------------
# Audit Logs Viewer
# -------------------------------------------------------------------------
@admin_bp.route('/admin/audit-logs')
@login_required
@roles_required('admin')
def audit_logs():
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(150).all()
    return render_template('audit_logs.html', logs=logs)
