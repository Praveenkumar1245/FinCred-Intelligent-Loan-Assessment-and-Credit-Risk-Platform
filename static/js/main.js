// FinCred AI — Main Interactive Client Scripts

document.addEventListener('DOMContentLoaded', function () {
    // 1. Auto-dismiss flash alerts
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            if (alert && alert.parentNode) {
                alert.classList.remove('show');
                setTimeout(() => alert.remove(), 250);
            }
        }, 6000);
    });

    // 2. Interactive Loan Calculator (in Loan Application Form)
    const amountInput = document.getElementById('loan_amount_requested');
    const tenureInput = document.getElementById('loan_tenure_months');
    const rateInput = document.getElementById('bank_requirement_id');
    const liveEmiDisplay = document.getElementById('live_emi_display');

    function calculateLiveEmi() {
        if (!amountInput || !tenureInput || !liveEmiDisplay) return;
        
        const P = parseFloat(amountInput.value) || 0;
        const n = parseInt(tenureInput.value) || 36;
        
        // Extract rate from selected bank option data-rate attribute
        let rate = 10.5;
        if (rateInput && rateInput.selectedOptions && rateInput.selectedOptions[0]) {
            const rVal = rateInput.selectedOptions[0].getAttribute('data-rate');
            if (rVal) rate = parseFloat(rVal);
        }

        if (P <= 0 || n <= 0) {
            liveEmiDisplay.innerText = '₹0.00';
            return;
        }

        const r = (rate / 100.0) / 12.0;
        let emi = 0;
        if (r === 0) {
            emi = P / n;
        } else {
            emi = (P * r * Math.pow(1 + r, n)) / (Math.pow(1 + r, n) - 1);
        }

        liveEmiDisplay.innerText = '₹' + Math.round(emi).toLocaleString('en-IN') + '/mo';
    }

    if (amountInput) amountInput.addEventListener('input', calculateLiveEmi);
    if (tenureInput) tenureInput.addEventListener('input', calculateLiveEmi);
    if (rateInput) rateInput.addEventListener('change', calculateLiveEmi);
    calculateLiveEmi();

    // 3. Document Upload Hint Assistant
    const docTypeSelect = document.getElementById('document_type');
    const docHintBox = document.getElementById('doc_type_hint');
    const hints = {
        'salary_slip': 'Upload your official monthly payslip (PDF/Image) showing Gross Pay, Net Pay, and Deductions.',
        'bank_statement': 'Upload official bank statement (minimum 3-6 months) showing consistent salary credit entries.',
        'increment_letter': 'Upload the annual appraisal / salary revision letter verifying your salary increment date and revised CTC.',
        'id_proof': 'Upload official Government Photo ID (PAN Card, Passport, or Aadhaar) to verify name and Date of Birth.',
        'address_proof': 'Upload recent Utility bill, Voter ID, or Rental agreement for address verification.',
        'tax_doc': 'Upload Form 16 (Part A & B) or Income Tax Return (ITR-V) acknowledgment.',
        'credit_report': 'Upload official credit bureau report (CIBIL / Experian) PDF.',
        'education_cert': 'Upload Semester Marksheet or Degree Certificate showing completion and backlog records.',
        'property_docs': 'Upload registered Title Deed, Sale Agreement, Allotment Letter, or Property Tax Receipt verifying legal ownership.',
        'property_documents': 'Upload registered Title Deed, Sale Agreement, Allotment Letter, or Property Tax Receipt verifying legal ownership.'
    };

    if (docTypeSelect && docHintBox) {
        docTypeSelect.addEventListener('change', function () {
            docHintBox.innerText = hints[this.value] || 'Upload official supporting document in PDF or high-resolution image.';
        });
    }
});

// Quick Login Demo Credential Helper
function quickLogin(username, password) {
    const uField = document.getElementById('username');
    const pField = document.getElementById('password');
    if (uField && pField) {
        uField.value = username;
        pField.value = password;
        const form = uField.closest('form');
        if (form) form.submit();
    }
}
