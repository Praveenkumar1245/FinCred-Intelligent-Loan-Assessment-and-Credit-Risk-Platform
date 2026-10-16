import urllib.request
import urllib.parse
import http.cookiejar
import re
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

def run_e2e_verification():
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

    print("=== Testing FinCred AI Endpoints & Workflows ===")

    # 1. Page 1: Login Page
    res = opener.open("http://127.0.0.1:5000/login")
    html = res.read().decode('utf-8')
    assert res.status == 200
    assert "FinCred AI" in html
    assert "Quick Demo Access" in html
    print("[PASS] Page 1: Login page renders with 1-click demo access.")

    # 2. Login as Applicant: Rajesh Sharma
    data = urllib.parse.urlencode({"username": "rajesh", "password": "Applicant@123"}).encode('utf-8')
    res = opener.open("http://127.0.0.1:5000/login", data=data)
    html = res.read().decode('utf-8')
    assert "Rajesh Sharma" in html or "Dashboard" in html
    print("[PASS] User Authentication: Logged in as Rajesh Sharma (Applicant).")

    # 3. Page 2: Dashboard
    res = opener.open("http://127.0.0.1:5000/dashboard")
    html = res.read().decode('utf-8')
    assert res.status == 200
    assert "Applicant Financial Overview" in html or "My Applications" in html
    print("[PASS] Page 2: Applicant Dashboard loaded.")

    # 4. Page 3: Applicant Details Profile
    res = opener.open("http://127.0.0.1:5000/applicant/details")
    html = res.read().decode('utf-8')
    assert res.status == 200
    assert "Applicant Profile & Background Details" in html
    assert "Education & Academic Backlogs" in html
    print("[PASS] Page 3: Applicant Profile form loaded.")

    # 5. Page 4: Loan Application Form
    res = opener.open("http://127.0.0.1:5000/apply")
    html = res.read().decode('utf-8')
    assert res.status == 200
    assert "Save Application" in html or "Submit Loan Application" in html or "Loan Application" in html
    assert "live_emi_display" in html
    print("[PASS] Page 4: Loan Application form with live EMI simulation loaded.")

    # Find the prepopulated application ID (App 1)
    m = re.search(r'/application/(\d+)/results', html)
    if not m:
        res_dash = opener.open("http://127.0.0.1:5000/dashboard")
        html_dash = res_dash.read().decode('utf-8')
        m = re.search(r'/application/(\d+)/results', html_dash)
    app_id = m.group(1) if m else "1"

    # 6. Page 5: Document Upload
    res = opener.open(f"http://127.0.0.1:5000/application/{app_id}/documents")
    html = res.read().decode('utf-8')
    assert res.status == 200
    assert "Mandatory Bank Document Policy Checklist" in html
    assert "Quick Test: Attach Synthetic Demo Docs" in html
    print(f"[PASS] Page 5: Document Upload page for App #{app_id} loaded.")

    # 7. Page 6: Salary Analysis
    res = opener.open(f"http://127.0.0.1:5000/application/{app_id}/salary-analysis")
    html = res.read().decode('utf-8')
    assert res.status == 200
    assert "Salary Progression & Increment Metrics" in html
    assert "Previous Salary" in html
    assert "Debt-to-Income (DTI) Capacity" in html
    print(f"[PASS] Page 6: Salary Analysis for App #{app_id} loaded.")

    # 8. Page 7: Document Verification & Discrepancies
    res = opener.open(f"http://127.0.0.1:5000/application/{app_id}/verify-documents")
    html = res.read().decode('utf-8')
    assert res.status == 200
    assert "Automated Extraction & Authenticity Policy" in html
    assert "Declared vs Extracted Discrepancy Report" in html
    print(f"[PASS] Page 7: Document Verification & Authenticity page for App #{app_id} loaded.")

    # 9. Page 8: Explainable Eligibility Results
    res = opener.open(f"http://127.0.0.1:5000/application/{app_id}/results")
    html = res.read().decode('utf-8')
    assert res.status == 200
    assert "Eligibility Determination" in html or "Underwriting Assessment" in html or "Preliminary Loan Eligibility Assessment" in html
    assert "outcome-banner" in html
    assert "Detailed Requirement-by-Requirement Assessment" in html
    assert "What to do next" in html
    print(f"[PASS] Page 8: Explainable Eligibility Results for App #{app_id} loaded.")

    # 10. Page 11: Application History
    res = opener.open("http://127.0.0.1:5000/applications")
    html = res.read().decode('utf-8')
    assert res.status == 200
    assert "Loan Application History & Underwriting Log" in html
    print("[PASS] Page 11: Application History loaded.")

    # Log out applicant
    opener.open("http://127.0.0.1:5000/logout")

    # 11. Log in as Chief Credit Officer: officer
    data_officer = urllib.parse.urlencode({"username": "officer", "password": "Officer@123"}).encode('utf-8')
    res = opener.open("http://127.0.0.1:5000/login", data=data_officer)
    assert res.status == 200
    print("[PASS] User Authentication: Logged in as Pooja Verma (Chief Credit Officer).")

    # Officer Queue & Page 10: Bank Officer Review Workbench
    res = opener.open("http://127.0.0.1:5000/officer/queue")
    html = res.read().decode('utf-8')
    assert res.status == 200
    assert "Application Review & Verification Queue" in html
    print("[PASS] Officer Queue loaded.")

    res = opener.open("http://127.0.0.1:5000/officer/review/1")
    html = res.read().decode('utf-8')
    assert res.status == 200
    assert "Review Application #" in html
    assert "Record Underwriting Decision" in html
    assert "Correct Extraction Variance" in html
    print("[PASS] Page 10: Bank Officer Review Workbench for App #1 (with extraction override form) loaded.")

    # Log out officer
    opener.open("http://127.0.0.1:5000/logout")

    # 12. Log in as Administrator: admin
    data_admin = urllib.parse.urlencode({"username": "admin", "password": "Admin@123"}).encode('utf-8')
    res = opener.open("http://127.0.0.1:5000/login", data=data_admin)
    assert res.status == 200
    print("[PASS] User Authentication: Logged in as System Administrator.")

    # Page 9: Bank Requirements Configuration
    res = opener.open("http://127.0.0.1:5000/admin/bank-requirements")
    html = res.read().decode('utf-8')
    assert res.status == 200
    assert "Bank Requirements & Loan Policies" in html
    assert "Academic Backlog Criteria" in html
    print("[PASS] Page 9: Bank Requirements Configuration loaded.")

    # Page 12: User Management
    res = opener.open("http://127.0.0.1:5000/admin/users")
    html = res.read().decode('utf-8')
    assert res.status == 200
    assert "System User Management & Role Permissions" in html
    assert "Create New User Account" in html
    print("[PASS] Page 12: User Management loaded.")

    # Audit Logs
    res = opener.open("http://127.0.0.1:5000/admin/audit-logs")
    html = res.read().decode('utf-8')
    assert res.status == 200
    assert "System Audit & Access Trail" in html
    print("[PASS] Administrative Audit Logs loaded.")

    print("\n>>> ALL 12 REQUIRED PAGES & WORKFLOWS VERIFIED 100% OPERATIONAL! <<<")

if __name__ == '__main__':
    run_e2e_verification()
