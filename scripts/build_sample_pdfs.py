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
        "category": "everyday_products",
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
        "category": "everyday_products",
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
        "category": "general_bis",
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
        "category": "industry",
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
    {
        "file": "sample_food_packaged_drinking_water.pdf",
        "name": "Food Safety Guide — Packaged Drinking Water & BIS (SAMPLE)",
        "standard_number": "FOOD-WATER-GUIDE",
        "title": "Packaged Drinking Water and BIS Certification — Consumer Guide (Sample)",
        "year": 2024,
        "doc_type": "guide",
        "category": "food",
        "source_url": "",
        "pages": [
            ("PACKAGED DRINKING WATER AND BIS",
             "Packaged drinking water is one of the products for which BIS certification has been "
             "mandatory in India under a Quality Control Order. The applicable Indian Standard for "
             "packaged drinking water (other than packaged natural mineral water) is IS 14543. "
             "Packaged natural mineral water is covered by IS 13428. Manufacturers of packaged "
             "drinking water must obtain a BIS licence and bear the ISI mark before selling in "
             "India. Verify the latest requirement and scope on the official BIS source."),
            ("WHAT IS IN THE STANDARD",
             "The standard lays down requirements for hygiene of the source water, treatment such "
             "as filtration, reverse osmosis or disinfection as applicable, microbiological limits, "
             "chemical limits for parameters such as total dissolved solids and pesticide residues, "
             "packaging in food-grade containers, and testing per the prescribed methods. The "
             "manufacturer must operate a Scheme of Testing and Inspection with regular testing of "
             "each lot."),
            ("WHAT THE CONSUMER SHOULD CHECK",
             "1. The ISI mark on the bottle or pack together with the licence number in CM/L "
             "format.\n"
             "2. Verify the licence on the BIS website or the BIS Care mobile application.\n"
             "3. The manufacturing or batch date and the best before date.\n"
             "4. An intact, tamper-evident seal; the bottle stored away from direct sunlight.\n"
             "5. The declared type: packaged drinking water or natural mineral water; these are "
             "different standards.\n\n"
             "If a packaged water bottle does not carry the ISI mark and licence number, do not "
             "buy it and report it through the BIS Care app."),
            ("FOOD PRODUCTS AND OTHER AUTHORITIES",
             "Most food products in India are regulated by the Food Safety and Standards Authority "
             "of India (FSSAI) under the Food Safety and Standards Act. BIS certification applies "
             "to specific notified food products such as packaged drinking water, and BIS standards "
             "also exist for many food-contact materials and some processed foods. For a given "
             "food product, check the FSSAI licence number on the pack first, and the ISI mark "
             "where BIS certification applies. Certification for most foods other than notified "
             "items is voluntary."),
        ],
    },
    {
        "file": "sample_hallmarking_huid_guide.pdf",
        "name": "Gold & Silver Hallmarking — HUID Consumer Guide (SAMPLE)",
        "standard_number": "HALLMARK-GUIDE",
        "title": "Understanding BIS Hallmarking, HUID and Fineness — Consumer Guide (Sample)",
        "year": 2024,
        "doc_type": "guide",
        "category": "hallmarking",
        "source_url": "",
        "pages": [
            ("WHAT IS HALLMARKING",
             "Hallmarking is the accurate determination and official recording of the proportionate "
             "content of precious metal in jewellery and artefacts. In India the Bureau of Indian "
             "Standards operates the hallmarking scheme: jewellery conforming to the relevant "
             "Indian Standard is assayed by a BIS-recognised Assaying and Hallmarking Centre and "
             "marked with the BIS hallmark."),
            ("WHAT IS HUID",
             "HUID stands for Hallmark Unique Identification. It is a six-character alphanumeric "
             "code laser-marked on each hallmarked jewellery item. Every hallmarked piece gets a "
             "unique HUID, which allows the consumer to trace that specific item: who the jeweller "
             "is, which Assaying and Hallmarking Centre hallmarked it, the fineness and when it was "
             "hallmarked. HUID-based hallmarking has been in force since July 2021."),
            ("PARTS OF THE BIS HALLMARK",
             "A complete BIS hallmark on gold jewellery contains five marks:\n"
             "1. The BIS mark (triangle).\n"
             "2. The purity or fineness grade, for example 916 for 22 karat, 750 for 18 karat, 585 "
             "for 14 karat and 999 for 24 karat gold.\n"
             "3. The mark of the BIS-recognised Assaying and Hallmarking Centre.\n"
             "4. The identification mark of the jeweller.\n"
             "5. The six-character HUID code.\n\n"
             "If any of these is missing, ask the jeweller for an explanation before buying."),
            ("HOW TO VERIFY HALLMARK INFORMATION",
             "Consumers can verify a HUID using the official BIS Care mobile application or the "
             "BIS website. Enter the six-character HUID to see the registered details of the item. "
             "The BIS hallmarking scheme applies to registered jewellers selling gold jewellery; "
             "hallmarking of gold jewellery in mandatory scope has been implemented in phases from "
             "June 2021. Silver hallmarking is voluntary. Always verify the current scope and "
             "rules on the official BIS source."),
            ("IMPORTANT LIMITATIONS",
             "The presence of a hallmark indicates that the item was assayed at the time of "
             "hallmarking. A hallmark is a mark of conformity, not a guarantee of a specific "
             "item's current condition. BIS Buddy cannot judge whether any particular jewellery "
             "item is genuine; it can only explain which markings exist and how to verify them "
             "through official channels. For a definitive assessment, consult a BIS-recognised "
             "Assaying and Hallmarking Centre."),
        ],
    },
    {
        "file": "sample_electronics_electrical_guide.pdf",
        "name": "Electronics & Electrical Products — BIS Marks Guide (SAMPLE)",
        "standard_number": "ELEC-GUIDE",
        "title": "BIS Certification Marks on Electronics and Electrical Products — Consumer Guide (Sample)",
        "year": 2024,
        "doc_type": "guide",
        "category": "electronics_electrical",
        "source_url": "",
        "pages": [
            ("TWO SCHEMES: ISI MARK AND CRS REGISTRATION",
             "Electrical and electronic products reach the consumer under two BIS schemes. Under "
             "the Product Certification (ISI mark) scheme, a BIS officer audits the factory, "
             "samples are tested independently and the factory continues to be surveilled; products "
             "like cables, wires, plugs, sockets and switches carry the ISI mark with a CM/L "
             "licence number. Under the Registration Scheme (CRS), the manufacturer tests the "
             "product in a BIS-recognised laboratory, registers the product with BIS and declares "
             "conformity; electronics such as chargers, IT equipment, LED lamps and batteries carry "
             "a BIS registration mark with a registration number beginning with R-."),
            ("COMMON ELECTRICAL PRODUCTS AND THEIR STANDARDS",
             "PVC insulated cables and wires for household wiring are covered by IS 694. Plugs and "
             "socket-outlets up to 250 V are covered by IS 1293. Domestic switches are covered by "
             "IS 3854. Safety of household and similar electrical appliances follows IS 302. "
             "Safety of audio/video, information and communication technology equipment including "
             "chargers follows IS 62368-1. Self-ballasted LED lamps for general lighting follow "
             "IS 16102. Verify the exact standard applicable to a product on the official BIS "
             "source."),
            ("WHAT THE CONSUMER SHOULD CHECK BEFORE BUYING",
             "1. The ISI mark or the BIS CRS registration mark, as applicable to the product.\n"
             "2. For ISI products, the CM/L licence number printed below the mark.\n"
             "3. For CRS products, the R- registration number on the product or its label.\n"
             "4. The rated voltage, current and power markings on the product.\n"
             "5. That the mark is on the product itself, not only on the packaging.\n"
             "6. Verify the licence or registration on the BIS website or BIS Care app.\n\n"
             "Avoid electrical products with no BIS marking: unmarked wires, plugs and chargers "
             "are a common cause of electrical accidents."),
            ("MANDATORY VERSUS VOLUNTARY",
             "Which electrical products require mandatory certification changes over time as the "
             "government notifies Quality Control Orders. Many household electrical items such as "
             "cables, plugs, sockets and switches have long been in mandatory scope, while certain "
             "appliances remain voluntary. Always check the current QCO list on the official BIS "
             "source before making a purchase decision."),
        ],
    },
    {
        "file": "sample_everyday_products_guide.pdf",
        "name": "Everyday Products — ISI Mark Buying Guide (SAMPLE)",
        "standard_number": "EVERYDAY-GUIDE",
        "title": "ISI Mark Buying Guide for Everyday Household Products (Sample)",
        "year": 2024,
        "doc_type": "guide",
        "category": "everyday_products",
        "source_url": "",
        "pages": [
            ("PRESSURE COOKERS",
             "Pressure cookers are covered by IS 2347 and BIS certification for domestic pressure "
             "cookers has been mandatory for decades. A domestic pressure cooker sold in India "
             "must carry the ISI mark with the licence number. Before buying, check the ISI mark "
             "is stamped on the cooker body or lid, check the gasket and safety plug, and verify "
             "the licence number on the BIS website. Verify the latest requirement on the official "
             "BIS source."),
            ("TOYS",
             "Toys are covered by the Toys Quality Control Order under which toys sold in India "
             "must conform to the relevant Indian Standard safety requirements, such as IS 9873 "
             "for safety aspects related to mechanical and physical properties, and carry the ISI "
             "mark. Check the age grading on the pack and avoid toys with small detachable parts "
             "for children under three."),
            ("LPG CYLINDERS AND HELMETS",
             "LPG cylinders are covered by IS 3196; check the due test date ring on the cylinder "
             "neck and never accept an overdue cylinder. Industrial safety helmets follow IS 2925 "
             "and protective helmets for two-wheeler riders follow IS 4151; look for the ISI mark "
             "on the shell and check the harness and shell condition."),
            ("CEMENT AND STEEL",
             "Ordinary Portland cement is covered by IS 269 for 33 grade, IS 8112 for 43 grade and "
             "IS 12269 for 53 grade; Portland Pozzolana cement is covered by IS 1489. High strength "
             "deformed steel bars for concrete reinforcement are covered by IS 1786. Check the ISI "
             "mark on every cement bag and the week of packing; buy fresh cement."),
            ("GENERAL CHECKLIST FOR ANY EVERYDAY PRODUCT",
             "1. Look for the ISI mark on the product itself, not only the box.\n"
             "2. Note the CM/L licence number below the mark and verify it on the BIS website or "
             "BIS Care app.\n"
             "3. Confirm the product category matches the licence scope.\n"
             "4. Check manufacturing date, batch and any expiry or test-due marking.\n"
             "5. Prefer sellers who provide a proper bill that names the product.\n\n"
             "If a product category is not covered in this knowledge base, ask the seller for the "
             "standard claimed and verify it on the official BIS source."),
        ],
    },
    {
        "file": "sample_general_bis_overview.pdf",
        "name": "About BIS — Indian Standards, Marks and Consumer Services (SAMPLE)",
        "standard_number": "BIS-OVERVIEW",
        "title": "About the Bureau of Indian Standards — Overview for Consumers and Industry (Sample)",
        "year": 2024,
        "doc_type": "guide",
        "category": "general_bis",
        "source_url": "",
        "pages": [
            ("WHAT IS BIS",
             "The Bureau of Indian Standards (BIS) is the National Standards Body of India, "
             "established under the BIS Act 2016. BIS formulates Indian Standards, operates "
             "certification schemes including the product certification (ISI mark) scheme, the "
             "Registration Scheme for electronics, the hallmarking scheme for gold and silver "
             "jewellery, and provides testing services through its laboratories. BIS also handles "
             "consumer grievances related to misuse of the Standard Mark and quality of certified "
             "products."),
            ("INDIAN STANDARDS AND MARKS",
             "An Indian Standard (IS) is a technical standard published by BIS prescribing "
             "requirements a product must meet. The ISI mark is the certification mark used under "
             "product certification. The CRS mark indicates registration under the mandatory "
             "registration scheme for electronics and IT goods. The BIS hallmark is the mark used "
             "on hallmarked gold and silver jewellery with the HUID code. The Hallmark Unique "
             "Identification (HUID) is a six-character alphanumeric code laser-marked on each "
             "hallmarked item, traceable through the BIS Care application."),
            ("CONSUMER SERVICES AND COMPLAINTS",
             "Consumers can check the genuineness of a licence, registration or HUID through the "
             "BIS Care mobile application or the BIS website. Complaints about misuse of the ISI "
             "mark or quality issues in certified products can be filed through the BIS Care app, "
             "the BIS website or the nearest BIS branch office. BIS operates Standards Clubs in "
             "educational institutions and conducts training and awareness programmes. The official "
             "BIS portal is the authoritative source for current rules, lists and fee schedules."),
            ("MSME AND STARTUP RELEVANCE",
             "BIS operates a Simplified Procedure for micro and small enterprises, granting a "
             "provisional licence based on self-test reports with independent verification, "
             "followed by a factory audit. MSMEs and startups preparing for certification should "
             "set up the quality control and test facilities required by the applicable Indian "
             "Standard and prepare documentation such as the process flow chart, machinery list "
             "and calibration records. Verify current facilitation measures on the official BIS "
             "portal."),
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


DOCS.extend([
    {
        "file": "sample_water_quality_guide.pdf",
        "name": "Drinking Water Quality — BIS Standards & Testing (SAMPLE)",
        "title": "Drinking Water Quality, Testing and BIS Certification — Reference Guide (Sample)",
        "year": 2024,
        "doc_type": "guide",
        "category": "water",
        "source_url": "",
        "pages": [
            ("1. SCOPE OF THIS GUIDE",
             "This guide explains, for consumers and small businesses, how Indian Standards "
             "relate to packaged drinking water, packaged natural mineral water and the "
             "testing of water quality. It is a training aid and not an official BIS document. "
             "Always verify current requirements on the official BIS source."),
            ("2. PACKAGED DRINKING WATER vs NATURAL MINERAL WATER",
             "Packaged drinking water is treated water from any source, packed for sale, and is "
             "covered by IS 14543 (Packaged Drinking Water, Other than Packaged Natural Mineral "
             "Water). Packaged natural mineral water is water from a protected underground "
             "source and is covered by IS 13428 (Packaged Natural Mineral Water). The two are "
             "different products with different standards: mineral water must not be treated to "
             "alter its essential mineral character, while packaged drinking water may be "
             "treated by filtration, reverse osmosis, disinfection and similar processes. Both "
             "products have been under mandatory BIS certification through Quality Control "
             "Orders. Verify the latest status on the official BIS source."),
            ("3. BIS CERTIFICATION AND MARKING",
             "Under the certification scheme the manufacturer operates under a BIS licence and "
             "the bottles or packs carry the ISI mark together with the licence number (CM/L), "
             "the IS standard number, batch identification and the manufacturing date. Consumers "
             "should check the ISI mark, the licence number, the type of water declared on the "
             "label (packaged drinking water or natural mineral water) and the best-before date "
             "before purchase. Product sold without the required mark should not be accepted."),
            ("4. WATER QUALITY REQUIREMENTS AND TESTING",
             "Water quality is assessed for physical, chemical and microbiological parameters. "
             "Test methods for water and wastewater are covered by the IS 3025 series (Methods "
             "of Sampling and Test, Physical and Chemical), which is used part by part for "
             "parameters such as pH, turbidity, total dissolved solids and residual chlorine. "
             "Microbiological requirements (for example absence of coliform bacteria and faecal "
             "streptococci) form part of the packaged water standards. Sampling procedures for "
             "water analysis are described in IS 3025 Part 1. Drinking-water acceptability "
             "criteria for public supplies are specified in IS 10500 (Drinking Water)."),
            ("5. LABORATORY TESTING AND CONSUMER TIPS",
             "Water testing should be done by laboratories that follow the relevant IS 3025 "
             "test methods. For packaged water, consumers cannot test at home: rely on the BIS "
             "mark, intact seals, clear labelling and purchase before the best-before date. For "
             "borewell or municipal supply, a laboratory test report should state the parameter, "
             "the result, the unit, the method used (IS 3025 part) and the acceptable limit "
             "referenced. If a packaged water product does not carry the required BIS mark, "
             "consumers may report it through the official BIS complaint channels."),
        ],
    },
    {
        "file": "sample_food_packaging_guide.pdf",
        "name": "Food Packaging & Food-Contact Materials — BIS Guide (SAMPLE)",
        "title": "Food Packaging and Food-Contact Materials — BIS Standards Guide (Sample)",
        "year": 2024,
        "doc_type": "guide",
        "category": "packaging",
        "source_url": "",
        "pages": [
            ("1. SCOPE OF THIS GUIDE",
             "This guide summarises how Indian Standards relate to packaging that touches food: "
             "plastics, glass, metal containers and paper or board, together with labelling and "
             "marking expectations. It is a training aid, not an official BIS publication."),
            ("2. PLASTIC PACKAGING AND FOOD CONTACT",
             "Materials intended for contact with foodstuffs are addressed by IS 9833 (Positive "
             "List of Plastics and Materials in Contact with Foodstuffs) and related "
             "specifications for polyethylene, polypropylene, PET and polystyrene containers. "
             "The positive-list approach means only listed polymers and additives may be used. "
             "Consumers should look for a food-grade or food-safe declaration and use the "
             "container only for the temperature range stated by the maker."),
            ("3. GLASS, METAL AND PAPER PACKAGING",
             "Glass containers for food products are covered by Indian Standards for glass "
             "tumbler and bottle requirements; metal containers for processed food (cans) have "
             "specifications covering lacquer/coating inside the can; paper and board for food "
             "packaging (cartons, paper cups) have specifications covering food-contact quality. "
             "The key consumer check is that the package is intact, clean and declared suitable "
             "for food contact by the manufacturer."),
            ("4. LABELLING AND MARKING ON PACKAGES",
             "Packaged food labels must declare the product name, ingredients in descending "
             "order, net quantity, lot or batch number, manufacturing date, best-before or use-"
             "by date, storage instructions, the FSSAI licence number and the veg or non-veg "
             "symbol as applicable. Where a product carries BIS certification, the ISI mark and "
             "licence number also appear on the package. Legal metrology rules require the "
             "maker or packer name and the net quantity declaration to be prominent."),
            ("5. WHAT CONSUMERS SHOULD CHECK",
             "Before buying packaged food: check the seal integrity, the best-before date, the "
             "batch number, the storage conditions and, where BIS certification applies, the "
             "ISI mark with the CM/L licence number. For reusable containers at home, avoid "
             "heating food in containers not declared microwave-safe, and retire scratched or "
             "discoloured plastic containers."),
        ],
    },
    {
        "file": "sample_hallmark_verification_guide.pdf",
        "name": "How to Verify a BIS Hallmark — Step-by-Step Consumer Guide (SAMPLE)",
        "title": "Verifying BIS Hallmarks on Gold and Silver Jewellery — Consumer Guide (Sample)",
        "year": 2024,
        "doc_type": "guide",
        "category": "hallmarking",
        "source_url": "",
        "pages": [
            ("1. WHY VERIFY A HALLMARK",
             "The BIS hallmark is the consumer's primary assurance that the fineness (purity) "
             "declared on a jewellery item was assayed by a BIS-recognised Assaying and "
             "Hallmarking Centre. Verification protects buyers from under-caratage and "
             "misdeclared purity. This guide is a training aid; official requirements are "
             "published by BIS."),
            ("2. THE FIVE COMPONENTS OF A BIS HALLMARK",
             "A full BIS hallmark on a jewellery item consists of: (1) the BIS standard mark "
             "(the BIS logo); (2) the fineness grade, for example 999 for 24K equivalent, 916 "
             "for 22K, 875 for 21K, 750 for 18K and 585 for 14K gold, and 925 for sterling "
             "silver; (3) the mark of the BIS-recognised Assaying and Hallmarking Centre; "
             "(4) the jeweller's or manufacturer's identification mark; and (5) the HUID - a "
             "six-digit alphanumeric unique identification code laser-marked on the item."),
            ("3. STEP-BY-STEP CONSUMER VERIFICATION",
             "Step 1: look for the BIS logo on the item. Step 2: read the fineness number and "
             "confirm it matches what the bill declares (916 means 22K). Step 3: locate the HUID "
             "six-character code. Step 4: open the official BIS Care mobile application or the "
             "BIS website verify facility, enter the HUID and confirm that the returned details "
             "(jeweller, centre, fineness) match the item. Step 5: check the purchase invoice "
             "mentions the hallmarking details. If any component is missing or the HUID does not "
             "verify, decline the purchase or demand an explanation from the jeweller."),
            ("4. HALLMARKING CENTRES AND FINENESS RULES",
             "Only BIS-recognised Assaying and Hallmarking Centres may apply the hallmark. The "
             "centres sample and assay jewellery lots to confirm the declared fineness before "
             "marking. Fineness grades in use for gold include 999, 916, 875, 750 and 585; for "
             "silver, common grades are 999, 958, 925, 900 and 800 as applicable under the "
             "relevant Indian Standards (IS 1417 for gold, IS 2112 for silver marking). The "
             "hallmarking of gold jewellery and artefacts has been made mandatory in phases "
             "through government orders; the current coverage and exemptions should be verified "
             "on the official BIS source."),
            ("5. WHAT A HALLMARK DOES NOT GUARANTEE",
             "The hallmark attests the fineness of the metal at the time of assaying. It is not "
             "a certificate for the weight of stones, the making charges, the design originality "
             "or the buy-back value offered by a jeweller. Consumers should also keep the "
             "invoice, because it links the item to the declared hallmark details. For disputes, "
             "BIS complaint channels and consumer forums are the appropriate escalation paths."),
        ],
    },
    {
        "file": "sample_bis_services_guide.pdf",
        "name": "BIS Services, Schemes and Consumer Channels — Overview (SAMPLE)",
        "title": "BIS Services, Certification Schemes and Consumer Channels — Overview (Sample)",
        "year": 2024,
        "doc_type": "guide",
        "category": "general_bis",
        "source_url": "",
        "pages": [
            ("1. WHAT THE BUREAU OF INDIAN STANDARDS DOES",
             "The Bureau of Indian Standards (BIS) is India's national standards body, set up "
             "under the BIS Act 2016. It formulates Indian Standards, operates product "
             "certification schemes (the ISI mark scheme and the Compulsory Registration Scheme), "
             "runs the hallmarking scheme for gold and silver, manages laboratory recognition "
             "and testing services, and provides consumer grievance and awareness channels."),
            ("2. PRODUCT CERTIFICATION SCHEMES",
             "The Product Certification Schemes operate through licences granted to manufacturers "
             "whose products and factory-level quality control conform to the relevant Indian "
             "Standard. Certified products carry the ISI mark with a CM/L licence number. The "
             "Compulsory Registration Scheme (CRS) covers electronics and IT goods: manufacturers "
             "register declarations of conformity and self-declare testing to the relevant "
             "standard, and registered goods carry the BIS registration mark with an R-number. "
             "Which products are mandatory is determined by Quality Control Orders and ministry "
             "notifications; the current lists must be verified on the official BIS source."),
            ("3. HALLMARKING AND TESTING SERVICES",
             "The hallmarking scheme covers gold and silver jewellery assayed and marked by "
             "BIS-recognised Assaying and Hallmarking Centres. BIS also operates and recognises "
             "laboratories for testing, and laboratory recognition services for other testing "
             "facilities. Consumers and manufacturers can use the BIS laboratories and services "
             "through the official portals."),
            ("4. STANDARDS DEVELOPMENT AND CONSUMER PARTICIPATION",
             "Indian Standards are developed through technical committees with industry, "
             "regulators, academia and consumer participation. Standards Clubs in educational "
             "institutions, Standards National Months activities and training programmes are the "
             "main awareness channels. MSMEs and startups can access hand-holding, registration "
             "fee concessions and simplified application routes announced from time to time; "
             "verify current schemes on the official BIS source."),
            ("5. CONSUMER COMPLAINTS AND VERIFICATION CHANNELS",
             "Consumers can report misuse of the ISI mark, unmarked mandatory products, defective "
             "certified products and hallmarking grievances through BIS online complaint "
             "channels, the BIS Care mobile application and the consumer grievance portal. The "
             "BIS Care app also verifies HUID codes and licence details. For escalations, "
             "consumer commissions under the Consumer Protection Act remain available."),
        ],
    },
    {
        "file": "sample_construction_materials_guide.pdf",
        "name": "Construction Materials — Cement, Steel & BIS Certification (SAMPLE)",
        "title": "BIS Certification for Construction Materials — Cement, Steel and Concrete (Sample)",
        "year": 2024,
        "doc_type": "guide",
        "category": "construction",
        "source_url": "",
        "pages": [
            ("1. SCOPE OF THIS GUIDE",
             "This guide summarises how Indian Standards apply to common construction materials: "
             "cement, reinforcing steel, structural steel and concrete practice. It is a training "
             "aid, not an official BIS publication."),
            ("2. CEMENT STANDARDS AND GRADES",
             "Ordinary Portland Cement is specified by IS 269 (33 grade), IS 8112 (43 grade) and "
             "IS 12269 (53 grade). Portland Pozzolana Cement is covered by IS 1489. Tests are "
             "per IS 4031 (physical) and IS 4032 (chemical). Cement has long been under mandatory "
             "BIS certification: bags carry the ISI mark, licence number, grade and week-year of "
             "packing. Use fresh cement; strength reduces with long storage."),
            ("3. REINFORCEMENT AND STRUCTURAL STEEL",
             "High strength deformed reinforcement bars are covered by IS 1786; mild steel bars "
             "by IS 432. Structural steel sections are covered by IS 2062 and related product "
             "specifications. TMT bars for buildings are commonly certified against IS 1786 and "
             "carry the ISI mark with grade marking (for example Fe 500 or Fe 550D). Check the "
             "grade marking on every bar and the manufacturer's test certificate for the lot."),
            ("4. CONCRETE AND SITE QUALITY CHECKS",
             "Concrete design and construction practice is covered by IS 456 (Plain and "
             "Reinforced Concrete - Code of Practice) and concrete admixtures by IS 9103. Site "
             "checks include slump testing of fresh concrete, cube testing for compressive "
             "strength at 7 and 28 days, and curing practice per the code. Materials arriving on "
             "site should match the specified Indian Standard and carry the required marks."),
            ("5. BUYER AND BUILDER CHECKLIST",
             "For cement: verify the ISI mark, licence number, grade and packing week. For steel: "
             "verify the grade embossing, manufacturer's test certificate and ISI mark where "
             "certification applies. For ready-mix concrete: ask for the mix design, the IS 456 "
             "compliance statement and cube test reports. Mandatory certification coverage "
             "changes through Quality Control Orders; verify the current list on the official "
             "BIS source before procurement."),
        ],
    },
])


def main() -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    for spec in DOCS:
        path = SAMPLE_DIR / spec["file"]
        build_pdf(path, spec["title"], spec["pages"], "SAMPLE DATA")
        print(f"built {path.name}")


if __name__ == "__main__":
    sys.exit(main())
