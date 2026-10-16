import os
import re
from pathlib import Path
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from config import Config

# Safe import for PyMuPDF
try:
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

# Configure Tesseract path if available
if hasattr(Config, 'TESSERACT_CMD') and os.path.exists(Config.TESSERACT_CMD):
    pytesseract.pytesseract.tesseract_cmd = Config.TESSERACT_CMD


class DocumentProcessor:
    """
    Automated document ingestion, PDF extraction via PyMuPDF,
    scanned image OCR via Tesseract, structured field extraction,
    and cross-document discrepancy checking.
    """

    @staticmethod
    def extract_raw_text(file_path):
        """
        Extract raw text from PDF or Image file.
        Returns (text, method, success, error_message).
        """
        ext = Path(file_path).suffix.lower()
        if ext == '.pdf':
            return DocumentProcessor._extract_pdf_text(file_path)
        elif ext in ('.png', '.jpg', '.jpeg'):
            return DocumentProcessor._extract_image_text(file_path)
        else:
            return "", "unsupported", False, f"Unsupported file extension: {ext}"

    @staticmethod
    def _extract_pdf_text(file_path):
        """Extract text from PDF using PyMuPDF"""
        if not fitz:
            return "", "pymupdf_missing", False, "PyMuPDF is not installed."
        
        try:
            doc = fitz.open(file_path)
            extracted_pages = []
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_text = page.get_text("text")
                extracted_pages.append(page_text)
            
            full_text = "\n".join(extracted_pages).strip()
            
            # If PDF contains no selectable text (scanned PDF), try extracting page images for OCR
            if len(full_text) < 30 and len(doc) > 0:
                ocr_texts = []
                for page_num in range(min(len(doc), 3)): # Up to first 3 pages
                    page = doc[page_num]
                    pix = page.get_pixmap(dpi=150)
                    temp_img_path = f"{file_path}_temp_p{page_num}.png"
                    pix.save(temp_img_path)
                    ocr_t, _, _, _ = DocumentProcessor._extract_image_text(temp_img_path)
                    try:
                        os.remove(temp_img_path)
                    except Exception:
                        pass
                    if ocr_t:
                        ocr_texts.append(ocr_t)
                if ocr_texts:
                    return "\n".join(ocr_texts), "pymupdf_raster_ocr", True, None

            return full_text, "pymupdf", True, None
        except Exception as e:
            return "", "pymupdf_error", False, f"PDF extraction failed: {str(e)}"

    @staticmethod
    def _extract_image_text(file_path):
        """Extract text from scanned image using Tesseract OCR with preprocessing"""
        try:
            img = Image.open(file_path)
            # Image preprocessing for better OCR: convert to grayscale, increase contrast
            gray = img.convert('L')
            enhancer = ImageEnhance.Contrast(gray)
            enhanced = enhancer.enhance(1.5)
            
            # Check if tesseract binary is accessible
            tess_ok = False
            try:
                # Test run
                text = pytesseract.image_to_string(enhanced, config='--psm 6')
                tess_ok = True
                return text.strip(), "tesseract_ocr", True, None
            except Exception as ocr_err:
                # If tesseract binary not found on Windows PATH, fallback gracefully
                pass
            
            # Graceful fallback: inspect image properties or provide safe fallback
            fallback_msg = (
                f"[Image scanned: {img.size[0]}x{img.size[1]} {img.format}]. "
                "Tesseract executable not detected on system PATH. "
                "Image uploaded successfully; requires bank officer manual visual verification."
            )
            return fallback_msg, "ocr_binary_unavailable", True, None
        except Exception as e:
            return "", "ocr_error", False, f"Image OCR extraction error: {str(e)}"

    @staticmethod
    def extract_structured_fields(raw_text, document_type='salary_slip'):
        """
        Extract applicant name, company name, salary amount, salary month,
        deductions, bank salary credits, and document dates using intelligent regex patterns.
        """
        data = {
            "applicant_name": None,
            "company_name": None,
            "salary_amount": None,
            "salary_month": None,
            "deductions": None,
            "bank_credits": None,
            "document_date": None,
            "confidence_score": 0.0
        }

        if not raw_text:
            return data

        lines = [line.strip() for line in raw_text.split('\n') if line.strip()]

        # 1. Applicant Name Extraction
        name_patterns = [
            r'(?:Purchaser|Buyer|Owner|Allottee|Transferee|Employee\s*Name|Emp\s*Name|Name\s*of\s*Employee|Account\s*Holder|Customer\s*Name|Name)\s*[:\-]?\s*([A-Za-z\s\.\,\'\-]{3,40})',
            r'(?:Mr\.|Ms\.|Mrs\.|Dr\.)\s+([A-Za-z\s]{3,35})'
        ]
        for pat in name_patterns:
            match = re.search(pat, raw_text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                # Clean candidate
                candidate = re.sub(r'[\r\n].*', '', candidate).strip()
                candidate = re.split(r'[,;]|(?:\s+S/o|\s+D/o|\s+W/o)', candidate)[0].strip()
                if len(candidate) > 2 and not any(kw in candidate.lower() for kw in ['date', 'bank', 'slip', 'salary', 'number', 'address']):
                    data["applicant_name"] = candidate
                    break

        # 2. Company / Employer / Vendor Name
        company_patterns = [
            r'(?:Company|Employer|Organization|Firm|Establishment|Vendor|Builder|Developer)\s*[:\-]\s*([A-Za-z0-9\.\,\&\-\' ]{3,60})',
            r'([A-Za-z0-9\s\.\,\&]{3,50}\s+(?:Pvt\s*Ltd|Private\s*Limited|Limited|Ltd|Corp|Corporation|LLC|Technologies|Solutions|Services|Bank|Developers))'
        ]
        for pat in company_patterns:
            match = re.search(pat, raw_text, re.IGNORECASE)
            if match:
                candidate = match.group(1).strip()
                candidate = re.sub(r'^(?:Company|Employer|Vendor|Builder|Developer)\s*[:\-]\s*', '', candidate, flags=re.IGNORECASE).strip()
                candidate = re.split(r'[,;]|(?:\s+Rep\s+by)', candidate)[0].strip()
                if len(candidate) > 2:
                    data["company_name"] = candidate
                    break

        # 3. Monthly Salary (Net / Gross) or Property Consideration
        salary_patterns = [
            r'(?:Net\s*Pay(?:able)?|Net\s*Salary|Take\s*Home\s*Pay|Net\s*Amount)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d\,]+(?:\.\d{2})?)',
            r'(?:Total\s*Earnings|Gross\s*(?:Pay|Salary|Earnings))\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d\,]+(?:\.\d{2})?)',
            r'(?:Salary\s*Credited|Amount\s*Credited|Credit\s*Amount)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d\,]+(?:\.\d{2})?)',
            r'(?:Consideration\s*(?:Amount|Value)?|Property\s*Value|Total\s*Sale\s*(?:Price|Consideration)|Agreement\s*Value)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d\,]+(?:\.\d{2})?)'
        ]
        for pat in salary_patterns:
            match = re.search(pat, raw_text, re.IGNORECASE)
            if match:
                amt_str = match.group(1).replace(',', '').strip()
                try:
                    val = float(amt_str)
                    max_allowed = 1000000000 if document_type in ('property_docs', 'property_documents') else 5000000
                    if 5000 <= val <= max_allowed:
                        data["salary_amount"] = val
                        break
                except ValueError:
                    pass

        # 4. Salary Deductions
        deduction_patterns = [
            r'(?:Total\s*Deductions|Total\s*Deduction|Deductions)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d\,]+(?:\.\d{2})?)',
            r'(?:PF|Provident\s*Fund|TDS|Income\s*Tax)\s*[:\-]?\s*(?:Rs\.?|INR|₹)?\s*([\d\,]+(?:\.\d{2})?)'
        ]
        for pat in deduction_patterns:
            match = re.search(pat, raw_text, re.IGNORECASE)
            if match:
                amt_str = match.group(1).replace(',', '').strip()
                try:
                    val = float(amt_str)
                    if 0 <= val <= 1000000:
                        data["deductions"] = val
                        break
                except ValueError:
                    pass

        # 5. Salary Month / Pay Period
        month_patterns = [
            r'(?:Pay\s*Period|Month|Salary\s*Month|Pay\s*Slip\s*for)\s*[:\-]?\s*([A-Za-z]{3,9}\s*[\,\-]?\s*\d{4})',
            r'((?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})',
            r'((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s\-\/]+\d{2,4})'
        ]
        for pat in month_patterns:
            match = re.search(pat, raw_text, re.IGNORECASE)
            if match:
                data["salary_month"] = match.group(1).strip()
                break

        # 6. Bank Salary Credits
        credit_patterns = [
            r'(?:SALARY\s*CREDIT|SALARY\s*NEFT|ACH\s*SALARY|BY\s*SALARY|CMS\s*SALARY)[\s\:\-]*([\d\,]+(?:\.\d{2})?)',
            r'([A-Za-z0-9\s\/\*\-]+SALARY[A-Za-z0-9\s\/\*\-]*)\s+([\d\,]+\.\d{2})\s+Cr'
        ]
        for pat in credit_patterns:
            match = re.search(pat, raw_text, re.IGNORECASE)
            if match:
                # Group could be 1 or 2
                for g in range(1, match.lastindex + 1 if match.lastindex else 1):
                    val_str = match.group(g).replace(',', '').strip()
                    try:
                        val = float(val_str)
                        if 5000 <= val <= 5000000:
                            data["bank_credits"] = val
                            break
                    except ValueError:
                        continue
                if data["bank_credits"]:
                    break

        # 7. Document Dates
        date_patterns = [
            r'(?:Date(?:\s*of\s*Registration)?|Generated\s*on|Statement\s*Date|Dated|Registered\s*on)\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})',
            r'(\d{1,2}[\/\-\.](?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\/\-\.]\d{2,4})',
            r'(\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4})'
        ]
        for pat in date_patterns:
            match = re.search(pat, raw_text, re.IGNORECASE)
            if match:
                data["document_date"] = match.group(1).strip()
                break

        # Calculate Confidence Score (0 to 100)
        found_fields = sum(1 for k, v in data.items() if k != "confidence_score" and v is not None)
        max_fields = 7
        data["confidence_score"] = round((found_fields / max_fields) * 100.0, 1)

        return data

    @staticmethod
    def cross_check_application(application, extracted_data_list):
        """
        Cross-check declared applicant details with extracted documents data.
        Returns a dictionary with:
        - has_discrepancy: bool
        - discrepancies: list of discrepancy dicts (field, declared, extracted, difference, note)
        - verified_salary: float or None
        - verification_summary: string
        """
        discrepancies = []
        verified_salaries = []
        company_matches = []
        name_matches = []

        declared_salary = float(application.declared_monthly_salary or 0)
        declared_company = (application.company_name or "").strip().lower()
        declared_name = (application.applicant.full_name or "").strip().lower()

        for ext in extracted_data_list:
            if not ext:
                continue
            
            doc_type = getattr(ext.source_document, 'document_type', None) if hasattr(ext, 'source_document') else None
            is_property_doc = (doc_type in ('property_docs', 'property_documents'))

            # Check salary discrepancy (for income documents, not property deeds)
            if ext.salary_amount_extracted and not is_property_doc:
                extracted_sal = float(ext.salary_amount_extracted)
                verified_salaries.append(extracted_sal)
                diff = extracted_sal - declared_salary
                pct_diff = round((diff / declared_salary) * 100.0, 2) if declared_salary > 0 else 0
                
                # If difference is more than 5% or Rs. 1000
                if abs(diff) > max(1000, declared_salary * 0.05):
                    discrepancies.append({
                        "field": "Monthly Salary",
                        "declared": f"₹{declared_salary:,.2f}",
                        "extracted": f"₹{extracted_sal:,.2f}",
                        "difference": f"{'+' if diff > 0 else ''}₹{diff:,.2f} ({'+' if pct_diff > 0 else ''}{pct_diff}%)",
                        "severity": "high" if abs(diff) > 5000 else "medium",
                        "explanation": (
                            f"The uploaded salary document shows ₹{extracted_sal:,.2f}, whereas "
                            f"the declared monthly salary is ₹{declared_salary:,.2f}. "
                            f"Difference of ₹{abs(diff):,.2f} requires verification by a bank officer."
                        ),
                        "source_doc_id": ext.document_id
                    })

            # Check company name match (for employer docs, not property developer/vendors)
            if ext.company_name_extracted and not is_property_doc:
                doc_comp = ext.company_name_extracted.strip().lower()
                # Check substring match or word overlap
                declared_words = set(re.findall(r'\w+', declared_company))
                doc_words = set(re.findall(r'\w+', doc_comp))
                overlap = declared_words.intersection(doc_words)
                
                if not overlap and len(declared_company) > 3 and len(doc_comp) > 3:
                    discrepancies.append({
                        "field": "Employer / Company Name",
                        "declared": application.company_name,
                        "extracted": ext.company_name_extracted,
                        "difference": "Mismatch",
                        "severity": "medium",
                        "explanation": (
                            f"Declared employer '{application.company_name}' does not clearly match "
                            f"'{ext.company_name_extracted}' found on the uploaded document."
                        ),
                        "source_doc_id": ext.document_id
                    })
                else:
                    company_matches.append(True)

            # Check applicant name match
            if ext.applicant_name_extracted:
                doc_name = ext.applicant_name_extracted.strip().lower()
                declared_name_parts = set(re.findall(r'\w+', declared_name))
                doc_name_parts = set(re.findall(r'\w+', doc_name))
                overlap = declared_name_parts.intersection(doc_name_parts)
                
                if not overlap and len(declared_name) > 3 and len(doc_name) > 3:
                    discrepancies.append({
                        "field": "Applicant Name",
                        "declared": application.applicant.full_name,
                        "extracted": ext.applicant_name_extracted,
                        "difference": "Name mismatch",
                        "severity": "high",
                        "explanation": (
                            f"Applicant name '{application.applicant.full_name}' differs from "
                            f"'{ext.applicant_name_extracted}' extracted from the document."
                        ),
                        "source_doc_id": ext.document_id
                    })
                else:
                    name_matches.append(True)

        avg_verified_sal = (
            sum(verified_salaries) / len(verified_salaries)
            if verified_salaries else None
        )

        return {
            "has_discrepancy": len(discrepancies) > 0,
            "discrepancies": discrepancies,
            "verified_salary": avg_verified_sal,
            "salary_sample_count": len(verified_salaries),
            "disclaimer": (
                "Automated text extraction is an analytical aid and does not constitute conclusive proof of document authenticity. "
                "Any discrepancy or ambiguous field must be formally inspected and verified by an authorized bank officer."
            )
        }
