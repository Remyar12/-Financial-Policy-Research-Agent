"""
State definition and typed schemas for the Financial Policy Research Agent.
"""

from typing import List, Dict, Any
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """
    State maintained across the 5 nodes of the LangGraph workflow.
    """
    # Inputs
    user_question: str
    trusted_websites: List[str]

    # Node 1: Website Router
    selected_website: str
    routing_reasoning: str
    is_out_of_scope: bool

    # Node 2: Query Generator
    search_query: str
    search_queries_history: List[str]

    # Node 3: DuckDuckGo Search
    search_results: List[Dict[str, str]]

    # Node 4: Content Extractor
    extracted_documents: List[Dict[str, Any]]

    # Node 5: Answer Generator
    final_answer: str
    sources_used: List[Dict[str, str]]
