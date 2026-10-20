"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";
import ChatWidget from "./ChatWidget";
import Icon from "./Icon";
import Notifications from "./Notifications";
import { Avatar, Loading, Logo, Modal } from "./ui";
import { api } from "@/lib/api";
import { SessionContext } from "@/lib/session";

const NAV = [
  ["/app", "home", "Overview"],
  ["/app/analyses", "list", "My analyses"],
  ["/app/profile", "user", "My profile"],
];

export default function AppShell({ children }) {
  const router = useRouter();
  const pathname = usePathname() || "/app";
  const [user, setUser] = useState(null);
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");
  const [confirmOut, setConfirmOut] = useState(false);

  const refreshHealth = useCallback(() => {
    api("/api/health").then(setHealth).catch(() => setHealth({ api: false, ollama: false, models: [] }));
  }, []);

  useEffect(() => {
    api("/api/auth/me")
      .then((d) => setUser(d.user))
      .catch((e) => (e.status === 401 ? router.replace("/signin") : setError(e.message)));
    refreshHealth();
    const t = setInterval(refreshHealth, 30000);
    return () => clearInterval(t);
  }, [router, refreshHealth]);

  async function signOut() {
    await api("/api/auth/signout", { method: "POST" }).catch(() => {});
    router.replace("/signin");
  }

  if (error) return <div className="content"><Loading>{error}</Loading></div>;
  if (!user) return <div className="content"><Loading>Opening your workspace…</Loading></div>;

  const active = (href) => (href === "/app" ? pathname === "/app" : pathname.startsWith(href));
  const ai = health && health.ollama;
  return (
    <SessionContext.Provider value={{ user, setUser, health, refreshHealth }}>
      <div className="shell">
        <aside className="side">
          <Link href="/app"><Logo /></Link>
          <Link className="btn primary new" href="/app/new"><Icon name="plus" size={17} stroke={2.4} /> New analysis</Link>
          {NAV.map(([href, ico, label]) => (
            <Link key={href} href={href} className={`item${active(href) ? " on" : ""}`}><Icon name={ico} size={18} /> {label}</Link>
          ))}
          <div className="grow" />
          <div className={`ai${ai ? "" : " off"}`}>
            <b><i /> {ai ? "Local AI ready" : "Local AI stopped"}</b>
            {ai ? `Ollama · ${health.models.length} model${health.models.length === 1 ? "" : "s"}` : "Open the Ollama app on this computer."}
          </div>
          <button className="item signout" onClick={() => setConfirmOut(true)}><Icon name="logout" size={18} /> Sign out</button>
        </aside>
        <div className="main">
          <div className="topbar">
            <Notifications />
            <div className="who"><b>{user.name}</b><span>{user.organization || user.email}</span></div>
            <Avatar name={user.name} picture={user.picture} />
          </div>
          <div className="content">{children}</div>
        </div>
      </div>
      <ChatWidget />
      <Modal open={confirmOut} title="Sign out?" onClose={() => setConfirmOut(false)}
        actions={<>
          <button className="btn" onClick={() => setConfirmOut(false)}>Cancel</button>
          <button className="btn danger" onClick={signOut}><Icon name="logout" size={16} /> Sign out</button>
        </>}>
        Your analyses stay saved. You will need to sign in again to access them.
      </Modal>
    </SessionContext.Provider>
  );
}
