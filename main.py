# main.py references tobacco_analyzer.py (module __init__)
from search_strategies import SearchStrategies
from analyzer import Analyzer
import os
from dotenv import load_dotenv
import sys
import google.generativeai as genai
from prompts import SEARCH_V1
from content_store import UCSFContentStore


GEMINI = 'gemini-1.5-flash'


load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)
model = genai.GenerativeModel(GEMINI)
query = "how did philip morris use non profits to their benefit" # input("Enter your research question about tobacco documents: ")

strategies = SearchStrategies(model, query).generate_search_strategies(SEARCH_V1.format(uq=query))
content_store = UCSFContentStore()

analyzer = Analyzer(model, strategies, content_store)
analysis, docs = analyzer.analyze_topic(query)
top_summaries = analyzer.summarize_top_documents(query, docs, analysis, 3)
print(top_summaries)