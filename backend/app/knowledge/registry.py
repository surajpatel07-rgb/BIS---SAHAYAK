"""Knowledge-base registry: categories, products, related questions.

Single source of truth for the six knowledge categories. Everything here is
configurable — add a category to CATEGORIES and a product to PRODUCTS and the
API, category detection, retrieval filtering and product pages pick it up.

HONESTY POLICY (important for SIH):
- standard_number values are real, well-known BIS references transcribed for a
  demo knowledge base; every product carries info_status="DEMO" and a
  verify_note telling users to confirm on official BIS sources.
- Products whose BIS standard we do NOT reliably know carry an empty
  standard_number and certification_status="info-not-available" — the UI and
  the assistant then say "Information not available in the current knowledge
  base" instead of inventing a number.
- certification_status reflects long-standing BIS practice (mandatory QCO
  items vs voluntary certification); it is NOT legal advice and the assistant
  always recommends verifying the current list on the official BIS source.
"""
from __future__ import annotations

from dataclasses import dataclass, field


# ----------------------------------------------------------------------------
# Categories
# ----------------------------------------------------------------------------
@dataclass
class KnowledgeCategory:
    key: str  # canonical key stored on documents (e.g. "food")
    label: str  # human label
    emoji: str
    description: str
    # Detection keywords (English + Hindi transliteration + Devanagari).
    keywords: tuple[str, ...] = ()
    # Follow-up question templates evaluated against the detected category.
    related_question_templates: tuple[str, ...] = ()


