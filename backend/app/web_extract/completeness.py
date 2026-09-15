from re import findall

PROMPT_FIELD_HINTS = (
    (("project", "projects"), ("project", "projects")),
    (("price", "cost", "pricing"), ("price", "cost")),
    (("profile", "full name"), ("profile", "name")),
    (("title", "heading"), ("title", "heading", "name")),
    (("product",), ("name", "title", "product")),
    (("review", "reviews", "rating", "ratings", "stars"), ("review", "rating", "star")),
    (
        ("spec", "specs", "specification", "specifications", "feature", "features", "battery"),
        ("spec", "feature", "battery"),
    ),
    (("description", "about", "overview", "summary"), ("description", "about", "overview", "summary")),
    (("author", "authors"), ("author",)),
    (("image", "images", "photo", "photos"), ("image", "photo")),
    (("sku", "asin", "model number"), ("sku", "asin", "model")),
)

PROMPT_TERM_STOPWORDS = frozenset(
    {
        "about",
        "extract",
        "from",
        "give",
        "json",
        "list",
        "page",
        "please",
        "provide",
        "public",
        "return",
        "that",
        "this",
        "what",
        "with",
    }
)


def flatten_extract_blob(data: dict) -> str:
    keys: list[str] = []
    values: list[str] = []

    def walk(value) -> None:
        if isinstance(value, dict):
            for nested_key, nested_value in value.items():
                keys.append(str(nested_key))
                walk(nested_value)
            return
        if isinstance(value, list):
            for item in value:
                walk(item)
            return
        if value in (None, ""):
            return
        values.append(str(value))

    walk(data)
    return f"{' '.join(keys)} {' '.join(values)}".lower()


def merge_extract_data(base: dict, incoming: dict) -> dict:
    merged = dict(base)
    for key, value in incoming.items():
        current = merged.get(key)
        if current in (None, "", [], {}):
            merged[key] = value
            continue
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = merge_extract_data(current, value)
            continue
        if isinstance(current, list) and isinstance(value, list):
            combined = list(current)
            for item in value:
                if item not in combined:
                    combined.append(item)
            merged[key] = combined
    return merged


def extract_needs_another_pass(prompt: str, data: dict, fields: list[str] | tuple[str, ...] | None = None) -> bool:
    if not data:
        return True
    blob = flatten_extract_blob(data)
    if fields:
        return any(field.strip().lower() not in blob for field in fields if field.strip())
    prompt_l = prompt.lower()
    for prompt_words, hints in PROMPT_FIELD_HINTS:
        if not any(word in prompt_l for word in prompt_words):
            continue
        if not any(hint in blob for hint in hints):
            return True
    return False


def prompt_search_terms(prompt: str) -> list[str]:
    text = prompt.lower()
    terms: list[str] = []
    for prompt_words, _hints in PROMPT_FIELD_HINTS:
        for word in prompt_words:
            if word in text and word not in terms:
                terms.append(word)
    for raw in findall(r"[A-Za-z][A-Za-z0-9_-]{3,}", prompt):
        word = raw.lower()
        if word in PROMPT_TERM_STOPWORDS or word in terms:
            continue
        terms.append(word)
    return terms[:12]
