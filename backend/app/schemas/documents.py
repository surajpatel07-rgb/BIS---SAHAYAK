"""Document and search schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    standard_number: str
    title: str
    year: int | None
    document_type: str
    category: str
    description: str
    file_path: str
    file_size: int
    page_count: int
    source_url: str
    status: str
    error_message: str
    created_at: datetime
    updated_at: datetime


class DocumentDetailOut(DocumentOut):
    chunk_count: int = 0


class DocumentSearchOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    standard_number: str
    title: str
    year: int | None
    document_type: str
    category: str
    status: str
    source_url: str


class ConversationSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    mode: str
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    role: str
    content: str
    sources_json: dict | list | None = None
    created_at: datetime


class ConversationDetail(ConversationSummary):
    messages: list[MessageOut] = []


class FeedbackRequest(BaseModel):
    message_id: int
    rating: int = Field(ge=-1, le=1)
    comment: str = Field(default="", max_length=2000)


class FeedbackOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    message_id: int
    rating: int
    comment: str
    created_at: datetime


class AdminStats(BaseModel):
    total_documents: int
    indexed_documents: int
    processing_documents: int
    failed_documents: int
    total_chunks: int
    total_conversations: int
    total_messages: int
    total_users: int
    llm_provider: str
    embedding_provider: str


class SearchHit(BaseModel):
    """A semantic chunk-level search hit from /api/search."""

    document_id: int
    document_name: str
    standard_number: str
    title: str
    page: int
    section: str
    snippet: str
    score: float


class SemanticSearchResponse(BaseModel):
    query: str
    results: list[SearchHit]


class StatusResponse(BaseModel):
    ok: bool
    detail: str = ""
