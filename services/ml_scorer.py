import json
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler

class MLScorer:
    """
    Machine Learning Credit Risk & Approval Probability Scorer using scikit-learn.
    Trained on synthetic banking risk profiles to estimate default risk,
    approval probability, and feature risk drivers.
    """
    _model = None
    _scaler = None

    @classmethod
    def _initialize_model(cls):
        """Train a lightweight, calibrated Random Forest model on synthetic banking profiles"""
        if cls._model is not None:
            return

        # Features:
        # 0: Monthly Income (INR)
        # 1: Projected DTI Ratio (%)
        # 2: Credit Score (300-900)
        # 3: Employment Experience (Months)
        # 4: Loan-to-Annual-Income Ratio
        # 5: Verification Confidence (0-100)
        # 6: Active Backlogs Count

        np.random.seed(42)
        n_samples = 1500

        # Generate realistic synthetic distribution
        income = np.random.uniform(15000, 200000, n_samples)
        dti = np.random.uniform(10, 80, n_samples)
        credit_score = np.random.uniform(450, 850, n_samples)
        tenure = np.random.uniform(3, 120, n_samples)
        loan_ratio = np.random.uniform(0.5, 6.0, n_samples)
        verification_conf = np.random.uniform(20, 100, n_samples)
        backlogs = np.random.choice([0, 1, 2, 3, 4], size=n_samples, p=[0.75, 0.15, 0.05, 0.03, 0.02])

        X = np.column_stack([
            income, dti, credit_score, tenure, loan_ratio, verification_conf, backlogs
        ])

        # Approval logic ground truth with non-linear relationships
        score = (
            (credit_score - 500) * 0.35 +
            (100 - dti) * 0.40 +
            np.minimum(income / 1000.0, 100) * 0.25 +
            np.minimum(tenure, 60) * 0.20 +
            (verification_conf * 0.20) -
            (loan_ratio * 12.0) -
            (backlogs * 15.0)
        )
        # Binary target: 1 = Low/Manageable Risk (Approved), 0 = High Risk (Rejected)
        y = (score > 60).astype(int)

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        rf = RandomForestClassifier(n_estimators=60, max_depth=6, random_state=42)
        rf.fit(X_scaled, y)

        cls._scaler = scaler
        cls._model = rf

    @classmethod
    def evaluate(cls, application, assessment):
        """
        Evaluate an application and assessment, returning:
        - risk_score: float (0 to 100)
        - approval_probability: float (0 to 100)
        - risk_tier: 'Low', 'Moderate', 'High'
        - risk_factors: list of risk / positive contributor strings
        """
        cls._initialize_model()

        monthly_income = float(assessment.current_verified_income or application.declared_monthly_salary or 30000)
        dti = float(assessment.projected_dti_ratio or 40.0)
        credit = float(application.credit_score or 650)
        tenure = float(application.experience_months or 12)
        annual_income = max(1.0, monthly_income * 12)
        loan_ratio = float(application.loan_amount_requested or 100000) / annual_income
        
        # Verification confidence from documents
        doc_conf = 85.0 if assessment.income_verification_status == 'fully_verified' else (
            60.0 if assessment.income_verification_status == 'partially_verified' else 35.0
        )
        
        backlogs = float(application.applicant.backlog_count or 0)

        feature_vector = np.array([[
            monthly_income, dti, credit, tenure, loan_ratio, doc_conf, backlogs
        ]])
        feature_scaled = cls._scaler.transform(feature_vector)

        # Get probability of approval
        prob_approved = cls._model.predict_proba(feature_scaled)[0][1]
        approval_pct = round(prob_approved * 100.0, 1)

        # Calculate Risk Score (inverse of approval)
        risk_score = round(100.0 - approval_pct, 1)

        # Determine Tier
        if risk_score <= 35.0:
            risk_tier = "Low"
        elif risk_score <= 65.0:
            risk_tier = "Moderate"
        else:
            risk_tier = "High"

        # Generate transparent factor drivers
        risk_factors = []
        if dti > 50.0:
            risk_factors.append({
                "type": "negative",
                "label": "High Debt-to-Income",
                "detail": f"Projected DTI is {dti:.1f}%, which exceeds safe lending limits (50%)."
            })
        elif dti <= 35.0:
            risk_factors.append({
                "type": "positive",
                "label": "Healthy DTI Ratio",
                "detail": f"Projected DTI is manageable at {dti:.1f}%."
            })

        if credit >= 740:
            risk_factors.append({
                "type": "positive",
                "label": "Prime Credit Profile",
                "detail": f"Credit score of {int(credit)} demonstrates strong repayment history."
            })
        elif credit < 650:
            risk_factors.append({
                "type": "negative",
                "label": "Subprime Credit Score",
                "detail": f"Credit score of {int(credit)} indicates elevated historical credit risk."
            })

        if assessment.income_verification_status == 'fully_verified':
            risk_factors.append({
                "type": "positive",
                "label": "Income Verified",
                "detail": "Monthly salary is corroborated by multiple uploaded payslips."
            })
        elif assessment.income_verification_status == 'unverified':
            risk_factors.append({
                "type": "warning",
                "label": "Unverified Income",
                "detail": "Salary is based on applicant declaration without verified payslip records."
            })

        # Loan-specific factor drivers
        lt_code = application.loan_type_code or 'personal_loan'
        if lt_code == 'gold_loan':
            ltv = float(assessment.calculated_ltv_ratio or 0.0)
            if ltv > 0 and ltv <= 75.0:
                risk_factors.append({
                    "type": "positive",
                    "label": "Secured Gold Collateral",
                    "detail": f"Loan is backed by physical gold with safe {ltv:.1f}% LTV ratio."
                })
            elif ltv > 75.0:
                risk_factors.append({
                    "type": "negative",
                    "label": "Excessive Gold LTV",
                    "detail": f"LTV is {ltv:.1f}%, exceeding regulatory 75% lending ceiling."
                })
        elif lt_code == 'home_loan':
            ltv = float(assessment.calculated_ltv_ratio or 0.0)
            if ltv > 0 and ltv <= 80.0:
                risk_factors.append({
                    "type": "positive",
                    "label": "First Mortgage Security",
                    "detail": f"Property collateral provides robust risk mitigation ({ltv:.1f}% LTV)."
                })
        elif lt_code == 'business_loan':
            vintage = int(application.loan_specific_data.get('business_vintage_months', 0) or 0)
            if vintage >= 24:
                risk_factors.append({
                    "type": "positive",
                    "label": "Commercial Stability",
                    "detail": f"Business operating history of {vintage} months demonstrates stability."
                })

        # Update assessment object
        assessment.ml_risk_score = risk_score
        assessment.ml_approval_probability = approval_pct
        assessment.ml_risk_tier = risk_tier
        assessment.ml_risk_factors_json = json.dumps(risk_factors)

        return {
            "risk_score": risk_score,
            "approval_probability": approval_pct,
            "risk_tier": risk_tier,
            "risk_factors": risk_factors
        }
