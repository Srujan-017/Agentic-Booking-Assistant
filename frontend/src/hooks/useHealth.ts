import { useEffect, useState } from "react";
import { getHealth } from "../api/client";

export type ConnectionState = "checking" | "online" | "offline";

const POLL_MS = 15000;

export function useHealth() {
  const [state, setState] = useState<ConnectionState>("checking");

  useEffect(() => {
    let cancelled = false;

    async function check() {
      try {
        await getHealth();
        if (!cancelled) setState("online");
      } catch {
        if (!cancelled) setState("offline");
      }
    }

    void check();
    const interval = setInterval(check, POLL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  return state;
}
