"""
Node 3: DuckDuckGo Search (Tool Node)
Executes DuckDuckGo search restricted strictly to the selected trusted domain.
"""

import logging
from typing import Dict, Any
from config import MAX_SEARCH_RESULTS, normalize_domain
from state import AgentState
from tools.search_tool import search_duckduckgo_restricted

logger = logging.getLogger("Node3_DuckDuckGoSearch")


def duckduckgo_search_node(state: AgentState) -> Dict[str, Any]:
    """
    Runs the DuckDuckGo search tool with the generated query.
    """
    search_query = state.get("search_query", "")
    selected_website = state.get("selected_website", "")
    is_out_of_scope = state.get("is_out_of_scope", False)
    
    clean_domain = normalize_domain(selected_website)
    
    if is_out_of_scope or not search_query or clean_domain in ("none", ""):
        logger.info("DuckDuckGo Search: Skipping search as topic is out of scope or query is empty.")
        return {"search_results": []}

    logger.info(f"DuckDuckGo Search: Running query '{search_query}' on domain '{clean_domain}'")

    results = search_duckduckgo_restricted(
        query=search_query,
        target_domain=clean_domain,
        max_results=MAX_SEARCH_RESULTS
    )

    logger.info(f"Search retrieved {len(results)} search results.")
    return {
        "search_results": results
    }
