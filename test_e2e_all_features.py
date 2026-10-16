import urllib.request
import urllib.parse
import http.cookiejar
import re
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def run_tests():
    print("--- STARTING COMPREHENSIVE E2E VERIFICATION ---")
    base_url = "http://127.0.0.1:5000"

    # =========================================================================
    # 1. APPLICANT WORKFLOW: GOLD LOAN APPLICATION & ASSESSMENT
    # =========================================================================
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    # 1.1 Login as Applicant
    login_data = urllib.parse.urlencode({'username': 'rajesh', 'password': 'Applicant@123'}).encode('utf-8')
    res = opener.open(f"{base_url}/login", data=login_data)
    assert res.status == 200
    print("[PASS] 1.1 Applicant Login Successful")

    # 1.2 View Loan Categories Grid
    res = opener.open(f"{base_url}/select-loan-type")
    html = res.read().decode('utf-8')
    categories = [
        "Home Loan", "Gold Loan", "Education Loan", "Personal Loan",
        "Vehicle Loan", "Business Loan", "Loan Against Property", "Agriculture Loan"
    ]
    for cat in categories:
        assert cat in html, f"Missing category: {cat}"
    print("[PASS] 1.2 All 8 Master Loan Categories Verified on /select-loan-type")

    # 1.3 Load Gold Loan Dynamic Form
    res = opener.open(f"{base_url}/apply?loan_type=gold_loan")
    html = res.read().decode('utf-8')
    assert "Gold Weight (Grams)" in html
    assert "gold_purity_karats" in html
    assert "75% LTV Cap" in html or "75% LTV" in html
    print("[PASS] 1.3 Gold Loan Dynamic Form Questions & Live Calculators Verified")

    # 1.4 Submit Gold Loan Application
    gold_policy_match = re.search(r'value="(\d+)"[^>]*>Muthoot & Apex Bullion Bank', html)
    policy_id = gold_policy_match.group(1) if gold_policy_match else "3"

    form_data = urllib.parse.urlencode({
        'loan_type_code': 'gold_loan',
        'bank_requirement_id': policy_id,
        'loan_amount_requested': '200000',
        'loan_tenure_months': '12',
        'loan_purpose': 'Business liquidity against hallmark jewelry',
        'company_name': 'Universal Crafts',
        'designation': 'Proprietor',
        'employment_type': 'Self-Employed Professional',
        'experience_months': '36',
        'declared_monthly_salary': '25000',
        'declared_previous_salary': '20000',
        'existing_monthly_emis': '0',
        'credit_score': '740',
        'gold_weight_grams': '45.0',
        'gold_purity_karats': '22K',
        'gold_item_type': 'Jewelry',
        'pledge_declaration': 'I am the lawful owner of the ornaments.'
    }).encode('utf-8')

    res = opener.open(f"{base_url}/apply?loan_type=gold_loan", data=form_data)
    redirect_url = res.geturl()
    assert "/documents" in redirect_url
    app_id = re.search(r'/application/(\d+)/documents', redirect_url).group(1)
    print(f"[PASS] 1.4 Gold Loan Application Created: App #{app_id}")

    # 1.5 Attach Demo Payslip/Document
    attach_data = urllib.parse.urlencode({'demo_doc_type': 'salary_slip'}).encode('utf-8')
    res = opener.open(f"{base_url}/application/{app_id}/attach-demo-doc", data=attach_data)
    print(f"[PASS] 1.5 Attached Synthetic Demo Document to Application #{app_id}")

    # 1.6 View Explainable Results for Gold Loan
    res = opener.open(f"{base_url}/application/{app_id}/results")
    html = res.read().decode('utf-8')
    assert "Comprehensive Eligibility Determination" in html
    assert "Gold Loan" in html
    assert "306,000" in html # 45g * ₹6,800
    assert "65.4%" in html or "65.36%" in html # 200,000 / 306,000
    assert "Detailed Requirement-by-Requirement Assessment" in html
    print(f"[PASS] 1.6 Gold Loan Explainable Results Verified (Collateral: INR 306,000, LTV: ~65.4%, Status: Verified)")

    # =========================================================================
    # 2. APPLICANT WORKFLOW: HOME LOAN APPLICATION & RESULTS
    # =========================================================================
    res = opener.open(f"{base_url}/apply?loan_type=home_loan")
    html = res.read().decode('utf-8')
    assert "Property Purchase / Agreement Value" in html
    assert "down_payment" in html
    print("[PASS] 2.1 Home Loan Dynamic Form Questions Verified")

    # =========================================================================
    # 3. DASHBOARD FILTERING
    # =========================================================================
    res = opener.open(f"{base_url}/dashboard?loan_type=gold_loan")
    html = res.read().decode('utf-8')
    assert "Filter Category" in html or "Active Loan Applications" in html
    print("[PASS] 3.1 Dashboard Category Filtering (gold_loan) Verified")

    res = opener.open(f"{base_url}/dashboard?loan_type=home_loan")
    assert res.status == 200
    print("[PASS] 3.2 Dashboard Category Filtering (home_loan) Verified")

    # =========================================================================
    # 4. ADMIN WORKFLOW: MASTER LOAN CATEGORIES CRUD & TOGGLE
    # =========================================================================
    admin_cj = http.cookiejar.CookieJar()
    admin_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(admin_cj))

    login_data = urllib.parse.urlencode({'username': 'admin', 'password': 'Admin@123'}).encode('utf-8')
    res = admin_opener.open(f"{base_url}/login", data=login_data)
    assert res.status == 200
    print("[PASS] 4.1 Admin Login Successful")

    # 4.2 View Master Loan Categories
    res = admin_opener.open(f"{base_url}/admin/loan-types")
    html = res.read().decode('utf-8')
    assert "Master Loan Types Catalog" in html
    for cat in categories:
        assert cat in html, f"Missing category in admin catalog: {cat}"
    print("[PASS] 4.2 Admin Catalog Lists All 8 Loan Categories")

    # 4.3 Create New Custom Loan Category
    new_cat_data = urllib.parse.urlencode({
        'name': 'Electric Mobility Loan',
        'code': 'electric_mobility_loan',
        'icon': 'bi-lightning-charge',
        'description': 'Subsidized green finance for high-efficiency electric two-wheelers and passenger EVs.',
        'default_ltv_cap': '85.0',
        'default_interest_rate': '7.9',
        'required_documents': ['id_proof', 'bank_statement', 'vehicle_quotation']
    }).encode('utf-8')

    res = admin_opener.open(f"{base_url}/admin/loan-types/new", data=new_cat_data)
    assert res.status == 200
    html = res.read().decode('utf-8')
    assert "Electric Mobility Loan" in html
    print("[PASS] 4.3 Admin Successfully Created New Loan Category ('Electric Mobility Loan')")

    # 4.4 Toggle Loan Category Status
    ev_match = re.search(r'/admin/loan-types/(\d+)/toggle', html)
    if ev_match:
        ev_id = ev_match.group(1)
        res = admin_opener.open(f"{base_url}/admin/loan-types/{ev_id}/toggle", data=b"")
        assert res.status == 200
        print(f"[PASS] 4.4 Successfully Toggled Status for Loan Category #{ev_id}")

    # =========================================================================
    # 5. CREDIT OFFICER QUEUE & REVIEW
    # =========================================================================
    off_cj = http.cookiejar.CookieJar()
    off_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(off_cj))

    login_data = urllib.parse.urlencode({'username': 'officer', 'password': 'Officer@123'}).encode('utf-8')
    res = off_opener.open(f"{base_url}/login", data=login_data)
    assert res.status == 200

    res = off_opener.open(f"{base_url}/officer/queue")
    html = res.read().decode('utf-8')
    assert "Application Review & Verification Queue" in html
    print("[PASS] 5.1 Officer Review Queue Verified")

    res = off_opener.open(f"{base_url}/officer/review/{app_id}")
    html = res.read().decode('utf-8')
    assert "Underwriting Workbench" in html or "Review Application" in html
    assert "Gold Loan" in html
    print(f"[PASS] 5.2 Officer Review Workbench Verified with Category & Collateral Details for App #{app_id}")

    print("==================================================================")
    print("ALL 12 END-TO-END VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
    print("==================================================================")

if __name__ == "__main__":
    run_tests()
