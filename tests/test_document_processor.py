import pytest
from services.document_processor import DocumentProcessor

def test_extract_structured_fields_from_text():
    sample_slip_text = """
    APEX TECH SOLUTIONS PVT LTD
    IT Park, Sector 62, Noida, UP
    PAYSLIP FOR AUGUST 2024
    Employee Name: Rajesh Sharma
    Designation: Senior Software Engineer
    PAN: ABCPS1234F
    Basic Salary: 20000.00
    House Rent Allowance: 10000.00
    Total Deductions: 2600.00
    Net Pay: 32000.00
    Date: 31/08/2024
    """

    fields = DocumentProcessor.extract_structured_fields(sample_slip_text, 'salary_slip')
    
    assert fields["applicant_name"] == "Rajesh Sharma"
    assert "APEX TECH SOLUTIONS" in fields["company_name"].upper()
    assert fields["salary_amount"] == 32000.0
    assert "AUGUST 2024" in fields["salary_month"].upper()
    assert fields["confidence_score"] > 50.0

def test_salary_discrepancy_detection():
    # Mock class for test
    class MockApplicant:
        full_name = "Rajesh Sharma"
    
    class MockApp:
        id = 1
        declared_monthly_salary = 28000.0 # Declared 28k
        company_name = "Apex Tech Solutions Pvt Ltd"
        applicant = MockApplicant()

    class MockExtracted:
        document_id = 10
        salary_amount_extracted = 32000.0 # Document shows 32k
        company_name_extracted = "Apex Tech Solutions Pvt Ltd"
        applicant_name_extracted = "Rajesh Sharma"

    result = DocumentProcessor.cross_check_application(MockApp(), [MockExtracted()])

    assert result["has_discrepancy"] is True
    assert len(result["discrepancies"]) == 1
    disc = result["discrepancies"][0]
    assert disc["field"] == "Monthly Salary"
    assert "₹28,000.00" in disc["declared"]
    assert "₹32,000.00" in disc["extracted"]
    assert "₹4,000.00" in disc["difference"]
    assert "14.29%" in disc["difference"]