CATEGORIES: dict[str, KnowledgeCategory] = {c.key: c for c in [
    KnowledgeCategory(
        key="food",
        label="Food & Water",
        emoji="🍚",
        description="Packaged food, drinking water, dairy, oils, spices, cereals and food-contact materials.",
        keywords=(
            "food", "packaged food", "milk", "dairy", "ghee", "butter", "paneer", "curd",
            "edible oil", "mustard oil", "coconut oil", "refined oil", "spice", "spices",
            "turmeric", "chilli powder", "coriander powder", "cereal", "grain", "wheat",
            "rice", "atta", "flour", "maida", "suji", "rava", "besan", "pulse", "dal",
            "sugar", "jaggery", "honey", "salt", "tea", "coffee", "juice", "beverage",
            "food grade", "kitchen", "processed food", "snack", "biscuit", "bread",
            "noodle", "fssai", "additive", "food additive",
            # Hindi (translit + Devanagari)
            "khadya", "doodh", "dahi", "tel", "masala", "atta", "cheeni", "shakkar",
            "खाद्य", "पेय", "दूध", "तेल", "मसाला", "आटा", "चीनी", "खाद्य तेल",
        ),
        related_question_templates=(
            "Is BIS certification mandatory or voluntary for this product?",
            "What should I look for on the package before buying?",
            "Which authority regulates this product besides BIS?",
        ),
    ),
    KnowledgeCategory(
        key="water",
        label="Drinking Water",
        emoji="💧",
        description="Packaged drinking water, natural mineral water, water quality, sampling, microbiological and chemical testing requirements.",
        keywords=(
            "packaged drinking water", "mineral water", "natural mineral water",
            "drinking water", "water bottle", "bottled water", "water quality",
            "water testing", "water standard", "potable water", "bis water",
            "microbiological", "chemical requirements", "sampling",
            "is 14543", "is 13428", "is 10500", "is 3025",
            # Hindi
            "paani", "peene ka paani", "पानी", "पीने का पानी", "बोतलबंद पानी",
        ),
        related_question_templates=(
            "Is BIS certification mandatory for packaged drinking water?",
            "What is the difference between packaged drinking water and natural mineral water?",
            "What should I check on a water bottle label before buying?",
        ),
    ),
    KnowledgeCategory(
        key="packaging",
        label="Food & Product Packaging",
        emoji="📦",
        description="Food-contact materials and packaging: plastics, glass, metal containers, paper/board, labelling and marking requirements.",
        keywords=(
            "packaging", "food packaging", "food container", "food contact",
            "plastic packaging", "glass packaging", "metal container", "paper board",
            "carton", "pet bottle", "jute sack", "plastic film", "label", "labelling",
            "labeling", "marking requirements", "tiffin", "lunch box", "thermoware",
            # Hindi
            "पैकेजिंग", "डिब्बा", "बोतल",
        ),
        related_question_templates=(
            "What should I check for food-grade packaging marks?",
            "Which BIS standards apply to plastic food containers?",
            "What labelling information is required on packaged food?",
        ),
    ),
    KnowledgeCategory(
        key="hallmarking",
        label="Gold & Silver",
        emoji="💍",
        description="BIS hallmarking of gold and silver jewellery, HUID, purity grades and consumer verification.",
        keywords=(
            "hallmark", "hallmarking", "huid", "gold", "silver", "jewellery", "jewelry",
            "karat", "carat", "fineness", "916", "750", "585", "999", "bIS hallmark",
            "assaying", "assay", "purify", "purity", "bungie", "sona", "chaandi",
            "sone ki", "chaandi ki", "kundan", "ring", "bangle", "chain", "necklace",
            "ornament", "jeweller", "ahc", "assaying and hallmarking centre",
            # Hindi
            "सोना", "चाँदी", "चांदी", "गहना", "आभूषण", "हॉलमार्क", "शुद्धता", "मुल्य",
        ),
        related_question_templates=(
            "What does HUID stand for and how do I verify it?",
            "Which fineness grades are used in BIS hallmarking?",
            "What should I check on a hallmark before buying jewellery?",
        ),
    ),
    KnowledgeCategory(
        key="electronics_electrical",
        label="Electronics & Electrical",
        emoji="⚡",
        description="Household electrical appliances, wires, cables, plugs, switches, chargers, LEDs and batteries.",
        keywords=(
            "electrical", "electronics", "appliance", "wire", "wires", "cable", "cables",
            "plug", "plugs", "socket", "switch", "switches", "charger", "adapter",
            "power bank", "led", "lamp", "bulb", "light", "lighting", "battery",
            "batteries", "cell", "inverter", "geyser", "heater", "fan", "iron",
            "microwave", "washing machine", "refrigerator", "fridge", "ac",
            "air conditioner", "tv", "television", "laptop", "computer", "mobile",
            "smartphone", "crs", "registration scheme", "voltage", "insulation",
            "shock", "earthing",
            # Hindi
            "बिजली", "इलेक्ट्रॉनिक", "तार", "केबल", "बैटरी", "चार्जर", "बल्ब", "पंखा",
        ),
        related_question_templates=(
            "Does BIS certification apply mandatorily to this product?",
            "What safety marks should I look for before buying?",
            "What is the BIS Registration Scheme (CRS)?",
        ),
    ),
    KnowledgeCategory(
        key="everyday_products",
        label="Everyday Products",
        emoji="🏠",
        description="Helmets, pressure cookers, LPG cylinders, toys, cement, steel and other household items.",
        keywords=(
            "helmet", "helmets", "pressure cooker", "cooker", "lpg", "cylinder",
            "gas cylinder", "toy", "toys", "footwear", "shoes", "sandals",
            "furniture", "chair", "table", "bucket", "household", "kitchenware",
            "utensil", "cookware", "mattress", "textile", "personal use",
            "lock", "hinges", "tap", "pipe", "tank", "umbrella", "matchbox",
            "agarbatti", "helmet isi", "safety helmet", "two wheeler",
            # Hindi
            "हेलमेट", "कुकर", "सिलेंडर", "खिलौना", "सरिया", "लोहा",
        ),
        related_question_templates=(
            "Is the ISI mark mandatory for this product?",
            "How do I verify the ISI mark on the product or packaging?",
            "What should I check before buying this product?",
        ),
    ),
    KnowledgeCategory(
        key="construction",
        label="Construction & Building Materials",
        emoji="🧱",
        description="Cement, steel, reinforcement bars, concrete, building materials and related testing requirements.",
        keywords=(
            "cement", "portland cement", "concrete", "steel", "tmt", "reinforcement",
            "rebar", "building material", "construction", "bricks", "blocks",
            "vitrified tile", "tiles", "sanitary ware", "pvc pipe", "cpvc",
            # Hindi
            "सीमेंट", "निर्माण", "ईंट",
        ),
        related_question_templates=(
            "Which BIS standard applies to this construction material?",
            "Is BIS certification mandatory for cement?",
            "How is cement tested for strength and setting time?",
        ),
    ),
    KnowledgeCategory(
        key="general_bis",
        label="General BIS",
        emoji="📚",
        description="What BIS is, Indian Standards, certification marks, consumer services, complaints and awareness.",
        keywords=(
            "bis", "bureau", "bureau of indian standards", "indian standard",
            "indian standards", "isi mark", "standard mark", "what is bis",
            "certification scheme", "conformity", "conformity assessment",
            "laboratory", "lab", "testing lab", "consumer complaint", "grievance",
            "standards club", "training", "awareness", "manak", "manakonline",
            "bis act", "national standards body", "msme", "startup", "e-bis",
            "bis care", "verify app",
            # Hindi
            "बीआईएस", "मानक", "भारतीय मानक", "गुणवत्ता",
        ),
        related_question_templates=(
            "What is the difference between the ISI mark and the CRS mark?",
            "How can a consumer file a complaint about a certified product?",
            "Where can I find the official text of an Indian Standard?",
        ),
    ),
    KnowledgeCategory(
        key="industry",
        label="Industry & Manufacturing",
        emoji="🏭",
        description="Certification process, licensing, testing, documentation and compliance for manufacturers.",
        keywords=(
            "manufacturer", "manufacturing", "factory", "plant", "production",
            "licence", "license", "apply", "application", "documentation",
            "compliance", "audit", "factory inspection", "soti", "scheme of testing",
            "marking fee", "sms", "standard marking", "qco", "quality control order",
            "import", "export", "startup certification", "msme certification",
            "conformity assessment", "third party", "self-declaration",
            # Hindi
            "उद्योग", "कारखाना", "निर्माता", "लाइसेंस",
        ),
        related_question_templates=(
            "What are the steps in the BIS product certification process?",
            "What documentation does a manufacturer need for a BIS licence?",
            "What is the Scheme of Testing and Inspection (STI)?",
        ),
    ),
]}

