"""
Financial Policy Research Agent - Standard Terminal CLI.
Uses fixed trusted websites (irdai.gov.in, pfrda.org.in) with standard plain-text output.
"""

import os
import sys
import logging
import warnings
from dotenv import load_dotenv

# Load environment variables (including LangSmith API keys)
load_dotenv()

# Sync LangSmith & LangChain tracing environment variables
if os.getenv("LANGSMITH_TRACING", "").lower() in ("true", "1") and not os.getenv("LANGCHAIN_TRACING_V2"):
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
if os.getenv("LANGSMITH_API_KEY") and not os.getenv("LANGCHAIN_API_KEY"):
    os.environ["LANGCHAIN_API_KEY"] = os.environ["LANGSMITH_API_KEY"]
if os.getenv("LANGSMITH_PROJECT") and not os.getenv("LANGCHAIN_PROJECT"):
    os.environ["LANGCHAIN_PROJECT"] = os.environ["LANGSMITH_PROJECT"]

# Suppress library deprecation and socket warnings for clean output
warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.ERROR)

from config import DEFAULT_TRUSTED_WEBSITES, LLM_PROVIDER, OLLAMA_MODEL
from graph import financial_research_agent
from state import AgentState


def print_separator():
    print("=" * 80)


def run_agent_workflow(question: str):
    """
    Executes the LangGraph workflow and prints only the Question, Answer, and Official Source Links.
    """
    initial_state: AgentState = {
        "user_question": question,
        "trusted_websites": DEFAULT_TRUSTED_WEBSITES,
        "search_queries_history": [],
        "extracted_documents": [],
    }

    print("\nSearching trusted sources and generating answer...")

    # Execute workflow (LangSmith records all intermediate nodes in the background)
    result = financial_research_agent.invoke(initial_state)

    final_answer = result.get("final_answer", "No answer generated.")
    sources = result.get("sources_used", [])

    # If sources_used wasn't populated or is empty, extract from extracted_documents
    if not sources and result.get("extracted_documents"):
        valid_docs = [
            d for d in result.get("extracted_documents", [])
            if d.get("status") in ("success", "partial_snippet") and d.get("url")
        ]
        sources = [{"title": d.get("title", "Official Policy Document"), "url": d.get("url")} for d in valid_docs]

    print("\n" + "=" * 80)
    print("QUESTION:")
    print(question)
    print("=" * 80)
    print("\nANSWER:")
    print(final_answer)
    print("\n" + "=" * 80)
    print("SOURCES / OFFICIAL LINKS:")
    if sources:
        seen_urls = set()
        count = 1
        for s in sources:
            url = s.get("url")
            title = s.get("title", "Official Policy Document")
            if url and url not in seen_urls:
                seen_urls.add(url)
                print(f" [{count}] {title}")
                print(f"     {url}")
                count += 1
    else:
        print("  No official sources retrieved.")
    print("=" * 80 + "\n")


def main():
    tracing_flag = (os.getenv("LANGCHAIN_TRACING_V2", "").lower() in ("true", "1") or 
                    os.getenv("LANGSMITH_TRACING", "").lower() in ("true", "1"))
    has_api_key = bool(os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY"))
    tracing_active = tracing_flag and has_api_key
    project_name = os.getenv("LANGCHAIN_PROJECT") or os.getenv("LANGSMITH_PROJECT", "financial-policy-research-agent")
    
    print_separator()
    print("FINANCIAL POLICY RESEARCH AGENT")
    print(f"LLM Engine: {LLM_PROVIDER.upper()} ({OLLAMA_MODEL})")
    print(f"Active Trusted Websites: {', '.join(DEFAULT_TRUSTED_WEBSITES)}")
    print(f"LangSmith Monitoring: {'ENABLED (Project: ' + project_name + ')' if tracing_active else 'DISABLED'}")
    print_separator()

    while True:
        try:
            print("\nEnter your financial policy question (or 'exit' to quit):")
            question = input("> ").strip()
            
            if not question:
                continue

            if question.lower() in ("exit", "quit", "q"):
                print("Exiting. Goodbye!")
                break

            run_agent_workflow(question)

        except KeyboardInterrupt:
            print("\nExiting. Goodbye!")
            sys.exit(0)
        except Exception as e:
            print(f"\nError executing workflow: {e}")


if __name__ == "__main__":
    main()
