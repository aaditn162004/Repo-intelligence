"""
Tree-sitter-based AST parser for extracting structured code elements.
Supports Python, JavaScript, TypeScript, Java, Go, and more.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import structlog

from app.models.code_chunk import ChunkType, CodeChunk

logger = structlog.get_logger()

try:
    from tree_sitter_languages import get_language
    from tree_sitter_languages import get_parser as get_ts_parser

    def _make_parser(lang: str):
        return get_ts_parser(lang)

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    logger.warning("tree_sitter_languages not available — falling back to regex parser")


# ---------------------------------------------------------------------------
# Query definitions per language (Tree-sitter S-expression queries)
# ---------------------------------------------------------------------------

PYTHON_QUERIES = {
    "functions": """
        (function_definition
          name: (identifier) @name
          parameters: (parameters) @params
          body: (block) @body) @func
    """,
    "classes": """
        (class_definition
          name: (identifier) @name
          body: (block) @body) @class
    """,
    "imports": """
        [
          (import_statement) @import
          (import_from_statement) @import
        ]
    """,
    "decorators": """
        (decorated_definition
          (decorator) @decorator)
    """,
}

JS_TS_QUERIES = {
    "functions": """
        [
          (function_declaration
            name: (identifier) @name) @func
          (arrow_function) @func
          (method_definition
            name: (property_identifier) @name) @func
        ]
    """,
    "classes": """
        (class_declaration
          name: (identifier) @name) @class
    """,
    "imports": """
        [
          (import_statement) @import
          (import_declaration) @import
        ]
    """,
    "exports": """
        (export_statement) @export
    """,
}

JAVA_QUERIES = {
    "classes": """
        (class_declaration
          name: (identifier) @name) @class
    """,
    "methods": """
        (method_declaration
          name: (identifier) @name) @method
    """,
    "imports": """
        (import_declaration) @import
    """,
}

GO_QUERIES = {
    "functions": """
        (function_declaration
          name: (identifier) @name) @func
    """,
    "methods": """
        (method_declaration
          name: (field_identifier) @name) @method
    """,
    "types": """
        (type_declaration) @type
    """,
    "imports": """
        (import_declaration) @import
    """,
}


# ---------------------------------------------------------------------------
# Main parser class
# ---------------------------------------------------------------------------


class ASTParser:
    """Parses source files using Tree-sitter to extract structured code elements."""

    def __init__(self):
        self._parsers: Dict[str, Any] = {}
        self._available = TREE_SITTER_AVAILABLE

    def _get_parser(self, language: str):
        if language not in self._parsers and self._available:
            try:
                self._parsers[language] = _make_parser(language)
            except Exception as e:
                logger.warning("Failed to load parser", language=language, error=str(e))
                self._parsers[language] = None
        return self._parsers.get(language)

    def parse_file(
        self, file_path: str, content: str, language: str, repository_id: str
    ) -> List[CodeChunk]:
        if self._available:
            try:
                return self._parse_with_tree_sitter(file_path, content, language, repository_id)
            except Exception as e:
                logger.warning("Tree-sitter parse failed, falling back to regex", error=str(e))
        return self._parse_with_regex(file_path, content, language, repository_id)

    # ------------------------------------------------------------------
    # Tree-sitter parsing
    # ------------------------------------------------------------------

    def _parse_with_tree_sitter(
        self, file_path: str, content: str, language: str, repository_id: str
    ) -> List[CodeChunk]:
        parser = self._get_parser(language)
        if parser is None:
            return self._parse_with_regex(file_path, content, language, repository_id)

        tree = parser.parse(content.encode("utf-8"))
        chunks: List[CodeChunk] = []

        if language == "python":
            chunks.extend(self._extract_python_chunks(tree, content, file_path, repository_id))
        elif language in ("javascript", "typescript"):
            chunks.extend(
                self._extract_js_ts_chunks(tree, content, file_path, repository_id, language)
            )
        elif language == "java":
            chunks.extend(self._extract_java_chunks(tree, content, file_path, repository_id))
        elif language == "go":
            chunks.extend(self._extract_go_chunks(tree, content, file_path, repository_id))
        else:
            chunks.extend(
                self._extract_generic_chunks(tree, content, file_path, repository_id, language)
            )

        # Always add a module-level chunk for the whole file
        if chunks:
            module_chunk = self._make_module_chunk(file_path, content, language, repository_id)
            chunks.insert(0, module_chunk)

        return chunks

    def _node_text(self, node, content_bytes: bytes) -> str:
        return content_bytes[node.start_byte : node.end_byte].decode("utf-8", errors="replace")

    def _extract_python_chunks(
        self, tree, content: str, file_path: str, repository_id: str
    ) -> List[CodeChunk]:
        chunks = []
        content_bytes = content.encode("utf-8")
        lines = content.splitlines()

        def walk(node, parent_name: Optional[str] = None):
            if node.type == "function_definition":
                name_node = node.child_by_field_name("name")
                name = self._node_text(name_node, content_bytes) if name_node else "anonymous"
                body_text = self._node_text(node, content_bytes)
                docstring = self._extract_python_docstring(node, content_bytes)
                decorators = self._extract_python_decorators(node, content, lines)
                params_node = node.child_by_field_name("parameters")
                signature = f"def {name}{self._node_text(params_node, content_bytes) if params_node else '()'}"

                chunk_type = ChunkType.METHOD if parent_name else ChunkType.FUNCTION
                chunks.append(
                    CodeChunk(
                        repository_id=repository_id,
                        file_path=file_path,
                        language="python",
                        chunk_type=chunk_type,
                        name=name,
                        content=body_text,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        signature=signature,
                        docstring=docstring,
                        decorators=decorators,
                        parent_name=parent_name,
                        dependencies=self._extract_python_calls(body_text),
                    )
                )

            elif node.type == "class_definition":
                name_node = node.child_by_field_name("name")
                name = self._node_text(name_node, content_bytes) if name_node else "AnonymousClass"
                class_text = self._node_text(node, content_bytes)
                docstring = self._extract_python_docstring(node, content_bytes)
                decorators = self._extract_python_decorators(node, content, lines)
                chunks.append(
                    CodeChunk(
                        repository_id=repository_id,
                        file_path=file_path,
                        language="python",
                        chunk_type=ChunkType.CLASS,
                        name=name,
                        content=class_text,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        docstring=docstring,
                        decorators=decorators,
                    )
                )
                for child in node.children:
                    walk(child, parent_name=name)
                return

            elif node.type in ("import_statement", "import_from_statement"):
                import_text = self._node_text(node, content_bytes)
                chunks.append(
                    CodeChunk(
                        repository_id=repository_id,
                        file_path=file_path,
                        language="python",
                        chunk_type=ChunkType.IMPORT,
                        content=import_text,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                    )
                )

            for child in node.children:
                walk(child, parent_name=parent_name)

        walk(tree.root_node)
        return chunks

    def _extract_python_docstring(self, node, content_bytes: bytes) -> Optional[str]:
        for child in node.children:
            if child.type == "block":
                for stmt in child.children:
                    if stmt.type == "expression_statement":
                        for expr in stmt.children:
                            if expr.type in ("string", "concatenated_string"):
                                text = self._node_text(expr, content_bytes)
                                return text.strip("\"'").strip()
        return None

    def _extract_python_decorators(self, node, content: str, lines: List[str]) -> List[str]:
        decorators = []
        start_line = node.start_point[0]
        # Check lines above for decorators
        i = start_line - 1
        while i >= 0 and lines[i].strip().startswith("@"):
            decorators.insert(0, lines[i].strip())
            i -= 1
        return decorators

    def _extract_python_calls(self, code: str) -> List[str]:
        pattern = re.compile(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(")
        calls = list(set(pattern.findall(code)))
        builtins = {
            "print",
            "len",
            "range",
            "str",
            "int",
            "list",
            "dict",
            "set",
            "tuple",
            "isinstance",
            "hasattr",
            "getattr",
            "setattr",
            "type",
            "super",
            "enumerate",
        }
        return [c for c in calls if c not in builtins][:20]

    def _extract_js_ts_chunks(
        self, tree, content: str, file_path: str, repository_id: str, language: str
    ) -> List[CodeChunk]:
        chunks = []
        content_bytes = content.encode("utf-8")

        def walk(node, parent_name: Optional[str] = None):
            if node.type in ("function_declaration", "function"):
                name_node = node.child_by_field_name("name")
                name = self._node_text(name_node, content_bytes) if name_node else "anonymous"
                text = self._node_text(node, content_bytes)
                chunks.append(
                    CodeChunk(
                        repository_id=repository_id,
                        file_path=file_path,
                        language=language,
                        chunk_type=ChunkType.FUNCTION,
                        name=name,
                        content=text,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        parent_name=parent_name,
                    )
                )

            elif node.type in ("class_declaration", "class"):
                name_node = node.child_by_field_name("name")
                name = self._node_text(name_node, content_bytes) if name_node else "AnonymousClass"
                text = self._node_text(node, content_bytes)
                chunks.append(
                    CodeChunk(
                        repository_id=repository_id,
                        file_path=file_path,
                        language=language,
                        chunk_type=ChunkType.CLASS,
                        name=name,
                        content=text,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                    )
                )
                for child in node.children:
                    walk(child, parent_name=name)
                return

            elif node.type == "method_definition":
                name_node = node.child_by_field_name("name")
                name = self._node_text(name_node, content_bytes) if name_node else "method"
                text = self._node_text(node, content_bytes)
                chunks.append(
                    CodeChunk(
                        repository_id=repository_id,
                        file_path=file_path,
                        language=language,
                        chunk_type=ChunkType.METHOD,
                        name=name,
                        content=text,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        parent_name=parent_name,
                    )
                )

            elif node.type in ("import_statement", "import_declaration"):
                text = self._node_text(node, content_bytes)
                chunks.append(
                    CodeChunk(
                        repository_id=repository_id,
                        file_path=file_path,
                        language=language,
                        chunk_type=ChunkType.IMPORT,
                        content=text,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                    )
                )

            for child in node.children:
                walk(child, parent_name=parent_name)

        walk(tree.root_node)
        return chunks

    def _extract_java_chunks(
        self, tree, content: str, file_path: str, repository_id: str
    ) -> List[CodeChunk]:
        chunks = []
        content_bytes = content.encode("utf-8")

        def walk(node, parent_name: Optional[str] = None):
            if node.type == "class_declaration":
                name_node = node.child_by_field_name("name")
                name = self._node_text(name_node, content_bytes) if name_node else "Class"
                text = self._node_text(node, content_bytes)
                chunks.append(
                    CodeChunk(
                        repository_id=repository_id,
                        file_path=file_path,
                        language="java",
                        chunk_type=ChunkType.CLASS,
                        name=name,
                        content=text,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                    )
                )
                for child in node.children:
                    walk(child, parent_name=name)
                return

            elif node.type == "method_declaration":
                name_node = node.child_by_field_name("name")
                name = self._node_text(name_node, content_bytes) if name_node else "method"
                text = self._node_text(node, content_bytes)
                chunks.append(
                    CodeChunk(
                        repository_id=repository_id,
                        file_path=file_path,
                        language="java",
                        chunk_type=ChunkType.METHOD,
                        name=name,
                        content=text,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        parent_name=parent_name,
                    )
                )

            elif node.type == "import_declaration":
                text = self._node_text(node, content_bytes)
                chunks.append(
                    CodeChunk(
                        repository_id=repository_id,
                        file_path=file_path,
                        language="java",
                        chunk_type=ChunkType.IMPORT,
                        content=text,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                    )
                )

            for child in node.children:
                walk(child, parent_name=parent_name)

        walk(tree.root_node)
        return chunks

    def _extract_go_chunks(
        self, tree, content: str, file_path: str, repository_id: str
    ) -> List[CodeChunk]:
        chunks = []
        content_bytes = content.encode("utf-8")

        def walk(node, parent_name: Optional[str] = None):
            if node.type == "function_declaration":
                name_node = node.child_by_field_name("name")
                name = self._node_text(name_node, content_bytes) if name_node else "func"
                text = self._node_text(node, content_bytes)
                chunks.append(
                    CodeChunk(
                        repository_id=repository_id,
                        file_path=file_path,
                        language="go",
                        chunk_type=ChunkType.FUNCTION,
                        name=name,
                        content=text,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                    )
                )

            elif node.type == "method_declaration":
                name_node = node.child_by_field_name("name")
                name = self._node_text(name_node, content_bytes) if name_node else "method"
                text = self._node_text(node, content_bytes)
                chunks.append(
                    CodeChunk(
                        repository_id=repository_id,
                        file_path=file_path,
                        language="go",
                        chunk_type=ChunkType.METHOD,
                        name=name,
                        content=text,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                        parent_name=parent_name,
                    )
                )

            elif node.type == "type_declaration":
                text = self._node_text(node, content_bytes)
                chunks.append(
                    CodeChunk(
                        repository_id=repository_id,
                        file_path=file_path,
                        language="go",
                        chunk_type=ChunkType.TYPE,
                        content=text,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                    )
                )

            elif node.type == "import_declaration":
                text = self._node_text(node, content_bytes)
                chunks.append(
                    CodeChunk(
                        repository_id=repository_id,
                        file_path=file_path,
                        language="go",
                        chunk_type=ChunkType.IMPORT,
                        content=text,
                        start_line=node.start_point[0] + 1,
                        end_line=node.end_point[0] + 1,
                    )
                )

            for child in node.children:
                walk(child, parent_name=parent_name)

        walk(tree.root_node)
        return chunks

    def _extract_generic_chunks(
        self, tree, content: str, file_path: str, repository_id: str, language: str
    ) -> List[CodeChunk]:
        return [self._make_module_chunk(file_path, content, language, repository_id)]

    # ------------------------------------------------------------------
    # Regex fallback parser
    # ------------------------------------------------------------------

    def _parse_with_regex(
        self, file_path: str, content: str, language: str, repository_id: str
    ) -> List[CodeChunk]:
        chunks = [self._make_module_chunk(file_path, content, language, repository_id)]
        lines = content.splitlines()

        if language == "python":
            chunks.extend(self._regex_python(lines, file_path, repository_id))
        elif language in ("javascript", "typescript"):
            chunks.extend(self._regex_js(lines, file_path, repository_id, language))

        return chunks

    def _regex_python(
        self, lines: List[str], file_path: str, repository_id: str
    ) -> List[CodeChunk]:
        chunks = []
        func_re = re.compile(r"^(\s*)(async\s+)?def\s+(\w+)\s*\(")

        i = 0
        while i < len(lines):
            m = func_re.match(lines[i])
            if m:
                name = m.group(3)
                indent = len(m.group(1))
                start = i
                i += 1
                while i < len(lines):
                    stripped = lines[i]
                    if stripped and not stripped[0].isspace() and indent == 0:
                        break
                    if (
                        stripped
                        and len(stripped) - len(stripped.lstrip()) <= indent
                        and i > start + 1
                    ):
                        break
                    i += 1
                content = "\n".join(lines[start:i])
                chunks.append(
                    CodeChunk(
                        repository_id=repository_id,
                        file_path=file_path,
                        language="python",
                        chunk_type=ChunkType.FUNCTION,
                        name=name,
                        content=content,
                        start_line=start + 1,
                        end_line=i,
                    )
                )
                continue
            i += 1

        return chunks

    def _regex_js(
        self, lines: List[str], file_path: str, repository_id: str, language: str
    ) -> List[CodeChunk]:
        chunks = []
        func_re = re.compile(
            r"(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>)"
        )

        for i, line in enumerate(lines):
            m = func_re.search(line)
            if m:
                name = m.group(1) or m.group(2) or "anonymous"
                chunks.append(
                    CodeChunk(
                        repository_id=repository_id,
                        file_path=file_path,
                        language=language,
                        chunk_type=ChunkType.FUNCTION,
                        name=name,
                        content=line,
                        start_line=i + 1,
                        end_line=i + 1,
                    )
                )

        return chunks

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_module_chunk(
        self, file_path: str, content: str, language: str, repository_id: str
    ) -> CodeChunk:
        lines = content.splitlines()
        return CodeChunk(
            repository_id=repository_id,
            file_path=file_path,
            language=language,
            chunk_type=ChunkType.MODULE,
            name=Path(file_path).stem,
            content=content[:2000] if len(content) > 2000 else content,
            start_line=1,
            end_line=len(lines),
        )
