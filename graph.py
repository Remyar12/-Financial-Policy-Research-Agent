"""
LangGraph Workflow Definition for Financial Policy Research Agent.
Constructs the streamlined 5-node StateGraph for fast execution.
"""

import logging
from langgraph.graph import StateGraph, START, END

from state import AgentState
from nodes import (
    website_router_node,
    query_generator_node,
    duckduckgo_search_node,
    content_extractor_node,
    answer_generator_node,
)

logger = logging.getLogger("LangGraphWorkflow")


def create_financial_research_graph() -> StateGraph:
    """
    Assembles and returns the compiled 5-node LangGraph workflow.
    Executes in a streamlined linear pipeline:
    START -> website_router -> query_generator -> duckduckgo_search -> content_extractor -> answer_generator -> END
    """
    workflow = StateGraph(AgentState)

    # 1. Register the 5 active nodes
    workflow.add_node("website_router", website_router_node)
    workflow.add_node("query_generator", query_generator_node)
    workflow.add_node("duckduckgo_search", duckduckgo_search_node)
    workflow.add_node("content_extractor", content_extractor_node)
    workflow.add_node("answer_generator", answer_generator_node)

    # 2. Linear pipeline
    workflow.add_edge(START, "website_router")
    workflow.add_edge("website_router", "query_generator")
    workflow.add_edge("query_generator", "duckduckgo_search")
    workflow.add_edge("duckduckgo_search", "content_extractor")
    workflow.add_edge("content_extractor", "answer_generator")
    workflow.add_edge("answer_generator", END)

    return workflow.compile()


# Pre-compiled graph instance
financial_research_agent = create_financial_research_graph()
