import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Ensure project root is on sys.path (harmless if already present)
ROOT = os.path.abspath(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from search_strategies import SearchStrategies
from content_store import UCSFContentStore
from filter_ui import build_filters_interactively, build_solr_fqs
from prompt_manager_v2 import PromptManagerV2
from analyzer_v2 import AnalyzerV2
from summarize import Summarizer
from summary_prompt_manager_v2 import SummaryPromptManagerV2


def main():
    load_dotenv()
    api_key = os.getenv('GEMINI_API_KEY')
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash-lite')

    query = input("Enter your research question (press Enter for default): ").strip() or "youth women marketing tobacco"

    strategies = SearchStrategies(model, query).generate_search_strategies(
        f"Given this research question about tobacco documents: \"{query}\"\nGenerate 3 different search strategies to find industry documents that reveal intent of deception; however you cannot explicitly search for deception since Big Tobacco wouldn't call themselves deceptive. Each strategy should have 2-4 key terms that would help find relevant documents (not in quotes).\nReturn your response in this exact JSON format with no additional text:\n{{\n    \"strategies\": [\n        {{\n            \"search_terms\": \"term1 term2\",            \n            \"rationale\": \"why this might work\"\n        }}\n    ]\n}}"
    )

    # Interactive filters
    filters = build_filters_interactively()
    additional_fqs = build_solr_fqs(filters)

    content_store = UCSFContentStore()
    pm_v2 = PromptManagerV2()
    analyzer = AnalyzerV2(model, strategies, content_store, pm_v2)

    def _ask_int(prompt: str, default: int) -> int:
        raw = input(f"{prompt} (Enter for {default}): ").strip()
        if raw == "":
            return default
        try:
            v = int(raw)
            return v if v > 0 else default
        except Exception:
            return default

    rows = _ask_int("How many documents to retrieve per search strategy", 10)
    top_display = _ask_int("How many top document IDs display", 5)
    top_summarize = _ask_int("How many top documents to summarize", 3)

    analysis, docs = analyzer.analyze_topic(query, rows, additional_fqs)
    ranked = analyzer.rank_results(analysis, docs)

    print(f"\n[V2] Top {top_display} by label/confidence/facets:")
    for i, doc_id in enumerate(ranked[:top_display], start=1):
        info = analysis.get(doc_id, {})
        print(f"{i}. {doc_id}: {info.get('label')} (conf={info.get('confidence')})")

    # Summarize top M using v2 summary prompt
    summarizer = Summarizer(model, SummaryPromptManagerV2())
    top_docs = {doc_id: docs[doc_id] for doc_id in ranked[:top_summarize] if doc_id in docs}
    top_subset_scores = {doc_id: {"score": 3 if analysis[doc_id].get('label') == 'smoking_gun' else 2} for doc_id in top_docs}
    summarizer.summarize_top_documents(query, docs, top_subset_scores, n=len(top_docs))


if __name__ == "__main__":
    main()

