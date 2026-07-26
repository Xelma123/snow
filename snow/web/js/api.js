export function createApi(getBase, getToken) {
  async function request(path, options = {}) {
    const base = getBase().replace(/\/$/, "");
    const headers = { ...(options.headers || {}) };
    if (options.json !== undefined) {
      headers["Content-Type"] = "application/json";
    }
    const token = getToken();
    if (token) headers.Authorization = `Bearer ${token}`;

    const timeoutMs = options.timeoutMs ?? 60000;
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), timeoutMs);
    let r;
    try {
      r = await fetch(`${base}${path}`, {
        ...options,
        headers,
        signal: ctrl.signal,
        body: options.json !== undefined ? JSON.stringify(options.json) : options.body,
      });
    } catch (e) {
      if (e?.name === "AbortError") {
        throw new Error("İstek zaman aşımı — sunucu veya AI yavaş yanıt verdi.");
      }
      throw e;
    } finally {
      clearTimeout(timer);
    }

    const data = await r.json().catch(() => ({}));
    if (!r.ok) {
      let detail = data.detail || data.error || data.reply || `HTTP ${r.status}`;
      if (Array.isArray(detail)) {
        detail = detail.map((x) => x.msg || JSON.stringify(x)).join("; ");
      } else if (typeof detail === "object") {
        detail = JSON.stringify(detail);
      }
      throw new Error(detail);
    }
    return data;
  }

  return {
    health: (deep = false) => request(`/api/v1/health${deep ? "?deep=1" : ""}`, { timeoutMs: 15000 }),
    chat: (message, sessionId) =>
      request("/api/v1/chat", {
        method: "POST",
        json: { message, session_id: sessionId || null },
        timeoutMs: 90000,
      }),
    summary: () => request("/api/v1/home/summary", { timeoutMs: 20000 }),
    clearSession: (id) =>
      request(`/api/v1/sessions/${encodeURIComponent(id)}`, { method: "DELETE" }),
    jobs: () => request("/api/v1/jobs"),
    cancelJob: (id) =>
      request(`/api/v1/jobs/${encodeURIComponent(id)}`, { method: "DELETE" }),
    routines: () => request("/api/v1/routines"),
    runRoutine: (routineId) =>
      request("/api/v1/routines/run", {
        method: "POST",
        json: { routine_id: routineId },
      }),
  };
}
