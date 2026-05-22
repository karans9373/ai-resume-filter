const screeningForm = document.getElementById("screening-form");
const submitButton = document.getElementById("submit-button");
const statusMessage = document.getElementById("status-message");
const resultsCards = document.getElementById("results-cards");
const totalCandidates = document.getElementById("total-candidates");
const topMatch = document.getElementById("top-match");
const averageMatch = document.getElementById("average-match");
const loadSampleButton = document.getElementById("load-sample-button");
const jobDescriptionField = document.getElementById("job_description");

const publicJobsGrid = document.getElementById("public-jobs-grid");
const selectedPublicJobEmpty = document.getElementById("selected-public-job-empty");
const selectedPublicJobView = document.getElementById("selected-public-job-view");
const selectedPublicJobTitle = document.getElementById("selected-public-job-title");
const selectedPublicJobMeta = document.getElementById("selected-public-job-meta");
const selectedPublicJobStatus = document.getElementById("selected-public-job-status");
const selectedPublicJobCount = document.getElementById("selected-public-job-count");
const selectedPublicJobDescription = document.getElementById("selected-public-job-description");
const selectedRoleApplyCard = document.getElementById("selected-role-apply-card");

const profileMatchForm = document.getElementById("profile-match-form");
const matchedProfileCard = document.getElementById("matched-profile-card");
const atsScoreCard = document.getElementById("ats-score-card");
const atsScoreValue = document.getElementById("ats-score-value");
const atsScoreLabel = document.getElementById("ats-score-label");
const atsScoreRating = document.getElementById("ats-score-rating");
const atsSkillScore = document.getElementById("ats-skill-score");
const atsSimilarityScore = document.getElementById("ats-similarity-score");
const atsExperienceScore = document.getElementById("ats-experience-score");
const matchedJobsGrid = document.getElementById("matched-jobs-grid");
const matchStatus = document.getElementById("match-status");
const requestFallbackBox = document.getElementById("request-fallback-box");
const requestFallbackButton = document.getElementById("request-fallback-button");
const requestStatus = document.getElementById("request-status");

const futureJobRequestForm = document.getElementById("future-job-request-form");
const futureRequestStatus = document.getElementById("future-request-status");

const sampleRole = `We are hiring an AI/ML engineer with experience in Python, FastAPI, NLP, scikit-learn, TensorFlow, SQL, MongoDB, REST API development, HTML, CSS, Git, and candidate screening systems. The ideal applicant should have strong communication skills and experience building data-driven web applications.`;

const publicState = {
  jobs: [],
  selectedJobId: null,
};

let latestCandidateProfile = null;
let latestResumeFile = null;
let lastMatchedJobs = [];

document.addEventListener("DOMContentLoaded", async () => {
  hydrateStoredCandidateProfile();
  loadSampleButton?.addEventListener("click", () => {
    jobDescriptionField.value = sampleRole;
  });

  screeningForm?.addEventListener("submit", handleScreeningSubmit);
  profileMatchForm?.addEventListener("submit", handleProfileMatchSubmit);
  requestFallbackButton?.addEventListener("click", openFutureRequestPage);
  futureJobRequestForm?.addEventListener("submit", handleDedicatedFutureRequest);

  if (publicJobsGrid) {
    await loadPublicJobs();
  }
});

async function loadPublicJobs() {
  try {
    const response = await fetch("/api/public/jobs");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Unable to load open roles.");
    }

    publicState.jobs = payload;
    publicState.selectedJobId = payload[0]?.id || null;
    renderPublicJobs();
    renderSelectedPublicJob();
  } catch (error) {
    if (publicJobsGrid) {
      publicJobsGrid.innerHTML = `
        <div class="empty-panel compact-empty">
          <div>
            <h2>Roles could not load</h2>
            <p>${escapeHtml(error.message || "Please try again shortly.")}</p>
          </div>
        </div>
      `;
    }
  }
}

