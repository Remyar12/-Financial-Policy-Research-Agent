"""
Search Tool: DuckDuckGo restricted searching strictly within approved domains (PFRDA, IRDAI).
Validates live HTTP status to eliminate 404s and broken links.
"""

import logging
from typing import List, Dict
import requests

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS

from config import MAX_SEARCH_RESULTS, normalize_domain

logger = logging.getLogger("SearchTool")

CHECK_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def is_live_and_valid_url(url: str) -> bool:
    """
    Checks if URL is active, returns HTTP 200, and is not an obsolete subdomain or search pagination junk.
    """
    url_lower = url.lower()
    
    # 1. Reject deprecated subdomains
    if "oldwebsite." in url_lower or "old." in url_lower:
        return False
        
    # 2. Reject internal search query strings and pagination junk
    if any(param in url_lower for param in ["?q=", "?delta=", "?modifiedfrom=", "&start="]):
        return False

    # 3. Fast live check (verify it doesn't 404 or fail)
    try:
        r = requests.head(url, headers=CHECK_HEADERS, timeout=3, allow_redirects=True)
        if r.status_code == 200:
            return True
        # Try GET stream if HEAD was rejected
        r = requests.get(url, headers=CHECK_HEADERS, timeout=3, stream=True)
        return r.status_code == 200
    except Exception:
        return False


def search_duckduckgo_restricted(
    query: str,
    target_domain: str,
    max_results: int = MAX_SEARCH_RESULTS
) -> List[Dict[str, str]]:
    """
    Executes a DuckDuckGo search strictly constrained to `target_domain`.
    Enforces `site:<target_domain>` operator in the query and validates each result URL.
    
    Args:
        query: Search query text.
        target_domain: The single trusted domain to search within.
        max_results: Maximum number of search results to retrieve.
        
    Returns:
        List of dictionaries containing title, url, snippet, and domain.
    """
    clean_domain = normalize_domain(target_domain)
    if not clean_domain:
        logger.error("No valid domain provided for restricted search.")
        return []

    # Ensure query starts with or contains the exact site: restriction
    site_prefix = f"site:{clean_domain}"
    if site_prefix.lower() not in query.lower():
        words = [w for w in query.split() if not w.lower().startswith("site:")]
        final_query = f"{site_prefix} {' '.join(words)}"
    else:
        final_query = query.strip()

    logger.info(f"Executing restricted DuckDuckGo search: '{final_query}'")

    results: List[Dict[str, str]] = []
    
    try:
        with DDGS() as ddgs:
            ddg_gen = ddgs.text(
                final_query,
                max_results=max_results * 3,  # fetch candidates for validation
                safesearch="moderate"
            )
            
            if ddg_gen:
                for item in ddg_gen:
                    url = item.get("href") or item.get("url") or ""
                    
                    normalized_result_domain = normalize_domain(url)
                    
                    # Strict domain match
                    if not (
                        clean_domain == normalized_result_domain
                        or normalized_result_domain.endswith("." + clean_domain)
                        or clean_domain.endswith("." + normalized_result_domain)
                    ):
                        continue

                    # Validate live HTTP 200 status (no 404s)
                    if not is_live_and_valid_url(url):
                        logger.warning(f"Discarding broken/404 URL: {url}")
                        continue

                    results.append({
                        "title": item.get("title", "Untitled Policy Document").strip(),
                        "url": url.strip(),
                        "snippet": item.get("body", "").strip(),
                        "domain": clean_domain
                    })
                    
                    if len(results) >= max_results:
                        break
                        
    except Exception as e:
        logger.warning(f"DuckDuckGo search encountered an error: {e}")

    logger.info(f"DuckDuckGo search retrieved {len(results)} verified live domain results.")
    return results
