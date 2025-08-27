import os
import sys
from dotenv import load_dotenv
import google.generativeai as genai

# Ensure project root on sys.path when running from legacy_v1/
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from search_strategies import SearchStrategies
from legacy_v1.analyzer_v1 import Analyzer
from legacy_v1.prompts_v1 import SEARCH_V1
from legacy_v1.prompt_manager_v1 import PromptManager
from content_store import UCSFContentStore
from summarize import Summarizer

GEMINI = 'gemini-2.5-flash-lite'


load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)
model = genai.GenerativeModel(GEMINI)
query = "how did philip morris use non profits to their benefit"  # input("Enter your research question about tobacco documents: ")

strategies = SearchStrategies(model, query).generate_search_strategies(SEARCH_V1.format(uq=query))
content_store = UCSFContentStore()
prompt_manager = PromptManager()
summarizer = Summarizer(model, prompt_manager)
analyzer = Analyzer(model, strategies, content_store, prompt_manager)

scores, docs = analyzer.analyze_topic(query, 10) # sets how many Solr rows are fetched per strategy
summarizer.summarize_top_documents(query, docs, scores, 3) # controls how many top documents (by the v1 0–10 score) are summarized
