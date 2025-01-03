# main.py references tobacco_analyzer.py (module __init__)
from search_strategies import SearchStrategies
import tobacco_analyzer
import prompt_manager
import os
from dotenv import load_dotenv
import sys
import google.generativeai as genai
from prompts import SEARCH_V1, DOC_EVAL_V1, DOC_SUMMARY_V1, BATCH_DOC_EVAL
from content_store import UCSFContentStore
from tobacco_analyzer.analyzer import Analyzer

GEMINI = 'gemini-1.5-flash'


load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)
model = genai.GenerativeModel(GEMINI)
query = "how did malboro market to men" # input("Enter your research question about tobacco documents: ")

strategies = SearchStrategies(model, query).generate_search_strategies(SEARCH_V1.format(uq=query))
content_store = UCSFContentStore()

analysis = Analyzer(strategies, content_store, DOC_EVAL_V1, BATCH_DOC_EVAL)