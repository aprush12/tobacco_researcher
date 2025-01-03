'''
There are currently three main prompts:

* Search 
* Summarization
* Relevance scoring

'''

SEARCH_V1 = """
        Given this research question about tobacco documents: "{uq}"
        Generate 3 different search strategies. Each strategy should contain 2-4 key terms that would help find relevant documents.
        Return your response in this exact JSON format with no additional text:
        {{
            "strategies": [
                {{
                    "search_terms": "term1 term2",            
                    "rationale": "why this might work"
                }}
            ]
        }}
""".strip()

BATCH_DOC_EVAL = """
            Research context: {qc}\n\n"
            Analyze these tobacco industry documents. For each document, provide:\n"
                1. A relevance score (0-10)\n"
                2. Key entities found (people, projects, products, terms, dates)\n\n"
            Return only a JSON object like this example:\n{ej}\n\n"
            Documents to analyze:\n\n
            {dt}
"""
DOC_EVAL_V1 = ""
DOC_SUMMARY_V1 = ""