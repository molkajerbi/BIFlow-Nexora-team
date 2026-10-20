"use client";
import { useEffect, useState } from "react";
import { GoogleLogo, PasswordInput } from "@/components/AuthFrame";
import Icon from "@/components/Icon";
import { askBrowserNotifications, browserNotifications } from "@/components/Notifications";
import { Avatar, Section, Tiles } from "@/components/ui";
import { api, useApi } from "@/lib/api";
import { fmtDay, fmtInt } from "@/lib/format";
import { useSession } from "@/lib/session";

export default function Profile() {
  const { user, setUser, health } = useSession();
  const { data: stats } = useApi("/api/stats");
  const [name, setName] = useState(user.name);
  const [org, setOrg] = useState(user.organization || "");
  const [msg, setMsg] = useState(null);
  const [pw, setPw] = useState({ current: "", next: "" });
  const [pwMsg, setPwMsg] = useState(null);
  const { data: notif, refresh: refreshNotif } = useApi("/api/notifications");
  const [browser, setBrowser] = useState("default");
  const [mailMsg, setMailMsg] = useState(null);
  const [testing, setTesting] = useState(false);
  useEffect(() => setBrowser(browserNotifications()), []);
  const hasPassword = user.has_password !== false;

  async function toggleEmail(on) {
    try {
      await api("/api/me/notifications", { method: "PUT", body: { email: on } });
      refreshNotif();
    } catch (err) {
      setMailMsg(["crit", err.message]);
    }
  }

  async function testEmail() {
    setTesting(true);
    setMailMsg(null);
    try {
      await api("/api/me/notifications/test", { method: "POST" });
      setMailMsg(["ok", `Test email sent to ${user.email}. Remember to check your spam folder.`]);
    } catch (err) {
      setMailMsg(["crit", err.message]);
    }
    setTesting(false);
  }

  async function enableBrowser() {
    setBrowser(await askBrowserNotifications());
  }

  async function save(e) {
    e.preventDefault();
    try {
      const d = await api("/api/me", { method: "PUT", body: { name, organization: org } });
      setUser(d.user);
      setMsg(["ok", "Profile saved."]);
    } catch (err) {
      setMsg(["crit", err.message]);
    }
  }

  async function changePassword(e) {
    e.preventDefault();
    try {
      await api("/api/me/password", { method: "PUT", body: { current: pw.current, new: pw.next } });
      setPw({ current: "", next: "" });
      setPwMsg(["ok", hasPassword ? "Password changed." : "Password set: you can now also sign in with your email."]);
      if (!hasPassword) setUser({ ...user, has_password: true });
    } catch (err) {
      setPwMsg(["crit", err.message]);
    }
  }

  return (
    <>
      <div className="page-head">
        <div style={{ display: "flex", gap: "1rem", alignItems: "center" }}>
          <Avatar name={user.name} picture={user.picture} size={64} />
          <div>
            <h1>{user.name}</h1>
            <p>{user.email} · member since {fmtDay(user.created)}</p>
          </div>
        </div>
      </div>
      {stats && (
        <Tiles items={[
          { label: "Analyses", value: fmtInt(stats.analyses), note: `${stats.finished} finished`, accent: true },
          { label: "KPIs computed", value: fmtInt(stats.kpis), note: "across all your analyses" },
          { label: "Insights", value: fmtInt(stats.insights), note: "published and verified" },
          { label: "Local AI", value: health && health.ollama ? "Ready" : "Stopped", note: health && health.ollama ? (health.models || []).join(", ") : "open Ollama" },
        ]} />
      )}
      <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fit, minmax(340px, 1fr))", alignItems: "start" }}>
        <Section title="My information">
          <form className="panel" onSubmit={save}>
            <div className="field"><label htmlFor="n">Full name</label>
              <input id="n" className="input" value={name} onChange={(e) => setName(e.target.value)} required /></div>
            <div className="field"><label htmlFor="o">Organization</label>
              <input id="o" className="input" value={org} onChange={(e) => setOrg(e.target.value)} /></div>
            <div className="field"><label htmlFor="e">Email</label>
              <input id="e" className="input" value={user.email} disabled /></div>
            {user.google && <p className="linked"><GoogleLogo size={16} /> Linked to your Google account</p>}
            {msg && <p className={msg[0] === "ok" ? "ok-text" : "error-text"}>{msg[1]}</p>}
            <button className="btn primary"><Icon name="check" size={16} /> Save</button>
          </form>
        </Section>
        <Section title="Password">
          <form className="panel" onSubmit={changePassword}>
            {hasPassword ? (
              <div className="field"><label htmlFor="c">Current password</label>
                <PasswordInput id="c" value={pw.current} onChange={(v) => setPw({ ...pw, current: v })} /></div>
            ) : (
              <p className="hint" style={{ marginTop: 0 }}>You sign in with Google. Set a password if you also want to sign in with your email.</p>
            )}
            <div className="field"><label htmlFor="p">{hasPassword ? "New password" : "Password"}</label>
              <PasswordInput id="p" value={pw.next} onChange={(v) => setPw({ ...pw, next: v })} autoComplete="new-password" />
              <span className="hint">At least 8 characters.</span></div>
            {pwMsg && <p className={pwMsg[0] === "ok" ? "ok-text" : "error-text"}>{pwMsg[1]}</p>}
            <button className="btn"><Icon name="key" size={16} /> {hasPassword ? "Change the password" : "Set a password"}</button>
          </form>
        </Section>
      </div>
      <Section title="Notifications" lead="BIFlow tells you when an analysis finishes or stops: you can start an analysis, close the page and come back when it is ready.">
        <div className="panel notif-settings">
          <div className="opt">
            <span className="ico"><Icon name="bell" size={19} /></span>
            <div><b>In the app</b><span>The bell at the top right and an on-screen message. Always on.</span></div>
            <span className="badge ok dot">On</span>
          </div>
          <div className="opt">
            <span className="ico"><Icon name="monitor" size={19} /></span>
            <div><b>On the computer</b><span>A Windows notification, even when the BIFlow tab is in the background.</span></div>
            {browser === "granted" ? <span className="badge ok dot">On</span>
              : browser === "denied" ? <span className="badge warn dot">Blocked by the browser</span>
                : browser === "unsupported" ? <span className="badge neutral dot">Not available</span>
                  : <button className="btn sm" onClick={enableBrowser}><Icon name="bell" size={15} /> Turn on</button>}
          </div>
          <div className="opt">
            <span className="ico"><Icon name="mail" size={19} /></span>
            <div>
              <b>By email</b>
              <span>{notif && notif.email_configured
                ? `A summary sent to ${user.email} (never your data).`
                : "Not set up yet: fill in a sending account in the project's .env file, then restart the API."}</span>
            </div>
            {notif && notif.email_configured ? (
              <label className="toggle">
                <input type="checkbox" checked={!!notif.email_enabled} onChange={(e) => toggleEmail(e.target.checked)} />
                <span />
              </label>
            ) : <span className="badge neutral dot">Not set up</span>}
          </div>
          {notif && notif.email_configured && (
            <div className="opt-actions">
              <button className="btn sm" onClick={testEmail} disabled={testing}><Icon name="send" size={15} /> {testing ? "Sending…" : "Send me a test email"}</button>
            </div>
          )}
          {browser === "denied" && <p className="hint">To turn Windows notifications back on: click the padlock to the left of the site address, then allow "Notifications".</p>}
          {mailMsg && <p className={mailMsg[0] === "ok" ? "ok-text" : "error-text"}>{mailMsg[1]}</p>}
        </div>
      </Section>
    </>
  );
}
