"""
Tools package for DuckDuckGo searching and Trafilatura content extraction.
"""

from .search_tool import search_duckduckgo_restricted
from .extractor_tool import extract_webpage_content

__all__ = ["search_duckduckgo_restricted", "extract_webpage_content"]