# Categories whose documents often also answer questions detected in a
# neighbouring category (used to widen the metadata filter, see retrieval).
RELATED_CATEGORIES: dict[str, tuple[str, ...]] = {
    "food": ("water", "packaging"),
    "water": ("food", "packaging"),
    "packaging": ("food", "water"),
    "hallmarking": ("general_bis",),
    "everyday_products": ("construction", "electronics_electrical"),
    "construction": ("everyday_products",),
    "electronics_electrical": ("everyday_products",),
    "general_bis": ("industry",),
    "industry": ("general_bis",),
}


def related_categories_for(category_key: str) -> list[str]:
    """Canonical neighbours for a category (used to widen metadata filters)."""
    key = normalize_category(category_key)
    return [k for k in RELATED_CATEGORIES.get(key, ()) if k in CATEGORIES]


# Legacy category values already present in the DB are mapped to the new keys.
LEGACY_CATEGORY_MAP = {
    "cement": "everyday_products",
    "safety": "everyday_products",
    "consumer": "general_bis",
    "certification": "industry",
    "general": "general_bis",
}


def normalize_category(raw: str | None) -> str:
    """Map any stored/free-form category value to a canonical registry key."""
    v = (raw or "").strip().lower().replace(" ", "_").replace("-", "_")
    v = v.replace("&", "_")
    while "__" in v:
        v = v.replace("__", "_")
    if v in CATEGORIES:
        return v
    aliases = {
        "electronics": "electronics_electrical",
        "electrical": "electronics_electrical",
        "electronics_and_electrical": "electronics_electrical",
        "everyday": "everyday_products",
        "everyday_product": "everyday_products",
        "hallmark": "hallmarking",
        "gold_silver": "hallmarking",
        "gold_and_silver": "hallmarking",
        "household": "everyday_products",
        "consumer_products": "everyday_products",
        "food_and_water": "food",
        "water_quality": "water",
    }
    if v in aliases:
        return aliases[v]
    return LEGACY_CATEGORY_MAP.get(v, "general_bis")


