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


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    conversation_id: int | None = None
    mode: str = Field(default="consumer", pattern="^(consumer|industry)$")


class ChatResponse(BaseModel):
    conversation_id: int
    message_id: int
    answer: str
    sources: list[CitationSchema] = []
    mode: str
    llm_provider: str = "gemini"


class StreamChatRequest(ChatRequest):
    pass
