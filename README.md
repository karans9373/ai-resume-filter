# AI-Powered Resume Screening System

A modern HR web application for listing roles, receiving applications per role, opening uploaded resumes, viewing contact details, scoring candidates with AI-inspired ranking logic, and managing applicants in a clean dashboard.

## Features

- HR-only demo login and direct demo dashboard access
- Create and list job roles with title, department, location, type, and job description
- Upload multiple resumes for a specific role
- Support for PDF, DOCX, and TXT resume files
- Extract contact details, skills, education, and experience hints
- Apply NLP-style preprocessing with tokenization, stop-word removal, and light lemmatization
- Calculate weighted skill matching, job description similarity, section alignment, and final ranking scores
- View email, phone, short summary, AI score, and uploaded resume per candidate
- Delete candidates directly from the HR dashboard
- Persist jobs and applications in a local SQLite database

## Tech Stack

- Backend: FastAPI
- Frontend: HTML, CSS, JavaScript
- NLP/ML: Scikit-learn TF-IDF similarity with preprocessing, weighted skill extraction, and rule-based entity extraction
- Storage: SQLite by default with SQLAlchemy; easy to swap for PostgreSQL

## Run Locally

```bash
python -m uvicorn app.main:app --reload
```

Then open [http://127.0.0.1:8000](http://127.0.0.1:8000).

Demo HR credentials:

- Email: `hr@aetherresume.demo`
- Password: `HR12345`

## Main Routes

- `GET /`
- `GET /hr/login`
- `GET /hr/demo-login`
- `GET /hr/dashboard`
- `GET /hr/applications/{id}/resume`

## API Endpoints

- `GET /api/hr/jobs`
- `POST /api/hr/jobs`
- `GET /api/hr/jobs/{job_id}/applications`
- `POST /api/hr/jobs/{job_id}/applications`
- `DELETE /api/hr/applications/{application_id}`
- `GET /api/health`
- `GET /api/candidates`
- `POST /api/screen`

## Notes

- Image-only PDFs without selectable text cannot be parsed unless OCR is added.
- The app is designed as a standalone screening tool and does not include ATS integration or automated candidate communication.
- The preprocessing layer mirrors the synopsis workflow and is designed to be easy to upgrade to spaCy or NLTK later.

## Deployment

### Recommended backend deployment

This project is a FastAPI app with server-rendered HTML templates, file uploads, and a Python backend, so the simplest production deployment is a Python web host such as Render.

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --app-dir .`

### Netlify note

Netlify is a good fit for the frontend layer or custom domain/proxy setup, but this repository should not be deployed on Netlify by itself as a full Python app. If you want to use Netlify, deploy the FastAPI backend first on Render, then point Netlify to that backend with a proxy rule.
