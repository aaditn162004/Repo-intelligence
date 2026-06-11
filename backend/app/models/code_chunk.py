import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChunkType(str, Enum):
    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    MODULE = "module"
    IMPORT = "import"
    COMMENT = "comment"
    ROUTE = "route"
    DECORATOR = "decorator"
    INTERFACE = "interface"
    TYPE = "type"
    VARIABLE = "variable"
    SNIPPET = "snippet"


class CodeChunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    repository_id: str
    file_path: str
    language: str
    chunk_type: ChunkType
    name: Optional[str] = None
    content: str
    start_line: int
    end_line: int
    signature: Optional[str] = None
    docstring: Optional[str] = None
    imports: List[str] = []
    dependencies: List[str] = []
    parent_name: Optional[str] = None
    decorators: List[str] = []
    metadata: Dict[str, Any] = {}

    class Config:
        use_enum_values = True


class EmbeddedChunk(BaseModel):
    chunk_id: str
    repository_id: str
    embedding: List[float]
    text_for_embedding: str


class GraphNode(BaseModel):
    id: str
    repository_id: str
    node_type: str
    name: str
    file_path: str
    language: str
    metadata: Dict[str, Any] = {}


class GraphEdge(BaseModel):
    source_id: str
    target_id: str
    edge_type: str
    metadata: Dict[str, Any] = {}
