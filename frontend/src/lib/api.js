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

export const api = axios.create({ baseURL: `${BACKEND}/api`, withCredentials: true });
api.interceptors.request.use((cfg) => {
  cfg.headers["X-Demo-Session"] = sessionId();
  return cfg;
});

export function errMsg(e) {
  const d = e?.response?.data?.detail;
  if (d == null) return e?.message || "Something went wrong";
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
