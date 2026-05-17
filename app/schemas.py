from pydantic import BaseModel


class CandidateSchema(BaseModel):
    rank_position: int
    candidate_name: str
    file_name: str
    email: str
    phone: str
    skills: list[str]
    education: list[str]
    experience_highlights: list[str]
    skill_score: float
    similarity_score: float
    experience_score: float
    final_score: float
    match_percentage: float


class ScreeningResponse(BaseModel):
    total_candidates: int
    ranked_candidates: list[CandidateSchema]
