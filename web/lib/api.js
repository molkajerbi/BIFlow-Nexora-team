"use client";
// Access to the BIFlow FastAPI API. The session cookie is sent with every call (credentials: "include").
import { useCallback, useEffect, useRef, useState } from "react";

export function apiBase() {
  if (process.env.NEXT_PUBLIC_API_URL) return process.env.NEXT_PUBLIC_API_URL;
  if (typeof window !== "undefined") return `${window.location.protocol}//${window.location.hostname}:8000`;
  return "http://localhost:8000";
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

export async function api(path, { method = "GET", body, form } = {}) {
  let res;
  try {
    res = await fetch(`${apiBase()}${path}`, {
      method,
      credentials: "include",
      headers: body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: form || (body !== undefined ? JSON.stringify(body) : undefined),
    });
  } catch {
    throw new ApiError("The BIFlow server is not responding. Check that the API is running (uvicorn api.main:app --port 8000).", 0);
  }
  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (!res.ok) {
    const detail = data && data.detail;
    throw new ApiError(typeof detail === "string" ? detail : "Something went wrong.", res.status);
  }
  return data;
}

/** Uploads files with upload progress (useful for large datasets). */
export function uploadAnalysis(files, name, model, onProgress) {
  return new Promise((resolve, reject) => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f, f.name));
    form.append("name", name);
    form.append("model", model);
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${apiBase()}/api/jobs`);
    xhr.withCredentials = true;
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress && onProgress(Math.round((100 * e.loaded) / e.total));
    xhr.onload = () => {
      let data = null;
      try {
        data = JSON.parse(xhr.responseText);
      } catch {
        data = null;
      }
      if (xhr.status >= 200 && xhr.status < 300) resolve(data);
      else reject(new ApiError((data && data.detail) || "The upload failed.", xhr.status));
    };
    xhr.onerror = () => reject(new ApiError("The BIFlow server is not responding.", 0));
    xhr.send(form);
  });
}

export function downloadUrl(jobId, kind) {
  return `${apiBase()}/api/jobs/${jobId}/download/${kind}`;
}

/** Loads an API resource; refresh() reloads it; every (ms) reloads it regularly. */
export function useApi(path, { every = 0, enabled = true } = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const alive = useRef(true);
  const load = useCallback(async () => {
    if (!path || !enabled) return;
    try {
      const data = await api(path);
      if (alive.current) setState({ data, error: null, loading: false });
    } catch (error) {
      if (alive.current) setState((s) => ({ data: s.data, error, loading: false }));
    }
  }, [path, enabled]);
  useEffect(() => {
    alive.current = true;
    setState((s) => ({ ...s, loading: true }));
    load();
    let timer = null;
    if (every) timer = setInterval(load, every);
    return () => {
      alive.current = false;
      if (timer) clearInterval(timer);
    };
  }, [load, every]);
  return { ...state, refresh: load };
}
