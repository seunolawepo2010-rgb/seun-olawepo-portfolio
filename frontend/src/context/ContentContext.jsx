import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../lib/api";

const Ctx = createContext(null);

export function ContentProvider({ children }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    api.get("/content/bundle").then((r) => setData(r.data)).catch(() => setData(false));
  }, []);
  return <Ctx.Provider value={data}>{children}</Ctx.Provider>;
}

export const useContent = () => useContext(Ctx);
