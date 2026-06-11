from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import uuid
from datetime import datetime


class QueryType(str, Enum):
    ARCHITECTURE = "architecture"
    FLOW_TRACE = "flow_trace"
    BUG_LOCALIZATION = "bug_localization"
    DOCUMENTATION = "documentation"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    GENERAL = "general"


class QueryRequest(BaseModel):
    repository_id: str
    question: str
    query_type: Optional[QueryType] = None
    max_context_chunks: int = Field(default=10, ge=1, le=30)
    include_graph_context: bool = True
    stream: bool = True


class SourceReference(BaseModel):
    chunk_id: str
    file_path: str
    chunk_type: str
    name: Optional[str] = None
    start_line: int
    end_line: int
    relevance_score: float
    snippet: str


class QueryResponse(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    repository_id: str
    question: str
    answer: str
    query_type: QueryType
    sources: List[SourceReference] = []
    graph_context: Optional[Dict[str, Any]] = None
    reasoning_steps: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    tokens_used: int = 0


class DocumentationRequest(BaseModel):
    repository_id: str
    target: str
    doc_type: str = Field(default="module", description="module|function|api|architecture|readme")
    format: str = Field(default="markdown", description="markdown|html|plain")


class DocumentationResponse(BaseModel):
    repository_id: str
    target: str
    doc_type: str
    content: str
    format: str
