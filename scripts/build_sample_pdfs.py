"""Generate SAMPLE BIS-style PDF documents for development and testing.

These are NOT official BIS documents. They are synthetic documents created for
demonstrating the RAG pipeline. Each PDF is labeled as SAMPLE DATA.
"""
from __future__ import annotations

import sys
from pathlib import Path

import fitz  # PyMuPDF

SAMPLE_DIR = Path(__file__).resolve().parent.parent / "data" / "sample_documents"

DOCS: list[dict] = [
    {
        "file": "sample_IS_1234_cement_spec.pdf",
        "name": "IS 1234:2020 Portland Cement — Specification (SAMPLE)",
        "standard_number": "IS 1234:2020",
        "title": "Ordinary Portland Cement — Specification (Sample)",
        "year": 2020,
        "doc_type": "standard",
        "category": "cement",
        "source_url": "",
        "pages": [
            ("1. SCOPE",
             "This standard prescribes the requirements and the related methods of sampling "
             "and testing for ordinary Portland cement used in general concrete construction. "
             "This standard applies to 33, 43 and 53 grade ordinary Portland cement."),
            ("2. REFERENCES",
             "The following standards are referred to in this standard: IS 4031 for methods of "
             "physical tests on hydraulic cement, and IS 4032 for methods of chemical analysis "
             "of hydraulic cement."),
            ("3. MATERIALS AND MANUFACTURE",
             "Cement shall be manufactured by intimately mixing together calcareous and argillaceous "
             "materials, burning them at clinkering temperature, grinding the resultant clinker, and "
             "adding a small percentage of gypsum at the grinding stage."),
            ("4. REQUIREMENTS",
             "4.1 Fineness — The residue on 90-micron sieve shall not exceed 10 percent when tested "
             "per IS 4031 Part 1.\n\n"
             "4.2 Setting time — The initial setting time shall not be less than 30 minutes and the "
             "final setting time shall not exceed 600 minutes when tested per IS 4031 Part 4.\n\n"
             "4.3 Soundness — The expansion of cement paste shall not exceed 10 mm when tested by "
             "Le Chatelier method per IS 4031 Part 3.\n\n"
             "4.4 Compressive strength — The compressive strength of 53 grade cement shall be not "
             "less than 53 MPa at 28 days when tested per IS 4031 Part 6."),
            ("5. CERTIFICATION AND MARKING",
             "Every bag of cement shall be legibly and indelibly marked with the manufacturer's name, "
             "the grade of cement, the week and year of manufacture, and the BIS certification mark "
             "(ISI mark) under a valid BIS licence per the BIS Act 2016. Cement conforming to this "
             "standard may be marked with the Standard Mark under a BIS licence; the manufacturer "
             "must obtain a licence from BIS before applying the mark.\n\n"
             "5.1 Licence application — The manufacturer shall apply to BIS in the prescribed form "
             "with details of manufacturing process, quality control setup and test facilities."),
            ("6. SAMPLING AND TESTS",
             "The purchaser may sample cement per IS 3535. All tests shall be carried out in "
             "accordance with the methods given in IS 4031."),
        ],
    },
    {
        "file": "sample_IS_3025_helmet_spec.pdf",
        "name": "IS 2925:2020 Industrial Safety Helmets (SAMPLE)",
        "standard_number": "IS 2925:2020",
        "title": "Industrial Safety Helmets — Specification (Sample)",
        "year": 2020,
        "doc_type": "standard",
        "category": "safety",
        "source_url": "",
        "pages": [
            ("1. SCOPE",
             "This standard covers requirements for industrial safety helmets for protection of "
             "workers against impact from falling objects in industrial environments."),
            ("2. REQUIREMENTS",
             "2.1 Shock absorption — When tested per the method given in this standard, the "
             "transmitted force to the headform shall not exceed 5 kN.\n\n"
             "2.2 Penetration resistance — The striker shall not contact the headform when a "
             "3 kg conical striker is dropped from 1 m height.\n\n"
             "2.3 Chin strap — The helmet shall be provided with a chin strap adjustable to fit "
             "the wearer and release force between 150 N and 250 N."),
            ("3. CERTIFICATION AND MARKING",
             "Each helmet shall be permanently and legibly marked with manufacturer name, month and "
             "year of manufacture, size, and the BIS ISI certification mark under a valid BIS "
             "licence. Helmets may be marked with the Standard Mark only after the manufacturer "
             "obtains a BIS licence per the BIS Act 2016 and the BIS Conformity Assessment "
             "Regulations 2018.\n\n"
             "3.1 Factory inspection — BIS shall inspect the factory before granting a licence to "
             "verify testing facilities and quality control."),
            ("4. TEST METHODS",
             "Tests shall be carried out in accordance with the methods prescribed in this standard "
             "at ambient temperature 27 ± 2 degrees Celsius."),
        ],
    },
    {
        "file": "sample_bis_consumer_guide.pdf",
        "name": "BIS Consumer Guide — Understanding the ISI Mark (SAMPLE)",
        "standard_number": "CONSUMER-GUIDE",
        "title": "Understanding the ISI Mark — A Consumer Guide (Sample)",
        "year": 2024,
        "doc_type": "guide",
        "category": "consumer",
        "source_url": "",
        "pages": [
            ("WHAT IS THE ISI MARK",
             "The ISI mark is a certification mark issued by the Bureau of Indian Standards for "
             "products that conform to the relevant Indian Standard. The mark certifies that the "
             "product has been tested and found to conform to the requirements of the applicable "
             "Indian Standard."),
            ("HOW TO CHECK A PRODUCT IS BIS CERTIFIED",
             "1. Look for the ISI mark on the product or its packaging.\n"
             "2. Find the licence number (format CM/L-xxxxxxxxxx) printed below the mark.\n"
             "3. Verify the licence number on the BIS website under 'Product Certification — "
             "Verify Licence'.\n"
             "4. Check that the product category matches the licence scope.\n\n"
             "If a product bears the ISI mark without a valid licence number, consumers may lodge "
             "a complaint with BIS through the BIS Care mobile application or the BIS consumer "
             "complaints portal."),
            ("CONSUMER COMPLAINTS",
             "Consumers can file complaints about misuse of the ISI mark or substandard certified "
             "products through the BIS Care app, the BIS website complaint form, or by contacting "
             "the nearest BIS branch office. BIS may take action under the BIS Act 2016 including "
             "penalties for misuse of the Standard Mark."),
            ("MANDATORY CERTIFICATION SCHEMES",
             "Under the BIS Act 2016, certain products require mandatory BIS certification before "
             "sale in India. Examples include cement, steel, electrical appliances, LPG cylinders, "
             "food colours and automotive helmets. The list of goods subject to mandatory "
             "certification is issued by the Central Government through Quality Control Orders."),
        ],
    },
    {
        "file": "sample_bis_certification_process.pdf",
        "name": "BIS Product Certification Process for Manufacturers (SAMPLE)",
        "standard_number": "BIS-PROCESS",
        "title": "BIS Product Certification — Process Guide for Manufacturers (Sample)",
        "year": 2024,
        "doc_type": "guide",
        "category": "certification",
        "source_url": "",
        "pages": [
            ("OVERVIEW OF THE CERTIFICATION PROCESS",
             "The Bureau of Indian Standards operates product certification under the BIS Act 2016 "
             "and the BIS Conformity Assessment Regulations 2018. Domestic manufacturers follow the "
             "Normal Procedure (Scheme I) or the Simplified Procedure for small entities. Foreign "
             "manufacturers follow the Foreign Manufacturers Certification Scheme (FMCS)."),
            ("STEP-BY-STEP APPLICATION (NORMAL PROCEDURE)",
             "1. Submit application on the BIS portal with fees and factory details.\n"
             "2. BIS officer audits the factory: process, quality control and test facilities.\n"
             "3. Samples are drawn and tested in BIS-recognised laboratories.\n"
             "4. If the factory audit and test results conform, BIS grants a licence.\n"
             "5. The licence holder may apply the ISI mark on conforming product.\n\n"
             "The Simplified Procedure grants provisional licence based on self-test reports with "
             "independent testing, followed by factory audit within 90 days."),
            ("DOCUMENTS REQUIRED FROM THE MANUFACTURER",
             "Typical documents: factory registration proof, manufacturing process flow chart, list "
             "of machinery and test equipment, calibration certificates of test equipment, quality "
             "control plan, layout plan of the factory, trademark registration, and test reports "
             "from BIS-recognised labs. Exact requirements depend on the product's Indian Standard."),
            ("SCHEME OF TESTING AND INSPECTION",
             "The Scheme of Testing and Inspection (STI) defines the frequency of tests, sampling "
             "plan and records the licensee must maintain. The licensee must test each lot per the "
             "STI, maintain records for at least three years, and permit BIS inspection and "
             "surveillance visits."),
            ("FEES AND VALIDITY",
             "Application and licence fees are prescribed in the BIS Conformity Assessment "
             "Regulations 2018; consult the official BIS portal for the current fee schedule. A "
             "licence is normally valid for two years and renewable for further periods subject to "
             "continued conformity and surveillance."),
            ("MARKING REQUIREMENTS",
             "Every certified product must carry the ISI mark together with the licence number "
             "(CM/L format), the Indian Standard number on a single line below the mark, and any "
             "product-specific markings required by the applicable Indian Standard."),
        ],
    },
]


