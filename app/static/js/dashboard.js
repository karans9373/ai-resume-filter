const state = {
  jobs: [],
  selectedJobId: null,
  activeTab: "roles",
};

const jobList = document.getElementById("job-list");
const jobsCount = document.getElementById("jobs-count");
const applicationsCount = document.getElementById("applications-count");
const createJobForm = document.getElementById("create-job-form");
const editJobForm = document.getElementById("edit-job-form");
const uploadForm = document.getElementById("upload-form");
const refreshJobsButton = document.getElementById("refresh-jobs-button");
const selectedJobEmpty = document.getElementById("selected-job-empty");
const selectedJobView = document.getElementById("selected-job-view");
const selectedJobTitle = document.getElementById("selected-job-title");
const selectedJobMeta = document.getElementById("selected-job-meta");
const selectedJobStatus = document.getElementById("selected-job-status");
const selectedJobCount = document.getElementById("selected-job-count");
const metricTotalApps = document.getElementById("metric-total-apps");
const metricTopMatch = document.getElementById("metric-top-match");
const metricAverageMatch = document.getElementById("metric-average-match");
const applicationGrid = document.getElementById("application-grid");
const roleCatalog = document.getElementById("role-catalog");
const jobRequestGrid = document.getElementById("job-request-grid");
const jobRequestsCount = document.getElementById("job-requests-count");
const jobFormStatus = document.getElementById("job-form-status");
const editJobStatus = document.getElementById("edit-job-status");
const uploadStatus = document.getElementById("upload-status");

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  loadDashboardData();
  switchTab("roles");
});

function bindEvents() {
  refreshJobsButton?.addEventListener("click", loadJobs);

  document.querySelectorAll("[data-tab]").forEach((button) => {
    button.addEventListener("click", () => switchTab(button.dataset.tab));
  });

  createJobForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(createJobForm);
    setText(jobFormStatus, "Creating role...");

    try {
      const response = await fetch("/api/hr/jobs", { method: "POST", body: formData });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Could not create the role.");
      }

      createJobForm.reset();
      setText(jobFormStatus, "Role created. Loading the new role now.");
      await loadJobs(payload.id);
      switchTab("applications");
    } catch (error) {
      setText(jobFormStatus, error.message || "Something went wrong while creating the role.");
    }
  });

  editJobForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.selectedJobId) {
      setText(editJobStatus, "Select a role before editing.");
      return;
    }

    const formData = new FormData(editJobForm);
    setText(editJobStatus, "Saving job changes...");

    try {
      const response = await fetch(`/api/hr/jobs/${state.selectedJobId}`, {
        method: "PATCH",
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Could not update the job.");
      }

      replaceJob(payload);
      renderDashboard();
      setText(editJobStatus, "Role updated successfully.");
    } catch (error) {
      setText(editJobStatus, error.message || "Something went wrong while updating the role.");
    }
  });

  uploadForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!state.selectedJobId) {
      setText(uploadStatus, "Select a role before uploading resumes.");
      return;
    }

    const files = document.getElementById("resume-files").files;
    if (!files.length) {
      setText(uploadStatus, "Please choose at least one resume file.");
      return;
    }

    const formData = new FormData(uploadForm);
    setText(uploadStatus, "Uploading resumes and scoring candidates...");

    try {
      const response = await fetch(`/api/hr/jobs/${state.selectedJobId}/applications`, {
        method: "POST",
        body: formData,
      });
      const payload = await response.json();
      if (!response.ok) {
        const detail = typeof payload.detail === "string" ? payload.detail : payload.detail?.message;
        throw new Error(detail || "Could not upload the applications.");
      }

      uploadForm.reset();
      replaceJob(payload);
      renderDashboard();
      setText(uploadStatus, `Added ${payload.uploaded_files?.length || 0} application(s).`);
    } catch (error) {
      setText(uploadStatus, error.message || "Something went wrong while uploading resumes.");
    }
  });
}

function switchTab(tabName) {
  state.activeTab = tabName;
  document.querySelectorAll(".dashboard-tab-button").forEach((button) => {
    button.classList.toggle("active", button.dataset.tab === tabName);
  });
  document.querySelectorAll(".dashboard-tab-panel").forEach((panel) => {
    panel.classList.toggle("hidden", panel.id !== `tab-${tabName}`);
  });
}

async function loadDashboardData(preferredJobId = null) {
  await Promise.all([loadJobs(preferredJobId), loadJobRequests()]);
}

