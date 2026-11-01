"""
Content Extractor Tool: Fetches and extracts readable webpage text and metadata using Trafilatura & pypdf.
Strips boilerplate, ads, navigation, headers, footers, and properly extracts PDF regulatory documents.
"""

import io
import re
import logging
from typing import Dict, Any, Optional
import requests
import trafilatura
from config import FETCH_TIMEOUT_SECONDS, normalize_domain

logger = logging.getLogger("ContentExtractor")

# Maximum characters to keep per page to stay fast on CPU and within LLM context
MAX_CHARS_PER_PAGE = 3500

# Standard browser headers to prevent anti-scraping blocks
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml,application/pdf;q=0.9,*/*;q=0.8",
}


def sanitize_text(text: str) -> str:
    """Removes non-printable/corrupt characters and normalizes whitespace."""
    if not text:
        return ""
    # Filter out null bytes and strange binary characters
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]", "", text)
    # Normalize multiple newlines/spaces
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    return "\n".join(lines)


def extract_pdf_content(content_bytes: bytes, fallback_title: str) -> Dict[str, Any]:
    """Extracts clean text from PDF documents using pypdf."""
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(content_bytes))
        extracted_pages = []
        # Extract up to first 10 pages of regulatory document
        for page in reader.pages[:10]:
            page_text = page.extract_text()
            if page_text:
                extracted_pages.append(page_text.strip())
        
        full_text = "\n\n".join(extracted_pages)
        sanitized = sanitize_text(full_text)
        
        if len(sanitized) > MAX_CHARS_PER_PAGE:
            sanitized = sanitized[:MAX_CHARS_PER_PAGE] + "\n\n[... PDF content truncated for length ...]"
            
        return {
            "title": fallback_title or "Official PDF Document",
            "content": sanitized,
            "char_count": len(sanitized),
            "status": "success" if len(sanitized) > 50 else "empty",
            "error_message": None if len(sanitized) > 50 else "PDF contained no readable text (may be scanned image)."
        }
    except Exception as e:
        logger.warning(f"pypdf extraction error: {e}")
        return {
            "title": fallback_title or "Official PDF Document",
            "content": "",
            "char_count": 0,
            "status": "error",
            "error_message": f"PDF parse error: {e}"
        }


def extract_webpage_content(url: str, fallback_title: str = "") -> Dict[str, Any]:
    """
    Downloads and extracts clean readable text and metadata from a given URL using Trafilatura or pypdf.
    
    Args:
        url: The webpage or PDF URL to extract.
        fallback_title: Search result title to use if page metadata lacks one.
        
    Returns:
        Dictionary containing url, domain, title, date, author, content, char_count, and status.
    """
    clean_domain = normalize_domain(url)
    
    result: Dict[str, Any] = {
        "url": url,
        "domain": clean_domain,
        "title": fallback_title or "Untitled Document",
        "date": None,
        "author": None,
        "content": "",
        "char_count": 0,
        "status": "pending",
        "error_message": None,
    }
    
    if not url or not url.startswith("http"):
        result["status"] = "error"
        result["error_message"] = "Invalid URL format"
        return result

    logger.info(f"Extracting content from: {url}")
    
    try:
        # Check if URL directly points to a PDF
        if url.lower().split("?")[0].endswith(".pdf"):
            resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=FETCH_TIMEOUT_SECONDS)
            if resp.status_code == 200:
                pdf_res = extract_pdf_content(resp.content, fallback_title)
                result.update(pdf_res)
                return result
            else:
                result["status"] = "error"
                result["error_message"] = f"HTTP {resp.status_code} on PDF download"
                return result

        # First try fetching with requests to inspect Content-Type
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=FETCH_TIMEOUT_SECONDS)
        
        if resp.status_code != 200:
            result["status"] = "error"
            result["error_message"] = f"HTTP status {resp.status_code}"
            return result
            
        content_type = resp.headers.get("Content-Type", "").lower()
        
        if "application/pdf" in content_type:
            pdf_res = extract_pdf_content(resp.content, fallback_title)
            result.update(pdf_res)
            return result

        downloaded_html = resp.text

        # Extract structured metadata (title, author, date)
        metadata = trafilatura.extract_metadata(downloaded_html)
        if metadata:
            if metadata.title:
                result["title"] = metadata.title.strip()
            if metadata.date:
                result["date"] = str(metadata.date).strip()
            if metadata.author:
                result["author"] = str(metadata.author).strip()

        # Extract main body text with Trafilatura
        extracted_text = trafilatura.extract(
            downloaded_html,
            include_comments=False,
            include_tables=True,
            include_links=False,
            include_images=False,
            no_fallback=False,
            output_format="txt",
            deduplicate=True
        )

        if not extracted_text or len(extracted_text.strip()) < 50:
            # BeautifulSoup fallback if Trafilatura skipped unusual markup
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(downloaded_html, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "aside", "form"]):
                tag.decompose()
            extracted_text = soup.get_text(separator="\n", strip=True)

        sanitized_text = sanitize_text(extracted_text)

        if not sanitized_text or len(sanitized_text) < 50:
            result["status"] = "empty"
            result["content"] = "No readable text content could be extracted from this page."
            result["char_count"] = 0
            result["error_message"] = "Page content too short or inaccessible."
            return result

        if len(sanitized_text) > MAX_CHARS_PER_PAGE:
            sanitized_text = sanitized_text[:MAX_CHARS_PER_PAGE] + "\n\n[... Content truncated for length ...]"

        result["content"] = sanitized_text
        result["char_count"] = len(sanitized_text)
        result["status"] = "success"
        logger.info(f"Successfully extracted {len(sanitized_text)} characters from {url}")

    except Exception as e:
        logger.error(f"Error extracting content from {url}: {e}")
        result["status"] = "error"
        result["error_message"] = str(e)

    return result
