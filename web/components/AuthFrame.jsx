"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import Icon from "./Icon";
import PublicNav from "./PublicNav";
import { Spinner } from "./ui";
import { api } from "@/lib/api";

export default function AuthFrame({ title, highlight, text, children }) {
  return (
    <div className="auth">
      <PublicNav links={false} />
      <main className="auth-main">
        <div className="auth-side">
          <h1>{title} <span>{highlight}</span></h1>
          <p>{text}</p>
          <ul>
            <li><i><Icon name="lock" size={16} /></i>Your data and your account stay on this computer</li>
            <li><i><Icon name="cpu" size={16} /></i>A local AI, no API key and no subscription</li>
            <li><i><Icon name="shield" size={16} /></i>Every number verified, every decision explained</li>
          </ul>
        </div>
        {children}
      </main>
    </div>
  );
}

export function PasswordInput({ value, onChange, autoComplete = "current-password", id }) {
  const [show, setShow] = useState(false);
  return (
    <div className="input-wrap">
      <input id={id} className="input" type={show ? "text" : "password"} value={value} onChange={(e) => onChange(e.target.value)}
        autoComplete={autoComplete} required />
      <button type="button" onClick={() => setShow(!show)} aria-label={show ? "Hide password" : "Show password"}>
        <Icon name={show ? "eye-off" : "eye"} size={18} />
      </button>
    </div>
  );
}

/** The Google "G" logo (official colors). */
export function GoogleLogo({ size = 20 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" aria-hidden="true">
      <path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z" />
      <path fill="#FF3D00" d="m6.3 14.7 6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z" />
      <path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z" />
      <path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z" />
    </svg>
  );
}

let gsiPromise = null;
function loadGoogleScript() {
  if (typeof window !== "undefined" && window.google && window.google.accounts) return Promise.resolve();
  if (!gsiPromise) {
    gsiPromise = new Promise((resolve, reject) => {
      const s = document.createElement("script");
      s.src = "https://accounts.google.com/gsi/client";
      s.async = true;
      s.onload = () => resolve();
      s.onerror = () => { gsiPromise = null; reject(new Error("load")); };
      document.head.appendChild(s);
    });
  }
  return gsiPromise;
}

/**
 * "Continue with Google": the official Google button when a Google client ID is set in the API's .env file,
 * otherwise a button with the same look that explains how to turn it on.
 */
export function GoogleButton({ onError, text = "continue_with" }) {
  const router = useRouter();
  const host = useRef(null);
  const [clientId, setClientId] = useState(null);       // null: loading · "": not configured
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api("/api/auth/config").then((d) => setClientId(d.google_client_id || "")).catch(() => setClientId(""));
  }, []);

  useEffect(() => {
    if (!clientId) return;
    let alive = true;
    loadGoogleScript().then(() => {
      if (!alive || !host.current) return;
      window.google.accounts.id.initialize({
        client_id: clientId,
        ux_mode: "popup",
        callback: async ({ credential }) => {
          setBusy(true);
          onError("");
          try {
            await api("/api/auth/google", { method: "POST", body: { credential } });
            router.replace("/app");
          } catch (e) {
            onError(e.message);
            setBusy(false);
          }
        },
      });
      host.current.innerHTML = "";
      window.google.accounts.id.renderButton(host.current, {
        theme: "outline", size: "large", shape: "pill", text, logo_alignment: "center", locale: "en",
        width: Math.max(220, Math.min(400, host.current.offsetWidth || 380)),
      });
      setReady(true);
    }).catch(() => alive && onError("Google could not be loaded: check this computer's Internet connection."));
    return () => { alive = false; };
  }, [clientId, onError, router, text]);

  const label = text === "signup_with" ? "Sign up with Google" : "Continue with Google";
  if (clientId) {
    return (
      <div className="gsi">
        <div ref={host} className="gsi-host" />
        {!ready && <div className="btn block lg google" aria-hidden="true"><GoogleLogo /> {label}</div>}
        {busy && <div className="gsi-busy"><Spinner size={16} /> Signing you in…</div>}
      </div>
    );
  }
  return (
    <button type="button" className="btn block lg google" disabled={clientId === null}
      onClick={() => onError("Google sign-in is not set up on this computer yet: add BIFLOW_GOOGLE_CLIENT_ID to the .env file, then restart the API.")}>
      <GoogleLogo /> {label}
    </button>
  );
}

export function OrLine() {
  return <div className="or-line"><span>or with your email</span></div>;
}

/** Bottom of the sign-in / sign-up card: a short question and a clear button to the other page. */
export function SwitchLink({ question, href, icon, children }) {
  return (
    <div className="auth-alt">
      <span>{question}</span>
      <Link className="btn block" href={href}><Icon name={icon} size={17} /> {children} <Icon name="arrow" size={16} /></Link>
    </div>
  );
}
