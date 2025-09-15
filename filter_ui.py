import json


DOC_TYPES = [
    "Report", "Letter", "Memo", "Report Market Research", "Graphics", "Email", "Printout", "Revision",
    "Form", "Draft", "Chart", "Graph", "Map", "List", "Raw Data", "Table", "Speech", "Financial",
    "Questionnaire", "Presentation", "Promotional Material", "Manual", "Contract", "Agenda", "Publication",
    "Handwritten", "Proposal", "Notes", "Brand Review", "Photograph", "Routing Slip", "Personnel Information",
    "Advertisement", "Drawing", "Computer Printout", "Specification", "Marketing Document", "Organizational Chart",
    "Budget", "Budget Review", "Minutes", "Cartons", "Cigarette Package", "News Article", "Pack",
    "Market Research Report", "Report Scientific", "Telex", "Report Formal Report", "Brand Plan", "Corporate",
    "Agreement Resolution", "Magazine Article", "Deposition Exhibit", "Pleading", "Script", "Internet", "Footnote",
    "Study", "Deposition Use", "Newsletter", "Newspaper Article", "Telephone Record", "Bibliography", "Catalog",
    "Deposition", "Invoice", "Market Research Study", "Outline", "Slides", "Website Snapshot", "Email Attachment",
    "Legal Document", "Loose Email Attachment", "Pamphlet", "Video", "Website Internet", "Attachment", "Book",
    "Cartoon", "Computer Disk", "Diagram", "Fax", "Flow Chart", "Formal Legal Document", "Handbook", "Law",
    "Letter Consumer", "Meeting Materials", "Press Release", "Raw Data File", "Report R&d", "Survey Questionnaire",
    "Trial List"
]

COLLECTIONS = [
    "Master Settlement Agreement",
    "Topical Collections",
    "Additional Tobacco Documents",
]

BRANDS = [
    "Camel", "Winston", "Salem", "Doral", "Non-rjr Brands", "Kamel", "Vantage", "Eclipse", "Monarch",
    "Rjrtc Brands", "Now", "More", "Century", "Planet", "Magna", "Sterling", "Carolina Gold", "Hogshead",
    "B's", "Jumbos", "Camel Ff 85 Men", "Icebox", "Marlboro", "North Star", "Metro", "Sedona", "Horizon",
    "Newport", "Camel Nf 70", "City", "Camel Lt 85", "Politix", "Camel Ff 85", "House Blend", "Camel Ul 85",
    "Kool", "Camel Turkish Gold", "Camel Wides Ff 85", "Winston Select Ff 85", "Premier", "Gpc", "Cavalier",
    "Kamel Ff 85 Menthol", "Winston Ff 85", "Basic", "Camel Special Lights", "Bright", "Dakota", "American Spirit",
    "Chelsea", "Moonlight", "Red Kamel Lt 85", "Lucky Strike", "Winston Ul 85", "R01000", "Camel Menthol",
    "Winston Lt 85", "Parliament", "Salem Lt 85 Menthol", "Ritz", "Misty", "Carlton", "Benson & Hedges",
    "Salem Lt 100 Menthol", "Merit", "Virginia Slims", "Doral Ul 100", "Salem Ff 85 Menthol", "Montclair",
    "Red Kamel Ff 85", "Doral Ff 85", "Camel Ff 100", "Salem Ff 100 Menthol", "Tempo", "Doral Ul 85", "Camel 80",
    "Doral Lt 85", "Old Gold", "Camel Ryo Pouch", "Camel Lt 80", "Kamel Menthol", "Cambridge",
    "Salem Blacklabel Menthol", "Doral Lt 100", "Capri", "Maverick", "Kent", "Winston Ff 100", "Winston Ul 100",
    "Pall Mall", "Best Value", "Players", "Salem Preferred Menthol", "Doral Lt 100 Menthol", "Doral Ff 100",
    "Winston Lt 100", "Camel Ul 100", "Viceroy", "Kamel Lt 85 Menthol"
]


def _input(msg: str) -> str:
    try:
        return input(msg).strip()
    except EOFError:
        return ""


def _multi_select(options: list[str], title: str) -> list[str] | None:
    print(title)
    for idx, label in enumerate(options, start=1):
        print(f"{idx}. {label}")
    while True:
        raw = _input("> ")
        if raw == "":
            return None
        parts = [p.strip() for p in raw.split(',') if p.strip()]
        if not parts:
            print("Please enter comma-separated numbers or press Enter to stop.")
            continue
        out: list[str] = []
        try:
            seen = set()
            for p in parts:
                i = int(p)
                if not (1 <= i <= len(options)):
                    raise ValueError
                if i not in seen:
                    out.append(options[i - 1])
                    seen.add(i)
            return out
        except ValueError:
            print("Invalid selection; use numbers in range or Enter.")


