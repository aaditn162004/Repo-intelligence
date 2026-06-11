"""
Structure-aware chunker that builds semantic text blocks from AST chunks.
Combines nearby small chunks and splits oversized ones with overlap.
"""
from __future__ import annotations

from typing import List, Dict, Any

import structlog

from app.models.code_chunk import CodeChunk, ChunkType
from app.core.config import settings

logger = structlog.get_logger()


class StructureAwareChunker:
    """
    Takes raw AST-extracted CodeChunks and prepares them for embedding.
    Strategy:
      - Functions / classes are embedded as-is (capped at MAX_TOKENS chars)
      - Module chunks use the first N lines (header context)
      - Import blocks are collapsed into one chunk
      - Oversized chunks are split with overlap
    """

    MAX_CHARS = settings.CHUNK_SIZE * 4   # rough chars per embedding chunk
    OVERLAP_CHARS = settings.CHUNK_OVERLAP * 4

    def prepare_for_embedding(self, chunks: List[CodeChunk]) -> List[Dict[str, Any]]:
        """Return list of dicts with 'chunk' and 'text' keys ready for embedding."""
        results = []

        # Group imports together per file
        import_chunks: Dict[str, List[CodeChunk]] = {}
        other_chunks: List[CodeChunk] = []

        for chunk in chunks:
            if chunk.chunk_type == ChunkType.IMPORT:
                import_chunks.setdefault(chunk.file_path, []).append(chunk)
            else:
                other_chunks.append(chunk)

        # Merge imports into one chunk per file
        for file_path, imp_list in import_chunks.items():
            combined = "\n".join(c.content for c in imp_list)
            results.append({
                "chunk": imp_list[0],
                "text": self._format_embedding_text(imp_list[0], combined),
            })

        # Process remaining chunks
        for chunk in other_chunks:
            text = self._format_embedding_text(chunk, chunk.content)
            if len(text) <= self.MAX_CHARS:
                results.append({"chunk": chunk, "text": text})
            else:
                # Split oversized chunks
                sub_texts = self._split_text(text)
                for i, sub in enumerate(sub_texts):
                    results.append({"chunk": chunk, "text": sub, "sub_index": i})

        return results

    def _format_embedding_text(self, chunk: CodeChunk, content: str) -> str:
        """Build a rich text representation optimised for semantic search."""
        parts = []
        parts.append(f"File: {chunk.file_path}")
        parts.append(f"Language: {chunk.language}")
        parts.append(f"Type: {chunk.chunk_type}")
        if chunk.name:
            parts.append(f"Name: {chunk.name}")
        if chunk.parent_name:
            parts.append(f"Parent: {chunk.parent_name}")
        if chunk.signature:
            parts.append(f"Signature: {chunk.signature}")
        if chunk.docstring:
            parts.append(f"Docstring: {chunk.docstring[:200]}")
        if chunk.decorators:
            parts.append(f"Decorators: {', '.join(chunk.decorators)}")
        parts.append("\n" + content)
        return "\n".join(parts)

    def _split_text(self, text: str) -> List[str]:
        """Split text into overlapping windows."""
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + self.MAX_CHARS, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = end - self.OVERLAP_CHARS
        return chunks
