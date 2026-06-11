"""
Builds an LLM-ready context string from retrieval results.
"""
from __future__ import annotations

from typing import List, Dict, Any
from app.models.query import SourceReference


class ContextBuilder:

    def build_context(
        self,
        sources: List[SourceReference],
        graph_context: Dict[str, Any],
        max_chars: int = 8000,
    ) -> str:
        parts = ["## Retrieved Code Context\n"]
        used = len(parts[0])

        for i, src in enumerate(sources, 1):
            block = (
                f"### Source {i}: {src.file_path} (lines {src.start_line}-{src.end_line})\n"
                f"**Type:** {src.chunk_type}"
                + (f" | **Name:** `{src.name}`" if src.name else "")
                + f" | **Relevance:** {src.relevance_score:.2f}\n\n"
                f"```\n{src.snippet}\n```\n\n"
            )
            if used + len(block) > max_chars:
                break
            parts.append(block)
            used += len(block)

        if graph_context:
            affected = graph_context.get("affected_files", [])
            related = graph_context.get("related_files", [])
            if affected or related:
                graph_block = "\n## Graph Context\n"
                if affected:
                    graph_block += f"**Affected files:** {', '.join(affected[:5])}\n"
                if related:
                    graph_block += f"**Related files:** {', '.join(related[:5])}\n"
                parts.append(graph_block)

        return "".join(parts)

    def build_system_prompt(self, repository_name: str, query_type: str) -> str:
        base = (
            f"You are an expert software engineer analysing the '{repository_name}' codebase.\n"
            "You have been given relevant code context retrieved from a semantic code search.\n"
            "Answer the developer's question accurately and concisely, citing specific files and line numbers.\n"
            "When tracing flows, describe each step with the responsible function and file.\n"
            "Format your answer in Markdown.\n"
        )
        type_guidance = {
            "architecture": "Focus on high-level design patterns, component relationships, and data flow.",
            "flow_trace": "Trace the complete execution path step-by-step, function-by-function.",
            "bug_localization": "Identify the most likely locations for the bug, explain why, and suggest fixes.",
            "documentation": "Generate clear, well-structured documentation with examples.",
            "dependency_analysis": "Map all dependencies, highlight circular dependencies and breaking change risk.",
        }
        guidance = type_guidance.get(query_type, "")
        return base + (f"\n{guidance}" if guidance else "")
