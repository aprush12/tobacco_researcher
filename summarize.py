from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
from urllib.parse import urlencode

class Summarizer:
    def __init__(self, model, prompt_manager) -> None:
        self.model = model
        self.prompt_manager = prompt_manager

    def summarize(self, user_query, doc):
        return self.model.generate_content(self.prompt_manager.create_summary_prompt([doc], user_query)).text

    def summarize_top_documents(self, user_query, cached_docs, analysis_results, n = 3):
        # Sort documents by score in descending order
        top_docs = dict(
            sorted(
                analysis_results.items(),
                key=lambda item: item[1]['score'],
                reverse=True
            )[:n]
        )

        # Summarize directly!
        for doc_id in top_docs.keys():
            summary = self.summarize(user_query, cached_docs[doc_id])
            print(f"{summary}")
