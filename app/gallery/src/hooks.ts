import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, getLibrary, getStatus, type Library, type Status } from "./api";

/** Poll the daemon for status. Null means the daemon itself is unreachable. */
export function useStatus(intervalMs = 1400) {
  const [status, setStatus] = useState<Status | null>(null);
  const [reachable, setReachable] = useState(true);

  useEffect(() => {
    let alive = true;
    let timer: number;
    const tick = async () => {
      try {
        const s = await getStatus();
        if (!alive) return;
        setStatus(s);
        setReachable(true);
      } catch {
        if (!alive) return;
        setReachable(false);
      }
      if (alive) timer = window.setTimeout(tick, intervalMs);
    };
    tick();
    return () => {
      alive = false;
      window.clearTimeout(timer);
    };
  }, [intervalMs]);

  return { status, reachable };
}

export function useLibrary() {
  const [library, setLibrary] = useState<Library | null>(null);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    try {
      setLibrary(await getLibrary());
      setError(null);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : String(e));
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);
  return { library, error, reload };
}

export interface Toast {
  id: number;
  text: string;
  tone: "ok" | "err" | "info";
}

export function useToasts() {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const next = useRef(1);

  const push = useCallback((text: string, tone: Toast["tone"] = "info") => {
    const id = next.current++;
    setToasts((t) => [...t, { id, text, tone }]);
    window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200);
  }, []);

  /**
   * Run an action, reporting it. Returns whether it succeeded so callers do not
   * each re-implement the try/catch/toast dance the old app repeated per button.
   */
  const run = useCallback(
    async (label: string, fn: () => Promise<unknown>) => {
      push(`${label}…`, "info");
      try {
        await fn();
        push(`✓ ${label}`, "ok");
        return true;
      } catch (e) {
        push(`✗ ${label}: ${e instanceof Error ? e.message : String(e)}`, "err");
        return false;
      }
    },
    [push]
  );

  return { toasts, push, run };
}
