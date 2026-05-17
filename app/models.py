from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class JobRole(Base):
    __tablename__ = "job_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    department: Mapped[str] = mapped_column(Text, default="")
    location: Mapped[str] = mapped_column(Text, default="")
    employment_type: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="Open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    applications: Mapped[list["JobApplication"]] = relationship(
        "JobApplication",
        back_populates="job",
        cascade="all, delete-orphan",
    )


class JobApplication(Base):
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_roles.id"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    stored_file_name: Mapped[str] = mapped_column(Text, nullable=False)
    resume_path: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[str] = mapped_column(Text, default="[]")
    education: Mapped[str] = mapped_column(Text, default="[]")
    experience_highlights: Mapped[str] = mapped_column(Text, default="[]")
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    skill_score: Mapped[float] = mapped_column(Float, default=0)
    similarity_score: Mapped[float] = mapped_column(Float, default=0)
    experience_score: Mapped[float] = mapped_column(Float, default=0)
    final_score: Mapped[float] = mapped_column(Float, default=0)
    match_percentage: Mapped[float] = mapped_column(Float, default=0)
    rank_position: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped[JobRole] = relationship("JobRole", back_populates="applications")


class JobRequest(Base):
    __tablename__ = "job_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    file_name: Mapped[str] = mapped_column(Text, nullable=False)
    stored_file_name: Mapped[str] = mapped_column(Text, nullable=False)
    resume_path: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, default="")
    phone: Mapped[str] = mapped_column(Text, default="")
    requested_role: Mapped[str] = mapped_column(Text, default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[str] = mapped_column(Text, default="[]")
    education: Mapped[str] = mapped_column(Text, default="[]")
    experience_highlights: Mapped[str] = mapped_column(Text, default="[]")
    extracted_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
