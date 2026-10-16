# FinCred AI — Smart Loan Eligibility Checker

A professional, explainable banking web application designed for financial institutions and loan applicants. **FinCred AI** automates applicant data ingestion, inspects digital PDFs and scanned salary slips via **PyMuPDF** and **Tesseract OCR**, computes detailed salary progressions and debt obligations, evaluates borrower profiles against versioned bank requirements, and explains the final outcome in transparent, actionable plain English.

Unlike conventional underwriting tools that return simple binary approvals, FinCred AI displays **WHY** a borrower qualifies or falls short, highlights discrepancies across documents, identifies missing requirements, and outlines clear next steps for both bank officers and applicants.

---

## 🏛️ Core System Features

1. **Role-Based Access Control (RBAC):**
   - **Administrator:** Full governance over users, bank requirement rules, policy versioning, and audit trails.
   - **Bank Officer:** Application review workbench, document verification, manual extraction override/corrections, decision recording, and query management.
   - **Loan Applicant:** Guided loan application wizard, document upload repository, live EMI simulation, and explainable eligibility assessment reports.

2. **Automated Document Reading & Extraction:**
   - **Digital PDFs:** Extracted with high precision using **PyMuPDF**.
   - **Scanned Images & Docs:** Extracted using **Tesseract OCR** with image contrast preprocessing and automatic graceful fallback.
   - **Entity Extraction:** Extracts Applicant Name, Employer/Company Name, Monthly Gross & Net Salary, Pay Period/Month, Deductions, Bank Salary Credits, and Document Dates.
   - **Cross-Document Discrepancy Engine:** Compares declared salary against extracted payslips (e.g., declared ₹28,000 vs payslip ₹32,000) and flags variances for bank officer scrutiny.

3. **Financial Status & Salary Progression Engine (Step 5):**
   - **Salary Growth Analysis:** Calculates monthly delta and growth rate (e.g. Previous salary: ₹22,000 $\to$ Current salary: ₹32,000, Increase: ₹10,000 | +45.45%).
   - **Verified vs Declared Income:** Clearly labels verified amounts from payslips versus unverified applicant declarations.
   - **Average Verified Income:** Computes statistical averages over multiple uploaded slips using Python & **pandas**.
   - **Loan Amortization (EMI):** Calculates exact reducing-balance monthly installments:
     $$EMI = P \cdot r \cdot \frac{(1+r)^n}{(1+r)^n - 1}$$
   - **Debt-to-Income (DTI) Ratios:** Analyzes both current debt burden and projected post-loan DTI.
   - **Disposable Income:** Computes free cash surplus after subtracting existing EMIs, new loan EMI, and standard living expense baselines.

4. **Machine Learning Risk & Approval Scoring:**
   - Utilizes **scikit-learn** to score credit risk, default probability, and approval likelihood based on synthetic banking underwriting models.
   - Categorizes borrowers into Low, Moderate, or High Risk tiers with transparent factor drivers.

5. **Configurable Bank Requirements & Policy Versioning (Step 6):**
   - Admin-configurable limits: Min/Max Age, Min Monthly Income, Min Employment Tenure, Max DTI Ratio, Min Credit Score, Max Loan Amount & Tenure, and Mandatory Documents.
   - **Version Tracking:** Every policy modification increments the policy version to preserve historical audit integrity.
   - Clearly labelled sample demonstration policies out of the box.

6. **Multiple Loan Types & Category-Specific Underwriting:**
   - **8 Specialized Loan Categories:**
     1. **Home Loan:** Property valuation, down payment %, legal title, LTV ratio caps (up to 80-90%).
     2. **Gold Loan:** Hallmark purity (22K/24K), net grams, statutory 75% RBI LTV ceiling, live valuation against benchmark bullion rates.
     3. **Education Loan:** Target university, course category, active backlogs cap, parent/guardian co-applicant requirement.
     4. **Personal Loan:** Cash flow, unsecured risk parameters, FOIR/DTI ratio limits.
     5. **Vehicle Loan:** On-road invoice pricing, down payment %, hypothecation metrics.
     6. **Business Loan:** Entity operational vintage (months), annual revenue turnover, profit coverage.
     7. **Loan Against Property (LAP):** Registered title, encumbrance verification, commercial/residential LTV limits.
     8. **Agriculture Loan:** Cultivable land acreage, crop cycle, seasonal harvest cashflow.
   - **Loan Type Selection Portal (`/select-loan-type`):** Interactive card deck guiding applicants to the appropriate dynamic questionnaire.
   - **Admin Loan Type Catalog (`/admin/loan-types`):** Full administrator control to create, modify, configure document mandates, or toggle status of loan categories.

