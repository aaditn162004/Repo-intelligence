"""
Dependency graph builder using NetworkX.
Constructs file-level and symbol-level dependency relationships from parsed chunks.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
import structlog
import networkx as nx

from app.models.code_chunk import CodeChunk, ChunkType

logger = structlog.get_logger()


class DependencyGraph:
    """
    Builds and queries a directed dependency graph for a repository.

    Node types: file, module, class, function, method, external_lib
    Edge types: imports, calls, inherits, contains, depends_on
    """

    def __init__(self, repository_id: str):
        self.repository_id = repository_id
        self.graph: nx.DiGraph = nx.DiGraph()
        self._node_metadata: Dict[str, Dict[str, Any]] = {}

    def build_from_chunks(self, chunks: List[CodeChunk]) -> None:
        """Build the full dependency graph from a list of AST-parsed chunks."""
        # First pass: add all symbol nodes
        for chunk in chunks:
            self._add_chunk_node(chunk)

        # Second pass: add edges from import/dependency analysis
        for chunk in chunks:
            self._add_chunk_edges(chunk, chunks)

        # Add file-level containment edges
        self._add_file_containment(chunks)

        logger.info(
            "Dependency graph built",
            repository_id=self.repository_id,
            nodes=self.graph.number_of_nodes(),
            edges=self.graph.number_of_edges(),
        )

    def _add_chunk_node(self, chunk: CodeChunk) -> None:
        node_id = self._chunk_node_id(chunk)
        attrs = {
            "id": node_id,
            "chunk_id": chunk.id,
            "type": chunk.chunk_type,
            "name": chunk.name or Path(chunk.file_path).stem,
            "file_path": chunk.file_path,
            "language": chunk.language,
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
            "signature": chunk.signature or "",
            "docstring": (chunk.docstring or "")[:200],
        }
        self.graph.add_node(node_id, **attrs)
        self._node_metadata[node_id] = attrs

        # Also add a file node
        file_node = f"file::{chunk.file_path}"
        if not self.graph.has_node(file_node):
            self.graph.add_node(
                file_node,
                type="file",
                name=Path(chunk.file_path).name,
                file_path=chunk.file_path,
                language=chunk.language,
            )

    def _add_chunk_edges(self, chunk: CodeChunk, all_chunks: List[CodeChunk]) -> None:
        node_id = self._chunk_node_id(chunk)

        # Import edges: file → external_lib or internal_file
        if chunk.chunk_type == ChunkType.IMPORT:
            imported = self._resolve_import(chunk.content, chunk.file_path)
            for target in imported:
                if not self.graph.has_node(target):
                    self.graph.add_node(target, type="external_lib", name=target)
                self.graph.add_edge(
                    f"file::{chunk.file_path}", target, edge_type="imports", label="imports"
                )

        # Class inheritance
        if chunk.chunk_type == ChunkType.CLASS:
            parents = self._extract_base_classes(chunk.content, chunk.language)
            for parent in parents:
                parent_node = self._find_class_node(parent, all_chunks)
                target = parent_node if parent_node else f"external::{parent}"
                if not self.graph.has_node(target):
                    self.graph.add_node(target, type="external_class", name=parent)
                self.graph.add_edge(node_id, target, edge_type="inherits", label="inherits")

        # Method/function → parent class containment
        if chunk.parent_name:
            parent_node = self._find_node_by_name(chunk.parent_name, chunk.file_path)
            if parent_node:
                self.graph.add_edge(parent_node, node_id, edge_type="contains", label="contains")

        # Call dependencies
        for dep in chunk.dependencies:
            dep_node = self._find_node_by_name(dep, chunk.file_path)
            if dep_node and dep_node != node_id:
                self.graph.add_edge(node_id, dep_node, edge_type="calls", label="calls")

    def _add_file_containment(self, chunks: List[CodeChunk]) -> None:
        for chunk in chunks:
            if chunk.chunk_type not in (ChunkType.IMPORT, ChunkType.MODULE):
                file_node = f"file::{chunk.file_path}"
                chunk_node = self._chunk_node_id(chunk)
                if self.graph.has_node(file_node) and self.graph.has_node(chunk_node):
                    self.graph.add_edge(file_node, chunk_node, edge_type="contains", label="contains")

    def _resolve_import(self, import_text: str, current_file: str) -> List[str]:
        """Parse an import statement and return module names."""
        targets = []
        lines = import_text.strip().splitlines()
        for line in lines:
            line = line.strip()
            if line.startswith("import "):
                modules = line[7:].split(",")
                for m in modules:
                    name = m.strip().split(" as ")[0].strip().split(".")[0]
                    targets.append(f"lib::{name}")
            elif line.startswith("from "):
                parts = line.split(" import ")
                if parts:
                    mod = parts[0][5:].strip()
                    if mod.startswith("."):
                        targets.append(f"internal::{mod}")
                    else:
                        targets.append(f"lib::{mod.split('.')[0]}")
        return targets

    def _extract_base_classes(self, content: str, language: str) -> List[str]:
        import re
        if language == "python":
            m = re.search(r'class\s+\w+\s*\(([^)]+)\)', content)
            if m:
                return [b.strip() for b in m.group(1).split(",") if b.strip()]
        elif language in ("javascript", "typescript"):
            m = re.search(r'extends\s+(\w+)', content)
            if m:
                return [m.group(1)]
        return []

    def _find_class_node(self, class_name: str, all_chunks: List[CodeChunk]) -> Optional[str]:
        for chunk in all_chunks:
            if chunk.chunk_type == ChunkType.CLASS and chunk.name == class_name:
                return self._chunk_node_id(chunk)
        return None

    def _find_node_by_name(self, name: str, file_path: str) -> Optional[str]:
        for node_id, attrs in self.graph.nodes(data=True):
            if attrs.get("name") == name and attrs.get("file_path") == file_path:
                return node_id
        return None

    @staticmethod
    def _chunk_node_id(chunk: CodeChunk) -> str:
        name = chunk.name or "anonymous"
        return f"{chunk.chunk_type}::{chunk.file_path}::{name}::{chunk.start_line}"

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def get_dependents(self, node_id: str, depth: int = 2) -> List[str]:
        """Get nodes that depend on the given node (reverse edges)."""
        dependents = set()
        frontier = {node_id}
        for _ in range(depth):
            next_frontier = set()
            for n in frontier:
                for pred in self.graph.predecessors(n):
                    if pred not in dependents:
                        dependents.add(pred)
                        next_frontier.add(pred)
            frontier = next_frontier
        return list(dependents)

    def get_dependencies(self, node_id: str, depth: int = 2) -> List[str]:
        """Get nodes that the given node depends on."""
        deps = set()
        frontier = {node_id}
        for _ in range(depth):
            next_frontier = set()
            for n in frontier:
                for succ in self.graph.successors(n):
                    if succ not in deps:
                        deps.add(succ)
                        next_frontier.add(succ)
            frontier = next_frontier
        return list(deps)

    def find_path(self, source: str, target: str) -> Optional[List[str]]:
        try:
            return nx.shortest_path(self.graph, source, target)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None

    def get_affected_files(self, file_path: str) -> List[str]:
        """Files that would be affected if this file changes."""
        file_node = f"file::{file_path}"
        affected = set()
        if self.graph.has_node(file_node):
            for n in self.get_dependents(file_node, depth=3):
                attrs = self.graph.nodes.get(n, {})
                fp = attrs.get("file_path")
                if fp and fp != file_path:
                    affected.add(fp)
        return list(affected)

    def to_dict(self) -> Dict[str, Any]:
        """Serialise graph to JSON-safe dict for API response / cache."""
        nodes = []
        for node_id, attrs in self.graph.nodes(data=True):
            nodes.append({"id": node_id, **attrs})

        edges = []
        for src, dst, attrs in self.graph.edges(data=True):
            edges.append({"source": src, "target": dst, **attrs})

        return {
            "nodes": nodes,
            "edges": edges,
            "stats": {
                "node_count": self.graph.number_of_nodes(),
                "edge_count": self.graph.number_of_edges(),
            },
        }

    def get_subgraph(self, file_path: str, depth: int = 2) -> Dict[str, Any]:
        """Return a subgraph centred on a file — useful for visualisation."""
        center = f"file::{file_path}"
        if not self.graph.has_node(center):
            return {"nodes": [], "edges": []}

        relevant: Set[str] = {center}
        frontier = {center}
        for _ in range(depth):
            next_frontier = set()
            for n in frontier:
                for nb in list(self.graph.predecessors(n)) + list(self.graph.successors(n)):
                    if nb not in relevant:
                        relevant.add(nb)
                        next_frontier.add(nb)
            frontier = next_frontier

        sub = self.graph.subgraph(relevant)
        nodes = [{"id": n, **sub.nodes[n]} for n in sub.nodes]
        edges = [{"source": s, "target": t, **d} for s, t, d in sub.edges(data=True)]
        return {"nodes": nodes, "edges": edges}
