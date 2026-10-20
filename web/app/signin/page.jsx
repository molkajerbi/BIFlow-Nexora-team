"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import AuthFrame, { GoogleButton, OrLine, PasswordInput, SwitchLink } from "@/components/AuthFrame";
import Icon from "@/components/Icon";
import { Spinner } from "@/components/ui";
import { api } from "@/lib/api";

export default function SignIn() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api("/api/auth/me").then(() => router.replace("/app")).catch(() => {});
  }, [router]);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await api("/api/auth/signin", { method: "POST", body: { email, password } });
      router.replace("/app");
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  }

  return (
    <AuthFrame title="Welcome back to" highlight="BIFlow."
      text="Find your analyses, your KPIs, your dashboards and the assistant that explains every decision.">
      <form className="auth-card" onSubmit={submit}>
        <h2>Sign in</h2>
        <p className="sub">With Google, or with the email and password of your BIFlow account.</p>
        <GoogleButton onError={setError} text="signin_with" />
        <OrLine />
        <div className="field">
          <label htmlFor="email">Email</label>
          <input id="email" className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)}
            autoComplete="email" placeholder="you@company.com" required />
        </div>
        <div className="field">
          <label htmlFor="pw">Password</label>
          <PasswordInput id="pw" value={password} onChange={setPassword} />
        </div>
        {error && <p className="error-text">{error}</p>}
        <button className="btn primary block lg" disabled={busy}>
          {busy ? <Spinner /> : <Icon name="login" size={18} />} Sign in
        </button>
        <SwitchLink question="Don't have an account yet?" href="/signup" icon="user-plus">Create an account</SwitchLink>
      </form>
    </AuthFrame>
  );
}