async function loadJobs(preferredJobId = null) {
  try {
    const response = await fetch("/api/hr/jobs");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Could not load jobs.");
    }

    state.jobs = payload;
    if (preferredJobId) {
      state.selectedJobId = preferredJobId;
    } else if (!state.selectedJobId || !state.jobs.some((job) => job.id === state.selectedJobId)) {
      state.selectedJobId = state.jobs[0]?.id || null;
    }
    renderDashboard();
  } catch (error) {
    if (jobList) {
      jobList.innerHTML = `<div class="muted-copy">${escapeHtml(error.message || "Unable to load jobs.")}</div>`;
    }
  }
}

function renderDashboard() {
  renderJobList();
  renderRoleCatalog();
  updateCounts();
  renderSelectedJob();
}

function renderJobList() {
  if (!state.jobs.length) {
    jobList.innerHTML = `<div class="muted-copy">No roles yet. Create your first role to start collecting applications.</div>`;
    return;
  }

  jobList.innerHTML = state.jobs.map((job) => `
    <button type="button" class="job-list-item ${job.id === state.selectedJobId ? "active" : ""}" data-job-id="${job.id}">
      <h3>${escapeHtml(job.title)}</h3>
      <p>${escapeHtml(compactMeta(job))}</p>
      <small>${job.total_applications} application(s) | top ${formatScore(job.top_match)}%</small>
    </button>
  `).join("");

  document.querySelectorAll(".job-list-item").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedJobId = Number(button.dataset.jobId);
      renderDashboard();
      switchTab("applications");
    });
  });
}

function renderRoleCatalog() {
  if (!roleCatalog) {
    return;
  }

  if (!state.jobs.length) {
    roleCatalog.innerHTML = `
      <div class="empty-panel compact-empty">
        <div>
          <h2>No roles yet</h2>
          <p>Create a role first and it will appear here.</p>
        </div>
      </div>
    `;
    return;
  }

  roleCatalog.innerHTML = state.jobs.map((job) => `
    <button type="button" class="role-card ${job.id === state.selectedJobId ? "active" : ""}" data-role-card-id="${job.id}">
      <div class="role-card-top">
        <h3>${escapeHtml(job.title)}</h3>
        <span class="meta-pill">${escapeHtml(job.status)}</span>
      </div>
      <p>${escapeHtml(compactMeta(job))}</p>
      <div class="role-card-stats">
        <span>${job.total_applications} applications</span>
        <span>Top ${formatScore(job.top_match)}%</span>
        <span>Avg ${formatScore(job.average_match)}%</span>
      </div>
    </button>
  `).join("");

  document.querySelectorAll("[data-role-card-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedJobId = Number(button.dataset.roleCardId);
      renderDashboard();
      switchTab("applications");
    });
  });
}

function updateCounts() {
  const applications = state.jobs.reduce((sum, job) => sum + job.total_applications, 0);
  if (jobsCount) jobsCount.textContent = String(state.jobs.length);
  if (applicationsCount) applicationsCount.textContent = String(applications);
}

async function loadJobRequests() {
  if (!jobRequestGrid) {
    return;
  }

  try {
    const response = await fetch("/api/hr/job-requests");
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Could not load job requests.");
    }

    if (jobRequestsCount) {
      jobRequestsCount.textContent = String(payload.length);
    }

    if (!payload.length) {
      jobRequestGrid.innerHTML = `
        <div class="empty-panel compact-empty">
          <div>
            <h2>No job requests yet</h2>
            <p>When a candidate does not find a matching listed role, their request will appear here.</p>
          </div>
        </div>
      `;
      return;
    }

    jobRequestGrid.innerHTML = payload.map((request) => `
      <article class="application-card">
        <div class="application-top">
          <div>
            <span class="badge">Job Request</span>
            <h3 class="application-name">${escapeHtml(request.candidate_name)}</h3>
            <div class="candidate-subtle">${escapeHtml(request.requested_role || "General profile request")}</div>
          </div>
          <div class="application-score">
            <div class="candidate-subtle">${new Date(request.created_at).toLocaleDateString()}</div>
          </div>
        </div>

        <div class="application-contact">
          <span>Email: ${escapeHtml(request.email || "Not found")}</span>
          <span>Phone: ${escapeHtml(request.phone || "Not found")}</span>
        </div>

        <p class="application-summary">${escapeHtml(request.summary || "Profile summary not available.")}</p>

        <div class="application-skills">
          ${(request.skills || []).slice(0, 8).map((skill) => `<span class="application-skill">${escapeHtml(skill)}</span>`).join("")}
        </div>

        <div class="application-actions">
          <a class="solid-link" href="${request.resume_url}" target="_blank" rel="noreferrer">Open Resume</a>
          ${request.phone ? `<a class="ghost-link" href="tel:${escapeHtml(request.phone)}">Call Candidate</a>` : ""}
          ${request.email ? `<a class="ghost-link" href="mailto:${escapeHtml(request.email)}">Email Candidate</a>` : ""}
        </div>
      </article>
    `).join("");
  } catch (error) {
    jobRequestGrid.innerHTML = `<div class="muted-copy">${escapeHtml(error.message || "Unable to load job requests.")}</div>`;
  }
}