7. **Academic Backlog Policy Evaluation:**
   - Dedicated rule for student/education loans (e.g. Horizon Scholar Loan): compares active backlog counts against permitted caps.
   - If the selected bank does not evaluate academic backlogs (e.g. Personal/Home Loans), backlogs are transparently marked as *Not Applicable* and do not penalize the borrower.

8. **Four Explainable Assessment Outcomes:**
   - **Meets Requirements:** All verified checks satisfied.
   - **Does Not Meet Requirements:** One or more confirmed criteria failed.
   - **Pending Verification:** Mandatory documents or income records missing (missing docs are never treated as confirmed failures).
   - **Manual Review Required:** Borderline credit score or DTI requiring officer discretion.
   - For every requirement: Bank requirement, Applicant actual value, Result badge, Simple explanation, Supporting document, and Actionable next steps.

---

## 💻 Technology Stack

| Layer | Technology |
|---|---|
| **Frontend** | HTML5, CSS3, JavaScript (ES6+), Bootstrap 5.3, Bootstrap Icons |
| **Backend** | Python 3.10+ / 3.14+, Flask 3.0 |
| **Database** | SQLite via Flask-SQLAlchemy 3.1 / SQLAlchemy 2.0 |
| **PDF Extraction** | PyMuPDF (`pymupdf`) |
| **OCR Ingestion** | Tesseract OCR (`pytesseract`) + Pillow (PIL) |
| **Data Calculations**| Python, pandas, numpy |
| **Machine Learning**| scikit-learn (RandomForest risk classification) |
| **Visual Charts** | Chart.js 4.4 (Doughnut, Bar, and Gauge visualizations) |
| **Security** | PBKDF2/SHA-256 password hashing, RBAC decorators, CSRF protection, Audit Trail |

---

## 🧭 The Core Application Pages

| # | Page Name | Route | Description |
|---|---|---|---|
| 1 | **Login & Registration** | `/login`, `/register` | Role-based authentication with 1-click demo logins |
| 2 | **Loan Type Selection** | `/select-loan-type` | Interactive visual catalog of all 8 loan categories with loan terms |
| 3 | **Dashboard** | `/dashboard` | KPIs, review queue, category distribution chart, and category filters |
| 4 | **Applicant Details Form** | `/applicant/details` | Personal info, addresses, PAN, education & backlogs |
| 5 | **Dynamic Loan Application** | `/apply?loan_type=...` | Tailored questions, collateral calculators, and category policy selection |
| 6 | **Document Upload** | `/application/<id>/documents` | File ingestion, category-specific checklist, 1-click demo attachers |
| 7 | **Salary & Collateral Analysis** | `/application/<id>/salary-analysis` | Growth delta (+45.45%), verified vs declared, DTI, collateral metrics, charts |
| 8 | **Document Verification** | `/application/<id>/verify-documents` | Extracted vs declared cross-check & authenticity disclaimer |
| 9 | **Eligibility Results** | `/application/<id>/results` | 4 outcome states, loan-specific metrics, requirement breakdown, next steps |
| 10 | **Bank Requirements Config** | `/admin/bank-requirements` | Admin policy creation, versioning, category-specific limits, and backlog rules |
| 11 | **Loan Types Management** | `/admin/loan-types` | Admin catalog to create, edit, or disable master loan types |
| 12 | **Bank Officer Workbench** | `/officer/review/<id>` | Workbench: document preview, OCR correction, decision & notes |
| 13 | **Application History** | `/applications` | Historical application tracking with category filter bar |
| 14 | **User Management** | `/admin/users` | Admin account control, role assignments, and active toggles |

