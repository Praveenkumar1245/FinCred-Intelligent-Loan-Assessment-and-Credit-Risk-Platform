from datetime import datetime, date
from models import db, RequirementCheckResult, LoanApplication

class EligibilityEngine:
    """
    Transparent Bank Policy Rule Engine with Loan-Specific Underwriting.
    Evaluates applicant details, collateral valuations, business turnover,
    academic backlogs, and financial health against lender policies.
    Supports 8 distinct loan categories:
    - Home Loan, Gold Loan, Education Loan, Personal Loan,
      Vehicle Loan, Business Loan, Loan Against Property, Agriculture Loan.
    """

    @staticmethod
    def calculate_age(dob):
        """Calculate age from date of birth"""
        if not dob:
            return None
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    @staticmethod
    def run_assessment(application, assessment):
        """
        Evaluate bank requirements against the loan application using loan-specific logic.
        Clears previous checks and creates updated RequirementCheckResult records.
        Returns (overall_outcome, checks_list).
        """
        RequirementCheckResult.query.filter_by(application_id=application.id).delete()

        policy = application.bank_requirement
        loan_type_code = application.loan_type_code or 'personal_loan'
        specific_data = application.loan_specific_data or {}
        specific_metrics = assessment.loan_specific_metrics or {}

        checks = []
        order_idx = 0
        has_hard_fail = False
        has_pending = False
        has_manual_review = False

        applicant = application.applicant
        dob = applicant.date_of_birth
        age = EligibilityEngine.calculate_age(dob) if dob else None

        is_verified_income = assessment.income_verification_status in ('fully_verified', 'partially_verified')
        effective_income = assessment.current_verified_income if is_verified_income else (application.declared_monthly_salary or 0.0)
        uploaded_doc_types = {d.document_type: d for d in application.documents if d.verification_status != 'rejected'}

        # =============================================================
        # COMMON CHECK 1: Applicant Age Limit
        # =============================================================
        order_idx += 1
        min_age, max_age = policy.min_age, policy.max_age
        if age is None:
            status = "PENDING_VERIFICATION"
            has_pending = True
            actual_val = "Date of Birth Not Verified"
            explanation = "Your date of birth could not be confirmed because identity documents have not been verified."
            supporting_doc = "Identity Proof (PAN Card / Aadhaar / Passport)"
            next_step = "Upload government identity proof verifying your date of birth."
        elif min_age <= age <= max_age:
            status = "PASS"
            actual_val = f"{age} years (Eligible: {min_age} - {max_age} years)"
            explanation = f"Applicant age ({age} years) falls within the eligible bracket ({min_age} - {max_age} years) for {policy.loan_type}."
            supporting_doc = "Government Identity Proof"
            next_step = "Requirement satisfied."
        else:
            status = "FAIL"
            has_hard_fail = True
            actual_val = f"{age} years (Eligible: {min_age} - {max_age} years)"
            explanation = f"Applicant age of {age} years is outside the eligible criteria ({min_age} - {max_age} years)."
            supporting_doc = "Government Identity Proof"
            next_step = "Check eligibility with a co-applicant or explore schemes for other age brackets."

        checks.append(RequirementCheckResult(
            application_id=application.id,
            requirement_key="age_limit",
            requirement_label="Applicant Age Eligibility",
            bank_rule_text=f"Applicant age must be between {min_age} and {max_age} years",
            applicant_actual_value=actual_val,
            status=status,
            simple_explanation=explanation,
            supporting_document_info=supporting_doc,
            next_steps=next_step,
            order_index=order_idx
        ))

        # =============================================================
        # COMMON CHECK 2: Loan Amount & Tenure Product Caps
        # =============================================================
        order_idx += 1
        max_loan = policy.max_loan_amount
        max_tenure = policy.max_loan_tenure_months
        req_loan = application.loan_amount_requested
        req_tenure = application.loan_tenure_months

        if req_loan <= max_loan and req_tenure <= max_tenure:
            status = "PASS"
            actual_val = f"₹{req_loan:,.2f} for {req_tenure} months (Max: ₹{max_loan:,.2f}, {max_tenure} mos)"
            explanation = f"Requested loan amount and tenure conform to {policy.loan_type} standard policy limits."
            supporting_doc = "Loan Application Details"
            next_step = "Requirement satisfied."
        elif req_loan > max_loan:
            status = "FAIL"
            has_hard_fail = True
            excess = req_loan - max_loan
            actual_val = f"₹{req_loan:,.2f} (Cap: ₹{max_loan:,.2f})"
            explanation = f"Requested loan amount exceeds the product maximum cap by ₹{excess:,.2f}."
            supporting_doc = "Product Lending Terms"
            next_step = f"Adjust requested amount downwards to ₹{max_loan:,.2f} or explore jumbo loan facilities."
        else:
            status = "MANUAL_REVIEW"
            has_manual_review = True
            actual_val = f"Tenure {req_tenure} months (Cap: {max_tenure} months)"
            explanation = f"Requested tenure exceeds product standard tenure limit of {max_tenure} months."
            supporting_doc = "Repayment Schedule Terms"
            next_step = f"Select a repayment tenure of {max_tenure} months or fewer."

        checks.append(RequirementCheckResult(
            application_id=application.id,
            requirement_key="loan_parameters",
            requirement_label="Loan Amount & Tenure Limits",
            bank_rule_text=f"Max Loan: ₹{max_loan:,.2f}, Max Tenure: {max_tenure} months",
            applicant_actual_value=actual_val,
            status=status,
            simple_explanation=explanation,
            supporting_document_info=supporting_doc,
            next_steps=next_step,
            order_index=order_idx
        ))

        # =============================================================
        # LOAN-SPECIFIC EVALUATION PATHS
        # =============================================================

        if loan_type_code == 'gold_loan':
            # ---------------------------------------------------------
            # GOLD LOAN SPECIFIC CHECKS
            # ---------------------------------------------------------
            # Check 3.1: Pledged Gold Valuation & Weight
            order_idx += 1
            gold_weight = float(specific_data.get('gold_weight_grams', 0.0) or 0.0)
            gold_purity = str(specific_data.get('gold_purity_karats', '22K')).upper()
            gold_val = assessment.collateral_valuation

            if gold_weight <= 0:
                status = "PENDING_VERIFICATION"
                has_pending = True
                actual_val = "Gold Weight Not Declared"
                explanation = "Pledged gold weight and purity must be entered to calculate collateral valuation."
                supporting_doc = "Gold Appraisal Certificate (Pending)"
                next_step = "Declare the gross and net weight of gold jewelry being pledged."
            else:
                status = "PASS"
                actual_val = f"{gold_weight}g of {gold_purity} (Valuation: ₹{gold_val:,.2f})"
                explanation = (
                    f"Pledged gold ({gold_weight} grams, {gold_purity}) has an estimated market valuation "
                    f"of ₹{gold_val:,.2f} based on lender benchmark rates."
                )
                supporting_doc = "Gold Valuation & Weighing Memo"
                next_step = "Requirement satisfied. Bring jewelry to bank branch for physical karat purity assay."

            checks.append(RequirementCheckResult(
                application_id=application.id,
                requirement_key="gold_valuation",
                requirement_label="Gold Collateral Valuation",
                bank_rule_text="Pledged gold ornaments must be appraised by certified bank valuer",
                applicant_actual_value=actual_val,
                status=status,
                simple_explanation=explanation,
                supporting_document_info=supporting_doc,
                next_steps=next_step,
                order_index=order_idx
            ))

            # Check 3.2: Gold Loan-to-Value (LTV) Cap (RBI Ceiling: 75%)
            order_idx += 1
            actual_ltv = assessment.calculated_ltv_ratio
            max_ltv = float(policy.max_ltv_ratio or 75.0)

            if gold_val <= 0:
                status = "PENDING_VERIFICATION"
                has_pending = True
                actual_val = "Pending Gold Appraisal"
                explanation = "LTV calculation requires certified gold valuation."
                supporting_doc = "Gold Assay Report"
                next_step = "Submit gold jewelry for purity test."
            elif actual_ltv <= max_ltv:
                status = "PASS"
                actual_val = f"{actual_ltv:.1f}% LTV (Allowed Ceiling: {max_ltv:.1f}%)"
                explanation = (
                    f"Your requested loan of ₹{req_loan:,.2f} represents {actual_ltv:.1f}% of the pledged "
                    f"gold valuation (₹{gold_val:,.2f}), which is within the lender's {max_ltv:.1f}% LTV limit."
                )
                supporting_doc = "Pledge Valuation Sheet"
                next_step = "Requirement satisfied."
            else:
                status = "FAIL"
                has_hard_fail = True
                max_eligible = round(gold_val * (max_ltv / 100.0), 2)
                shortfall = req_loan - max_eligible
                actual_val = f"{actual_ltv:.1f}% LTV (Exceeds {max_ltv:.1f}% Cap)"
                explanation = (
                    f"Requested loan of ₹{req_loan:,.2f} exceeds the {max_ltv:.1f}% Loan-to-Value limit "
                    f"by ₹{shortfall:,.2f}. The maximum permissible loan against this gold is ₹{max_eligible:,.2f}."
                )
                supporting_doc = "Regulatory LTV Limit Notice"
                next_step = f"Pledge additional gold ornaments or adjust the requested loan amount downwards to ₹{max_eligible:,.2f}."

            checks.append(RequirementCheckResult(
                application_id=application.id,
                requirement_key="gold_ltv",
                requirement_label="Loan-to-Value (LTV) Ratio",
                bank_rule_text=f"Maximum allowable LTV is {max_ltv:.1f}% of market value",
                applicant_actual_value=actual_val,
                status=status,
                simple_explanation=explanation,
                supporting_document_info=supporting_doc,
                next_steps=next_step,
                order_index=order_idx
            ))

        elif loan_type_code == 'home_loan':
            # ---------------------------------------------------------
            # HOME LOAN SPECIFIC CHECKS
            # ---------------------------------------------------------
            # Check 3.1: Property Valuation & LTV
            order_idx += 1
            prop_val = float(specific_data.get('property_value', 0.0) or 0.0)
            actual_ltv = assessment.calculated_ltv_ratio
            max_ltv = float(policy.max_ltv_ratio or 80.0)

            if prop_val <= 0:
                status = "PENDING_VERIFICATION"
                has_pending = True
                actual_val = "Property Valuation Pending"
                explanation = "Declared property market purchase price or agreement value is required."
                supporting_doc = "Agreement of Sale / Valuation Report"
                next_step = "Enter the total agreement value of the residential property."
            elif actual_ltv <= max_ltv:
                status = "PASS"
                actual_val = f"{actual_ltv:.1f}% LTV on Property ₹{prop_val:,.2f}"
                explanation = f"LTV of {actual_ltv:.1f}% complies with the bank's maximum {max_ltv:.1f}% mortgage ceiling."
                supporting_doc = "Property Sale Agreement"
                next_step = "Requirement satisfied."
            else:
                status = "FAIL"
                has_hard_fail = True
                max_elig = round(prop_val * (max_ltv / 100.0), 2)
                actual_val = f"{actual_ltv:.1f}% LTV (Exceeds {max_ltv:.1f}%)"
                explanation = f"Requested loan exceeds the bank's {max_ltv:.1f}% LTV cap. Maximum loan for this property is ₹{max_elig:,.2f}."
                supporting_doc = "Property Valuation Sheet"
                next_step = f"Increase down payment to bring loan down to ₹{max_elig:,.2f}."

            checks.append(RequirementCheckResult(
                application_id=application.id,
                requirement_key="home_ltv",
                requirement_label="Mortgage Loan-to-Value (LTV)",
                bank_rule_text=f"Maximum Home Loan LTV <= {max_ltv:.1f}% of property cost",
                applicant_actual_value=actual_val,
                status=status,
                simple_explanation=explanation,
                supporting_document_info=supporting_doc,
                next_steps=next_step,
                order_index=order_idx
            ))

            # Check 3.2: Down Payment / Own Contribution
            order_idx += 1
            down_pmt = float(specific_data.get('down_payment', 0.0) or 0.0)
            down_pct = assessment.down_payment_pct
            min_down_pct = float(policy.min_down_payment_pct or 15.0)

            if down_pct >= min_down_pct:
                status = "PASS"
                actual_val = f"₹{down_pmt:,.2f} ({down_pct:.1f}% of property cost)"
                explanation = f"Borrower equity contribution of {down_pct:.1f}% satisfies the bank's minimum {min_down_pct:.1f}% down payment mandate."
                supporting_doc = "Bank Statement Margin Money Debit"
                next_step = "Requirement satisfied."
            else:
                status = "FAIL"
                has_hard_fail = True
                actual_val = f"₹{down_pmt:,.2f} ({down_pct:.1f}% < {min_down_pct:.1f}%)"
                explanation = f"Down payment contribution ({down_pct:.1f}%) is below the required {min_down_pct:.1f}% borrower margin."
                supporting_doc = "Own Contribution Proof"
                next_step = f"Increase down payment to at least {min_down_pct:.1f}% of property value."

            checks.append(RequirementCheckResult(
                application_id=application.id,
                requirement_key="down_payment",
                requirement_label="Borrower Own Contribution / Down Payment",
                bank_rule_text=f"Minimum {min_down_pct:.1f}% own contribution required",
                applicant_actual_value=actual_val,
                status=status,
                simple_explanation=explanation,
                supporting_document_info=supporting_doc,
                next_steps=next_step,
                order_index=order_idx
            ))

        elif loan_type_code == 'business_loan':
            # ---------------------------------------------------------
            # BUSINESS LOAN SPECIFIC CHECKS
            # ---------------------------------------------------------
            # Check 3.1: Business Operational Vintage
            order_idx += 1
            vintage = int(specific_data.get('business_vintage_months', 0) or 0)
            min_vintage = int(policy.min_business_vintage_months or 24)

            if vintage >= min_vintage:
                status = "PASS"
                actual_val = f"{vintage} months ({vintage // 12} yrs, required: {min_vintage} mos)"
                explanation = f"Business operational track record of {vintage} months satisfies lender vintage stability criteria."
                supporting_doc = "GST Registration Certificate / MSME Udyam"
                next_step = "Requirement satisfied."
            else:
                status = "FAIL"
                has_hard_fail = True
                actual_val = f"{vintage} months (Required: {min_vintage} months)"
                explanation = f"Business vintage of {vintage} months is less than the required {min_vintage} months operating history."
                supporting_doc = "Business Inception Proof"
                next_step = "Provide certificate of incorporation or apply under government startup/MUDRA schemes."

            checks.append(RequirementCheckResult(
                application_id=application.id,
                requirement_key="business_vintage",
                requirement_label="Business Operational Vintage",
                bank_rule_text=f"Minimum {min_vintage} months of continuous commercial operations",
                applicant_actual_value=actual_val,
                status=status,
                simple_explanation=explanation,
                supporting_document_info=supporting_doc,
                next_steps=next_step,
                order_index=order_idx
            ))

            # Check 3.2: Minimum Annual Turnover
            order_idx += 1
            turnover = float(specific_data.get('annual_turnover', 0.0) or 0.0)
            min_turnover = float(policy.min_annual_turnover or 2000000.0)

            if turnover >= min_turnover:
                status = "PASS"
                actual_val = f"₹{turnover:,.2f} (Required: ₹{min_turnover:,.2f})"
                explanation = f"Annual turnover of ₹{turnover:,.2f} satisfies the minimum revenue threshold."
                supporting_doc = "GST Returns (GSTR-3B) / Audited P&L"
                next_step = "Requirement satisfied."
            else:
                status = "FAIL"
                has_hard_fail = True
                actual_val = f"₹{turnover:,.2f} (Required: ₹{min_turnover:,.2f})"
                explanation = f"Annual turnover is below the bank's minimum benchmark of ₹{min_turnover:,.2f}."
                supporting_doc = "Financial Statements"
                next_step = "Submit 12 months audited bank statements or apply for micro-enterprise loan."

            checks.append(RequirementCheckResult(
                application_id=application.id,
                requirement_key="annual_turnover",
                requirement_label="Minimum Annual Turnover",
                bank_rule_text=f"Minimum annual turnover >= ₹{min_turnover:,.2f}",
                applicant_actual_value=actual_val,
                status=status,
                simple_explanation=explanation,
                supporting_document_info=supporting_doc,
                next_steps=next_step,
                order_index=order_idx
            ))

        elif loan_type_code == 'vehicle_loan':
            # ---------------------------------------------------------
            # VEHICLE LOAN SPECIFIC CHECKS
            # ---------------------------------------------------------
            order_idx += 1
            v_price = float(specific_data.get('vehicle_price', 0.0) or 0.0)
            actual_ltv = assessment.calculated_ltv_ratio
            max_ltv = float(policy.max_ltv_ratio or 85.0)

            if v_price <= 0:
                status = "PENDING_VERIFICATION"
                has_pending = True
                actual_val = "Vehicle Quotation Pending"
                explanation = "Vehicle showroom invoice/quotation price is needed for LTV determination."
                supporting_doc = "Proforma Invoice / Dealer Quotation"
                next_step = "Enter on-road or ex-showroom price of the target vehicle."
            elif actual_ltv <= max_ltv:
                status = "PASS"
                actual_val = f"{actual_ltv:.1f}% on vehicle cost ₹{v_price:,.2f}"
                explanation = f"Vehicle LTV ({actual_ltv:.1f}%) is within the lender's {max_ltv:.1f}% maximum financing limit."
                supporting_doc = "Authorized Dealer Proforma Invoice"
                next_step = "Requirement satisfied."
            else:
                status = "FAIL"
                has_hard_fail = True
                max_elig = round(v_price * (max_ltv / 100.0), 2)
                actual_val = f"{actual_ltv:.1f}% LTV (Exceeds {max_ltv:.1f}%)"
                explanation = f"Requested loan exceeds {max_ltv:.1f}% vehicle cost limit. Maximum eligible is ₹{max_elig:,.2f}."
                supporting_doc = "Auto Loan Policy Norms"
                next_step = f"Increase down payment to borrow a maximum of ₹{max_elig:,.2f}."

            checks.append(RequirementCheckResult(
                application_id=application.id,
                requirement_key="vehicle_ltv",
                requirement_label="Vehicle Loan-to-Value (LTV)",
                bank_rule_text=f"Maximum Vehicle LTV <= {max_ltv:.1f}%",
                applicant_actual_value=actual_val,
                status=status,
                simple_explanation=explanation,
                supporting_document_info=supporting_doc,
                next_steps=next_step,
                order_index=order_idx
            ))

        elif loan_type_code == 'loan_against_property':
            # ---------------------------------------------------------
            # LOAN AGAINST PROPERTY (LAP) CHECKS
            # ---------------------------------------------------------
            order_idx += 1
            lap_val = float(specific_data.get('property_market_value', 0.0) or 0.0)
            actual_ltv = assessment.calculated_ltv_ratio
            max_ltv = float(policy.max_ltv_ratio or 60.0)

            if lap_val <= 0:
                status = "PENDING_VERIFICATION"
                has_pending = True
                actual_val = "Property Valuation Pending"
                explanation = "Estimated market value of the mortgaged property must be provided."
                supporting_doc = "Property Title & Valuation Report"
                next_step = "Enter the current estimated market value of the property."
            elif actual_ltv <= max_ltv:
                status = "PASS"
                actual_val = f"{actual_ltv:.1f}% LTV against ₹{lap_val:,.2f}"
                explanation = f"LAP loan-to-value ratio ({actual_ltv:.1f}%) is within conservative lending limit ({max_ltv:.1f}%)."
                supporting_doc = "Property Title Deed"
                next_step = "Requirement satisfied."
            else:
                status = "FAIL"
                has_hard_fail = True
                max_elig = round(lap_val * (max_ltv / 100.0), 2)
                actual_val = f"{actual_ltv:.1f}% LTV (Exceeds {max_ltv:.1f}%)"
                explanation = f"Requested loan exceeds maximum mortgage cap of {max_ltv:.1f}%. Max loan is ₹{max_elig:,.2f}."
                supporting_doc = "Secured Lending Guidelines"
                next_step = f"Adjust requested amount downwards to ₹{max_elig:,.2f}."

            checks.append(RequirementCheckResult(
                application_id=application.id,
                requirement_key="lap_ltv",
                requirement_label="Mortgage Collateral LTV Ratio",
                bank_rule_text=f"Maximum LAP LTV <= {max_ltv:.1f}%",
                applicant_actual_value=actual_val,
                status=status,
                simple_explanation=explanation,
                supporting_document_info=supporting_doc,
                next_steps=next_step,
                order_index=order_idx
            ))

        elif loan_type_code == 'agriculture_loan':
            # ---------------------------------------------------------
            # AGRICULTURE LOAN SPECIFIC CHECKS
            # ---------------------------------------------------------
            order_idx += 1
            acres = float(specific_data.get('land_holding_acres', 0.0) or 0.0)
            min_acres = float(policy.min_land_acres or 2.0)

            if acres >= min_acres:
                status = "PASS"
                actual_val = f"{acres:.1f} Acres (Required: >= {min_acres:.1f} Acres)"
                explanation = f"Land holding of {acres:.1f} acres meets minimum agricultural landholding norms."
                supporting_doc = "Patta / 7/12 Extract / Land Record"
                next_step = "Requirement satisfied."
            else:
                status = "FAIL"
                has_hard_fail = True
                actual_val = f"{acres:.1f} Acres (< {min_acres:.1f} Acres)"
                explanation = f"Declared cultivable land ({acres:.1f} acres) is below minimum lender requirement of {min_acres:.1f} acres."
                supporting_doc = "Revenue Land Records"
                next_step = "Add joint family land records or apply under marginal farmer / tenant schemes."

            checks.append(RequirementCheckResult(
                application_id=application.id,
                requirement_key="land_holding",
                requirement_label="Agricultural Land Holding",
                bank_rule_text=f"Minimum cultivable landholding >= {min_acres:.1f} acres",
                applicant_actual_value=actual_val,
                status=status,
                simple_explanation=explanation,
                supporting_document_info=supporting_doc,
                next_steps=next_step,
                order_index=order_idx
            ))

        # =============================================================
        # REPAYMENT CAPACITY CHECKS (Income, DTI, Credit Score)
        # =============================================================
        # For non-gold loans, evaluate Monthly Income and DTI strictly:
        if loan_type_code != 'gold_loan':
            # Check: Minimum Monthly / Co-Applicant Income
            order_idx += 1
            min_income = policy.min_monthly_income
            co_app_inc = float(specific_data.get('co_applicant_income', 0.0) or 0.0) if loan_type_code == 'education_loan' else 0.0
            total_income = effective_income + co_app_inc

            if not is_verified_income and (not uploaded_doc_types.get('salary_slip')) and loan_type_code in ('personal_loan', 'home_loan', 'vehicle_loan', 'loan_against_property'):
                status = "PENDING_VERIFICATION"
                has_pending = True
                actual_val = f"₹{application.declared_monthly_salary:,.2f} (Declared, Unverified)"
                explanation = f"Declared monthly income is ₹{application.declared_monthly_salary:,.2f}. Recent salary slips/income docs have not been verified."
                supporting_doc = "Salary Slips / Income Proof (Pending upload)"
                next_step = "Upload your recent 3 months' salary slips to enable automated verification."
            elif total_income >= min_income:
                status = "PASS"
                actual_val = f"₹{total_income:,.2f} ({'Co-Applicant Supported' if co_app_inc > 0 else 'Verified'})"
                explanation = f"Evaluated monthly income of ₹{total_income:,.2f} satisfies the lender's minimum income requirement of ₹{min_income:,.2f}."
                supporting_doc = "Income Proof / Verified Payroll"
                next_step = "Requirement satisfied."
            else:
                status = "FAIL"
                has_hard_fail = True
                shortfall = min_income - total_income
                actual_val = f"₹{total_income:,.2f} (Shortfall: ₹{shortfall:,.2f})"
                explanation = f"Income of ₹{total_income:,.2f} is ₹{shortfall:,.2f} below the configured minimum of ₹{min_income:,.2f}."
                supporting_doc = "Income Records"
                next_step = "Add a co-applicant with additional verifiable income or explore lower ticket loan schemes."

            checks.append(RequirementCheckResult(
                application_id=application.id,
                requirement_key="min_income",
                requirement_label="Minimum Income Benchmark",
                bank_rule_text=f"Minimum monthly income >= ₹{min_income:,.2f}",
                applicant_actual_value=actual_val,
                status=status,
                simple_explanation=explanation,
                supporting_document_info=supporting_doc,
                next_steps=next_step,
                order_index=order_idx
            ))

            # Check: Debt-to-Income (DTI) Ratio
            order_idx += 1
            max_dti = policy.max_dti_ratio
            actual_dti = assessment.projected_dti_ratio

            if actual_dti <= max_dti:
                status = "PASS"
                actual_val = f"{actual_dti:.1f}% (Existing: ₹{assessment.existing_monthly_emis:,.0f} + New EMI: ₹{assessment.estimated_new_emi:,.0f})"
                explanation = f"Projected total debt represents {actual_dti:.1f}% of income, well within the bank's maximum allowable limit of {max_dti:.1f}%."
                supporting_doc = "Bank Statement EMI Debits"
                next_step = "Requirement satisfied."
            elif actual_dti <= max_dti + 10.0:
                status = "MANUAL_REVIEW"
                has_manual_review = True
                actual_val = f"{actual_dti:.1f}% (Policy Limit: {max_dti:.1f}%)"
                explanation = f"Projected DTI is {actual_dti:.1f}%, slightly above the standard {max_dti:.1f}% benchmark. Officer review needed."
                supporting_doc = "Financial Assessment History"
                next_step = "Consider extending repayment tenure to lower the monthly EMI."
            else:
                status = "FAIL"
                has_hard_fail = True
                actual_val = f"{actual_dti:.1f}% (Policy Limit: {max_dti:.1f}%)"
                explanation = f"Projected debt obligations represent {actual_dti:.1f}% of income, significantly exceeding the safe {max_dti:.1f}% limit."
                supporting_doc = "Obligation Records"
                next_step = "Reduce requested loan amount or prepay existing commitments."

            checks.append(RequirementCheckResult(
                application_id=application.id,
                requirement_key="max_dti",
                requirement_label="Debt-to-Income (DTI) Ratio",
                bank_rule_text=f"Maximum total debt obligations <= {max_dti:.1f}% of income",
                applicant_actual_value=actual_val,
                status=status,
                simple_explanation=explanation,
                supporting_document_info=supporting_doc,
                next_steps=next_step,
                order_index=order_idx
            ))

        # Check: Bureau Credit Score
        order_idx += 1
        min_credit = policy.min_credit_score
        credit = application.credit_score

        if not credit:
            status = "PENDING_VERIFICATION"
            has_pending = True
            actual_val = "Bureau Pull Pending"
            explanation = "Your credit score has not yet been submitted or retrieved from the bureau."
            supporting_doc = "Credit Bureau Report"
            next_step = "Upload official credit bureau report (CIBIL / Experian)."
        elif credit >= min_credit:
            status = "PASS"
            actual_val = f"{credit} (Cutoff: {min_credit})"
            explanation = f"Credit score of {credit} satisfies the lender benchmark of {min_credit}."
            supporting_doc = "Credit Bureau Report"
            next_step = "Requirement satisfied."
        elif credit >= min_credit - 30:
            status = "MANUAL_REVIEW"
            has_manual_review = True
            actual_val = f"{credit} (Cutoff: {min_credit})"
            explanation = f"Credit score of {credit} is marginally below the {min_credit} benchmark. Bank officer review required."
            supporting_doc = "Repayment History Record"
            next_step = "Provide evidence of error-free repayments for the last 6 months."
        else:
            status = "FAIL"
            has_hard_fail = True
            actual_val = f"{credit} (Cutoff: {min_credit})"
            explanation = f"Credit score of {credit} is {min_credit - credit} points below the minimum required cutoff of {min_credit}."
            supporting_doc = "Credit Bureau Report"
            next_step = "Settle overdue accounts, reduce revolving balances, and reapply."

        checks.append(RequirementCheckResult(
            application_id=application.id,
            requirement_key="credit_score",
            requirement_label="Credit Bureau Score",
            bank_rule_text=f"Minimum credit score >= {min_credit}",
            applicant_actual_value=actual_val,
            status=status,
            simple_explanation=explanation,
            supporting_document_info=supporting_doc,
            next_steps=next_step,
            order_index=order_idx
        ))

        # =============================================================
        # ACADEMIC BACKLOG CHECK (Step 7: Check Backlogs When Applicable)
        # =============================================================
        order_idx += 1
        backlog_count = applicant.backlog_count or 0

        if policy.backlog_policy_enabled:
            max_allowed = policy.max_allowed_backlogs
            if backlog_count <= max_allowed:
                status = "PASS"
                actual_val = f"{backlog_count} active backlog(s) (Permitted: <= {max_allowed})"
                explanation = (
                    f"The selected bank ({policy.bank_name}) enforces an academic eligibility rule allowing up to "
                    f"{max_allowed} active backlogs. Your profile has {backlog_count} backlogs, which satisfies the rule."
                )
                supporting_doc = "Degree / Academic Transcript Certificate"
                next_step = "Academic requirement satisfied."
            else:
                status = "FAIL"
                has_hard_fail = True
                actual_val = f"{backlog_count} active backlogs (Permitted: <= {max_allowed})"
                explanation = (
                    f"The selected bank's policy ({policy.bank_name}) for this loan restricts active academic backlogs "
                    f"to a maximum of {max_allowed}. Your declared backlog count ({backlog_count}) exceeds the limit."
                )
                supporting_doc = "Semester Mark Sheets / Degree Certificate"
                next_step = "Clear pending academic backlogs or provide university clearance completion certificate."
        else:
            status = "NOT_APPLICABLE"
            actual_val = f"{backlog_count} backlogs (Academic policy inactive for {policy.loan_type})"
            explanation = (
                f"The selected policy ({policy.bank_name} - {policy.loan_type}) evaluates borrower capacity and collateral; "
                "it does not consider academic backlogs for eligibility. Academic backlogs have zero adverse effect on this evaluation."
            )
            supporting_doc = "Policy Exemption Notice"
            next_step = "No action required. Academic backlog status does not affect this loan product."

        checks.append(RequirementCheckResult(
            application_id=application.id,
            requirement_key="backlog_check",
            requirement_label="Academic Backlog Policy",
            bank_rule_text=(
                f"Max {policy.max_allowed_backlogs} backlogs allowed"
                if policy.backlog_policy_enabled
                else f"Policy does not evaluate academic backlogs for {policy.loan_type}"
            ),
            applicant_actual_value=actual_val,
            status=status,
            simple_explanation=explanation,
            supporting_document_info=supporting_doc,
            next_steps=next_step,
            order_index=order_idx
        ))

        # =============================================================
        # MANDATORY DOCUMENT CHECK (Loan-Specific Catalog & Policy)
        # =============================================================
        order_idx += 1
        from services.document_catalog import evaluate_application_document_slots
        slots, doc_progress = evaluate_application_document_slots(application)

        required_doc_types = policy.required_documents_list
        missing_docs = []
        for dt in required_doc_types:
            if dt in uploaded_doc_types:
                continue
            # Handle aliases across loan policies
            if dt in ('property_docs', 'property_documents', 'property_sale_agreement', 'property_valuation') and any(
                k in uploaded_doc_types for k in ('property_docs', 'property_documents', 'property_sale_agreement', 'property_valuation')
            ):
                continue
            if dt in ('land_records', 'land_records_patta') and any(k in uploaded_doc_types for k in ('land_records', 'land_records_patta')):
                continue
            if dt in ('gold_valuation_cert', 'gold_valuation_appraisal', 'gold_ownership_declaration', 'gold_ownership_receipt') and any(
                k in uploaded_doc_types for k in ('gold_valuation_cert', 'gold_valuation_appraisal', 'gold_ownership_declaration', 'gold_ownership_receipt')
            ):
                continue
            missing_docs.append(dt)

        doc_label_map = {
            "salary_slip": "Recent Salary Slips (3 months)",
            "bank_statement": "Bank Account Statements (6 months)",
            "id_proof": "Government Identity Proof (PAN / Passport)",
            "address_proof": "Address Proof (Aadhaar / Utility Bill)",
            "increment_letter": "Salary Increase / Appraisal Letter",
            "tax_doc": "Form 16 / ITR Tax Returns",
            "credit_report": "Credit Bureau Report",
            "education_cert": "Degree / Academic Certificate",
            "admission_letter": "University Admission Letter",
            "gold_ownership_declaration": "Gold Purchase Invoice / Ownership Declaration",
            "gold_valuation_cert": "Gold Valuation Certificate",
            "property_docs": "Property Title Deed / Sale Agreement / Tax Receipt",
            "property_documents": "Property Title Deed / Sale Agreement / Tax Receipt",
            "vehicle_quotation": "Dealer Proforma Invoice / Quotation",
            "business_pan": "Business Entity Registration / PAN",
            "gst_returns": "GST Filing Returns (GSTR-3B)",
            "land_records": "Land Ownership Records / Patta / 7/12 Extract",
            "land_records_patta": "Land Ownership Records / Patta / 7/12 Extract",
            "crop_declaration": "Agricultural Crop Sowing Declaration"
        }

        # Check satisfies if either standard policy required docs are present or dynamic checklist is satisfied
        if not missing_docs or doc_progress['can_submit']:
            status = "PASS"
            actual_val = f"All {len(required_doc_types)} required document categories uploaded ({doc_progress['total_uploaded']} files attached)"
            explanation = f"All mandatory document categories specified by {policy.bank_name} for {policy.loan_type} have been uploaded."
            supporting_doc = "Uploaded Documents Repository"
            next_step = "Requirement satisfied. Documents are undergoing officer authentication."
        else:
            status = "PENDING_VERIFICATION"
            has_pending = True
            missing_names = [doc_label_map.get(dt, dt.replace('_', ' ').title()) for dt in missing_docs]
            if not missing_names and doc_progress['missing_required']:
                missing_names = doc_progress['missing_required']
            actual_val = f"{len(missing_names)} mandatory document(s) missing"
            explanation = (
                f"The lender policy for {policy.loan_type} mandates: {', '.join(missing_names)}. "
                "These documents have not yet been provided."
            )
            supporting_doc = "Missing documents list"
            next_step = f"Upload the following required documents: {', '.join(missing_names)}."

        checks.append(RequirementCheckResult(
            application_id=application.id,
            requirement_key="mandatory_docs",
            requirement_label="Mandatory Lender Documentation",
            bank_rule_text=f"Requires {len(required_doc_types)} verified documents for {policy.loan_type}",
            applicant_actual_value=actual_val,
            status=status,
            simple_explanation=explanation,
            supporting_document_info=supporting_doc,
            next_steps=next_step,
            order_index=order_idx
        ))

        # Persist all checks
        for c in checks:
            db.session.add(c)

        # Determine Final Overall Outcome
        if has_hard_fail:
            overall_outcome = "does_not_meet"
        elif has_pending:
            overall_outcome = "pending_verification"
        elif has_manual_review:
            overall_outcome = "manual_review"
        else:
            overall_outcome = "meets_requirements"

        application.status = overall_outcome
        application.policy_version_used = policy.policy_version
        db.session.commit()

        return overall_outcome, checks
