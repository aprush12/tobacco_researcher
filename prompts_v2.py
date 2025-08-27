"""
Prompts v2: smoking-gun triage and evidence schema.
"""

BATCH_DOC_EVAL_V2 = """
You are evaluating tobacco industry documents for this research question: "{uq}".

Classify each document into one of four labels and extract concise evidence:

- smoking_gun: Direct admission, explicit directive/plan/targeting, or concrete budget/action advancing the query (e.g., "target teenage girls", "approve $X for youth campaign").
- strong: Highly relevant but indirect language; suggests intent or action without explicit admission/directive.
- related: Contextual or tangentially relevant; no concrete action/admission related to the query.
- irrelevant: Not meaningfully related to the query.

Rules:
- Quote only text that appears in the provided OCR content; keep each quote <= 30 words.
- Provide character offsets "start" and "end" for each quote based on the provided OCR snippet.
- Be conservative when assigning smoking_gun; if in doubt, use strong or related.
- Prefer internal memos, brand plans, budgets over news/press clippings and attachments.

Return ONLY a JSON object with document IDs as keys, matching this schema:
{ej}

Documents:
{dt}
""".strip()

EXAMPLE_JSON_EVAL_V2 = (
    '{\n'
    '  "doc_id123": {\n'
    '    "label": "smoking_gun",\n'
    '    "confidence": 0.82,\n'
    '    "tie_break_score": 3,\n'
    '    "evidence": [\n'
    '      {"quote": "Approve $250,000 for the teen girls pilot in malls", "start": 3451, "end": 3504}\n'
    '    ],\n'
    '    "reasons": "Direct budget approval targeting teen girls marketing.",\n'
    '    "facets": {\n'
    '      "doc_type": "Brand Plan",\n'
    '      "date_in_range": true,\n'
    '      "mentions_brands": ["Camel"],\n'
    '      "targets_group": ["youth", "women"],\n'
    '      "budget_numbers": true,\n'
    '      "directive_language": true,\n'
    '      "explicit_target_terms": ["teen girls", "pilot"]\n'
    '    }\n'
    '  }\n'
    '}'
)

# Summarization prompt for v2
SING_SUMMARIZE_V2 = """Research Question: {uq}

Create a detailed summary of this tobacco industry document as it is relevant to the research question in this exact format:
    
    In a concise paragraph format, include the following:
    - Document title
    - Document type and year
    - Key findings or main points
    - Marketing strategies or business decisions if any
    - Public health implications if any

    Example of desired summary format:
    [ysvj0228]: This 2008 American Journal of Public Health article titled 'Tobacco and Menthol' examines how tobacco manufacturers manipulated menthol levels in cigarettes to target adolescents and young adults. The authors analyzed internal tobacco industry documents, conducted lab tests on various menthol cigarette brands, and reviewed data from the National Survey on Drug Use and Health. Their findings indicate that lower menthol levels, particularly in brands like Newport and Marlboro Milds, were more appealing to younger smokers because they masked the harshness of cigarettes, facilitating smoking initiation and nicotine addiction. Higher menthol levels were targeted toward long-term smokers. The study also reveals a significant increase in magazine advertising expenditures for menthol brands, despite a decline in overall cigarette sales.

    Document to summarize:
    {dt}
    """
