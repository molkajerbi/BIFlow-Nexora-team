"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AuthFrame, { GoogleButton, OrLine, PasswordInput, SwitchLink } from "@/components/AuthFrame";
import Icon from "@/components/Icon";
import { Spinner } from "@/components/ui";
import { api } from "@/lib/api";

export default function SignUp() {
  const router = useRouter();
  const [form, setForm] = useState({ name: "", organization: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (v) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => {
    api("/api/auth/me").then(() => router.replace("/app")).catch(() => {});
  }, [router]);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api("/api/auth/signup", { method: "POST", body: form });
      router.replace("/app");
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <AuthFrame title="Your first analysis," highlight="in a few minutes."
      text="Create your account: you will be able to drop a dataset, follow the agents live and find all your analyses.">
      <form className="auth-card" onSubmit={submit}>
        <h2>Create your account</h2>
        <p className="sub">Free, no credit card. One click with Google, or with your email.</p>
        <GoogleButton onError={setError} text="signup_with" />
        <OrLine />
        <div className="field">
          <label htmlFor="name">Full name</label>
          <input id="name" className="input" value={form.name} onChange={(e) => set("name")(e.target.value)} autoComplete="name" required />
        </div>
        <div className="field">
          <label htmlFor="org">Organization <span className="muted">(optional)</span></label>
          <input id="org" className="input" value={form.organization} onChange={(e) => set("organization")(e.target.value)} autoComplete="organization" />
        </div>
        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" className="input" type="email" value={form.email} onChange={(e) => set("email")(e.target.value)}
            autoComplete="email" placeholder="you@company.com" required />
        </div>
        <div className="field">
          <label htmlFor="pw">Password</label>
          <PasswordInput id="pw" value={form.password} onChange={set("password")} autoComplete="new-password" />
          <span className="hint">At least 8 characters.</span>
        </div>
        {error && <p className="error-text">{error}</p>}
        <button className="btn primary block lg" disabled={busy}>
          {busy ? <Spinner /> : <Icon name="user-plus" size={18} />} Create my account
        </button>
        <SwitchLink question="Already have an account?" href="/signin" icon="login">Sign in</SwitchLink>
      </form>
    </AuthFrame>
  );
}