function renderPublicJobs() {
  if (!publicJobsGrid) {
    return;
  }

  if (!publicState.jobs.length) {
    publicJobsGrid.innerHTML = `
      <div class="empty-panel compact-empty">
        <div>
          <h2>No open roles listed</h2>
          <p>HR has not published any open jobs yet.</p>
        </div>
      </div>
    `;
    return;
  }

  publicJobsGrid.innerHTML = publicState.jobs.map((job, index) => `
    <button type="button" class="public-job-card public-job-button ${job.id === publicState.selectedJobId ? "active" : ""}" data-public-job-id="${job.id}" style="animation-delay:${index * 70}ms">
      <div class="public-job-top">
        <h3>${escapeHtml(job.title)}</h3>
        <span class="meta-pill">${escapeHtml(job.status)}</span>
      </div>
      <p>${escapeHtml(compactJobMeta(job))}</p>
      <div class="public-job-stats">
        <span>${job.application_count} application(s)</span>
        <span>Listed by HR</span>
      </div>
      <p class="public-job-description clamp-text">${escapeHtml(job.description)}</p>
      <span class="job-open-link">Read role and analyze below</span>
    </button>
  `).join("");

  document.querySelectorAll("[data-public-job-id]").forEach((button) => {
    button.addEventListener("click", () => {
      publicState.selectedJobId = Number(button.dataset.publicJobId);
      renderPublicJobs();
      renderSelectedPublicJob();
    });
  });
}

function renderSelectedPublicJob() {
  if (!selectedPublicJobEmpty || !selectedPublicJobView) {
    return;
  }

  const job = publicState.jobs.find((item) => item.id === publicState.selectedJobId);
  if (!job) {
    selectedPublicJobEmpty.classList.remove("hidden");
    selectedPublicJobView.classList.add("hidden");
    selectedRoleApplyCard?.classList.add("hidden");
    return;
  }

  selectedPublicJobEmpty.classList.add("hidden");
  selectedPublicJobView.classList.remove("hidden");
  selectedPublicJobTitle.textContent = job.title;
  selectedPublicJobMeta.textContent = compactJobMeta(job);
  selectedPublicJobStatus.textContent = job.status;
  selectedPublicJobCount.textContent = `${job.application_count} application(s)`;
  selectedPublicJobDescription.textContent = job.description;

  if (latestCandidateProfile) {
    renderSelectedRoleApply(job, lastMatchedJobs);
  } else {
    selectedRoleApplyCard?.classList.add("hidden");
  }
}

