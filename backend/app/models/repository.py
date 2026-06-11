from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class IndexingStatus(str, Enum):
    PENDING = "pending"
    CLONING = "cloning"
    PARSING = "parsing"
    EMBEDDING = "embedding"
    GRAPHING = "graphing"
    READY = "ready"
    FAILED = "failed"


class Language(str, Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    GO = "go"
    RUST = "rust"
    CPP = "cpp"
    C = "c"
    RUBY = "ruby"
    PHP = "php"
    UNKNOWN = "unknown"


class RepositoryCreate(BaseModel):
    url: str = Field(..., description="GitHub repository URL")
    branch: str = Field(default="main", description="Branch to index")
    name: Optional[str] = None


class Repository(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    url: str
    branch: str = "main"
    status: IndexingStatus = IndexingStatus.PENDING
    languages: List[str] = []
    total_files: int = 0
    indexed_files: int = 0
    total_chunks: int = 0
    description: Optional[str] = None
    primary_language: Optional[str] = None
    framework_hints: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    indexed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}

    class Config:
        use_enum_values = True


class IndexingProgress(BaseModel):
    repository_id: str
    status: IndexingStatus
    stage: str
    progress: float = Field(ge=0.0, le=100.0)
    current_file: Optional[str] = None
    message: str = ""
    indexed_files: int = 0
    total_files: int = 0