def build_pdf(path: Path, title: str, pages: list[tuple[str, str]], sample_notice: str) -> None:
    doc = fitz.open()
    for page_title, body in pages:
        page = doc.new_page()  # A4
        rect = page.rect
        margin = 57
        y = margin

        page.insert_text(
            (margin, y),
            "SAMPLE DATA — NOT AN OFFICIAL BIS DOCUMENT",
            fontsize=9, fontname="helv", color=(0.7, 0.1, 0.1),
        )
        y += 22
        page.insert_text((margin, y), title, fontsize=15, fontname="hebo")
        y += 18
        page.insert_text((margin, y), page_title, fontsize=12, fontname="hebo",
                         color=(0.1, 0.2, 0.5))
        y += 14

        # simple text layout wrapping
        words = body.split()
        line = ""
        for w in words:
            trial = (line + " " + w).strip()
            if fitz.get_text_length(trial, fontname="helv", fontsize=10.5) > rect.width - 2 * margin:
                page.insert_text((margin, y), line, fontsize=10.5, fontname="helv")
                y += 15
                line = w
                if y > rect.height - margin:
                    y = margin
            else:
                line = trial
        if line:
            page.insert_text((margin, y), line, fontsize=10.5, fontname="helv")

        page.insert_text(
            (margin, rect.height - 30),
            f"{title} — page {doc.page_count}",
            fontsize=8, fontname="helv", color=(0.4, 0.4, 0.4),
        )
    doc.save(str(path))
    doc.close()


def main() -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    for spec in DOCS:
        path = SAMPLE_DIR / spec["file"]
        build_pdf(path, spec["title"], spec["pages"], "SAMPLE DATA")
        print(f"built {path.name}")


if __name__ == "__main__":
    sys.exit(main())