# ----------------------------------------------------------------------------
# Products (reference knowledge — DEMO status, verify on official BIS sources)
# ----------------------------------------------------------------------------
@dataclass
class Product:
    name: str
    category: str  # canonical category key
    subcategory: str = ""
    aliases: tuple[str, ...] = ()
    standard_number: str = ""  # empty ⇒ "information not available"
    standard_title: str = ""
    certification_status: str = "info-not-available"
    # mandatory | voluntary | scheme-specific | info-not-available
    scheme: str = ""  # ISI | CRS | HALLMARK | ""
    consumer_checklist: tuple[str, ...] = ()
    notes: str = ""

    @property
    def status_display(self) -> str:
        return {
            "mandatory": "Mandatory BIS certification (verify current QCO)",
            "voluntary": "BIS certification is voluntary for this product",
            "scheme-specific": "Certified under a BIS scheme (see notes)",
            "info-not-available": "Information not available in the current knowledge base",
        }.get(self.certification_status, self.certification_status)


PRODUCTS: list[Product] = [
    # ---------------- FOOD ----------------
    Product(
        name="Packaged Drinking Water",
        category="water",
        subcategory="Water",
        aliases=("packaged drinking water", "bottled water", "water bottle", "drinking water", "paani"),
        standard_number="IS 14543",
        standard_title="Packaged Drinking Water (Other than Packaged Natural Mineral Water) — Specification",
        certification_status="mandatory",
        scheme="ISI",
        consumer_checklist=(
            "Look for the ISI mark with the licence number (CM/L) on the bottle or pack.",
            "Check the manufacturing/batch date and 'best before' date.",
            "Check that the seal is intact and the bottle is stored away from sunlight.",
            "Report unmarked or suspicious packaged water to the seller and BIS.",
        ),
        notes="Packaged drinking water has long required BIS certification under a Quality Control Order. Verify the latest requirement on the official BIS source.",
    ),
    Product(
        name="Packaged Natural Mineral Water",
        category="water",
        subcategory="Water",
        aliases=("mineral water", "natural mineral water"),
        standard_number="IS 13428",
        standard_title="Packaged Natural Mineral Water — Specification",
        certification_status="mandatory",
        scheme="ISI",
        consumer_checklist=(
            "Check for the ISI mark and licence number on the label.",
            "Natural mineral water must come from a protected underground source named on the label.",
        ),
        notes="Certification has been mandatory under a Quality Control Order. Verify the latest status on the official BIS source.",
    ),
    Product(
        name="Water Quality Testing and Sampling",
        category="water",
        subcategory="Testing",
        aliases=("water testing", "water quality", "sampling of water", "water analysis", "potability test"),
        standard_number="IS 3025",
        standard_title="Methods of Sampling and Test (Physical and Chemical) for Water and Wastewater (Part 1 and onwards)",
        certification_status="voluntary",
        scheme="",
        consumer_checklist=(
            "Ask any water-testing lab which IS 3025 part the analysis was done per.",
            "Drinking-water acceptability limits are specified separately (see the drinking-water quality guidance).",
        ),
        notes="IS 3025 is a test-method series (not a product certification): laboratories use it to analyse water quality part by part (pH, turbidity, microbiological parameters, etc.).",
    ),
    Product(
        name="Silver Jewellery Hallmarking",
        category="hallmarking",
        subcategory="Hallmarking",
        aliases=("silver", "silver jewellery", "chaandi", "chandi", "silver hallmark", "925", "sterling"),
        standard_number="IS 2112",
        standard_title="Silver and Silver Alloys, Jewellery/Artefacts — Fineness and Marking",
        certification_status="scheme-specific",
        scheme="HALLMARK",
        consumer_checklist=(
            "Look for the BIS hallmark with the fineness grade (e.g. 925 for sterling silver).",
            "Verify the HUID on the official BIS Care app before purchase.",
        ),
    ),
    Product(
        name="Wheat Flour (Atta)",
        category="food",
        subcategory="Cereals & Flours",
        aliases=("atta", "wheat flour", "flour", "gehu ka atta"),
        standard_number="IS 1159",
        standard_title="Wheat Atta — Specification",
        certification_status="voluntary",
        scheme="ISI",
        consumer_checklist=(
            "Check the manufacturing/best-before date and ingredients list.",
            "An ISI mark on flour indicates the maker chose voluntary BIS certification.",
            "Food safety compliance for sale is governed by FSSAI — check the FSSAI licence number too.",
        ),
        notes="Most processed foods fall under FSSAI regulation; BIS certification for them is voluntary unless a specific Quality Control Order applies.",
    ),
    Product(
        name="Maida (Refined Wheat Flour)",
        category="food",
        subcategory="Cereals & Flours",
        aliases=("maida", "refined flour"),
        standard_number="IS 1010",
        standard_title="Maida — Specification",
        certification_status="voluntary",
        scheme="ISI",
    ),
    Product(
        name="Besan (Gram Flour)",
        category="food",
        subcategory="Cereals & Flours",
        aliases=("besan", "gram flour", "chana flour"),
        standard_number="IS 947",
        standard_title="Besan (Gram Flour) — Specification",
        certification_status="voluntary",
        scheme="ISI",
    ),
    Product(
        name="Food-Grade Plastics & Containers",
        category="packaging",
        subcategory="Food Contact Materials",
        aliases=("food container", "tiffin", "lunch box", "plastic container", "food grade plastic", "packaging"),
        standard_number="IS 9833",
        standard_title="List of Plastics and Materials in Contact with Foodstuffs — Positive List",
        certification_status="voluntary",
        scheme="ISI",
        consumer_checklist=(
            "Prefer containers labelled food-grade / microwave-safe.",
            "Avoid using damaged or discoloured plastic containers for hot food.",
        ),
    ),
    Product(
        name="Spices and Spice Powders",
        category="food",
        subcategory="Spices",
        aliases=("spice", "spices", "turmeric", "haldi", "chilli powder", "coriander powder", "masala", "garam masala"),
        standard_number="",
        standard_title="",
        certification_status="info-not-available",
        consumer_checklist=(
            "Check the FSSAI licence number, ingredients and best-before date on the pack.",
            "BIS standards exist for some spice products; this knowledge base does not list a specific number — ask an admin to index the relevant standard.",
        ),
        notes="Specific BIS standard numbers for spices are not recorded in this knowledge base, so none is shown (the assistant never invents numbers).",
    ),
    Product(
        name="Edible Oils",
        category="food",
        subcategory="Oils",
        aliases=("edible oil", "cooking oil", "mustard oil", "coconut oil", "sunflower oil", "refined oil", "tel"),
        standard_number="",
        standard_title="",
        certification_status="info-not-available",
        consumer_checklist=(
            "Check the FSSAI licence number, AGMARK where present, and the packaging date.",
            "Store oils away from direct sunlight.",
        ),
        notes="BIS has published standards for several edible oils, but this knowledge base does not record specific numbers for them.",
    ),
    Product(
        name="Milk and Dairy Products",
        category="food",
        subcategory="Dairy",
        aliases=("milk", "dairy", "doodh", "ghee", "butter", "paneer", "curd", "dahi", "milk powder"),
        standard_number="",
        standard_title="",
        certification_status="info-not-available",
        consumer_checklist=(
            "Check the FSSAI licence number and packaging date on milk packs.",
            "For UHT milk check the aseptic seal; refrigerate pasteurised milk promptly.",
        ),
        notes="Dairy is primarily regulated by FSSAI; some BIS standards exist for milk products. Numbers are not recorded in this knowledge base.",
    ),
    # ---------------- HALLMARKING ----------------
    Product(
        name="Gold Jewellery Hallmarking",
        category="hallmarking",
        subcategory="Hallmarking",
        aliases=("gold", "gold jewellery", "sona", "gold hallmark", "916", "22k", "18k", "sone ki anguthi"),
        standard_number="IS 1417",
        standard_title="Gold and Gold Alloys, Jewellery/Artefacts — Fineness and Marking",
        certification_status="scheme-specific",
        scheme="HALLMARK",
        consumer_checklist=(
            "Look for the BIS hallmark: BIS mark, fineness grade (e.g. 916 for 22K), jeweller's mark, Assaying & Hallmarking Centre mark and the HUID code.",
            "Verify the HUID on the official BIS Care app / BIS website before purchase.",
            "Ask for an itemised invoice mentioning the purity and hallmark.",
            "Gold hallmarking became mandatory in phases from 2021 for registered jewellers — verify the current scope on the official BIS source.",
        ),
        notes="HUID (Hallmark Unique Identification) is a six-character alphanumeric code laser-marked on each hallmarked item since July 2021. The assistant cannot judge whether a specific piece is genuine — it explains what can be checked.",
    ),
    Product(
        name="Silver Jewellery Hallmarking",
        category="hallmarking",
        subcategory="Hallmarking",
        aliases=("silver", "silver jewellery", "chaandi", "chandi", "silver hallmark", "925"),
        standard_number="IS 2112",
        standard_title="Silver and Silver Alloys, Jewellery/Artefacts — Fineness and Marking",
        certification_status="scheme-specific",
        scheme="HALLMARK",
        consumer_checklist=(
            "Silver hallmarking is voluntary — an unmarked item is not necessarily impure, and a claimed hallmark should be verified.",
            "Look for the BIS mark, fineness grade (e.g. 925 sterling) and HUID where present.",
        ),
        notes="Verify the current hallmarking scope for silver on the official BIS source.",
    ),
    Product(
        name="Assaying of Gold Jewellery",
        category="hallmarking",
        subcategory="Testing",
        aliases=("assay", "assaying", "purity test", "gold testing"),
        standard_number="IS 1418",
        standard_title="Methods of Assaying Gold in Gold Jewellery and Artefacts",
        certification_status="voluntary",
        scheme="",
    ),
    # ---------------- ELECTRONICS & ELECTRICAL ----------------
    Product(
        name="PVC Insulated Cables and Wires",
        category="electronics_electrical",
        subcategory="Cables & Wires",
        aliases=("wire", "wires", "cable", "cables", "house wiring", "electric wire", "taar"),
        standard_number="IS 694",
        standard_title="PVC Insulated Cables for Working Voltages up to and including 1100 V — Specification",
        certification_status="mandatory",
        scheme="ISI",
        consumer_checklist=(
            "Look for the ISI mark and voltage rating printed on the sheath.",
            "Check the ISI mark is on the wire itself, not only the box.",
        ),
        notes="Household wiring cables have long been under mandatory certification. Verify the current Quality Control Order on the official BIS source.",
    ),
    Product(
        name="Plugs and Socket-Outlets",
        category="electronics_electrical",
        subcategory="Accessories",
        aliases=("plug", "plugs", "socket", "socket outlet", "extension board", "multiplug"),
        standard_number="IS 1293",
        standard_title="Plugs and Socket-Outlets of Rated Voltage up to and including 250 V — Specification",
        certification_status="mandatory",
        scheme="ISI",
        consumer_checklist=(
            "Check the ISI mark on the plug body and the current rating (e.g. 6 A / 16 A).",
            "Ensure shutters/shuttered sockets where children have access.",
        ),
    ),
    Product(
        name="Domestic Switches",
        category="electronics_electrical",
        subcategory="Accessories",
        aliases=("switch", "switches", "light switch", "modular switch"),
        standard_number="IS 3854",
        standard_title="Switches for Domestic and Similar Purposes — Specification",
        certification_status="mandatory",
        scheme="ISI",
    ),
    Product(
        name="Household Electrical Appliances (Safety)",
        category="electronics_electrical",
        subcategory="Appliances",
        aliases=("appliance", "geyser", "heater", "electric iron", "mixer", "fan", "washing machine", "microwave"),
        standard_number="IS 302",
        standard_title="Household and Similar Electrical Appliances — Safety (Part 1: General Requirements)",
        certification_status="voluntary",
        scheme="ISI",
        consumer_checklist=(
            "Prefer products carrying the ISI mark; check the power rating and plug condition.",
            "Follow the manufacturer's earthing/instalment instructions.",
        ),
        notes="Which appliances require mandatory certification changes over time (QCOs); verify the current list on the official BIS source.",
    ),
    Product(
        name="Mobile Chargers and IT Equipment (Safety)",
        category="electronics_electrical",
        subcategory="IT & Charging",
        aliases=("charger", "mobile charger", "adapter", "power adapter", "laptop charger", "computer", "laptop", "it equipment"),
        standard_number="IS 62368-1",
        standard_title="Audio/Video, Information and Communication Technology Equipment — Safety Requirements",
        certification_status="scheme-specific",
        scheme="CRS",
        consumer_checklist=(
            "Check for the BIS registration mark (CRS) on the charger.",
            "Avoid uncertified, very cheap chargers — they are a common fire/shock risk.",
        ),
        notes="Electronics and IT products are covered by the BIS Registration Scheme (CRS): manufacturers must register and self-declare conformity to the relevant Indian standard. IS 13252 covers IT equipment safety (earlier generation).",
    ),
    Product(
        name="LED Lamps (Self-Ballasted)",
        category="electronics_electrical",
        subcategory="Lighting",
        aliases=("led", "led bulb", "led lamp", "bulb", "light"),
        standard_number="IS 16102",
        standard_title="Self-Ballasted LED Lamps for General Lighting Services — Safety Requirements (Part 1)",
        certification_status="scheme-specific",
        scheme="CRS",
    ),
    Product(
        name="Portable Batteries and Cells",
        category="electronics_electrical",
        subcategory="Batteries",
        aliases=("battery", "batteries", "power bank", "cell", "lithium battery"),
        standard_number="IS 16046",
        standard_title="Secondary Cells and Batteries containing Alkaline or Non-Acid Electrolytes — Safety Requirements for Portable Sealed Cells and Batteries",
        certification_status="scheme-specific",
        scheme="CRS",
    ),
    # ---------------- EVERYDAY PRODUCTS ----------------
    Product(
        name="Industrial Safety Helmets",
        category="everyday_products",
        subcategory="Safety",
        aliases=("helmet", "helmets", "safety helmet", "industrial helmet"),
        standard_number="IS 2925",
        standard_title="Industrial Safety Helmets — Specification",
        certification_status="mandatory",
        scheme="ISI",
        consumer_checklist=(
            "Look for the ISI mark and licence number (CM/L) moulded or printed on the shell.",
            "Check the harness is intact and the shell has no cracks.",
        ),
    ),
    Product(
        name="Two-Wheeler Protective Helmets",
        category="everyday_products",
        subcategory="Safety",
        aliases=("bike helmet", "motorcycle helmet", "two wheeler helmet"),
        standard_number="IS 4151",
        standard_title="Protective Helmets for Two-Wheeler Riders — Specification",
        certification_status="mandatory",
        scheme="ISI",
    ),
    Product(
        name="Pressure Cookers",
        category="everyday_products",
        subcategory="Kitchen",
        aliases=("pressure cooker", "cooker", "cooker safety", "handi", "kukar"),
        standard_number="IS 2347",
        standard_title="Pressure Cookers — Specification",
        certification_status="mandatory",
        scheme="ISI",
        consumer_checklist=(
            "The ISI mark on pressure cookers is mandatory — do not buy an unmarked cooker.",
            "Check the gasket, safety plug and handle are intact before each use.",
        ),
        notes="Pressure cookers have been under mandatory BIS certification for decades. Verify the latest requirement on the official BIS source.",
    ),
    Product(
        name="LPG Cylinders",
        category="everyday_products",
        subcategory="Gas & Fuel",
        aliases=("lpg", "lpg cylinder", "gas cylinder", "cooking gas"),
        standard_number="IS 3196",
        standard_title="Liquefied Petroleum Gas (LPG) Cylinders — Specification (Part 1)",
        certification_status="mandatory",
        scheme="ISI",
        consumer_checklist=(
            "Check the test date ring on the cylinder neck and the ISI mark.",
            "Never accept a cylinder past its due test date; check the seal at delivery.",
        ),
    ),
    Product(
        name="Toys",
        category="everyday_products",
        subcategory="Children",
        aliases=("toy", "toys", "kids toy", "khilona"),
        standard_number="IS 9873",
        standard_title="Safety of Toys (Part 1: Safety Aspects Related to Mechanical and Physical Properties)",
        certification_status="mandatory",
        scheme="ISI",
        consumer_checklist=(
            "Under the Toys Quality Control Order, toys sold in India must carry the ISI mark — avoid unmarked toys.",
            "Check the age-grading label and avoid small detachable parts for under-3s.",
        ),
        notes="Toys require BIS certification under the Toys (Quality Control) Order, 2020. Verify the current scope on the official BIS source.",
    ),
    Product(
        name="Ordinary Portland Cement",
        category="construction",
        subcategory="Cement",
        aliases=("cement", "opc", "portland cement", "bora", "simint"),
        standard_number="IS 269",
        standard_title="Ordinary Portland Cement — Specification (33 grade; see also IS 8112 for 43 grade and IS 12269 for 53 grade)",
        certification_status="mandatory",
        scheme="ISI",
        consumer_checklist=(
            "Check the ISI mark on the bag and the week/month of packing.",
            "Use fresh cement — older bags lose strength.",
        ),
    ),
    Product(
        name="Portland Pozzolana Cement",
        category="everyday_products",
        subcategory="Construction",
        aliases=("ppc", "pozzolana cement", "ppc cement"),
        standard_number="IS 1489",
        standard_title="Portland-Pozzolana Cement — Specification (Part 1: fly ash based)",
        certification_status="mandatory",
        scheme="ISI",
    ),
    Product(
        name="TMT / Reinforcement Steel Bars",
        category="everyday_products",
        subcategory="Construction",
        aliases=("steel", "tmt", "sariya", "sariya rod", "reinforcement bar", "rebar", "deformed bar"),
        standard_number="IS 1786",
        standard_title="High Strength Deformed Steel Bars and Wires for Concrete Reinforcement — Specification",
        certification_status="mandatory",
        scheme="ISI",
    ),
    Product(
        name="Footwear",
        category="everyday_products",
        subcategory="Personal",
        aliases=("footwear", "shoes", "sandals", "chappal", "joota"),
        standard_number="",
        standard_title="",
        certification_status="info-not-available",
        consumer_checklist=(
            "Check sizing, sole grip and stitching quality.",
            "This knowledge base does not record which (if any) footwear standards carry mandatory certification.",
        ),
    ),
    Product(
        name="Furniture",
        category="everyday_products",
        subcategory="Home",
        aliases=("furniture", "chair", "table", "bed", "cupboard"),
        standard_number="",
        standard_title="",
        certification_status="info-not-available",
        consumer_checklist=(
            "Check material, finish and load ratings as claimed by the seller.",
        ),
        notes="BIS has published furniture standards in recent years; specific numbers are not recorded in this knowledge base.",
    ),
    # ---------------- GENERAL BIS / INDUSTRY (no product rows needed, but a
    # couple anchor entries help the UI) ----------------
    Product(
        name="BIS Product Certification (ISI Mark Scheme)",
        category="industry",
        subcategory="Certification",
        aliases=("isi mark scheme", "product certification", "scheme 1", "bis licence"),
        standard_number="",
        standard_title="",
        certification_status="scheme-specific",
        scheme="ISI",
        notes="Factory inspection, independent testing and the Scheme of Testing and Inspection (STI) underpin the ISI mark scheme.",
    ),
    Product(
        name="BIS Registration Scheme for Electronics (CRS)",
        category="industry",
        subcategory="Certification",
        aliases=("crs", "registration scheme", "mandatory registration"),
        standard_number="",
        standard_title="",
        certification_status="scheme-specific",
        scheme="CRS",
        notes="Under CRS, manufacturers of notified electronics/IT products register with BIS and self-declare conformity after testing in BIS-recognised labs.",
    ),
]

