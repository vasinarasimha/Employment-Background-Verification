import { useEffect, useMemo, useState } from "react";
import { api, setAuthToken } from "./api";

const initialLogin = { email: "", password: "" };
const initialCandidate = {
  full_name: "",
  email: "",
  phone: "",
  dob: "",
  position: "",
  credential_email: "",
  credential_password: "",
};
const initialCheck = { check_type: "employment", provider: "" };
const initialEmployer = { name: "" };
const initialStep = { check_type: "employment", default_provider: "" };
const initialUser = { full_name: "", email: "", password: "", role: "admin" };
const initialReportFilters = { startDate: "", endDate: "" };

function formatDate(value) {
  if (!value) return "-";
  return new Date(value).toLocaleString();
}

function downloadBlob(blob, filename) {
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

export default function App() {
  const [authUser, setAuthUser] = useState(null);
  const [loginForm, setLoginForm] = useState(initialLogin);

  const [summary, setSummary] = useState(null);
  const [employers, setEmployers] = useState([]);
  const [selectedEmployerId, setSelectedEmployerId] = useState("");
  const [steps, setSteps] = useState([]);
  const [candidates, setCandidates] = useState([]);
  const [selectedCandidateId, setSelectedCandidateId] = useState(null);
  const [selectedCandidate, setSelectedCandidate] = useState(null);

  const [candidateForm, setCandidateForm] = useState(initialCandidate);
  const [checkForm, setCheckForm] = useState(initialCheck);
  const [employerForm, setEmployerForm] = useState(initialEmployer);
  const [stepForm, setStepForm] = useState(initialStep);
  const [userForm, setUserForm] = useState(initialUser);
  const [reportFilters, setReportFilters] = useState(initialReportFilters);

  const [activeMenu, setActiveMenu] = useState("dashboard");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const role = authUser?.role || "";
  const isSuperAdmin = role === "super_admin";
  const isAdmin = role === "admin";
  const canCreateEmployer = isSuperAdmin || isAdmin;
  const canSeeReports = isSuperAdmin || isAdmin;
  const canManageCandidates = isSuperAdmin;
  const canCreateChecks = isSuperAdmin;
  const canVerifyChecks = isSuperAdmin || role === "agent";

  const selectedCandidateName = useMemo(() => {
    if (!selectedCandidate) return "None";
    return `${selectedCandidate.full_name} (${selectedCandidate.status})`;
  }, [selectedCandidate]);

  async function loadSummary() {
    const data = await api.getSummary();
    setSummary(data);
  }

  async function loadEmployers() {
    const data = await api.listEmployers();
    setEmployers(data);
    if (!selectedEmployerId && data.length > 0) {
      const defaultEmployerId = isSuperAdmin ? data[0].id : authUser?.employer_id || data[0].id;
      setSelectedEmployerId(String(defaultEmployerId));
    }
  }

  async function loadEmployerSteps(employerId) {
    if (!employerId) {
      setSteps([]);
      return;
    }
    const data = await api.listEmployerSteps(employerId);
    setSteps(data);
  }

  async function loadCandidates() {
    const data = await api.listCandidates();
    setCandidates(data);
    if (!selectedCandidateId && data.length > 0) {
      setSelectedCandidateId(data[0].id);
    }
    if (data.length === 0) {
      setSelectedCandidateId(null);
      setSelectedCandidate(null);
    }
  }

  async function loadCandidateDetails(candidateId) {
    if (!candidateId) {
      setSelectedCandidate(null);
      return;
    }
    const data = await api.getCandidate(candidateId);
    setSelectedCandidate(data);
  }

  async function bootstrap() {
    if (!authUser) return;
    setLoading(true);
    setError("");
    try {
      const tasks = [loadSummary(), loadEmployers()];
      if (!isAdmin) {
        tasks.push(loadCandidates());
      }
      await Promise.all(tasks);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    async function restoreSession() {
      try {
        const user = await api.me();
        setAuthUser(user);
      } catch {
        setAuthToken("");
      }
    }
    restoreSession();
  }, []);

  useEffect(() => {
    setActiveMenu("dashboard");
    bootstrap();
  }, [authUser]);

  useEffect(() => {
    if (selectedEmployerId) {
      loadEmployerSteps(selectedEmployerId).catch((err) => setError(err.message));
    }
  }, [selectedEmployerId]);

  useEffect(() => {
    if (!isAdmin && selectedCandidateId) {
      loadCandidateDetails(selectedCandidateId).catch((err) => setError(err.message));
    }
  }, [selectedCandidateId, isAdmin]);

  async function handleLogin(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);
    try {
      const data = await api.login(loginForm);
      setAuthToken(data.token);
      setAuthUser(data.user);
      setMessage(`Logged in as ${data.user.role}`);
      setLoginForm(initialLogin);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function handleLogout() {
    setAuthToken("");
    setAuthUser(null);
    setSummary(null);
    setCandidates([]);
    setEmployers([]);
    setSelectedEmployerId("");
    setSelectedCandidateId(null);
    setSelectedCandidate(null);
    setError("");
    setMessage("Logged out");
  }

  async function handleSeed() {
    setMessage("");
    setError("");
    try {
      const result = await api.seed();
      setMessage(result.message);
      await bootstrap();
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleCreateEmployer(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      const created = await api.createEmployer(employerForm);
      setEmployerForm(initialEmployer);
      setMessage(`Employer ${created.name} created`);
      await loadEmployers();
      setSelectedEmployerId(String(created.id));
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleCreateStep(event) {
    event.preventDefault();
    if (!selectedEmployerId) return;
    setError("");
    setMessage("");
    try {
      await api.createEmployerStep(selectedEmployerId, stepForm);
      setStepForm(initialStep);
      setMessage("Verification step added");
      await loadEmployerSteps(selectedEmployerId);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleCreateAccessUser(event) {
    event.preventDefault();
    if (!selectedEmployerId) return;
    setError("");
    setMessage("");
    try {
      await api.createUser({ ...userForm, employer_id: Number(selectedEmployerId) });
      setUserForm(initialUser);
      setMessage("Employer access user created");
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleCreateCandidate(event) {
    event.preventDefault();
    setMessage("");
    setError("");
    try {
      const body = { ...candidateForm };
      if (isSuperAdmin) {
        body.employer_id = Number(selectedEmployerId);
      }
      const created = await api.createCandidate(body);
      setCandidateForm(initialCandidate);
      setMessage(`Candidate ${created.full_name} created`);
      await bootstrap();
      setSelectedCandidateId(created.id);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleCreateCheck(event) {
    event.preventDefault();
    if (!selectedCandidateId) return;
    setMessage("");
    setError("");
    try {
      await api.createCheck(selectedCandidateId, checkForm);
      setCheckForm(initialCheck);
      setMessage("Background check initiated");
      await Promise.all([loadSummary(), loadCandidates(), loadCandidateDetails(selectedCandidateId)]);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleCheckUpdate(checkId, status) {
    setMessage("");
    setError("");
    try {
      await api.updateCheck(checkId, {
        status,
        result_notes: status === "passed" ? "No adverse findings" : "Potential discrepancy found; manual review required",
      });
      setMessage(`Check ${checkId} marked ${status}`);
      await Promise.all([loadSummary(), loadCandidates(), loadCandidateDetails(selectedCandidateId)]);
    } catch (err) {
      setError(err.message);
    }
  }

  async function handleReportDownload(format) {
    const { startDate, endDate } = reportFilters;
    if (!startDate || !endDate) {
      setError("start date and end date are required");
      return;
    }
    setError("");
    setMessage("");
    try {
      const blob = await api.downloadCandidateReport({ startDate, endDate, format });
      const fileName = format === "pdf" ? "candidate_report.pdf" : "candidate_report.xlsx";
      downloadBlob(blob, fileName);
      setMessage(`Downloaded ${fileName}`);
    } catch (err) {
      setError(err.message);
    }
  }

  if (!authUser) {
    return (
      <div className="layout">
        <header>
          <div>
            <h1>Employment Background Verification</h1>
            <p>Role-based verification workflow platform.</p>
          </div>
        </header>
        {error && <p className="error">{error}</p>}
        <article className="panel auth-panel">
          <h2>Login</h2>
          <p className="muted">Use credentials issued by your administrator.</p>
          <form onSubmit={handleLogin} className="stack">
            <input
              placeholder="Email"
              type="email"
              value={loginForm.email}
              onChange={(e) => setLoginForm({ ...loginForm, email: e.target.value })}
              required
            />
            <input
              placeholder="Password"
              type="password"
              value={loginForm.password}
              onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
              required
            />
            <button type="submit" disabled={loading}>
              Sign In
            </button>
          </form>
        </article>
      </div>
    );
  }

  return (
    <div className="layout">
      <header>
        <div>
          <h1>Employment Background Verification</h1>
          <p>
            Logged in: <strong>{authUser.full_name}</strong> ({authUser.role})
          </p>
        </div>
        <div className="row">
          {isSuperAdmin && <button onClick={handleSeed}>Seed Demo Data</button>}
          <button onClick={handleLogout}>Logout</button>
        </div>
      </header>

      {loading && <p>Loading...</p>}
      {error && <p className="error">{error}</p>}
      {message && <p className="message">{message}</p>}

      {(isAdmin || canSeeReports) && (
        <section className="panel">
          <div className="row">
            <button onClick={() => setActiveMenu("dashboard")}>Dashboard</button>
            <button onClick={() => setActiveMenu("employers")}>Employers</button>
            {canSeeReports && <button onClick={() => setActiveMenu("reports")}>Reports</button>}
          </div>
        </section>
      )}

      {(activeMenu === "dashboard" || !isAdmin) && (
        <section className="grid stats">
          {isAdmin ? (
            <>
              <article>
                <h3>Total Employers</h3>
                <strong>{summary?.total_employers ?? 0}</strong>
              </article>
              <article>
                <h3>Companies Using Portal</h3>
                <strong>{summary?.companies_with_candidates ?? 0}</strong>
              </article>
            </>
          ) : (
            <>
              <article>
                <h3>Total Candidates</h3>
                <strong>{summary?.total_candidates ?? 0}</strong>
              </article>
              <article>
                <h3>Pending</h3>
                <strong>{summary?.pending ?? 0}</strong>
              </article>
              <article>
                <h3>In Review</h3>
                <strong>{summary?.in_review ?? 0}</strong>
              </article>
              <article>
                <h3>Cleared / Flagged</h3>
                <strong>
                  {summary?.cleared ?? 0} / {summary?.flagged ?? 0}
                </strong>
              </article>
            </>
          )}
        </section>
      )}

      {(activeMenu === "employers" || !isAdmin) && (
        <>
          <section className="panel">
            <h2>Employer Context</h2>
            <div className="stack compact">
              <select value={selectedEmployerId} onChange={(e) => setSelectedEmployerId(e.target.value)}>
                {employers.map((employer) => (
                  <option key={employer.id} value={employer.id}>
                    {employer.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="checks">
              {steps.map((step) => (
                <div className="check-card" key={step.id}>
                  <p>
                    <strong>{step.check_type}</strong> via {step.default_provider}
                  </p>
                  <p className="muted">Active: {step.is_active ? "Yes" : "No"}</p>
                </div>
              ))}
              {!steps.length && <p className="muted">No employer verification steps configured.</p>}
            </div>
          </section>

          {canCreateEmployer && (
            <section className="grid content">
              <article className="panel">
                <h2>Create Employer</h2>
                <form onSubmit={handleCreateEmployer} className="stack">
                  <input
                    placeholder="Employer name"
                    value={employerForm.name}
                    onChange={(e) => setEmployerForm({ name: e.target.value })}
                    required
                  />
                  <button type="submit">Create Employer</button>
                </form>
              </article>

              {isSuperAdmin && (
                <article className="panel">
                  <h2>Add Employer Step</h2>
                  <form onSubmit={handleCreateStep} className="stack compact">
                    <select
                      value={stepForm.check_type}
                      onChange={(e) => setStepForm({ ...stepForm, check_type: e.target.value })}
                    >
                      <option value="employment">Employment</option>
                      <option value="criminal">Criminal</option>
                      <option value="education">Education</option>
                      <option value="identity">Identity</option>
                    </select>
                    <input
                      placeholder="Default provider"
                      value={stepForm.default_provider}
                      onChange={(e) => setStepForm({ ...stepForm, default_provider: e.target.value })}
                      required
                    />
                    <button type="submit" disabled={!selectedEmployerId}>
                      Add Step
                    </button>
                  </form>

                  <h2>Grant Employer Access</h2>
                  <form onSubmit={handleCreateAccessUser} className="stack">
                    <input
                      placeholder="Full name"
                      value={userForm.full_name}
                      onChange={(e) => setUserForm({ ...userForm, full_name: e.target.value })}
                      required
                    />
                    <input
                      placeholder="Email"
                      type="email"
                      value={userForm.email}
                      onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
                      required
                    />
                    <input
                      placeholder="Password"
                      type="password"
                      value={userForm.password}
                      onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                      required
                    />
                    <select value={userForm.role} onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}>
                      <option value="admin">Admin</option>
                      <option value="agent">Agent</option>
                    </select>
                    <button type="submit" disabled={!selectedEmployerId}>
                      Create User
                    </button>
                  </form>
                </article>
              )}
            </section>
          )}
        </>
      )}

      {activeMenu === "reports" && canSeeReports && (
        <section className="panel">
          <h2>Reports</h2>
          <p className="muted">Download candidate reports by date range.</p>
          <div className="stack compact">
            <input
              type="date"
              value={reportFilters.startDate}
              onChange={(e) => setReportFilters({ ...reportFilters, startDate: e.target.value })}
            />
            <input
              type="date"
              value={reportFilters.endDate}
              onChange={(e) => setReportFilters({ ...reportFilters, endDate: e.target.value })}
            />
            <div className="row">
              <button onClick={() => handleReportDownload("xlsx")}>Download Excel</button>
              <button onClick={() => handleReportDownload("pdf")}>Download PDF</button>
            </div>
          </div>
        </section>
      )}

      {!isAdmin && (
        <>
          <section className="grid content">
            {canManageCandidates && (
              <article className="panel">
                <h2>Create Candidate</h2>
                <form onSubmit={handleCreateCandidate} className="stack">
                  <input
                    placeholder="Full name"
                    value={candidateForm.full_name}
                    onChange={(e) => setCandidateForm({ ...candidateForm, full_name: e.target.value })}
                    required
                  />
                  <input
                    placeholder="Candidate profile email"
                    type="email"
                    value={candidateForm.email}
                    onChange={(e) => setCandidateForm({ ...candidateForm, email: e.target.value })}
                    required
                  />
                  <input
                    placeholder="Phone"
                    value={candidateForm.phone}
                    onChange={(e) => setCandidateForm({ ...candidateForm, phone: e.target.value })}
                    required
                  />
                  <input
                    placeholder="Date of Birth"
                    type="date"
                    value={candidateForm.dob}
                    onChange={(e) => setCandidateForm({ ...candidateForm, dob: e.target.value })}
                    required
                  />
                  <input
                    placeholder="Position"
                    value={candidateForm.position}
                    onChange={(e) => setCandidateForm({ ...candidateForm, position: e.target.value })}
                    required
                  />
                  <input
                    placeholder="Candidate login email"
                    type="email"
                    value={candidateForm.credential_email}
                    onChange={(e) => setCandidateForm({ ...candidateForm, credential_email: e.target.value })}
                    required
                  />
                  <input
                    placeholder="Candidate login password"
                    type="password"
                    value={candidateForm.credential_password}
                    onChange={(e) => setCandidateForm({ ...candidateForm, credential_password: e.target.value })}
                    required
                  />
                  <button type="submit">Create Candidate</button>
                </form>
              </article>
            )}

            <article className="panel">
              <h2>Candidates</h2>
              <ul className="candidate-list">
                {candidates.map((candidate) => (
                  <li key={candidate.id}>
                    <button
                      className={candidate.id === selectedCandidateId ? "active" : ""}
                      onClick={() => setSelectedCandidateId(candidate.id)}
                    >
                      <span>{candidate.full_name}</span>
                      <small>{candidate.position}</small>
                      <small>Status: {candidate.status}</small>
                    </button>
                  </li>
                ))}
              </ul>
            </article>
          </section>

          <section className="panel">
            <h2>Candidate Checks</h2>
            <p className="muted">Selected: {selectedCandidateName}</p>

            {canCreateChecks && (
              <form onSubmit={handleCreateCheck} className="stack compact">
                <select value={checkForm.check_type} onChange={(e) => setCheckForm({ ...checkForm, check_type: e.target.value })}>
                  <option value="employment">Employment History</option>
                  <option value="criminal">Criminal Record</option>
                  <option value="education">Education Verification</option>
                  <option value="identity">Identity Check</option>
                </select>
                <input
                  placeholder="Provider"
                  value={checkForm.provider}
                  onChange={(e) => setCheckForm({ ...checkForm, provider: e.target.value })}
                  required
                />
                <button type="submit" disabled={!selectedCandidateId}>
                  Start Check
                </button>
              </form>
            )}

            <div className="checks">
              {(selectedCandidate?.checks || []).map((check) => (
                <div className="check-card" key={check.id}>
                  <p>
                    <strong>{check.check_type}</strong> via {check.provider}
                  </p>
                  <p>Status: {check.status}</p>
                  <p>Initiated: {formatDate(check.initiated_at)}</p>
                  <p>Completed: {formatDate(check.completed_at)}</p>
                  <p className="muted">{check.result_notes || "No notes yet"}</p>
                  {canVerifyChecks && check.status === "in_progress" && (
                    <div className="row">
                      <button onClick={() => handleCheckUpdate(check.id, "passed")}>Mark Passed</button>
                      <button className="danger" onClick={() => handleCheckUpdate(check.id, "failed")}>
                        Mark Failed
                      </button>
                    </div>
                  )}
                </div>
              ))}
              {!selectedCandidate?.checks?.length && <p className="muted">No checks created yet.</p>}
            </div>
          </section>
        </>
      )}
    </div>
  );
}