def build_filters_interactively(default_date: str | None = None) -> dict:
    # Start with no default date selection unless provided explicitly
    selected: dict = {"date": [default_date]} if default_date else {}
    while True:
        print("\nPress Enter to run search, or choose a filter to add:")
        print(f"Currently selected: {selected}")
        print("1. date")
        print("2. document type")
        print("3. collection")
        print("4. brands")
        raw = _input("> ")
        if raw == "":
            return selected
        if not raw.isdigit() or not (1 <= int(raw) <= 4):
            print("Enter a number 1-4 or press Enter to run.")
            continue
        choice = int(raw)
        if choice == 1:
            # Date has presets plus custom, allow multi
            preset_labels = [
                "1980 TO 1990",
                "1990 TO 2000",
                "2000 TO 2012",
                "2013 TO 2020",
            ]
            presets = [f"[{lbl}]" for lbl in preset_labels]
            multi = _multi_select(preset_labels + ["Custom range (e.g., [1985 TO 1995])"],
                                  "Select one or more date ranges (Enter to stop):")
            new_dates: list[str] = []
            if multi:
                for m in multi:
                    if m in preset_labels:
                        new_dates.append(f"[{m}]")
                    else:
                        # Custom prompt
                        custom = _input("Enter custom date range (e.g., [1985 TO 1995]): ")
                        if custom:
                            new_dates.append(custom)
            if new_dates:
                selected["date"] = new_dates
        elif choice == 2:
            vals = _multi_select(DOC_TYPES, "Select one or more document types (Enter to stop):")
            if vals:
                selected["type"] = vals
        elif choice == 3:
            vals = _multi_select(COLLECTIONS, "Select one or more collections (Enter to stop):")
            if vals:
                selected["collection"] = vals
        elif choice == 4:
            vals = _multi_select(BRANDS, "Select one or more brands (Enter to stop):")
            if vals:
                selected["brand"] = vals


def _normalize_year(s: str) -> str | None:
    s = s.strip()
    return s if s.isdigit() and len(s) == 4 else None


def _normalize_yyyymmdd(s: str) -> str | None:
    s = s.strip()
    return s if s.isdigit() and len(s) == 8 else None


def _iso_datetime_from_year(y: str, end: bool) -> str:
    return f"{y}-12-31T00:00:00Z" if end else f"{y}-01-01T00:00:00Z"


def _iso_datetime_from_yyyymmdd(d: str) -> str:
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}T00:00:00Z"


def _normalize_date_range(rng: str) -> str | None:
    """
    Accepts inputs like:
    - "[1980 TO 1990]" or "1980 TO 1990"
    - "[19800101 TO 19901231]" or "19800101 TO 19901231"
    - Already ISO datetimes inside optional brackets
    Returns a Solr range for documentdateiso: "[YYYY-MM-DDTHH:MM:SSZ TO YYYY-MM-DDTHH:MM:SSZ]"
    """
    if not isinstance(rng, str) or not rng.strip():
        return None
    s = rng.strip()
    if s.startswith('[') and s.endswith(']'):
        s = s[1:-1].strip()
    if 'TO' not in s:
        return None
    start, end = [p.strip() for p in s.split('TO', 1)]

    # Year-only
    ys, ye = _normalize_year(start), _normalize_year(end)
    if ys and ye:
        return f"[{_iso_datetime_from_year(ys, False)} TO {_iso_datetime_from_year(ye, True)}]"

    # yyyymmdd
    ds, de = _normalize_yyyymmdd(start), _normalize_yyyymmdd(end)
    if ds and de:
        return f"[{_iso_datetime_from_yyyymmdd(ds)} TO {_iso_datetime_from_yyyymmdd(de)}]"

    # If looks like ISO already (has '-' and 'T'), just ensure brackets
    if ('-' in start and 'T' in start) and ('-' in end and 'T' in end):
        return f"[{start} TO {end}]"
    return None


def build_solr_fqs(filters: dict) -> list[str]:
    fqs: list[str] = []
    # Date ranges
    dates = filters.get("date") or []
    if isinstance(dates, list) and dates:
        # Normalize to documentdateiso ranges
        normed: list[str] = []
        for rng in dates:
            nr = _normalize_date_range(rng)
            if nr:
                normed.append(f"documentdateiso:{nr}")
        if normed:
            if len(normed) == 1:
                fqs.append(normed[0])
            else:
                fqs.append(f"({' OR '.join(normed)})")
    # Types
    types = filters.get("type") or []
    if isinstance(types, list) and types:
        def q(val: str) -> str:
            return f'"{val.replace("\"", "\\\"")}"'
        if len(types) == 1:
            fqs.append(f"dt:{q(types[0])}")
        else:
            or_expr = " OR ".join([f"dt:{q(t)}" for t in types])
            fqs.append(f"({or_expr})")
    # Collections
    cols = filters.get("collection") or []
    if isinstance(cols, list) and cols:
        def q(val: str) -> str:
            return f'"{val.replace("\"", "\\\"")}"'
        if len(cols) == 1:
            fqs.append(f"collection:{q(cols[0])}")
        else:
            or_expr = " OR ".join([f"collection:{q(c)}" for c in cols])
            fqs.append(f"({or_expr})")
    # Brands (assumes field name 'brand')
    brands = filters.get("brand") or []
    if isinstance(brands, list) and brands:
        def q(val: str) -> str:
            return f'"{val.replace("\"", "\\\"")}"'
        if len(brands) == 1:
            fqs.append(f"brand:{q(brands[0])}")
        else:
            or_expr = " OR ".join([f"brand:{q(b)}" for b in brands])
            fqs.append(f"({or_expr})")
    return fqs
