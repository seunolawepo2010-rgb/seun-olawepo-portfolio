import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../lib/api";
import snapshot from "../content/fallback.json";

const Ctx = createContext(null);
const wait = (ms) => new Promise((r) => { setTimeout(r, ms); });

async function loadBundle() {
  for (let i = 0; i < 3; i += 1) {
    try {
      return (await api.get("/content/bundle", { timeout: 10000 })).data; // eslint-disable-line no-await-in-loop
    } catch {
      await wait(1000 * 2 ** i); // eslint-disable-line no-await-in-loop
    }
  }
  return null;
}

export function ContentProvider({ children }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    const t = setTimeout(() => setData((d) => d || { ...snapshot, _fallback: true }), 12000);
    loadBundle().then((d) => { clearTimeout(t); setData(d || { ...snapshot, _fallback: true }); });
    return () => clearTimeout(t);
  }, []);
  return <Ctx.Provider value={data}>{children}</Ctx.Provider>;
}

export const useContent = () => useContext(Ctx);
