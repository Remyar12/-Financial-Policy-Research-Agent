"""
Node 4: Content Extractor (Python / Trafilatura)
Fetches and extracts clean readable text and metadata from the DuckDuckGo search result URLs.
Strips boilerplate, navigation, ads, and HTML.
"""

import logging
from typing import Dict, Any, List
from state import AgentState
from tools.extractor_tool import extract_webpage_content

logger = logging.getLogger("Node4_ContentExtractor")


def content_extractor_node(state: AgentState) -> Dict[str, Any]:
    """
    Extracts readable text and metadata from top search URLs using Trafilatura.
    Merges newly extracted documents with any existing documents from previous search iterations.
    """
    search_results = state.get("search_results", [])
    existing_docs = state.get("extracted_documents", [])
    
    existing_urls = {doc["url"] for doc in existing_docs if "url" in doc}
    newly_extracted: List[Dict[str, Any]] = []

    logger.info(f"Node 4 [Content Extractor]: Processing {len(search_results)} search result URLs.")

    for item in search_results:
        url = item.get("url", "")
        title = item.get("title", "")
        snippet = item.get("snippet", "")
        
        if not url or url in existing_urls:
            continue
            
        doc_data = extract_webpage_content(url=url, fallback_title=title)
        
        # If full extraction produced empty text but search result has a snippet, keep snippet as fallback
        if doc_data.get("status") in ("empty", "error") and snippet:
            doc_data["content"] = f"[Search Snippet Summary]: {snippet}"
            doc_data["char_count"] = len(doc_data["content"])
            doc_data["status"] = "partial_snippet"

        newly_extracted.append(doc_data)
        existing_urls.add(url)

    # Combine all valid documents extracted so far across iterations
    all_documents = existing_docs + newly_extracted
    
    successful_count = sum(1 for d in all_documents if d.get("status") in ("success", "partial_snippet"))
    logger.info(f"Total documents extracted: {len(all_documents)} ({successful_count} valid/readable).")

    return {
        "extracted_documents": all_documents
    }
