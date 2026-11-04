import axios from "axios";

const BACKEND = process.env.REACT_APP_BACKEND_URL;

function sessionId() {
  let s = localStorage.getItem("demo_sid");
  if (!s) {
    s = (window.crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`).replace(/[^a-zA-Z0-9-]/g, "");
    localStorage.setItem("demo_sid", s);
  }
  return s;
}

export const api = axios.create({ baseURL: `${BACKEND}/api`, withCredentials: true, timeout: 45000 });
api.interceptors.request.use((cfg) => {
  cfg.headers["X-Demo-Session"] = sessionId();
  return cfg;
});
api.interceptors.response.use(null, async (err) => {
  const cfg = err.config;
  const transient = !err.response || [502, 503, 504].includes(err.response.status);
  if (cfg && cfg.method === "get" && transient && !cfg._retried) {
    cfg._retried = true;
    await new Promise((r) => { setTimeout(r, 1500); });
    return api(cfg);
  }
  return Promise.reject(err);
});

const UNREACHABLE = "The demo service is temporarily unreachable. Please try again in a moment.";

export function errMsg(e) {
  if (!e?.response || [502, 503, 504].includes(e.response.status)) return UNREACHABLE;
  if (e.response.status >= 500) return "Something went wrong on our side. Please try again.";
  const d = e?.response?.data?.detail;
  if (d == null) return "Something went wrong";
  if (typeof d === "string") return d;
  if (Array.isArray(d)) return d.map((x) => x?.msg || JSON.stringify(x)).join(" ");
  return d.msg || String(d);
}

export async function download(path, filename) {
  const r = await api.get(path, { responseType: "blob" });
  const url = URL.createObjectURL(r.data);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const demoSession = sessionId;
