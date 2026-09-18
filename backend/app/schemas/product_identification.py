"""Schemas for the AI Product Identifier feature."""
from pydantic import BaseModel, Field


class StandardRecommendation(BaseModel):
    """A BIS standard recommendation backed by retrieved evidence."""

    is_number: str  # e.g. "IS 2346" — empty when the chunk has no standard number
    title: str  # document/standard title
    relevance: str  # why this standard appears applicable
    evidence: str  # short quote/paraphrase from the retrieved BIS document
    source: str  # document name + page, e.g. "ELECTRONICS-GUIDE.pdf, page 4"
    source_url: str = ""
    document_id: int
    page: int
    section: str = ""
    category: str
    confidence: float  # evidence-strength 0-1
    match_level: str  # strong | moderate | weak


class PossibleProduct(BaseModel):
    name: str
    confidence: float


class IdentifiedProduct(BaseModel):
    name: str
    category: str
    confidence: float
    product_type: str = ""
    brand: str = ""
    model: str = ""
    specifications: list[str] = []
    markings: list[str] = []
    packaging_info: str = ""
    possible_matches: list[PossibleProduct] = []


class ProductIdentificationResponse(BaseModel):
    """Full response for POST /api/product-identification and /match-standard.

    One schema serves both endpoints: /identify with an image returns the
    product identification plus the initial standard matching; /match-standard
    returns it again for a user-confirmed product name (possible_matches empty).
    """

    product: IdentifiedProduct
    standards: list[StandardRecommendation] = []
    # Honest-warning strings shown to the user (image quality, low confidence,
    # no matching standard found, offline mode, ...). Never internal details.
    warnings: list[str] = []
    # True when the standards list is empty/weak — the UI shows the
    # "no sufficiently relevant BIS Standard was found" notice.
    needs_verification: bool = True
    query_used: str = ""  # the BIS search query derived from the identification
    llm_provider: str = "gemini"


class MatchStandardRequest(BaseModel):
    product_name: str = Field(min_length=2, max_length=200)
    category: str = ""
