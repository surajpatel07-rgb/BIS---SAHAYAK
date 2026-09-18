"""Chat schemas."""
from pydantic import BaseModel, Field


class CitationSchema(BaseModel):
    document_id: int
    document_name: str
    standard_number: str
    title: str
    page: int
    section: str
    chunk_id: int
    relevance_score: float
    source_url: str
    document_type: str
    category: str
    year: int | None = None
    snippet: str
    # Provenance (displayed on citation cards)
    source_name: str = ""
    source_type: str = "demo"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = None
    mode: str = Field(default="consumer", pattern="^(consumer|industry)$")
    # Optional explicit category filter (from the UI category selector)
    category: str | None = None


class ChatResponse(BaseModel):
    conversation_id: int
    message_id: int
    answer: str
    sources: list[CitationSchema] = []
    mode: str
    llm_provider: str = "gemini"
    # Query-understanding additions
    detected_category: str = "general_bis"
    category_label: str = "General BIS"
    category_confidence: float = 0.0
    language: str = "en"
    related_questions: list[str] = []


class StreamChatRequest(ChatRequest):
    pass
