"""
Node 5: Answer Generator (LLM)
Generates the final clean, comprehensive response strictly grounded in the extracted webpage content.
Provides clear, professional policy explanations without trailing source clutter.
"""

import logging
import re
from typing import Dict, Any, List
from langchain_core.messages import SystemMessage, HumanMessage
from config import get_llm
from state import AgentState

logger = logging.getLogger("Node5_AnswerGenerator")


def answer_generator_node(state: AgentState) -> Dict[str, Any]:
    """
    Synthesizes the final answer strictly using extracted sources in a clean, professional format.
    """
    user_question = state.get("user_question", "")
    extracted_docs = state.get("extracted_documents", [])
    selected_website = state.get("selected_website", "")
    is_out_of_scope = state.get("is_out_of_scope", False)
    
    logger.info("Answer Generator: Generating grounded answer or out-of-scope response.")

    valid_docs = [d for d in extracted_docs if d.get("content") and d.get("status") in ("success", "partial_snippet")]

    # If question is explicitly out-of-scope, no website selected, or 0 documents found
    if is_out_of_scope or selected_website in ("none", "") or not valid_docs:
        final_answer = (
            f"The provided trusted websites (irdai.gov.in and pfrda.org.in) do not contain the information requested regarding '{user_question}'.\n\n"
            f"This agent strictly provides verified answers derived exclusively from official IRDAI (Insurance) and PFRDA (Pensions/NPS) regulatory portals."
        )
        return {
            "final_answer": final_answer,
            "sources_used": []
        }

    # Format document contents
    formatted_sources_for_prompt = []
    sources_metadata: List[Dict[str, str]] = []

    for idx, doc in enumerate(valid_docs, start=1):
        url = doc.get("url", "N/A")
        title = doc.get("title", "Untitled Policy Document")
        date_str = f" (Published: {doc.get('date')})" if doc.get("date") else ""
        content_snippet = doc.get("content", "")[:3500]
        
        sources_metadata.append({
            "index": str(idx),
            "title": title,
            "url": url,
            "domain": doc.get("domain", selected_website)
        })
        
        formatted_sources_for_prompt.append(
            f"--- SOURCE [{idx}] ---\n"
            f"Title: {title}{date_str}\n"
            f"URL: {url}\n"
            f"Content:\n{content_snippet}\n"
        )

    context_block = "\n\n".join(formatted_sources_for_prompt)

    system_prompt = (
        "You are an authoritative Financial Policy Research Assistant.\n"
        "Your task is to answer the user's question directly, clearly, and cleanly USING ONLY THE RETRIEVED SOURCES.\n\n"
        "STRICT GROUNDING GUIDELINES:\n"
        "1. Grounding: Base your answer strictly on the facts, guidelines, regulations, and circulars provided.\n"
        "2. If the retrieved sources DO NOT contain sufficient information to answer the question, state:\n"
        "   'The provided trusted websites (irdai.gov.in and pfrda.org.in) do not contain the information requested regarding this query.'\n"
        "3. Zero Hallucination: Do NOT invent, assume, extrapolate, or use external knowledge outside the provided trusted sources.\n"
        "4. Tone & Structure: Deliver a clean, professional, well-structured answer.\n"
        "5. Focus on the Answer: Provide ONLY the direct policy answer. Do NOT append any 'Sources Cited' or 'References' section at the end.\n"
    )

    user_prompt = (
        f"User Question: {user_question}\n"
        f"Target Official Domain: {selected_website}\n\n"
        f"RETRIEVED OFFICIAL SOURCES:\n{context_block}\n\n"
        "Please provide the clean, detailed, and directly relevant policy answer:"
    )

    llm = get_llm(temperature=0.1)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]

    try:
        response = llm.invoke(messages)
        content = response.content.strip()
        
        # Clean up any residual source lists at the bottom if model generated them
        cleaned_answer = re.split(r"(?i)\n*###?\s*Verified Sources Cited.*", content)[0].strip()
        cleaned_answer = re.split(r"(?i)\n*###?\s*Sources Cited.*", cleaned_answer)[0].strip()
        cleaned_answer = re.split(r"(?i)\n*###?\s*References:?.*", cleaned_answer)[0].strip()
        
        final_answer = cleaned_answer
    except Exception as e:
        logger.error(f"Error generating final answer with LLM: {e}")
        final_answer = (
            f"Error generating answer: {e}\n\n"
            f"Retrieved {len(valid_docs)} source(s) from {selected_website}."
        )

    return {
        "final_answer": final_answer,
        "sources_used": sources_metadata,
    }