async function handleScreeningSubmit(event) {
  event.preventDefault();
  const formData = new FormData(screeningForm);
  const files = document.getElementById("resumes").files;

  if (!files.length) {
    setStatus("Please upload at least one resume file.");
    return;
  }

  submitButton.disabled = true;
  submitButton.textContent = "Analyzing...";
  setStatus("Processing resumes and building the ranked shortlist...");

  try {
    const response = await fetch("/api/screen", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();

    if (!response.ok) {
      const detail = typeof payload.detail === "string"
        ? payload.detail
        : payload.detail?.message || "Unable to process the submitted resumes.";
      throw new Error(detail);
    }

    renderResults(payload.ranked_candidates || []);
    setStatus(`Analysis complete. Ranked ${payload.total_candidates} candidate(s).`);
  } catch (error) {
    renderResults([]);
    setStatus(error.message || "Something went wrong while screening resumes.");
  } finally {
    submitButton.disabled = false;
    submitButton.textContent = "Analyze Resumes";
  }
}

async function handleProfileMatchSubmit(event) {
  event.preventDefault();
  const selectedJob = publicState.jobs.find((item) => item.id === publicState.selectedJobId);
  if (!selectedJob) {
    setText(matchStatus, "Please select a role first.");
    return;
  }

  const fileInput = document.getElementById("match_resume");
  const resumeFile = fileInput.files[0];
  if (!resumeFile) {
    setText(matchStatus, "Please upload your resume first.");
    return;
  }

  const formData = new FormData(profileMatchForm);
  formData.set("selected_job_id", String(selectedJob.id));
  latestResumeFile = resumeFile;
  setText(matchStatus, "Reading your resume and finding matching roles...");
  renderAnalyzingState(selectedJob);

  try {
    const response = await fetch("/api/public/match-jobs", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Unable to match your resume with open roles.");
    }

    latestCandidateProfile = payload.profile;
    lastMatchedJobs = payload.matches || [];
    storeCandidateProfile();
    renderMatchedProfile(payload.profile);
    renderAtsScore(payload.selected_job_match, payload.top_overall_match, selectedJob);
    renderMatchedJobs(lastMatchedJobs);
    renderSelectedRoleApply(selectedJob, lastMatchedJobs, payload.selected_job_match);
    setText(
      matchStatus,
      payload.has_matches
        ? "Your resume was analyzed. Review the selected role result first, then apply."
        : "No direct listed role matched enough. Use the future request page to send your resume to HR."
    );
    requestFallbackBox?.classList.toggle("hidden", payload.has_matches);
  } catch (error) {
    renderMatchError(error.message || "Something went wrong while matching your resume.");
    setText(matchStatus, error.message || "Something went wrong while matching your resume.");
  }
}

function renderAnalyzingState(selectedJob) {
  if (matchedProfileCard) {
    matchedProfileCard.innerHTML = `
      <strong>Analyzing uploaded resume</strong>
      <p>Your profile, contact details, and extracted skills will appear here in a moment.</p>
    `;
  }

  if (matchedJobsGrid) {
    matchedJobsGrid.innerHTML = `
      <div class="empty-panel compact-empty">
        <div>
          <h2>Checking suggested jobs</h2>
          <p>We are comparing your resume with all listed roles from HR.</p>
        </div>
      </div>
    `;
  }

  if (atsScoreCard) {
    atsScoreCard.classList.remove("hidden");
    atsScoreValue.textContent = "...";
    atsScoreLabel.textContent = `Checking ATS-style fit for ${selectedJob.title}.`;
    if (atsScoreRating) {
      atsScoreRating.textContent = "Calculating";
      atsScoreRating.className = "ats-rating-badge";
    }
    atsSkillScore.textContent = "Skill ...";
    atsSimilarityScore.textContent = "Similarity ...";
    atsExperienceScore.textContent = "Experience ...";
  }

  if (selectedRoleApplyCard) {
    selectedRoleApplyCard.classList.remove("hidden");
    selectedRoleApplyCard.innerHTML = `
      <div class="apply-focus-head">
        <div>
          <strong>${escapeHtml(selectedJob.title)}</strong>
          <p>We are checking how your uploaded resume fits this selected role.</p>
        </div>
        <span class="ranked-score-pill small-score">...</span>
      </div>
    `;
  }
}

function renderMatchError(message) {
  if (matchedProfileCard) {
    matchedProfileCard.innerHTML = `
      <strong>Resume analysis could not finish</strong>
      <p>${escapeHtml(message)}</p>
    `;
  }

  if (matchedJobsGrid) {
    matchedJobsGrid.innerHTML = `
      <div class="empty-panel compact-empty">
        <div>
          <h2>Suggested jobs unavailable right now</h2>
          <p>${escapeHtml(message)}</p>
        </div>
      </div>
    `;
  }

  if (atsScoreCard) {
    atsScoreCard.classList.remove("hidden");
    atsScoreValue.textContent = "--";
    atsScoreLabel.textContent = message;
    if (atsScoreRating) {
      atsScoreRating.textContent = "Unavailable";
      atsScoreRating.className = "ats-rating-badge";
    }
    atsSkillScore.textContent = "Skill --";
    atsSimilarityScore.textContent = "Similarity --";
    atsExperienceScore.textContent = "Experience --";
  }
}

function renderAtsScore(selectedJobMatch, topOverallMatch, selectedJob) {
  if (!atsScoreCard) {
    return;
  }

  const scoreSource = selectedJobMatch || topOverallMatch;
  if (!scoreSource) {
    atsScoreCard.classList.add("hidden");
    return;
  }

  const usingSelectedRole = selectedJobMatch && Number(selectedJobMatch.id) === Number(selectedJob.id);
  atsScoreCard.classList.remove("hidden");
  const score = Number(scoreSource.match_percentage || 0);
  const rating = getAtsRating(score);
  atsScoreValue.textContent = `${formatScore(score)}%`;
  atsScoreLabel.textContent = usingSelectedRole
    ? `ATS-style fit for ${selectedJob.title}`
    : `Best ATS-style fit found for ${scoreSource.title}`;
  if (atsScoreRating) {
    atsScoreRating.textContent = rating.label;
    atsScoreRating.className = `ats-rating-badge ${rating.className}`;
  }
  atsSkillScore.textContent = `Skill ${formatScore(scoreSource.skill_score)}%`;
  atsSimilarityScore.textContent = `Similarity ${formatScore(scoreSource.similarity_score)}%`;
  atsExperienceScore.textContent = `Experience ${formatScore(scoreSource.experience_score)}%`;
}

function getAtsRating(score) {
  if (score >= 80) {
    return { label: "Excellent", className: "excellent" };
  }
  if (score >= 65) {
    return { label: "Good", className: "good" };
  }
  if (score >= 45) {
    return { label: "Average", className: "average" };
  }
  return { label: "Needs Improvement", className: "needs-work" };
}

function renderSelectedRoleApply(selectedJob, matches, selectedJobMatch) {
  if (!selectedRoleApplyCard) {
    return;
  }

  const matchedJob = selectedJobMatch || matches.find((item) => Number(item.id) === Number(selectedJob.id));
  if (!matchedJob) {
    selectedRoleApplyCard.classList.remove("hidden");
    selectedRoleApplyCard.innerHTML = `
      <div class="apply-focus-head">
        <div>
          <strong>${escapeHtml(selectedJob.title)}</strong>
          <p>This selected role is visible, but your resume is not a strong enough match yet.</p>
        </div>
        <span class="ranked-score-pill small-score">Low Fit</span>
      </div>
      <div class="ranked-metric-row">
        <span class="meta-pill">Try another listed role</span>
        <span class="meta-pill">Or send to HR for future reference</span>
      </div>
    `;
    return;
  }

  selectedRoleApplyCard.classList.remove("hidden");
  selectedRoleApplyCard.innerHTML = `
    <div class="apply-focus-head">
      <div>
        <strong>${escapeHtml(matchedJob.title)}</strong>
        <p>${escapeHtml(matchedJob.summary || "Your profile matches this role.")}</p>
      </div>
      <span class="ranked-score-pill small-score">${formatScore(matchedJob.match_percentage)}%</span>
    </div>
    <div class="ranked-metric-row">
      <span class="meta-pill">Skill ${formatScore(matchedJob.skill_score)}%</span>
      <span class="meta-pill">Similarity ${formatScore(matchedJob.similarity_score)}%</span>
      <span class="meta-pill">Experience ${formatScore(matchedJob.experience_score)}%</span>
    </div>
    <div class="skill-list">${(matchedJob.matched_skills || []).map((skill) => `<span>${escapeHtml(skill)}</span>`).join("")}</div>
    <button type="button" class="candidate-primary-button inline-apply-button selected-apply-button" data-job-id="${matchedJob.id}">Apply For This Role</button>
  `;

  selectedRoleApplyCard.querySelector(".selected-apply-button")?.addEventListener("click", () => {
    handleApply(matchedJob.id);
  });
}

async function handleApply(jobId) {
  if (!latestCandidateProfile || !latestResumeFile) {
    setText(matchStatus, "Upload and analyze your resume before applying.");
    return;
  }

  const formData = new FormData();
  formData.append("candidate_name", latestCandidateProfile.candidate_name || "");
  formData.append("email", latestCandidateProfile.email || "");
  formData.append("phone", latestCandidateProfile.phone || "");
  formData.append("resume", latestResumeFile);

  setText(matchStatus, "Sending your application...");

  try {
    const response = await fetch(`/api/public/jobs/${jobId}/apply`, {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Unable to submit your application.");
    }

    setText(matchStatus, `Applied successfully for ${payload.job_title}.`);
    await loadPublicJobs();
  } catch (error) {
    setText(matchStatus, error.message || "Something went wrong while applying.");
  }
}

function renderMatchedProfile(profile) {
  if (!matchedProfileCard) {
    return;
  }

  matchedProfileCard.innerHTML = `
    <strong>${escapeHtml(profile.candidate_name || "Candidate profile")}</strong>
    <p>${escapeHtml(profile.summary || "Profile summary generated from uploaded resume.")}</p>
    <div class="ranked-contact-grid">
      <span>Email: ${escapeHtml(profile.email || "Not found")}</span>
      <span>Phone: ${escapeHtml(profile.phone || "Not found")}</span>
    </div>
    <div class="skill-list">${(profile.skills || []).map((skill) => `<span>${escapeHtml(skill)}</span>`).join("")}</div>
  `;
}

function renderMatchedJobs(matches) {
  if (!matchedJobsGrid) {
    return;
  }

  const filteredMatches = matches.filter((job) => Number(job.id) !== Number(publicState.selectedJobId));
  if (!filteredMatches.length) {
    matchedJobsGrid.innerHTML = `
      <div class="empty-panel compact-empty">
        <div>
          <h2>No other matched roles found</h2>
          <p>The selected role result is shown above. If no strong fit exists, use the future request option.</p>
        </div>
      </div>
    `;
    return;
  }

  matchedJobsGrid.innerHTML = filteredMatches.map((job, index) => `
    <article class="public-job-card matched-job-card" style="animation-delay:${index * 80}ms">
      <div class="public-job-top">
        <h3>${escapeHtml(job.title)}</h3>
        <span class="ranked-score-pill small-score">${formatScore(job.match_percentage)}%</span>
      </div>
      <p>${escapeHtml(compactJobMeta(job))}</p>
      <div class="ranked-metric-row">
        <span class="meta-pill">Skill ${formatScore(job.skill_score)}%</span>
        <span class="meta-pill">Similarity ${formatScore(job.similarity_score)}%</span>
        <span class="meta-pill">Experience ${formatScore(job.experience_score)}%</span>
      </div>
      <div class="skill-list">${(job.matched_skills || []).map((skill) => `<span>${escapeHtml(skill)}</span>`).join("")}</div>
      <p class="public-job-description">${escapeHtml(job.summary)}</p>
      <button type="button" class="candidate-primary-button inline-apply-button" data-job-id="${job.id}">Apply</button>
    </article>
  `).join("");

  document.querySelectorAll(".inline-apply-button").forEach((button) => {
    button.addEventListener("click", () => handleApply(button.dataset.jobId));
  });
}

function openFutureRequestPage() {
  if (latestCandidateProfile) {
    storeCandidateProfile();
  }
  window.open("/candidate/job-request", "_blank");
}

async function handleDedicatedFutureRequest(event) {
  event.preventDefault();
  const formData = new FormData(futureJobRequestForm);
  const resume = document.getElementById("future_resume")?.files?.[0];
  if (!resume) {
    setText(futureRequestStatus, "Please upload your resume first.");
    return;
  }

  setText(futureRequestStatus, "Sending your request to HR...");
  try {
    const response = await fetch("/api/public/job-requests", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Unable to send your request.");
    }

    setText(futureRequestStatus, "Sent successfully. HR can now review your resume, phone number, email, and request details.");
    futureJobRequestForm.reset();
    clearStoredCandidateProfile();
  } catch (error) {
    setText(futureRequestStatus, error.message || "Something went wrong while sending your request.");
  }
}

function hydrateStoredCandidateProfile() {
  const raw = window.localStorage.getItem("candidateProfileDraft");
  if (!raw) {
    return;
  }

  try {
    const draft = JSON.parse(raw);
    const nameField = document.getElementById("match_candidate_name") || document.getElementById("future_candidate_name");
    const emailField = document.getElementById("match_email") || document.getElementById("future_email");
    const phoneField = document.getElementById("match_phone") || document.getElementById("future_phone");
    const requestedRoleField = document.getElementById("future_requested_role");

    if (document.getElementById("match_candidate_name")) {
      document.getElementById("match_candidate_name").value = draft.candidate_name || "";
      document.getElementById("match_email").value = draft.email || "";
      document.getElementById("match_phone").value = draft.phone || "";
    }

    if (nameField && nameField.id.startsWith("future")) {
      nameField.value = draft.candidate_name || "";
      emailField.value = draft.email || "";
      phoneField.value = draft.phone || "";
      if (requestedRoleField && !requestedRoleField.value) {
        requestedRoleField.value = draft.requested_role || "Any future role related to my resume";
      }
    }
  } catch (error) {
    window.localStorage.removeItem("candidateProfileDraft");
  }
}

function storeCandidateProfile() {
  const requestedRole = publicState.jobs.find((item) => item.id === publicState.selectedJobId)?.title || "";
  const payload = {
    ...latestCandidateProfile,
    requested_role: requestedRole,
  };
  window.localStorage.setItem("candidateProfileDraft", JSON.stringify(payload));
}

function clearStoredCandidateProfile() {
  window.localStorage.removeItem("candidateProfileDraft");
}

function setStatus(message) {
  if (statusMessage) {
    statusMessage.textContent = message;
  }
}

function renderResults(candidates) {
  if (!resultsCards) {
    return;
  }

  if (!candidates.length) {
    resultsCards.innerHTML = `
      <div class="empty-panel compact-empty">
        <div>
          <h2>No screening results yet</h2>
          <p>Upload resumes above to generate ranked result cards.</p>
        </div>
      </div>
    `;
    if (totalCandidates) totalCandidates.textContent = "0";
    if (topMatch) topMatch.textContent = "0%";
    if (averageMatch) averageMatch.textContent = "0%";
    return;
  }

  const average = candidates.reduce((sum, candidate) => sum + candidate.match_percentage, 0) / candidates.length;
  if (totalCandidates) totalCandidates.textContent = String(candidates.length);
  if (topMatch) topMatch.textContent = `${formatScore(candidates[0].match_percentage)}%`;
  if (averageMatch) averageMatch.textContent = `${formatScore(average)}%`;

  resultsCards.innerHTML = candidates.map((candidate, index) => `
    <article class="ranked-result-card" style="animation-delay:${index * 80}ms">
      <div class="ranked-result-top">
        <div>
          <span class="rank-badge">#${candidate.rank_position}</span>
          <h3>${escapeHtml(candidate.candidate_name)}</h3>
          <p class="candidate-file">${escapeHtml(candidate.file_name)}</p>
        </div>
        <div class="ranked-score-pill">${formatScore(candidate.match_percentage)}%</div>
      </div>

      <div class="ranked-contact-grid">
        <span>Email: ${escapeHtml(candidate.email || "Not found")}</span>
        <span>Phone: ${escapeHtml(candidate.phone || "Not found")}</span>
      </div>

      <div class="ranked-metric-row">
        <span class="meta-pill">Skill ${formatScore(candidate.skill_score)}%</span>
        <span class="meta-pill">Similarity ${formatScore(candidate.similarity_score)}%</span>
        <span class="meta-pill">Experience ${formatScore(candidate.experience_score)}%</span>
      </div>

      <div class="skill-list">${(candidate.skills || []).map((skill) => `<span>${escapeHtml(skill)}</span>`).join("")}</div>

      <div class="meta-list">
        ${renderMeta(candidate.education, "Education")}
        ${renderMeta(candidate.experience_highlights, "Experience")}
      </div>
    </article>
  `).join("");
}

function renderMeta(items, label) {
  if (!items?.length) {
    return `<span>${label}: not found</span>`;
  }
  return items.map((item) => `<span>${label}: ${escapeHtml(item)}</span>`).join("");
}

function compactJobMeta(job) {
  return [job.department, job.location, job.employment_type].filter(Boolean).join(" | ") || "Role details available";
}

function formatScore(value) {
  return Number(value || 0).toFixed(1);
}

function setText(element, text) {
  if (element) {
    element.textContent = text;
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}
