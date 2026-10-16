from pathlib import Path
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

class SampleDocGenerator:
    """
    Generates synthetic demonstration PDFs (salary slips, bank statements, increment letters)
    using PyMuPDF for easy one-click testing and demonstration.
    """

    @staticmethod
    def ensure_sample_documents(sample_dir):
        """Generate demo documents if not already created"""
        sample_dir = Path(sample_dir)
        sample_dir.mkdir(parents=True, exist_ok=True)

        if not fitz:
            return {}

        paths = {
            "salary_slip": sample_dir / "Sample_Salary_Slip_Aug2024.pdf",
            "bank_statement": sample_dir / "Sample_Bank_Statement.pdf",
            "increment_letter": sample_dir / "Sample_Increment_Letter.pdf",
            "property_docs": sample_dir / "Sample_Property_Title_Deed.pdf",
            "property_documents": sample_dir / "Sample_Property_Title_Deed.pdf",
            "id_proof": sample_dir / "Sample_Identity_Proof_Aadhaar.pdf",
            "pan_card": sample_dir / "Sample_PAN_Card.pdf",
            "address_proof": sample_dir / "Sample_Address_Proof_Utility.pdf",
            "gold_valuation": sample_dir / "Sample_Gold_Valuation_Certificate.pdf",
            "gold_valuation_appraisal": sample_dir / "Sample_Gold_Valuation_Certificate.pdf",
            "gold_ownership_receipt": sample_dir / "Sample_Gold_Purchase_Receipt.pdf",
            "pledge_declaration": sample_dir / "Sample_Gold_Pledge_Declaration.pdf",
            "admission_letter": sample_dir / "Sample_University_Admission_Letter.pdf",
            "fee_structure": sample_dir / "Sample_Course_Fee_Structure.pdf",
            "education_cert": sample_dir / "Sample_Academic_Degree_Transcript.pdf",
            "vehicle_quotation": sample_dir / "Sample_Vehicle_Dealer_Quotation.pdf",
            "business_reg": sample_dir / "Sample_Business_Registration_Udyam.pdf",
            "land_records": sample_dir / "Sample_Land_Revenue_Patta.pdf",
            "tax_doc": sample_dir / "Sample_Form16_Tax_Return.pdf"
        }

        # 1. Salary Slip
        if not paths["salary_slip"].exists():
            doc = fitz.open()
            page = doc.new_page(width=595, height=842) # A4
            
            # Header
            page.draw_rect(fitz.Rect(40, 40, 555, 100), color=(0.08, 0.22, 0.38), fill=(0.08, 0.22, 0.38))
            page.insert_text((60, 75), "APEX TECH SOLUTIONS PVT LTD", fontsize=18, color=(1, 1, 1))
            page.insert_text((60, 92), "IT Park, Sector 62, Noida, UP - 201309 | CIN: U72200UP2018PTC109823", fontsize=9, color=(0.8, 0.85, 0.9))

            # Title
            page.insert_text((220, 130), "PAYSLIP FOR AUGUST 2024", fontsize=14, color=(0.08, 0.22, 0.38))
            page.draw_line(fitz.Point(40, 145), fitz.Point(555, 145), color=(0.8, 0.8, 0.8))

            # Employee details
            y = 170
            page.insert_text((50, y), "Employee Name: Rajesh Sharma", fontsize=11, color=(0, 0, 0))
            page.insert_text((330, y), "Designation: Senior Software Engineer", fontsize=11, color=(0, 0, 0))
            y += 22
            page.insert_text((50, y), "Employee ID: ATS-10492", fontsize=11, color=(0, 0, 0))
            page.insert_text((330, y), "Department: Engineering", fontsize=11, color=(0, 0, 0))
            y += 22
            page.insert_text((50, y), "Bank Account: HDFC Bank - 501004928192", fontsize=11, color=(0, 0, 0))
            page.insert_text((330, y), "PAN: ABCPS1234F", fontsize=11, color=(0, 0, 0))
            y += 22
            page.insert_text((50, y), "Pay Period: August 2024", fontsize=11, color=(0, 0, 0))
            page.insert_text((330, y), "Date: 31/08/2024", fontsize=11, color=(0, 0, 0))

            # Table Header
            y += 35
            page.draw_rect(fitz.Rect(40, y, 555, y + 25), fill=(0.92, 0.94, 0.97))
            page.insert_text((55, y + 17), "EARNINGS", fontsize=10, color=(0.08, 0.22, 0.38))
            page.insert_text((230, y + 17), "AMOUNT (₹)", fontsize=10, color=(0.08, 0.22, 0.38))
            page.insert_text((315, y + 17), "DEDUCTIONS", fontsize=10, color=(0.08, 0.22, 0.38))
            page.insert_text((480, y + 17), "AMOUNT (₹)", fontsize=10, color=(0.08, 0.22, 0.38))

            # Table rows
            y += 25
            rows = [
                ("Basic Salary", "20,000.00", "Provident Fund (PF)", "2,400.00"),
                ("House Rent Allowance (HRA)", "10,000.00", "Professional Tax (PT)", "200.00"),
                ("Special Allowance", "4,600.00", "TDS / Income Tax", "0.00"),
                ("Transport Allowance", "0.00", "Total Deductions", "2,600.00")
            ]
            for r1, r2, r3, r4 in rows:
                y += 20
                page.insert_text((55, y), r1, fontsize=9.5, color=(0.2, 0.2, 0.2))
                page.insert_text((245, y), r2, fontsize=9.5, color=(0.2, 0.2, 0.2))
                page.insert_text((315, y), r3, fontsize=9.5, color=(0.2, 0.2, 0.2))
                page.insert_text((495, y), r4, fontsize=9.5, color=(0.2, 0.2, 0.2))

            # Totals
            y += 30
            page.draw_rect(fitz.Rect(40, y, 555, y + 30), fill=(0.88, 0.92, 0.96))
            page.insert_text((55, y + 20), "Total Gross Earnings: ₹34,600.00", fontsize=11, color=(0.08, 0.22, 0.38))
            page.insert_text((315, y + 20), "Total Deductions: ₹2,600.00", fontsize=11, color=(0.08, 0.22, 0.38))

            # Net Pay Box
            y += 45
            page.draw_rect(fitz.Rect(40, y, 555, y + 45), color=(0.08, 0.22, 0.38), fill=(0.95, 0.97, 1.0))
            page.insert_text((60, y + 28), "NET PAY: ₹32,000.00", fontsize=15, color=(0.08, 0.22, 0.38))
            page.insert_text((280, y + 28), "(Rupees Thirty-Two Thousand Only)", fontsize=10, color=(0.3, 0.3, 0.3))

            # Footer
            page.insert_text((60, 780), "This is a computer-generated payslip and requires no physical signature.", fontsize=8, color=(0.5, 0.5, 0.5))
            doc.save(str(paths["salary_slip"]))
            doc.close()

        # 2. Bank Statement
        if not paths["bank_statement"].exists():
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.draw_rect(fitz.Rect(40, 40, 555, 95), fill=(0.05, 0.18, 0.32))
            page.insert_text((60, 70), "METRO TRUST BANK", fontsize=16, color=(1, 1, 1))
            page.insert_text((60, 85), "Statement of Account - Current / Savings", fontsize=9.5, color=(0.85, 0.9, 0.95))

            page.insert_text((50, 125), "Account Holder: Rajesh Sharma", fontsize=11, color=(0, 0, 0))
            page.insert_text((50, 142), "Account Number: 501004928192", fontsize=10, color=(0.2, 0.2, 0.2))
            page.insert_text((350, 125), "Statement Period: 01/06/2024 to 31/08/2024", fontsize=9.5, color=(0.2, 0.2, 0.2))
            page.insert_text((350, 142), "Statement Date: 01/09/2024", fontsize=9.5, color=(0.2, 0.2, 0.2))

            y = 180
            page.draw_rect(fitz.Rect(40, y, 555, y + 22), fill=(0.93, 0.94, 0.96))
            page.insert_text((50, y + 15), "Date", fontsize=9, color=(0.1, 0.2, 0.3))
            page.insert_text((130, y + 15), "Transaction Particulars", fontsize=9, color=(0.1, 0.2, 0.3))
            page.insert_text((350, y + 15), "Debit (₹)", fontsize=9, color=(0.1, 0.2, 0.3))
            page.insert_text((430, y + 15), "Credit (₹)", fontsize=9, color=(0.1, 0.2, 0.3))
            page.insert_text((500, y + 15), "Balance (₹)", fontsize=9, color=(0.1, 0.2, 0.3))

            txns = [
                ("30/06/2024", "SALARY CREDIT - APEX TECH SOLUTIONS", "-", "32,000.00", "48,250.00"),
                ("05/07/2024", "UPI / RENT TRANSFER", "10,000.00", "-", "38,250.00"),
                ("31/07/2024", "SALARY CREDIT - APEX TECH SOLUTIONS", "-", "32,000.00", "64,120.00"),
                ("03/08/2024", "AUTO DEBIT - HDFC PERSONAL LOAN EMI", "4,500.00", "-", "59,620.00"),
                ("31/08/2024", "ACH SALARY CREDIT - APEX TECH SOLUTIONS", "-", "32,000.00", "86,410.00")
            ]
            y += 22
            for dt, desc, dr, cr, bal in txns:
                y += 24
                page.insert_text((50, y), dt, fontsize=8.5, color=(0.2, 0.2, 0.2))
                page.insert_text((130, y), desc, fontsize=8.5, color=(0.2, 0.2, 0.2))
                page.insert_text((360, y), dr, fontsize=8.5, color=(0.2, 0.2, 0.2))
                page.insert_text((440, y), cr, fontsize=8.5, color=(0.0, 0.5, 0.2) if cr != '-' else (0.2, 0.2, 0.2))
                page.insert_text((500, y), bal, fontsize=8.5, color=(0.2, 0.2, 0.2))

            doc.save(str(paths["bank_statement"]))
            doc.close()

        # 3. Increment Letter
        if not paths["increment_letter"].exists():
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.insert_text((60, 70), "APEX TECH SOLUTIONS PVT LTD", fontsize=15, color=(0.08, 0.22, 0.38))
            page.insert_text((60, 88), "Human Resources Department | Date: 15/06/2024", fontsize=10, color=(0.4, 0.4, 0.4))
            page.draw_line(fitz.Point(60, 105), fitz.Point(535, 105), color=(0.8, 0.8, 0.8))

            page.insert_text((60, 135), "To,", fontsize=11, color=(0, 0, 0))
            page.insert_text((60, 150), "Rajesh Sharma", fontsize=11, color=(0, 0, 0))
            page.insert_text((60, 165), "Designation: Senior Software Engineer", fontsize=11, color=(0, 0, 0))
            page.insert_text((60, 180), "Emp ID: ATS-10492", fontsize=11, color=(0, 0, 0))

            page.insert_text((60, 215), "Subject: Annual Compensation Revision & Promotion Letter", fontsize=12, color=(0.08, 0.22, 0.38))

            body1 = (
                "Dear Rajesh,\n\n"
                "In recognition of your exceptional performance and dedication towards engineering deliverables, "
                "management is pleased to announce a revision in your compensation structure effective 01 July 2024.\n\n"
                "Your previous monthly compensation of Rs. 22,000.00 (Twenty-Two Thousand Only) has been revised "
                "to Rs. 32,000.00 (Thirty-Two Thousand Only) per month. This constitutes an annual increment of Rs. 1,20,000.00 "
                "(Monthly increase: Rs. 10,000.00 | 45.45% increment)."
            )
            rect = fitz.Rect(60, 240, 535, 380)
            page.insert_textbox(rect, body1, fontsize=10.5, color=(0.15, 0.15, 0.15))

            page.insert_text((60, 410), "Summary of Revised Structure:", fontsize=11, color=(0.08, 0.22, 0.38))
            page.insert_text((80, 435), "• Previous Monthly Salary: Rs. 22,000.00", fontsize=10.5, color=(0.2, 0.2, 0.2))
            page.insert_text((80, 455), "• Revised Current Monthly Salary: Rs. 32,000.00", fontsize=10.5, color=(0.2, 0.2, 0.2))
            page.insert_text((80, 475), "• Monthly Salary Increase: Rs. 10,000.00", fontsize=10.5, color=(0.2, 0.2, 0.2))
            page.insert_text((80, 495), "• Percentage Revision: 45.45%", fontsize=10.5, color=(0.2, 0.2, 0.2))
            page.insert_text((80, 515), "• Effective Date: 01/07/2024", fontsize=10.5, color=(0.2, 0.2, 0.2))

            page.insert_text((60, 560), "Sincerely,", fontsize=11, color=(0, 0, 0))
            page.insert_text((60, 580), "Human Resources & Talent Management", fontsize=11, color=(0.08, 0.22, 0.38))
            page.insert_text((60, 595), "Apex Tech Solutions Pvt Ltd", fontsize=10, color=(0.4, 0.4, 0.4))

            doc.save(str(paths["increment_letter"]))
            doc.close()

        # 4. Property Documents (Deed of Sale / Title Deed)
        if not paths["property_docs"].exists():
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)

            # Elegant Navy Header Band
            page.draw_rect(fitz.Rect(40, 40, 555, 95), color=(0.08, 0.22, 0.38), fill=(0.08, 0.22, 0.38))
            page.insert_text((60, 72), "OFFICE OF THE SUB-REGISTRAR OF ASSURANCES", fontsize=15, color=(1, 1, 1))
            page.insert_text((60, 88), "GOVERNMENT LAND REVENUE & REGISTRATION DEPARTMENT | REGION: NORTH-IV", fontsize=8.5, color=(0.85, 0.9, 0.95))

            # Document Title Banner
            page.insert_text((160, 125), "DEED OF ABSOLUTE SALE & TITLE CONVEYANCE", fontsize=13, color=(0.08, 0.22, 0.38))
            page.draw_line(fitz.Point(40, 138), fitz.Point(555, 138), color=(0.8, 0.8, 0.8))

            # Registration Metadata Box
            y = 150
            page.draw_rect(fitz.Rect(40, y, 555, y + 55), fill=(0.95, 0.96, 0.98), color=(0.85, 0.88, 0.92))
            page.insert_text((55, y + 18), "Document Reg No: DL-REG-2023-88492", fontsize=9.5, color=(0.1, 0.1, 0.1))
            page.insert_text((320, y + 18), "Date of Registration: 18/11/2023", fontsize=9.5, color=(0.1, 0.1, 0.1))
            page.insert_text((55, y + 38), "Book No: 1 | Volume: 482 | Pages: 12-28", fontsize=9.5, color=(0.1, 0.1, 0.1))
            page.insert_text((320, y + 38), "Stamp Duty Paid: Rs. 3,30,000.00 (Challan #88392)", fontsize=9.5, color=(0.1, 0.1, 0.1))

            # Parties Section
            y += 75
            page.insert_text((45, y), "SCHEDULE I: DETAILS OF CONTRACTING PARTIES", fontsize=11, color=(0.08, 0.22, 0.38))
            page.draw_line(fitz.Point(45, y + 5), fitz.Point(555, y + 5), color=(0.08, 0.22, 0.38))

            y += 25
            page.insert_text((55, y), "1. VENDOR / TRANSFEROR:", fontsize=10, color=(0.3, 0.3, 0.3))
            page.insert_text((55, y + 18), "Company: Prime Heritage Developers Pvt Ltd, Rep by Managing Director", fontsize=10, color=(0, 0, 0))
            page.insert_text((55, y + 34), "Corporate Office: 104, Horizon Towers, MG Road, Gurgaon, Haryana", fontsize=9, color=(0.3, 0.3, 0.3))

            y += 55
            page.insert_text((55, y), "2. PURCHASER / TRANSFEREE (BENEFICIARY):", fontsize=10, color=(0.3, 0.3, 0.3))
            page.insert_text((55, y + 18), "Purchaser: Rajesh Sharma, S/o Shri Om Prakash Sharma", fontsize=10, color=(0, 0, 0))
            page.insert_text((55, y + 34), "PAN: ABCPS1234F | Aadhaar No: XXXX-XXXX-4819", fontsize=9, color=(0.3, 0.3, 0.3))

            # Property Schedule Section
            y += 60
            page.insert_text((45, y), "SCHEDULE II: DESCRIPTION OF CONVEYED PROPERTY", fontsize=11, color=(0.08, 0.22, 0.38))
            page.draw_line(fitz.Point(45, y + 5), fitz.Point(555, y + 5), color=(0.08, 0.22, 0.38))

            y += 25
            page.insert_text((55, y), "Property Description: Residential Flat No. 402, 4th Floor, Tower B", fontsize=10, color=(0, 0, 0))
            page.insert_text((55, y + 18), "Project Name: Royal Residency Township, Sector 45, Gurgaon", fontsize=10, color=(0, 0, 0))
            page.insert_text((55, y + 34), "Super Built-up Area: 1,650 Sq. Ft. | Carpet Area: 1,280 Sq. Ft.", fontsize=9.5, color=(0.2, 0.2, 0.2))
            page.insert_text((55, y + 50), "Revenue Khata No: 482/19 | Survey No: 88/2 | City Municipal Limits", fontsize=9.5, color=(0.2, 0.2, 0.2))

            # Consideration & Value Box
            y += 75
            page.draw_rect(fitz.Rect(40, y, 555, y + 60), fill=(0.92, 0.96, 0.94), color=(0.2, 0.6, 0.3))
            page.insert_text((55, y + 22), "TOTAL SALE CONSIDERATION / AGREEMENT VALUE:", fontsize=11, color=(0.08, 0.4, 0.2))
            page.insert_text((55, y + 45), "Consideration Amount: Rs. 55,00,000.00 (Fifty-Five Lakhs Only)", fontsize=13, color=(0.08, 0.22, 0.38))

            # Encumbrance & Legal Title Warranty
            y += 80
            page.insert_text((45, y), "TITLE CERTIFICATION & WARRANTY:", fontsize=10.5, color=(0.08, 0.22, 0.38))
            body_text = (
                "The Vendor hereby covenants with the Purchaser that the schedule property is absolute, marketable, "
                "free from all encumbrances, charges, liens, mortgages, attachments, property tax arrears, and litigation. "
                "The Purchaser has acquired absolute, clear, and unencumbered ownership rights along with all undivided share."
            )
            rect = fitz.Rect(45, y + 10, 555, y + 60)
            page.insert_textbox(rect, body_text, fontsize=9, color=(0.2, 0.2, 0.2))

            # Seal & Signature Footer
            page.insert_text((55, 780), "[SEAL OF SUB-REGISTRAR]", fontsize=9, color=(0.4, 0.4, 0.4))
            page.insert_text((350, 780), "Authorized Registrar Signature & Seal", fontsize=9, color=(0.4, 0.4, 0.4))
            doc.save(str(paths["property_docs"]))
            doc.close()

        # 5. Identity Proof (Government UID / Aadhaar)
        if not paths["id_proof"].exists():
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.draw_rect(fitz.Rect(40, 40, 555, 95), fill=(0.12, 0.35, 0.55))
            page.insert_text((60, 72), "UNIQUE IDENTIFICATION AUTHORITY OF INDIA", fontsize=15, color=(1, 1, 1))
            page.insert_text((60, 88), "GOVERNMENT OF INDIA | AADHAAR IDENTITY CARD", fontsize=8.5, color=(0.85, 0.9, 0.95))
            page.draw_rect(fitz.Rect(50, 130, 160, 260), fill=(0.94, 0.96, 0.98), color=(0.7, 0.8, 0.9))
            page.insert_text((75, 200), "[ PHOTO ]", fontsize=11, color=(0.4, 0.5, 0.6))
            page.insert_text((190, 150), "Name: Rajesh Sharma", fontsize=13, color=(0.1, 0.2, 0.3))
            page.insert_text((190, 175), "Date of Birth: 15/05/1990", fontsize=11, color=(0.2, 0.2, 0.2))
            page.insert_text((190, 200), "Gender: Male", fontsize=11, color=(0.2, 0.2, 0.2))
            page.insert_text((190, 225), "Aadhaar Number: 4920 8819 1049", fontsize=14, color=(0.08, 0.22, 0.38))
            page.insert_text((190, 250), "Address: Flat 402, Royal Residency, Sector 45, Gurgaon, HR - 122003", fontsize=9.5, color=(0.3, 0.3, 0.3))
            doc.save(str(paths["id_proof"]))
            doc.close()

        # 6. PAN Card
        if not paths["pan_card"].exists():
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.draw_rect(fitz.Rect(40, 40, 555, 90), fill=(0.05, 0.25, 0.45))
            page.insert_text((60, 70), "INCOME TAX DEPARTMENT, GOVT OF INDIA", fontsize=14, color=(1, 1, 1))
            page.insert_text((60, 85), "PERMANENT ACCOUNT NUMBER (PAN) CARD", fontsize=9, color=(0.85, 0.9, 0.95))
            page.insert_text((60, 140), "Name: RAJESH SHARMA", fontsize=12, color=(0, 0, 0))
            page.insert_text((60, 165), "Father's Name: OM PRAKASH SHARMA", fontsize=11, color=(0.2, 0.2, 0.2))
            page.insert_text((60, 190), "Date of Birth: 15/05/1990", fontsize=11, color=(0.2, 0.2, 0.2))
            page.insert_text((60, 220), "Permanent Account Number:", fontsize=10, color=(0.4, 0.4, 0.4))
            page.insert_text((60, 245), "PAN: ABCPS1234F", fontsize=16, color=(0.08, 0.22, 0.38))
            doc.save(str(paths["pan_card"]))
            doc.close()

        # 7. Address Proof (Utility / Electricity Bill)
        if not paths["address_proof"].exists():
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.draw_rect(fitz.Rect(40, 40, 555, 90), fill=(0.1, 0.3, 0.25))
            page.insert_text((60, 70), "STATE POWER DISTRIBUTION CORPORATION LTD", fontsize=14, color=(1, 1, 1))
            page.insert_text((60, 85), "MONTHLY ELECTRICITY UTILITY & RESIDENTIAL ADDRESS PROOF", fontsize=8.5, color=(0.85, 0.95, 0.9))
            page.insert_text((60, 140), "Consumer Name: Rajesh Sharma", fontsize=12, color=(0, 0, 0))
            page.insert_text((60, 160), "Consumer ID: ELEC-4810928-N", fontsize=10, color=(0.2, 0.2, 0.2))
            page.insert_text((60, 185), "Service Address: Flat 402, Royal Residency, Sector 45, Gurgaon, HR - 122003", fontsize=10.5, color=(0.1, 0.1, 0.1))
            page.insert_text((60, 210), "Billing Period: 01/08/2024 - 31/08/2024 | Status: Paid in Full", fontsize=9.5, color=(0.3, 0.3, 0.3))
            doc.save(str(paths["address_proof"]))
            doc.close()

        # 8. Gold Valuation Certificate
        if not paths["gold_valuation"].exists():
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.draw_rect(fitz.Rect(40, 40, 555, 95), fill=(0.55, 0.42, 0.08))
            page.insert_text((60, 72), "APEX BULLION ASSAYERS & VALUERS LTD", fontsize=15, color=(1, 1, 1))
            page.insert_text((60, 88), "GOVERNMENT APPROVED VALUER & BIS HALLMARK CENTRE | REG: VAL-G-4019", fontsize=8.5, color=(0.95, 0.9, 0.8))
            page.insert_text((60, 140), "Customer Name: Vikram Singh / Rajesh Sharma", fontsize=11, color=(0, 0, 0))
            page.insert_text((60, 160), "Valuation Date: 16/10/2026 | Assayer Certificate: GLD-VAL-2026-992", fontsize=10, color=(0.2, 0.2, 0.2))
            page.draw_rect(fitz.Rect(50, 180, 545, 260), fill=(0.98, 0.96, 0.90), color=(0.8, 0.65, 0.2))
            page.insert_text((65, 205), "Pledged Article: 22 Karat BIS Hallmark Gold Jewelry (Necklace & Bangles)", fontsize=10.5, color=(0.1, 0.1, 0.1))
            page.insert_text((65, 225), "Gross Weight: 48.20 Grams | Net Pure Weight: 45.00 Grams", fontsize=10.5, color=(0.1, 0.1, 0.1))
            page.insert_text((65, 245), "Benchmark Market Rate: Rs. 6,800.00 / Gram (22K)", fontsize=10.5, color=(0.1, 0.1, 0.1))
            page.draw_rect(fitz.Rect(50, 280, 545, 340), fill=(0.92, 0.95, 0.92), color=(0.2, 0.6, 0.3))
            page.insert_text((65, 305), "TOTAL NET APPRAISED GOLD VALUE: Rs. 3,06,000.00", fontsize=13, color=(0.08, 0.4, 0.2))
            page.insert_text((65, 325), "Statutory Maximum 75% RBI LTV Eligible Loan Ceiling: Rs. 2,29,500.00", fontsize=10.5, color=(0.08, 0.22, 0.38))
            doc.save(str(paths["gold_valuation"]))
            doc.close()

        # 9. University Admission Letter & Fee Structure
        if not paths["admission_letter"].exists():
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.draw_rect(fitz.Rect(40, 40, 555, 95), fill=(0.18, 0.15, 0.45))
            page.insert_text((60, 72), "HORIZON GLOBAL INSTITUTE OF TECHNOLOGY", fontsize=15, color=(1, 1, 1))
            page.insert_text((60, 88), "FACULTY OF GRADUATE STUDIES | OFFICE OF ADMISSIONS", fontsize=8.5, color=(0.9, 0.9, 0.95))
            page.insert_text((60, 140), "Student Name: Priya Nair", fontsize=11, color=(0, 0, 0))
            page.insert_text((60, 160), "Admit Term: Academic Year 2026-2027 | Student ID: HGI-2026-4029", fontsize=10, color=(0.2, 0.2, 0.2))
            page.insert_text((60, 185), "Program: Master of Science in Artificial Intelligence & Data Systems (M.S.)", fontsize=11, color=(0.08, 0.22, 0.38))
            page.insert_text((60, 210), "Program Duration: 24 Months (Full-Time Residential)", fontsize=10, color=(0.2, 0.2, 0.2))
            page.insert_text((60, 245), "TUITION & RESIDENTIAL EXPENSE BREAKDOWN:", fontsize=11, color=(0.18, 0.15, 0.45))
            page.insert_text((80, 270), "• Tuition & Laboratory Fees: Rs. 14,00,000.00", fontsize=10, color=(0.2, 0.2, 0.2))
            page.insert_text((80, 290), "• Campus Housing & Living Allowance: Rs. 4,50,000.00", fontsize=10, color=(0.2, 0.2, 0.2))
            page.insert_text((80, 310), "• Books, Laptop & Study Material: Rs. 1,50,000.00", fontsize=10, color=(0.2, 0.2, 0.2))
            page.insert_text((60, 345), "Total Estimated Course Cost: Rs. 20,00,000.00 (Twenty Lakhs Only)", fontsize=12, color=(0.08, 0.4, 0.2))
            doc.save(str(paths["admission_letter"]))
            doc.close()

        # 10. Vehicle Quotation
        if not paths["vehicle_quotation"].exists():
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.draw_rect(fitz.Rect(40, 40, 555, 90), fill=(0.2, 0.2, 0.25))
            page.insert_text((60, 70), "APEX MOTORS AUTOMOBILE DEALERSHIP", fontsize=15, color=(1, 1, 1))
            page.insert_text((60, 85), "AUTHORIZED AUTOMOTIVE SALES & SERVICE | PROFORMA QUOTATION", fontsize=8.5, color=(0.9, 0.9, 0.95))
            page.insert_text((60, 135), "Customer Name: Rajesh Sharma", fontsize=11, color=(0, 0, 0))
            page.insert_text((60, 155), "Vehicle Model: Nexon EV Empowered Plus (Electric Long Range)", fontsize=11, color=(0.08, 0.22, 0.38))
            page.insert_text((80, 185), "1. Ex-Showroom Vehicle Price: Rs. 13,20,000.00", fontsize=10, color=(0.2, 0.2, 0.2))
            page.insert_text((80, 205), "2. RTO Road Tax & Registration: Rs. 75,000.00", fontsize=10, color=(0.2, 0.2, 0.2))
            page.insert_text((80, 225), "3. Comprehensive Insurance (3 Years): Rs. 55,000.00", fontsize=10, color=(0.2, 0.2, 0.2))
            page.insert_text((60, 260), "Total On-Road Quotation Price: Rs. 14,50,000.00", fontsize=13, color=(0.08, 0.4, 0.2))
            page.insert_text((60, 285), "Customer Down Payment (15%): Rs. 2,17,500.00 | Net Loan Required: Rs. 12,32,500.00", fontsize=10.5, color=(0.1, 0.1, 0.1))
            doc.save(str(paths["vehicle_quotation"]))
            doc.close()

        # 11. Business Registration & GST
        if not paths["business_reg"].exists():
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.draw_rect(fitz.Rect(40, 40, 555, 90), fill=(0.15, 0.35, 0.45))
            page.insert_text((60, 70), "MINISTRY OF MICRO, SMALL & MEDIUM ENTERPRISES", fontsize=14, color=(1, 1, 1))
            page.insert_text((60, 85), "UDYAM REGISTRATION CERTIFICATE | GOVERNMENT OF INDIA", fontsize=8.5, color=(0.85, 0.95, 0.95))
            page.insert_text((60, 135), "Enterprise Name: Universal Crafts & Logistics Pvt Ltd", fontsize=12, color=(0, 0, 0))
            page.insert_text((60, 155), "Registration No: UDYAM-DL-03-0049281", fontsize=10.5, color=(0.2, 0.2, 0.2))
            page.insert_text((60, 175), "Major Activity: Services / Trading | Enterprise Type: Small Enterprise", fontsize=10, color=(0.2, 0.2, 0.2))
            page.insert_text((60, 195), "Date of Incorporation / Vintage: 12/04/2021 (Vintage: > 36 Months)", fontsize=10, color=(0.2, 0.2, 0.2))
            page.insert_text((60, 215), "GSTIN: 07AAAAU1234F1Z8 | Annual Turnover: Rs. 50,00,000.00", fontsize=10.5, color=(0.08, 0.22, 0.38))
            doc.save(str(paths["business_reg"]))
            doc.close()

        # 12. Land Revenue Records / Patta
        if not paths["land_records"].exists():
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.draw_rect(fitz.Rect(40, 40, 555, 90), fill=(0.1, 0.4, 0.2))
            page.insert_text((60, 70), "GOVERNMENT LAND REVENUE DEPARTMENT", fontsize=14, color=(1, 1, 1))
            page.insert_text((60, 85), "AGRICULTURAL LAND HOLDING EXTRACT (PATTA / KHASRA / 7-12)", fontsize=8.5, color=(0.9, 0.95, 0.9))
            page.insert_text((60, 135), "Landholder Name: Rajesh Sharma", fontsize=12, color=(0, 0, 0))
            page.insert_text((60, 155), "Village / Tehsil: North Rampur, District: Meerut", fontsize=10, color=(0.2, 0.2, 0.2))
            page.insert_text((60, 175), "Survey / Khasra No: 142/1, 142/2 | Land Category: Irrigated Cultivable", fontsize=10.5, color=(0.2, 0.2, 0.2))
            page.insert_text((60, 195), "Total Landholding Acreage: 3.50 Acres (Min Required: 2.0 Acres)", fontsize=12, color=(0.08, 0.4, 0.2))
            page.insert_text((60, 215), "Primary Crops: Sugarcane, Wheat & Mustard | Scale of Finance: Rs. 50,000 / Acre", fontsize=10, color=(0.1, 0.1, 0.1))
            doc.save(str(paths["land_records"]))
            doc.close()

        # 13. Form 16 / Tax Return
        if not paths["tax_doc"].exists():
            doc = fitz.open()
            page = doc.new_page(width=595, height=842)
            page.draw_rect(fitz.Rect(40, 40, 555, 90), fill=(0.15, 0.2, 0.35))
            page.insert_text((60, 70), "FORM NO. 16 — CERTIFICATE UNDER SECTION 203 OF IT ACT", fontsize=13, color=(1, 1, 1))
            page.insert_text((60, 85), "CENTRAL BOARD OF DIRECT TAXES | TDS FROM SALARIES (FY 2024-25)", fontsize=8.5, color=(0.85, 0.9, 0.95))
            page.insert_text((60, 135), "Employee: Rajesh Sharma | PAN: ABCPS1234F", fontsize=11, color=(0, 0, 0))
            page.insert_text((60, 155), "Employer: Apex Tech Solutions Pvt Ltd | TAN: DELA09281F", fontsize=10.5, color=(0.2, 0.2, 0.2))
            page.insert_text((60, 180), "Gross Salary Reported: Rs. 4,15,200.00", fontsize=11, color=(0.08, 0.22, 0.38))
            page.insert_text((60, 200), "Total Tax Deducted at Source (TDS): Rs. 0.00 (Exempt under Sec 87A)", fontsize=10, color=(0.2, 0.2, 0.2))
            doc.save(str(paths["tax_doc"]))
            doc.close()

        return paths
