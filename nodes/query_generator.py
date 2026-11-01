"""
Node 2: Query Generator (LLM)
Generates targeted DuckDuckGo search queries strictly constrained with the `site:<domain>` operator.
"""

import json
import logging
import re
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from config import get_llm, normalize_domain
from state import AgentState

logger = logging.getLogger("Node2_QueryGenerator")


def query_generator_node(state: AgentState) -> Dict[str, Any]:
    """
    Generates an optimized search query constrained to the selected trusted domain.
    """
    user_question = state.get("user_question", "")
    selected_website = state.get("selected_website", "")
    history = state.get("search_queries_history", [])
    is_out_of_scope = state.get("is_out_of_scope", False)
    
    clean_domain = normalize_domain(selected_website)
    
    if is_out_of_scope or clean_domain in ("none", ""):
        logger.info("Query Generator: Skipping search query generation as topic is out of scope.")
        return {
            "search_query": "",
            "search_queries_history": history
        }
    
    logger.info(f"Query Generator: Generating search query for domain '{clean_domain}'")

    system_prompt = (
        "You are an expert Search Query Generator for Financial Regulations & Policy.\n"
        "Your task is to craft an effective, targeted search query for DuckDuckGo.\n\n"
        f"MANDATORY REQUIREMENT: The query MUST begin with 'site:{clean_domain}' followed by 3-6 precise keywords.\n"
        "Do NOT include punctuation, quotes, or boolean operators.\n"
        "Focus on exact regulatory terminology, policy names, or master circular terms.\n\n"
        "Output ONLY a valid JSON object with:\n"
        "- \"search_query\": The complete query string including site: prefix.\n"
        "- \"rationale\": Why this formulation is chosen.\n"
    )

    user_prompt = (
        f"User Question: {user_question}\n"
        f"Target Domain: {clean_domain}\n\n"
        "Generate the search query JSON."
    )

    llm = get_llm(temperature=0.2)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    default_query = f"site:{clean_domain} {user_question}".strip()

    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            generated_query = data.get("search_query", "").strip()
            if not generated_query.startswith(f"site:{clean_domain}"):
                # Enforce site prefix
                words = [w for w in generated_query.split() if not w.startswith("site:")]
                generated_query = f"site:{clean_domain} {' '.join(words)}"
        else:
            generated_query = default_query
            
    except Exception as e:
        logger.warning(f"Query Generator error: {e}. Using default query.")
        generated_query = default_query

    updated_history = list(history) + [generated_query]

    logger.info(f"Generated Search Query: '{generated_query}'")
    return {
        "search_query": generated_query,
        "search_queries_history": updated_history,
    }
