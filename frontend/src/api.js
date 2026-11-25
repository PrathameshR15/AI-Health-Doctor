const API_BASE_URL = "/api";

export const getAuthToken = () => localStorage.getItem("sh_token");
export const setAuthToken = (token) => localStorage.setItem("sh_token", token);
export const removeAuthToken = () => localStorage.removeItem("sh_token");

export const getUser = () => {
  const u = localStorage.getItem("sh_user");
  return u ? JSON.parse(u) : null;
};
export const setUser = (user) => localStorage.setItem("sh_user", JSON.stringify(user));
export const removeUser = () => localStorage.removeItem("sh_user");

async function request(endpoint, options = {}) {
  const token = getAuthToken();
  const headers = {
    ...options.headers,
  };

  // Only set Content-Type if body is not FormData
  if (!(options.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (response.status === 401) {
    removeAuthToken();
    removeUser();
    window.dispatchEvent(new Event("auth-changed"));
    throw new Error("Session expired. Please log in again.");
  }

  if (!response.ok) {
    let errMessage = `Error ${response.status}`;
    try {
      const errData = await response.json();
      errMessage = errData.detail || JSON.stringify(errData);
    } catch {
      errMessage = await response.text();
    }
    throw new Error(errMessage);
  }

  return response.json();
}

export const api = {
  // Auth
  login: (email, password) => request("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) }),
  register: (data) => request("/auth/register", { method: "POST", body: JSON.stringify(data) }),
  getProfile: () => request("/auth/me"),
  updateProfile: (data) => request("/auth/profile", { method: "PUT", body: JSON.stringify(data) }),
  updateConsent: (consent) => request("/auth/consent", { method: "POST", body: JSON.stringify({ consent }) }),

  // Feature 1: AI Virtual Doctor / Symptom Checker
  startSymptomSession: (chief_complaint) => request("/symptom-checker/start", { method: "POST", body: JSON.stringify({ chief_complaint }) }),
  answerSymptomQuestion: (session_id, answer) => request("/symptom-checker/answer", { method: "POST", body: JSON.stringify({ session_id, answer }) }),
  getSymptomSessions: () => request("/symptom-checker/sessions"),
  getSymptomSessionDetail: (id) => request(`/symptom-checker/session/${id}`),
  getDoctorReviewStatus: (assessment_id) => request(`/symptom-checker/doctor-status/${assessment_id}`),
  getPatientConsultationHistory: () => request("/symptom-checker/patient-history"),
  startFollowUpSession: (previous_session_id, progress_update = "") => request("/symptom-checker/follow-up-start", { method: "POST", body: JSON.stringify({ previous_session_id, progress_update }) }),

  // Feature 2: Medical Reports
  uploadReport: (formData) => request("/reports/upload", { method: "POST", body: formData }),
  getReports: () => request("/reports/list"),
  getReportDetail: (id) => request(`/reports/${id}`),

  // Feature 3: Medical History & FHIR
  getHistorySummary: (patient_id = null) => request(`/history/summary${patient_id ? `?patient_id=${patient_id}` : ""}`),
  exportFHIRBundle: (patient_id = null) => request(`/history/fhir-export${patient_id ? `?patient_id=${patient_id}` : ""}`),

  // Feature 4: Health Precautions
  getPrecautions: (symptoms_or_conditions) => request("/precautions/guidance", { method: "POST", body: JSON.stringify({ symptoms_or_conditions }) }),

  // Feature 5: Medical Test Guidance
  getTestGuidance: (symptoms_or_condition) => request("/tests/guidance", { method: "POST", body: JSON.stringify({ symptoms_or_condition }) }),

  // Feature 6: Allergy & Diet Assistant
  getAllergiesAndDiet: (patient_id = null) => request(`/allergy-diet/my-records${patient_id ? `?patient_id=${patient_id}` : ""}`),
  addAllergyRecord: (data) => request("/allergy-diet/add", { method: "POST", body: JSON.stringify(data) }),
  doctorApproveDiet: (record_id, data) => request(`/allergy-diet/doctor-approve/${record_id}`, { method: "PUT", body: JSON.stringify(data) }),

  // Feature 7: Doctor Consultation Summary
  generateConsultationSOAP: (data) => request("/consultation/generate", { method: "POST", body: JSON.stringify(data) }),

  // Feature 8: Symptom-Based Medication Education
  getMedicationInfo: (symptoms_or_condition, medication_name = null) => request("/medication/info", { method: "POST", body: JSON.stringify({ symptoms_or_condition, medication_name }) }),

  // Unified Health Analysis
  analyzeFullHealth: (data) => request("/analyze/full-assessment", { method: "POST", body: JSON.stringify(data) }),
  getPreviousAssessments: () => request("/analyze/previous"),
  getAssessmentDetail: (id) => request(`/analyze/detail/${id}`),

  // Doctor Portal
  getDoctorDashboard: () => request("/doctor/dashboard-stats"),
  getDoctorPatients: (search = "") => request(`/doctor/patients${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  getDoctorPatientDetail: (id) => request(`/doctor/patient/${id}`),
  getDoctorAssessments: (statusFilter = "") => request(`/doctor/assessments${statusFilter ? `?status_filter=${statusFilter}` : ""}`),
  reviewAssessment: (id, data) => request(`/doctor/assessment-review/${id}`, { method: "POST", body: JSON.stringify(data) }),
  createDoctorNote: (data) => request("/doctor/notes", { method: "POST", body: JSON.stringify(data) }),

  // Medical Knowledge Search
  searchKnowledge: (q) => request(`/knowledge/search?q=${encodeURIComponent(q)}`),
  getAllGuidelines: () => request("/knowledge/all"),
};