function renderSelectedJob() {
  const job = state.jobs.find((item) => item.id === state.selectedJobId);
  if (!job) {
    selectedJobEmpty.classList.remove("hidden");
    selectedJobView.classList.add("hidden");
    return;
  }

  selectedJobEmpty.classList.add("hidden");
  selectedJobView.classList.remove("hidden");

  selectedJobTitle.textContent = job.title;
  selectedJobMeta.textContent = compactMeta(job);
  selectedJobStatus.textContent = job.status;
  selectedJobCount.textContent = `${job.total_applications} application(s)`;
  metricTotalApps.textContent = String(job.total_applications);
  metricTopMatch.textContent = `${formatScore(job.top_match)}%`;
  metricAverageMatch.textContent = `${formatScore(job.average_match)}%`;
  fillEditForm(job);

  if (!job.applications.length) {
    applicationGrid.innerHTML = `
      <div class="empty-panel compact-empty">
        <div>
          <h2>No applications for this role yet</h2>
          <p>Upload resumes above and they will appear here with phone number, email, score, and resume preview links.</p>
        </div>
      </div>
    `;
    return;
  }

  applicationGrid.innerHTML = job.applications.map((application) => `
    <article class="application-card">
      <div class="application-top">
        <div>
          <span class="badge">Rank #${application.rank_position}</span>
          <h3 class="application-name">${escapeHtml(application.candidate_name)}</h3>
          <div class="candidate-subtle">${escapeHtml(application.file_name)}</div>
          <div class="application-contact">
            <span>Email: ${escapeHtml(application.email || "Not found")}</span>
            <span>Phone: ${escapeHtml(application.phone || "Not found")}</span>
          </div>
        </div>
        <div class="application-score">
          <div class="score-value">${formatScore(application.match_percentage)}%</div>
          <div class="candidate-subtle">AI match score</div>
        </div>
      </div>

      <p class="application-summary">${escapeHtml(application.summary || "Profile summary not available.")}</p>

      <div class="application-meta">
        <span class="meta-pill">Skill ${formatScore(application.skill_score)}%</span>
        <span class="meta-pill">Similarity ${formatScore(application.similarity_score)}%</span>
        <span class="meta-pill">Experience ${formatScore(application.experience_score)}%</span>
      </div>

      <div class="application-skills">
        ${(application.skills || []).slice(0, 8).map((skill) => `<span class="application-skill">${escapeHtml(skill)}</span>`).join("")}
      </div>

      <div class="application-actions">
        <a class="solid-link" href="${application.resume_url}" target="_blank" rel="noreferrer">Open Resume</a>
        ${application.phone ? `<a class="ghost-link" href="tel:${escapeHtml(application.phone)}">Call</a>` : ""}
        ${application.email ? `<a class="ghost-link" href="mailto:${escapeHtml(application.email)}">Email</a>` : ""}
        <button type="button" class="danger-button delete-application-button" data-id="${application.id}">Delete Candidate</button>
      </div>
    </article>
  `).join("");

  document.querySelectorAll(".delete-application-button").forEach((button) => {
    button.addEventListener("click", async () => {
      const applicationId = Number(button.dataset.id);
      const confirmed = window.confirm("Delete this candidate from the role list?");
      if (!confirmed) {
        return;
      }
      button.disabled = true;
      button.textContent = "Deleting...";
      await deleteApplication(applicationId);
    });
  });
}

function fillEditForm(job) {
  if (!editJobForm) {
    return;
  }

  document.getElementById("edit-title").value = job.title || "";
  document.getElementById("edit-department").value = job.department || "";
  document.getElementById("edit-location").value = job.location || "";
  document.getElementById("edit-employment-type").value = job.employment_type || "";
  document.getElementById("edit-status").value = job.status || "Open";
  document.getElementById("edit-description").value = job.description || "";
}

async function deleteApplication(applicationId) {
  try {
    const response = await fetch(`/api/hr/applications/${applicationId}`, { method: "DELETE" });
    const payload = await response.json();
    if (!response.ok) {
      throw new Error(payload.detail || "Could not delete the candidate.");
    }

    await loadJobs(state.selectedJobId);
  } catch (error) {
    alert(error.message || "Unable to delete the candidate.");
  }
}

function replaceJob(jobPayload) {
  const index = state.jobs.findIndex((job) => job.id === jobPayload.id);
  if (index >= 0) {
    state.jobs[index] = jobPayload;
  } else {
    state.jobs.unshift(jobPayload);
  }
  state.selectedJobId = jobPayload.id;
}

function compactMeta(job) {
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
