"""
Node 1: Website Router (LLM)
Selects the most relevant website strictly from the user-provided trusted website list.
Never selects any domain outside the trusted list.
"""

import json
import logging
import re
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from config import get_llm, normalize_domain
from state import AgentState

logger = logging.getLogger("Node1_WebsiteRouter")


def website_router_node(state: AgentState) -> Dict[str, Any]:
    """
    Routes the query to the single best domain from the user-provided trusted websites.
    """
    user_question = state.get("user_question", "")
    trusted_websites = state.get("trusted_websites", [])
    
    # Normalize trusted websites
    normalized_trusted = [normalize_domain(site) for site in trusted_websites if normalize_domain(site)]
    
    if not normalized_trusted:
        raise ValueError("Cannot route query: No trusted websites provided in state.")

    logger.info(f"Website Router: Selecting best domain among -> {normalized_trusted}")

    # Fast heuristic routing to save LLM inference time
    question_lower = user_question.lower()
    
    # 1. Check known out-of-scope financial & non-financial topics (e.g. RBI repo rate, SEBI, crypto, general AI)
    out_of_scope_keywords = [
        "repo rate", "reverse repo", "rbi", "reserve bank", "monetary policy", "cash reserve ratio", "crr", "slr",
        "sebi", "stock market", "demat", "mutual fund", "sensex", "nifty", "ipo allotment", "crypto", "bitcoin",
        "prompting", "zero-shot", "few-shot", "python", "javascript", "cricket", "weather", "recipe", "movie"
    ]
    if any(k in question_lower for k in out_of_scope_keywords):
        logger.info("Question detected as out-of-scope for IRDAI and PFRDA.")
        return {
            "selected_website": "none",
            "routing_reasoning": "Out of scope: Question does not pertain to IRDAI (Insurance) or PFRDA (Pensions).",
            "is_out_of_scope": True
        }

    if any(k in question_lower for k in ["pfrda", "pension", "nps", "pran", "apy", "superannuation", "retirement", "cra", "tier 1", "tier 2", "atal pension"]) and "pfrda.org.in" in normalized_trusted:
        logger.info("Fast router matched 'pfrda.org.in'")
        return {
            "selected_website": "pfrda.org.in",
            "routing_reasoning": "Direct match: Question relates to Pension / NPS under PFRDA regulatory domain.",
            "is_out_of_scope": False
        }
    if any(k in question_lower for k in ["irdai", "insurance", "insurer", "policyholder", "tpa", "premium", "claim settlement", "surrender value", "ulip", "motor policy", "health insurance", "life insurance", "annuity", "actuary"]) and "irdai.gov.in" in normalized_trusted:
        logger.info("Fast router matched 'irdai.gov.in'")
        return {
            "selected_website": "irdai.gov.in",
            "routing_reasoning": "Direct match: Question relates to Insurance under IRDAI regulatory domain.",
            "is_out_of_scope": False
        }

    system_prompt = (
        "You are a Financial Domain Router for two specific Indian regulatory bodies:\n"
        "1. irdai.gov.in (Insurance Regulatory and Development Authority - Insurance policies, claims, surrender values, insurers)\n"
        "2. pfrda.org.in (Pension Fund Regulatory and Development Authority - NPS, APY, pensions, retirement funds)\n\n"
        "Your task: Decide if the user's question belongs to 'irdai.gov.in', 'pfrda.org.in', or 'none' (if unrelated to insurance/pensions, e.g. RBI banking, repo rates, SEBI stock market, general AI, general knowledge).\n\n"
        "Output ONLY a valid JSON object with:\n"
        "- \"selected_domain\": 'irdai.gov.in', 'pfrda.org.in', or 'none'\n"
        "- \"reasoning\": Brief reason for selection.\n"
    )

    user_prompt = f"User Question: {user_question}\n\nSelect domain ('irdai.gov.in', 'pfrda.org.in', or 'none'):"

    llm = get_llm(temperature=0.0)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    selected_domain = normalized_trusted[0]
    reasoning = "Defaulted to first trusted domain."

    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            candidate_raw = data.get("selected_domain", "").strip().lower()
            if candidate_raw in ("none", "null", "neither", "n/a", "no"):
                return {
                    "selected_website": "none",
                    "routing_reasoning": data.get("reasoning", "Question falls outside IRDAI and PFRDA scopes."),
                    "is_out_of_scope": True
                }
            
            candidate = normalize_domain(candidate_raw)
            matched = False
            for trusted in normalized_trusted:
                if candidate == trusted or candidate in trusted or trusted in candidate:
                    selected_domain = trusted
                    reasoning = data.get("reasoning", "Matched relevant domain.")
                    matched = True
                    break
            
            if not matched:
                return {
                    "selected_website": "none",
                    "routing_reasoning": "Question does not match IRDAI or PFRDA domains.",
                    "is_out_of_scope": True
                }
        else:
            selected_domain = normalized_trusted[0]
            
    except Exception as e:
        logger.warning(f"Error in Website Router LLM: {e}. Defaulting to first trusted domain.")
        selected_domain = normalized_trusted[0]
        reasoning = f"Default selection due to error: {e}"

    logger.info(f"Selected Website: '{selected_domain}' ({reasoning})")
    return {
        "selected_website": selected_domain,
        "routing_reasoning": reasoning,
        "is_out_of_scope": False
    }
