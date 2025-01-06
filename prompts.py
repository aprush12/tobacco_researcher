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

BATCH_DOC_EVAL_V1 = """
            Research context: {uq}\n\n"
            Analyze these tobacco industry documents. For each document, provide:\n"
                1. A relevance score (0-10)\n"
                2. Key entities found (people, projects, products, terms, dates)\n\n"
            Return only a JSON object like this example:\n{ej}\n\n"
            Documents to analyze:\n\n
            {dt}
"""

EXAMPLE_JSON_EVAL_V1 = (
    '{\n'
    '    "doc_id1": {\n'
    '        "score": 7,\n'
    '        "entities": {\n'
    '            "people": ["name1", "name2"],\n'
    '            "projects": ["project1"],\n'
    '            "products": ["product1"],\n'
    '            "terms": ["term1"],\n'
    '            "dates": ["date1"]\n'
    '        }\n'
    '    }\n'
    '}'
)

SING_SUMMARIZE_V1 = """Research Question: {uq}

Create a detailed summary of this tobacco industry document as it is relevant to the research question in this exact format:

    [Document ID]: A summary that includes
    - Document title
    - Document type and year
    - Key findings or main points
    - Notable people, organizations, or projects if any
    - Specific data, numbers, or research findings if any
    - Marketing strategies or business decisions if any
    - Public health implications if any

    Example of desired summary format:
    [ysvj0228]: This 2008 American Journal of Public Health article titled 'Tobacco and Menthol' examines how tobacco manufacturers manipulated menthol levels in cigarettes to target adolescents and young adults. The authors analyzed internal tobacco industry documents, conducted lab tests on various menthol cigarette brands, and reviewed data from the National Survey on Drug Use and Health. Their findings indicate that lower menthol levels, particularly in brands like Newport and Marlboro Milds, were more appealing to younger smokers because they masked the harshness of cigarettes, facilitating smoking initiation and nicotine addiction. Higher menthol levels were targeted toward long-term smokers. The study also reveals a significant increase in magazine advertising expenditures for menthol brands, despite a decline in overall cigarette sales.

    Document to summarize:
    {dt}
    """
#SING_DOC_EVAL_V1 = ""
#SING_DOC_SUMMARY_V1 = ""