---

## 🚀 Windows Installation & Setup Guide

### Prerequisites
- Python 3.10 or higher installed on Windows (ensure `python` is added to your Windows PATH).
- *(Optional)* [Tesseract OCR for Windows](https://github.com/UB-Mannheim/tesseract/wiki) for scanned image processing.

### Step 1: Open PowerShell or Command Prompt
Navigate to the project root directory:
```powershell
cd d:\2.0
```

### Step 2: Create and Activate a Python Virtual Environment
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
# Or in Windows CMD:
# .\venv\Scripts\activate.bat
```

### Step 3: Install Required Dependencies
```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Step 4: Configure Environment Variables
Copy the example environment configuration:
```powershell
Copy-Item .env.example .env
```
If Tesseract is installed at a custom location, ensure `TESSERACT_CMD` in `.env` points to your `tesseract.exe` (e.g. `C:\Program Files\Tesseract-OCR\tesseract.exe`).

### Step 5: Start the FinCred AI Server
```powershell
python app.py
```
The server will initialize the SQLite database (`instance/fincred.db`), generate synthetic demonstration PDF documents, seed baseline demo users and policies, and begin listening at:
👉 **`http://127.0.0.1:5000`**

---

## 🔑 Preloaded Demo Accounts & Test Profiles

For instant evaluation, the login screen includes **1-click quick-fill buttons**:

| Account Name | Username | Password | Role | Demonstration Scenario |
|---|---|---|---|---|
| **System Administrator** | `admin` | `Admin@123` | `admin` | Configure bank policies, manage master loan types catalog, version rules & audit logs |
| **Chief Credit Officer** | `officer` | `Officer@123` | `bank_officer` | Review applications, verify documents, inspect collateral metrics, record decisions |
| **Rajesh Sharma** | `rajesh` | `Applicant@123` | `applicant` | Prime Personal & Home Loan applications preloaded with verified payslip & increment letter |
| **Priya Nair** | `priya` | `Applicant@123` | `applicant` | Education Loan with 2 active backlogs, triggering academic backlog policy check |
| **Vikram Singh** | `vikram` | `Applicant@123` | `applicant` | Gold Loan with 45g 22K pledged jewelry under 75% LTV regulatory threshold |

---

## 🧪 Running Automated Tests

FinCred AI includes a comprehensive test suite covering mathematical calculations, regex parsing, backlog policy evaluations, multi-category loan underwriting, and authentication:

```powershell
python -m pytest -v
```

All 16 automated test suites validate:
- Loan amortization EMI formula and edge cases.
- Salary progression calculation (+₹10,000 / +45.45% from specification).
- Structured entity extraction from payslips.
- Cross-check salary discrepancy detection (₹28,000 declared vs ₹32,000 extracted).
- Academic backlog evaluation across Personal Loans (disabled) vs Education Loans (active rule).
- Master loan categories seeding & catalog management.
- Gold loan collateral valuation and statutory 75% LTV cap enforcement.
- Business loan vintage and annual turnover underwriting.
- Route accessibility, role enforcement, and session security.

### End-to-End System Verification
Run the complete multi-role end-to-end simulation:
```powershell
python test_e2e_all_features.py
```
This script exercises 12 critical user journeys across applicant loan application, collateral valuation, synthetic document attachment, explainable results rendering, dashboard category filtering, admin catalog CRUD, and bank officer review.

---

## 🔒 Security & Data Integrity

- **Password Security:** Salted and hashed using Werkzeug PBKDF2/SHA-256. Passwords are never stored in plain text.
- **Upload Validation:** Strictly enforces whitelist extensions (`.pdf`, `.png`, `.jpg`, `.jpeg`), sanitizes file names via `secure_filename`, and enforces a 16MB ceiling.
- **Audit Logging:** Automatically logs user logins, document uploads, manual officer corrections, policy updates, and final underwriting decisions with timestamps and IP addresses.
- **Data Isolation:** Applicants can only inspect their own loan submissions; officers and admins have role-scoped access to queues and sensitive financial documentation.
