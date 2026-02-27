const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000/api";

let authToken = localStorage.getItem("auth_token") || "";

export function setAuthToken(token) {
  authToken = token || "";
  if (authToken) {
    localStorage.setItem("auth_token", authToken);
  } else {
    localStorage.removeItem("auth_token");
  }
}

async function request(path, options = {}) {
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers,
    ...options,
  });

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || "Request failed");
  }

  return payload;
}

export const api = {
  login: (body) => request("/auth/login", { method: "POST", body: JSON.stringify(body) }),
  me: () => request("/auth/me"),

  listEmployers: () => request("/employers"),
  createEmployer: (body) => request("/employers", { method: "POST", body: JSON.stringify(body) }),
  listEmployerSteps: (employerId) => request(`/employers/${employerId}/steps`),
  createEmployerStep: (employerId, body) =>
    request(`/employers/${employerId}/steps`, { method: "POST", body: JSON.stringify(body) }),
  createUser: (body) => request("/users", { method: "POST", body: JSON.stringify(body) }),

  getSummary: () => request("/dashboard/summary"),
  listCandidates: () => request("/candidates"),
  getCandidate: (id) => request(`/candidates/${id}`),
  createCandidate: (body) => request("/candidates", { method: "POST", body: JSON.stringify(body) }),
  updateCandidate: (id, body) => request(`/candidates/${id}`, { method: "PATCH", body: JSON.stringify(body) }),
  createCheck: (candidateId, body) => request(`/candidates/${candidateId}/checks`, { method: "POST", body: JSON.stringify(body) }),
  updateCheck: (checkId, body) => request(`/checks/${checkId}`, { method: "PATCH", body: JSON.stringify(body) }),
  downloadCandidateReport: async ({ startDate, endDate, format }) => {
    const params = new URLSearchParams({
      start_date: startDate,
      end_date: endDate,
      format,
    });
    const response = await fetch(`${API_BASE_URL}/reports/candidates?${params.toString()}`, {
      headers: authToken ? { Authorization: `Bearer ${authToken}` } : {},
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => ({}));
      throw new Error(payload.error || "Request failed");
    }
    return response.blob();
  },
  seed: () => request("/seed", { method: "POST" }),
};
