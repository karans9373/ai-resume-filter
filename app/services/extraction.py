import re
from collections import Counter

from .nlp import preprocess_text


SKILL_KEYWORDS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "node.js",
    "node",
    "fastapi",
    "flask",
    "django",
    "sql",
    "postgresql",
    "mongodb",
    "mysql",
    "html",
    "css",
    "tailwind",
    "bootstrap",
    "git",
    "github",
    "docker",
    "kubernetes",
    "aws",
    "azure",
    "gcp",
    "tensorflow",
    "pytorch",
    "scikit-learn",
    "nlp",
    "machine learning",
    "data analysis",
    "pandas",
    "numpy",
    "opencv",
    "rest api",
    "api",
    "c",
    "c++",
    "c#",
    "php",
    "laravel",
    "spring boot",
    "power bi",
    "excel",
    "communication",
    "problem solving",
}

EDUCATION_KEYWORDS = (
    "b.tech",
    "bachelor",
    "master",
    "mca",
    "bca",
    "b.sc",
    "m.sc",
    "phd",
    "degree",
    "university",
    "college",
)

EXPERIENCE_KEYWORDS = (
    "experience",
    "worked",
    "intern",
    "developer",
    "engineer",
    "analyst",
    "manager",
    "project",
)


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def extract_email(text: str) -> str:
    match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    return match.group(0) if match else ""


def extract_phone(text: str) -> str:
    match = re.search(r"(\+?\d[\d\s\-()]{8,}\d)", text)
    return match.group(0) if match else ""


def extract_candidate_name(text: str, fallback: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return fallback

    for line in lines[:8]:
        if len(line.split()) in {2, 3, 4} and not re.search(r"\d|@|resume|curriculum", line.lower()):
            return line.title()

    return fallback


def extract_skills(text: str) -> list[str]:
    lowered = normalize_text(text).lower()
    hits = []
    for skill in SKILL_KEYWORDS:
        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
        if re.search(pattern, lowered):
            hits.append(skill)
    return sorted(set(hits))


def extract_education(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    results = []
    for line in lines:
        lowered = line.lower()
        if any(keyword in lowered for keyword in EDUCATION_KEYWORDS):
            results.append(line)
    return results[:5]


def extract_experience_highlights(text: str) -> list[str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    results = []
    for line in lines:
        lowered = line.lower()
        if any(keyword in lowered for keyword in EXPERIENCE_KEYWORDS):
            results.append(line)
    return results[:6]


def extract_years_of_experience(text: str) -> float:
    matches = re.findall(r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)", text.lower())
    numeric = [float(item) for item in matches]
    return max(numeric) if numeric else 0.0


def extract_top_keywords(text: str, limit: int = 15) -> list[str]:
    words = preprocess_text(text).split()
    filtered = [
        word
        for word in words
        if word not in {"with", "from", "have", "this", "that", "your", "will", "using", "them"}
    ]
    counts = Counter(filtered)
    return [word for word, _ in counts.most_common(limit)]


def extract_required_skills(job_description: str) -> list[str]:
    return extract_skills(job_description)


def extract_priority_skills(job_description: str) -> list[str]:
    sentences = [line.strip() for line in re.split(r"[\n.]", job_description) if line.strip()]
    priority_markers = ("must", "required", "mandatory", "need", "should", "strong", "expert", "proficient")
    priority_hits = set()

    for sentence in sentences:
        lowered = sentence.lower()
        if any(marker in lowered for marker in priority_markers):
            priority_hits.update(extract_skills(sentence))

    return sorted(priority_hits)
