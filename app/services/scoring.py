import json

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .extraction import (
    extract_candidate_name,
    extract_education,
    extract_email,
    extract_experience_highlights,
    extract_phone,
    extract_priority_skills,
    extract_required_skills,
    extract_skills,
    extract_top_keywords,
    extract_years_of_experience,
)
from .nlp import preprocess_text, split_sentences


def score_candidate(file_name: str, resume_text: str, job_description: str) -> dict:
    cleaned_resume = resume_text.strip()
    cleaned_job = job_description.strip()
    preprocessed_resume = preprocess_text(cleaned_resume)
    preprocessed_job = preprocess_text(cleaned_job)

    resume_skills = extract_skills(cleaned_resume)
    job_skills = extract_required_skills(cleaned_job)
    priority_skills = extract_priority_skills(cleaned_job)
    skill_overlap = sorted(set(resume_skills) & set(job_skills))
    priority_overlap = sorted(set(resume_skills) & set(priority_skills))

    skill_score = calculate_weighted_skill_score(job_skills, priority_skills, skill_overlap)

    similarity_score = calculate_similarity(preprocessed_resume, preprocessed_job)
    years_of_experience = extract_years_of_experience(cleaned_resume)
    experience_score = min(years_of_experience / 10, 1.0)
    section_alignment_score = calculate_section_alignment(cleaned_resume, cleaned_job)

    final_score = (
        (skill_score * 0.5)
        + (similarity_score * 0.25)
        + (experience_score * 0.1)
        + (section_alignment_score * 0.15)
    )
    match_percentage = round(final_score * 100, 2)

    return {
        "file_name": file_name,
        "candidate_name": extract_candidate_name(cleaned_resume, file_name.rsplit(".", 1)[0].replace("_", " ")),
        "email": extract_email(cleaned_resume),
        "phone": extract_phone(cleaned_resume),
        "skills": resume_skills,
        "education": extract_education(cleaned_resume),
        "experience_highlights": extract_experience_highlights(cleaned_resume),
        "extracted_text": cleaned_resume,
        "preprocessed_text": preprocessed_resume,
        "skill_score": round(skill_score * 100, 2),
        "similarity_score": round(similarity_score * 100, 2),
        "experience_score": round(experience_score * 100, 2),
        "section_alignment_score": round(section_alignment_score * 100, 2),
        "final_score": round(final_score * 100, 2),
        "match_percentage": match_percentage,
        "matched_skills": skill_overlap,
        "priority_skills": priority_skills,
        "matched_priority_skills": priority_overlap,
        "suggested_keywords": extract_top_keywords(cleaned_job),
    }


def calculate_similarity(resume_text: str, job_description: str) -> float:
    if not resume_text or not job_description:
        return 0.0

    vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
    matrix = vectorizer.fit_transform([resume_text, job_description])
    return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])


def calculate_weighted_skill_score(
    job_skills: list[str], priority_skills: list[str], skill_overlap: list[str]
) -> float:
    if not job_skills:
        return 0.0

    weight_map = {skill: 1.0 for skill in set(job_skills)}
    for skill in priority_skills:
        weight_map[skill] = 1.8

    matched_weight = sum(weight_map.get(skill, 1.0) for skill in skill_overlap)
    total_weight = sum(weight_map.values())
    return matched_weight / total_weight if total_weight else 0.0


def calculate_section_alignment(resume_text: str, job_description: str) -> float:
    resume_sentences = split_sentences(resume_text)
    job_sentences = split_sentences(job_description)
    if not resume_sentences or not job_sentences:
        return 0.0

    jd_keywords = set(extract_top_keywords(job_description, limit=12))
    matched_sentences = 0
    for sentence in resume_sentences:
        sentence_tokens = set(preprocess_text(sentence).split())
        if sentence_tokens & jd_keywords:
            matched_sentences += 1

    return min(matched_sentences / max(len(job_sentences), 1), 1.0)


def serialize_list(values: list[str]) -> str:
    return json.dumps(values)


def deserialize_list(payload: str) -> list[str]:
    try:
        return json.loads(payload or "[]")
    except json.JSONDecodeError:
        return []
