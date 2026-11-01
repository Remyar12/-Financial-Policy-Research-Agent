"""
Configuration and LLM Provider Factory for Financial Policy Research Agent.
Supports Ollama (default free local), Google Gemini, Groq, and OpenAI.
"""

import os
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Fixed Trusted Financial Websites
DEFAULT_TRUSTED_WEBSITES = [
    "irdai.gov.in",
    "pfrda.org.in",
]

# Provider and Model Settings
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

# Local Ollama Settings
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Google Gemini Settings
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

# Groq Settings
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# OpenAI Settings
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Search and Extractor Configuration
MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
FETCH_TIMEOUT_SECONDS = int(os.getenv("FETCH_TIMEOUT_SECONDS", "10"))


def normalize_domain(raw_url_or_domain: str) -> str:
    """
    Extracts a clean domain name (e.g. 'irdai.gov.in') from an input string or URL.
    """
    cleaned = raw_url_or_domain.strip().lower()
    if not cleaned:
        return ""
    if not cleaned.startswith("http://") and not cleaned.startswith("https://"):
        cleaned = "https://" + cleaned
    
    parsed = urlparse(cleaned)
    domain = parsed.netloc or parsed.path
    if domain.startswith("www."):
        domain = domain[4:]
    domain = domain.split("/")[0]
    return domain


def get_llm(temperature: float = 0.1):
    """
    Returns the configured LLM instance based on LLM_PROVIDER.
    """
    provider = os.getenv("LLM_PROVIDER", LLM_PROVIDER).lower()

    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=temperature
        )

    elif provider in ("gemini", "google"):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY / GOOGLE_API_KEY environment variable is not set.")
        from langchain_google_genai import ChatGoogleGenerativeAI
        return ChatGoogleGenerativeAI(
            model=GEMINI_MODEL,
            google_api_key=GEMINI_API_KEY,
            temperature=temperature
        )

    elif provider == "groq":
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY environment variable is not set.")
        from langchain_groq import ChatGroq
        return ChatGroq(
            model_name=GROQ_MODEL,
            groq_api_key=GROQ_API_KEY,
            temperature=temperature
        )

    elif provider == "openai":
        if not OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY environment variable is not set.")
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model_name=OPENAI_MODEL,
            openai_api_key=OPENAI_API_KEY,
            temperature=temperature
        )

    else:
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=temperature
        )
