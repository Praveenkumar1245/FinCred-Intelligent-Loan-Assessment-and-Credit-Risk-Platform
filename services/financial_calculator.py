import math
import json
import pandas as pd
from models import db, FinancialAssessment

class FinancialCalculator:
    """
    Financial calculation engine using Python and pandas.
    Calculates salary deltas, percentage growth, verified incomes,
    loan amortization EMI, Debt-to-Income (DTI), disposable income,
    and loan-specific metrics (LTV, Gold valuation, Turnover ratios, Down payments).
    """

    @staticmethod
    def calculate_loan_emi(principal, annual_interest_rate, tenure_months):
        """
        Standard reducing balance EMI calculation:
        EMI = P * r * (1+r)^n / ((1+r)^n - 1)
        """
        if principal <= 0 or tenure_months <= 0:
            return 0.0
        
        monthly_rate = (annual_interest_rate / 100.0) / 12.0
        if monthly_rate == 0:
            return round(principal / tenure_months, 2)
            
        emi = (
            principal * monthly_rate * ((1 + monthly_rate) ** tenure_months)
        ) / (((1 + monthly_rate) ** tenure_months) - 1)
        return round(emi, 2)

    @staticmethod
    def evaluate_salary_growth(current_salary, previous_salary):
        """
        Calculate salary delta and percentage increase/decrease.
        Example: Prev 22000, Curr 32000 -> Diff +10000, 45.45%
        """
        if not previous_salary or previous_salary <= 0:
            return {
                "difference": 0.0,
                "percentage": 0.0,
                "has_previous": False,
                "direction": "none",
                "summary": "No previous salary declared or applicable."
            }

        diff = current_salary - previous_salary
        pct = round((diff / previous_salary) * 100.0, 2)
        direction = "increase" if diff > 0 else ("decrease" if diff < 0 else "neutral")

        return {
            "difference": round(diff, 2),
            "percentage": pct,
            "has_previous": True,
            "direction": direction,
            "summary": (
                f"Monthly salary changed from ₹{previous_salary:,.2f} to ₹{current_salary:,.2f}. "
                f"Net change: {'+' if diff > 0 else ''}₹{diff:,.2f} ({'+' if pct > 0 else ''}{pct}%)."
            )
        }

    @staticmethod
    def compute_assessment(application):
        """
        Compute complete financial assessment for a loan application.
        Applies loan-specific metrics (Gold valuation, Home/LAP LTV, Business turnover, etc.).
        """
        declared_current_salary = float(application.declared_monthly_salary or 0.0)
        declared_prev_salary = float(application.declared_previous_salary or 0.0) if application.declared_previous_salary else None
        existing_emis = float(application.existing_monthly_emis or 0.0)
        requested_loan_amount = float(application.loan_amount_requested or 0.0)
        tenure_months = int(application.loan_tenure_months or 36)
        
        policy = application.bank_requirement
        interest_rate = float(policy.interest_rate_pct or 10.5) if policy else 10.5
        loan_type_code = application.loan_type_code or 'personal_loan'
        specific_data = application.loan_specific_data or {}

        # Inspect uploaded & extracted documents for verified salary data
        verified_salaries = []
        has_increment_letter = False

        for doc in application.documents:
            if doc.document_type == 'increment_letter' and doc.verification_status != 'rejected':
                has_increment_letter = True
            
            if doc.document_type == 'salary_slip' and doc.verification_status != 'rejected':
                if doc.extracted_record and doc.extracted_record.salary_amount_extracted:
                    verified_salaries.append(float(doc.extracted_record.salary_amount_extracted))

        for srec in application.salary_records:
            if srec.is_verified and srec.net_salary:
                verified_salaries.append(float(srec.net_salary))

        # Use pandas for statistical calculations over salary history
        if verified_salaries:
            salary_series = pd.Series(verified_salaries)
            avg_verified_sal = round(float(salary_series.mean()), 2)
            current_verified_income = round(float(salary_series.iloc[-1]), 2)
            income_verification_status = "fully_verified" if len(verified_salaries) >= 3 else "partially_verified"
        else:
            avg_verified_sal = declared_current_salary
            current_verified_income = declared_current_salary
            income_verification_status = "unverified"

        # Education loan co-applicant income support
        co_applicant_income = 0.0
        if loan_type_code == 'education_loan' and specific_data.get('co_applicant_income'):
            try:
                co_applicant_income = float(specific_data.get('co_applicant_income', 0))
            except ValueError:
                pass

        # Salary progression calculation
        growth_data = FinancialCalculator.evaluate_salary_growth(
            current_verified_income, declared_prev_salary
        )
        salary_inc_amt = growth_data["difference"]
        salary_inc_pct = growth_data["percentage"]
        
        salary_increase_supported = False
        if growth_data["has_previous"] and growth_data["direction"] == "increase":
            salary_increase_supported = has_increment_letter or (len(verified_salaries) >= 2 and verified_salaries[-1] > verified_salaries[0])

        # Estimated new EMI
        estimated_new_emi = FinancialCalculator.calculate_loan_emi(
            requested_loan_amount, interest_rate, tenure_months
        )
        projected_total_emi = round(existing_emis + estimated_new_emi, 2)

        # Debt-to-Income (DTI) calculations
        total_eval_income = current_verified_income + co_applicant_income
        effective_income = total_eval_income if total_eval_income > 0 else 1.0
        current_dti = round((existing_emis / effective_income) * 100.0, 2)
        projected_dti = round((projected_total_emi / effective_income) * 100.0, 2)

        # Disposable Income calculation
        living_expenses = round(effective_income * 0.30, 2)
        disposable_income = round(effective_income - existing_emis - estimated_new_emi - living_expenses, 2)

        # -------------------------------------------------------------
        # Loan-Specific Metrics Calculations
        # -------------------------------------------------------------
        collateral_val = 0.0
        calculated_ltv = 0.0
        down_payment_amt = 0.0
        down_payment_pct = 0.0
        turnover_ratio = 0.0
        specific_metrics = {}

        if loan_type_code == 'gold_loan':
            # Gold Valuation & LTV
            gold_weight = float(specific_data.get('gold_weight_grams', 0.0) or 0.0)
            purity = str(specific_data.get('gold_purity_karats', '22K')).upper()
            
            price_map = {
                '24K': float(policy.gold_price_per_gram_24k or 7400.0) if policy else 7400.0,
                '22K': float(policy.gold_price_per_gram_22k or 6800.0) if policy else 6800.0,
                '18K': float(policy.gold_price_per_gram_18k or 5500.0) if policy else 5500.0
            }
            gram_rate = price_map.get(purity, price_map['22K'])
            collateral_val = round(gold_weight * gram_rate, 2)
            
            if collateral_val > 0:
                calculated_ltv = round((requested_loan_amount / collateral_val) * 100.0, 2)
            
            max_ltv_cap = float(policy.max_ltv_ratio or 75.0) if policy else 75.0
            max_gold_loan = round(collateral_val * (max_ltv_cap / 100.0), 2)
            
            specific_metrics = {
                "gold_weight_grams": gold_weight,
                "gold_purity": purity,
                "gold_rate_per_gram": gram_rate,
                "total_gold_valuation": collateral_val,
                "calculated_ltv": calculated_ltv,
                "max_eligible_loan": max_gold_loan,
                "max_allowed_ltv": max_ltv_cap
            }

        elif loan_type_code == 'home_loan':
            # Property Value & LTV
            prop_val = float(specific_data.get('property_value', 0.0) or 0.0)
            down_pmt = float(specific_data.get('down_payment', 0.0) or 0.0)
            collateral_val = prop_val
            down_payment_amt = down_pmt

            if prop_val > 0:
                calculated_ltv = round((requested_loan_amount / prop_val) * 100.0, 2)
                down_payment_pct = round((down_pmt / prop_val) * 100.0, 2)

            specific_metrics = {
                "property_value": prop_val,
                "down_payment": down_pmt,
                "down_payment_pct": down_payment_pct,
                "calculated_ltv": calculated_ltv,
                "max_allowed_ltv": float(policy.max_ltv_ratio or 80.0) if policy else 80.0
            }

        elif loan_type_code == 'vehicle_loan':
            # Vehicle Price & LTV
            v_price = float(specific_data.get('vehicle_price', 0.0) or 0.0)
            v_down = float(specific_data.get('vehicle_down_payment', 0.0) or 0.0)
            collateral_val = v_price
            down_payment_amt = v_down

            if v_price > 0:
                calculated_ltv = round((requested_loan_amount / v_price) * 100.0, 2)
                down_payment_pct = round((v_down / v_price) * 100.0, 2)

            specific_metrics = {
                "vehicle_price": v_price,
                "down_payment": v_down,
                "down_payment_pct": down_payment_pct,
                "calculated_ltv": calculated_ltv,
                "vehicle_type": specific_data.get('vehicle_type', 'Car'),
                "vehicle_model": specific_data.get('vehicle_make_model', '')
            }

        elif loan_type_code == 'loan_against_property':
            # LAP Property Market Value & LTV
            lap_val = float(specific_data.get('property_market_value', 0.0) or 0.0)
            collateral_val = lap_val
            if lap_val > 0:
                calculated_ltv = round((requested_loan_amount / lap_val) * 100.0, 2)

            specific_metrics = {
                "property_market_value": lap_val,
                "calculated_ltv": calculated_ltv,
                "max_allowed_ltv": float(policy.max_ltv_ratio or 60.0) if policy else 60.0
            }

        elif loan_type_code == 'business_loan':
            # Annual Turnover & Cash Flow
            turnover = float(specific_data.get('annual_turnover', 0.0) or 0.0)
            net_profit = float(specific_data.get('annual_net_profit', 0.0) or 0.0)
            vintage = int(specific_data.get('business_vintage_months', 0) or 0)

            if turnover > 0:
                turnover_ratio = round((requested_loan_amount / turnover) * 100.0, 2)

            specific_metrics = {
                "annual_turnover": turnover,
                "annual_net_profit": net_profit,
                "business_vintage_months": vintage,
                "loan_to_turnover_ratio": turnover_ratio,
                "business_type": specific_data.get('business_type', 'Enterprise')
            }

        elif loan_type_code == 'education_loan':
            course_fee = float(specific_data.get('total_course_fee', 0.0) or 0.0)
            coverage_pct = round((requested_loan_amount / course_fee) * 100.0, 2) if course_fee > 0 else 100.0
            specific_metrics = {
                "course_name": specific_data.get('course_name', ''),
                "institution_name": specific_data.get('institution_name', ''),
                "study_location": specific_data.get('study_location', 'Domestic'),
                "total_course_fee": course_fee,
                "course_coverage_pct": coverage_pct,
                "co_applicant_name": specific_data.get('co_applicant_name', ''),
                "co_applicant_income": co_applicant_income
            }

        elif loan_type_code == 'agriculture_loan':
            acres = float(specific_data.get('land_holding_acres', 0.0) or 0.0)
            scale_rate = float(policy.scale_of_finance_per_acre or 50000.0) if policy else 50000.0
            scale_cap = round(acres * scale_rate, 2)
            specific_metrics = {
                "land_holding_acres": acres,
                "crop_activity_type": specific_data.get('crop_activity_type', 'Cultivation'),
                "annual_farm_income": float(specific_data.get('annual_farm_income', 0.0) or 0.0),
                "scale_of_finance_cap": scale_cap
            }

        # Save or update FinancialAssessment model record
        assessment = FinancialAssessment.query.filter_by(application_id=application.id).first()
        if not assessment:
            assessment = FinancialAssessment(application_id=application.id)
            db.session.add(assessment)

        assessment.current_verified_income = current_verified_income
        assessment.declared_income = declared_current_salary
        assessment.income_verification_status = income_verification_status
        assessment.previous_salary = declared_prev_salary
        assessment.salary_increase_amount = salary_inc_amt
        assessment.salary_increase_pct = salary_inc_pct
        assessment.salary_increase_supported = salary_increase_supported
        assessment.average_verified_salary = avg_verified_sal
        assessment.existing_monthly_emis = existing_emis
        assessment.estimated_new_emi = estimated_new_emi
        assessment.projected_total_emi = projected_total_emi
        assessment.current_dti_ratio = current_dti
        assessment.projected_dti_ratio = projected_dti
        assessment.living_expense_estimate = living_expenses
        assessment.estimated_disposable_income = disposable_income

        # Save loan-specific attributes
        assessment.collateral_valuation = collateral_val
        assessment.calculated_ltv_ratio = calculated_ltv
        assessment.down_payment_amount = down_payment_amt
        assessment.down_payment_pct = down_payment_pct
        assessment.business_turnover_ratio = turnover_ratio
        assessment.loan_specific_metrics = specific_metrics

        db.session.commit()
        return assessment
