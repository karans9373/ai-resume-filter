import re


STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "were",
    "will",
    "with",
    "using",
    "should",
    "able",
    "into",
    "your",
    "you",
    "we",
    "our",
}

LEMMATIZATION_SUFFIXES = ("ing", "ed", "es", "s")


def tokenize_text(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9+#.\-/]*", text.lower())


def simple_lemmatize(token: str) -> str:
    for suffix in LEMMATIZATION_SUFFIXES:
        if token.endswith(suffix) and len(token) > len(suffix) + 2:
            return token[: -len(suffix)]
    return token


def preprocess_text(text: str) -> str:
    tokens = tokenize_text(text)
    cleaned_tokens = []
    for token in tokens:
        if token in STOP_WORDS:
            continue
        cleaned_tokens.append(simple_lemmatize(token))
    return " ".join(cleaned_tokens)


def split_sentences(text: str) -> list[str]:
    return [chunk.strip() for chunk in re.split(r"(?<=[.!?])\s+|\n+", text) if chunk.strip()]