PRODUCTS_BY_NAME = {p.name.lower(): p for p in PRODUCTS}


def products_for_category(category_key: str) -> list[Product]:
    key = normalize_category(category_key)
    return [p for p in PRODUCTS if p.category == key]


def find_product(query: str) -> Product | None:
    """Find the first product whose name/alias appears in the query text."""
    q = f" {(query or '').lower()} "
    best: tuple[int, Product] | None = None
    for p in PRODUCTS:
        candidates = [p.name.lower(), *p.aliases]
        for cand in candidates:
            if not cand or len(cand) < 3:
                continue
            # whole-token-ish match so "iron" doesn't match "environment"
            import re

            pattern = r"(?<![a-z0-9])" + re.escape(cand) + r"(?![a-z0-9])"
            if re.search(pattern, q):
                if best is None or len(cand) > best[0]:
                    best = (len(cand), p)
    return best[1] if best else None


def related_questions_for(category_key: str, product: Product | None = None) -> list[str]:
    """Follow-up questions based ONLY on the detected category/product context."""
    cat = CATEGORIES.get(normalize_category(category_key))
    questions: list[str] = list(cat.related_question_templates) if cat else []
    if product and product.standard_number:
        questions.insert(0, f"Which Indian Standard applies to {product.name.lower()}?")
    return questions[:3]


def category_labels() -> dict[str, str]:
    """key -> display label (used by the frontend filter chips)."""
    return {k: f"{c.emoji} {c.label}" for k, c in CATEGORIES.items()}
