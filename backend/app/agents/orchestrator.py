"""
LangGraph multi-agent orchestration.

Agent graph:
  planner → retriever → [architect | documenter | impact_analyzer] → synthesizer → END

The planner classifies the query and routes to specialised agents.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, AsyncIterator
from typing_extensions import TypedDict, Annotated
import structlog

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_ollama import ChatOllama

from app.core.config import settings
from app.retrieval.hybrid_retriever import HybridRetriever
from app.retrieval.context_builder import ContextBuilder
from app.graph.knowledge_graph import KnowledgeGraphService
from app.models.query import QueryType, SourceReference

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# Graph state
# ---------------------------------------------------------------------------

class AgentState(TypedDict):
    repository_id: str
    repository_name: str
    question: str
    query_type: str
    sources: List[Dict[str, Any]]
    graph_context: Dict[str, Any]
    context_text: str
    architecture_summary: str
    agent_thoughts: List[str]
    final_answer: str
    reasoning_steps: List[str]
    error: Optional[str]


def _get_llm() -> ChatOllama:
    return ChatOllama(
        model=settings.LLM_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=settings.LLM_TEMPERATURE,
        num_predict=settings.LLM_MAX_TOKENS,
    )


# ---------------------------------------------------------------------------
# Agent node functions
# ---------------------------------------------------------------------------

def planner_node(state: AgentState) -> AgentState:
    """Classifies the query and refines it for downstream agents."""
    llm = _get_llm()
    question = state["question"]

    system = (
        "You are a query planner for a repository intelligence system.\n"
        "Classify the user's question into one of these types:\n"
        "  architecture, flow_trace, bug_localization, documentation, dependency_analysis, general\n"
        "Output ONLY the type name — nothing else."
    )
    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=question)])
    raw = response.content.strip().lower()

    type_map = {
        "architecture": QueryType.ARCHITECTURE,
        "flow_trace": QueryType.FLOW_TRACE,
        "flow": QueryType.FLOW_TRACE,
        "bug": QueryType.BUG_LOCALIZATION,
        "bug_localization": QueryType.BUG_LOCALIZATION,
        "documentation": QueryType.DOCUMENTATION,
        "doc": QueryType.DOCUMENTATION,
        "dependency": QueryType.DEPENDENCY_ANALYSIS,
        "dependency_analysis": QueryType.DEPENDENCY_ANALYSIS,
    }
    query_type = type_map.get(raw, QueryType.GENERAL)

    new_state = dict(state)
    new_state["query_type"] = query_type.value
    new_state["reasoning_steps"] = [f"Query classified as: **{query_type.value}**"]
    logger.info("Query classified", query_type=query_type.value)
    return AgentState(**new_state)


def retriever_node(state: AgentState) -> AgentState:
    """Not actually async — retriever must be called with inject_retriever."""
    # This is a placeholder; real injection happens in RepoAgentGraph.
    new_state = dict(state)
    new_state["reasoning_steps"] = list(state.get("reasoning_steps", [])) + [
        "Retrieved relevant code chunks via semantic + graph search."
    ]
    return AgentState(**new_state)


def architect_node(state: AgentState) -> AgentState:
    """Enriches context with architecture analysis."""
    llm = _get_llm()
    system = (
        "You are a software architect specialising in codebase analysis.\n"
        "Based on the provided code context, produce a concise architecture summary.\n"
        "Identify: key components, design patterns, data flow, service boundaries.\n"
        "Be specific — cite file paths and function names."
    )
    prompt = f"Architecture question: {state['question']}\n\n{state['context_text']}"
    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])

    new_state = dict(state)
    new_state["architecture_summary"] = response.content
    new_state["reasoning_steps"] = list(state.get("reasoning_steps", [])) + [
        "Architecture analysis complete."
    ]
    return AgentState(**new_state)


def documenter_node(state: AgentState) -> AgentState:
    """Generates documentation from retrieved code."""
    llm = _get_llm()
    system = (
        "You are a technical writer generating precise developer documentation.\n"
        "Generate well-structured Markdown documentation for the code provided.\n"
        "Include: purpose, parameters, return values, usage examples, edge cases."
    )
    prompt = f"Document this: {state['question']}\n\n{state['context_text']}"
    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])

    new_state = dict(state)
    new_state["architecture_summary"] = response.content
    new_state["reasoning_steps"] = list(state.get("reasoning_steps", [])) + [
        "Documentation generated."
    ]
    return AgentState(**new_state)


def impact_analyzer_node(state: AgentState) -> AgentState:
    """Analyses dependency impact for a proposed change."""
    llm = _get_llm()
    system = (
        "You are an impact analysis expert for software repositories.\n"
        "Given the dependency context and question, identify:\n"
        "  1. Directly affected modules\n"
        "  2. Transitively affected services\n"
        "  3. Risk level (low/medium/high)\n"
        "  4. Recommended testing strategy\n"
        "Be specific — cite file paths."
    )
    graph_summary = ""
    if state.get("graph_context"):
        affected = state["graph_context"].get("affected_files", [])
        graph_summary = f"\nAffected files from graph analysis: {', '.join(affected[:8])}"

    prompt = f"Impact question: {state['question']}\n{graph_summary}\n\n{state['context_text']}"
    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])

    new_state = dict(state)
    new_state["architecture_summary"] = response.content
    new_state["reasoning_steps"] = list(state.get("reasoning_steps", [])) + [
        "Impact analysis complete."
    ]
    return AgentState(**new_state)


def synthesizer_node(state: AgentState) -> AgentState:
    """Produces the final, comprehensive answer."""
    llm = _get_llm()
    context_builder = ContextBuilder()
    repo_name = state.get("repository_name", "the repository")
    query_type = state.get("query_type", "general")

    system = context_builder.build_system_prompt(repo_name, query_type)

    specialist_output = state.get("architecture_summary", "")
    prompt_parts = [f"Question: {state['question']}\n"]
    if specialist_output:
        prompt_parts.append(f"### Specialist Analysis:\n{specialist_output}\n\n")
    prompt_parts.append(state["context_text"])
    prompt = "\n".join(prompt_parts)

    response = llm.invoke([SystemMessage(content=system), HumanMessage(content=prompt)])

    new_state = dict(state)
    new_state["final_answer"] = response.content
    new_state["reasoning_steps"] = list(state.get("reasoning_steps", [])) + [
        "Final answer synthesised."
    ]
    return AgentState(**new_state)


# ---------------------------------------------------------------------------
# Routing logic
# ---------------------------------------------------------------------------

def route_after_planner(state: AgentState) -> str:
    qt = state.get("query_type", "general")
    if qt == QueryType.ARCHITECTURE.value:
        return "architect"
    if qt == QueryType.DOCUMENTATION.value:
        return "documenter"
    if qt == QueryType.DEPENDENCY_ANALYSIS.value:
        return "impact_analyzer"
    return "synthesizer"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

class RepoAgentGraph:
    """Builds and runs the LangGraph agent pipeline."""

    def __init__(
        self,
        retriever: HybridRetriever,
        knowledge_graph: KnowledgeGraphService,
    ):
        self._retriever = retriever
        self._kg = knowledge_graph
        self._graph = self._build_graph()

    def _build_graph(self) -> Any:
        workflow = StateGraph(AgentState)
        workflow.add_node("planner", planner_node)
        workflow.add_node("architect", architect_node)
        workflow.add_node("documenter", documenter_node)
        workflow.add_node("impact_analyzer", impact_analyzer_node)
        workflow.add_node("synthesizer", synthesizer_node)

        workflow.set_entry_point("planner")
        workflow.add_conditional_edges(
            "planner",
            route_after_planner,
            {
                "architect": "architect",
                "documenter": "documenter",
                "impact_analyzer": "impact_analyzer",
                "synthesizer": "synthesizer",
            },
        )
        workflow.add_edge("architect", "synthesizer")
        workflow.add_edge("documenter", "synthesizer")
        workflow.add_edge("impact_analyzer", "synthesizer")
        workflow.add_edge("synthesizer", END)

        return workflow.compile()

    async def run(
        self,
        repository_id: str,
        repository_name: str,
        question: str,
        top_k: int = 10,
    ) -> Dict[str, Any]:
        # Step 1: retrieval (async, outside graph)
        retrieval_result = await self._retriever.retrieve(
            repository_id=repository_id,
            query=question,
            top_k=top_k,
        )

        # Step 2: build context text
        context_builder = ContextBuilder()
        sources: List[SourceReference] = retrieval_result["sources"]
        graph_context = retrieval_result.get("graph_context", {})
        context_text = context_builder.build_context(sources, graph_context)

        initial_state = AgentState(
            repository_id=repository_id,
            repository_name=repository_name,
            question=question,
            query_type="general",
            sources=[s.model_dump() for s in sources],
            graph_context=graph_context,
            context_text=context_text,
            architecture_summary="",
            agent_thoughts=[],
            final_answer="",
            reasoning_steps=[],
            error=None,
        )

        # Step 3: run LangGraph pipeline
        final_state = await self._graph.ainvoke(initial_state)

        return {
            "answer": final_state["final_answer"],
            "query_type": final_state["query_type"],
            "sources": sources,
            "graph_context": graph_context,
            "reasoning_steps": final_state["reasoning_steps"],
        }

    async def stream(
        self,
        repository_id: str,
        repository_name: str,
        question: str,
        top_k: int = 10,
    ) -> AsyncIterator[str]:
        """Yield tokens as they are produced by the LLM."""
        import httpx

        # Retrieve context first
        retrieval_result = await self._retriever.retrieve(
            repository_id=repository_id,
            query=question,
            top_k=top_k,
        )
        sources: List[SourceReference] = retrieval_result["sources"]
        graph_context = retrieval_result.get("graph_context", {})
        context_builder = ContextBuilder()
        context_text = context_builder.build_context(sources, graph_context)

        # Classify query type (fast non-streaming call)
        llm = _get_llm()
        class_response = await llm.ainvoke([
            SystemMessage(content=(
                "Classify the user's question into one of: "
                "architecture, flow_trace, bug_localization, documentation, dependency_analysis, general. "
                "Output ONLY the type."
            )),
            HumanMessage(content=question),
        ])
        query_type = class_response.content.strip().lower()

        # Yield metadata token
        yield json.dumps({
            "type": "metadata",
            "query_type": query_type,
            "sources": [s.model_dump() for s in sources[:5]],
            "graph_context": graph_context,
        }) + "\n"

        # Stream answer directly via Ollama REST API (bypasses langchain buffering)
        system = context_builder.build_system_prompt(repository_name, query_type)
        prompt = f"Question: {question}\n\n{context_text}"

        async with httpx.AsyncClient(timeout=300.0) as client:
            async with client.stream(
                "POST",
                f"{settings.OLLAMA_BASE_URL}/api/chat",
                json={
                    "model": settings.LLM_MODEL,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": prompt},
                    ],
                    "stream": True,
                    "options": {
                        "temperature": settings.LLM_TEMPERATURE,
                        "num_predict": settings.LLM_MAX_TOKENS,
                    },
                },
            ) as response:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            yield json.dumps({"type": "token", "content": content}) + "\n"
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue

        yield json.dumps({"type": "done"}) + "\n"
