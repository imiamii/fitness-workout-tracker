const API_BASE = "http://localhost:8000";

function getToken() {
  return localStorage.getItem("token");
}

function getUserId() {
  return localStorage.getItem("user_id");
}

function logout() {
  localStorage.removeItem("token");
  localStorage.removeItem("user_id");
  window.location.href = "auth.html";
}

async function api(path, options = {}) {
  const headers = options.headers || {};
  headers["Content-Type"] = "application/json";

  const token = getToken();
  if (token) headers["Authorization"] = `Bearer ${token}`;

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  let data = null;
  const ct = res.headers.get("content-type") || "";
  if (ct.includes("application/json")) {
    data = await res.json();
  } else {
    data = await res.text();
  }

  if (!res.ok) {
    const msg = (data && data.detail) ? data.detail : "Request failed";
    throw new Error(msg);
  }

  return data;
}

function requireAuth() {
  if (!getToken() || !getUserId()) {
    window.location.href = "auth.html";
  }
}

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}
