"use client";
// Notifications: bell at the top right, on-screen message and Windows notification when an analysis finishes
// or stops. The notifications are created by the API (watcher in api/notify.py); here they are displayed.
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import Icon from "./Icon";
import { api } from "@/lib/api";
import { fmtAgo } from "@/lib/format";

const KIND = {
  success: { icon: "check-circle", cls: "ok" },
  blocked: { icon: "x-circle", cls: "crit" },
  failed: { icon: "alert", cls: "crit" },
  interrupted: { icon: "clock", cls: "warn" },
};

/** Browser notifications (Windows pop-up at the bottom right), if the user allowed them. */
export function browserNotifications() {
  if (typeof window === "undefined" || !("Notification" in window)) return "unsupported";
  return Notification.permission; // "granted" · "denied" · "default"
}

export async function askBrowserNotifications() {
  if (browserNotifications() === "unsupported") return "unsupported";
  return Notification.requestPermission();
}

function showSystemNotification(n) {
  if (browserNotifications() !== "granted") return;
  try {
    const note = new Notification(n.title, { body: n.body, tag: `biflow-${n.id}` });
    note.onclick = () => {
      window.focus();
      if (n.job_id) window.location.href = `/app/analyses/${n.job_id}`;
      note.close();
    };
  } catch {
    /* browser without system notifications: the bell and the on-screen message are enough */
  }
}

export default function Notifications() {
  const [data, setData] = useState({ items: [], unread: 0 });
  const [open, setOpen] = useState(false);
  const [toasts, setToasts] = useState([]);
  const lastId = useRef(null);
  const box = useRef(null);

  const load = useCallback(async () => {
    try {
      const d = await api("/api/notifications");
      const newest = d.items.length ? d.items[0].id : 0;
      if (lastId.current !== null) {
        const fresh = d.items.filter((n) => n.id > lastId.current && !n.read).reverse();
        fresh.forEach(showSystemNotification);
        if (fresh.length) setToasts((t) => [...t, ...fresh].slice(-3));
      }
      lastId.current = Math.max(lastId.current || 0, newest);
      setData(d);
    } catch {
      /* API briefly unavailable: try again on the next round */
    }
  }, []);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  useEffect(() => {
    if (!toasts.length) return;
    const t = setTimeout(() => setToasts((x) => x.slice(1)), 9000);
    return () => clearTimeout(t);
  }, [toasts]);

  useEffect(() => {
    if (!open) return;
    const close = (e) => box.current && !box.current.contains(e.target) && setOpen(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  async function markAll() {
    await api("/api/notifications/read", { method: "POST", body: { ids: null } }).catch(() => {});
    load();
  }

  async function readOne(n) {
    setOpen(false);
    setToasts((t) => t.filter((x) => x.id !== n.id));
    if (!n.read) await api("/api/notifications/read", { method: "POST", body: { ids: [n.id] } }).catch(() => {});
    load();
  }

  return (
    <>
      <div className="notif" ref={box}>
        <button className={`bell${open ? " on" : ""}`} onClick={() => setOpen(!open)} aria-label="Notifications"
          title="Notifications">
          <Icon name="bell" size={19} />
          {data.unread > 0 && <span className="count">{data.unread > 9 ? "9+" : data.unread}</span>}
        </button>
        {open && (
          <div className="notif-panel">
            <div className="notif-head">
              <b>Notifications</b>
              {data.unread > 0 && <button className="link" onClick={markAll}>Mark all as read</button>}
            </div>
            <div className="notif-list">
              {data.items.length === 0 ? (
                <div className="notif-empty">
                  <Icon name="bell" size={22} />
                  <b>No notifications</b>
                  <span>You will be told here as soon as an analysis finishes or stops.</span>
                </div>
              ) : data.items.map((n) => {
                const k = KIND[n.kind] || KIND.success;
                return (
                  <Link key={n.id} href={n.job_id ? `/app/analyses/${n.job_id}` : "/app"} onClick={() => readOne(n)}
                    className={`notif-item${n.read ? "" : " unread"}`}>
                    <span className={`ico ${k.cls}`}><Icon name={k.icon} size={17} /></span>
                    <span className="txt">
                      <b>{n.title}</b>
                      <span>{n.body}</span>
                      <small>{fmtAgo(n.created)}{n.emailed ? " · also sent by email" : ""}</small>
                    </span>
                  </Link>
                );
              })}
            </div>
            <Link className="notif-foot" href="/app/profile" onClick={() => setOpen(false)}>
              <Icon name="mail" size={15} /> Notification settings
            </Link>
          </div>
        )}
      </div>
      <div className="toasts" aria-live="polite">
        {toasts.map((n) => {
          const k = KIND[n.kind] || KIND.success;
          return (
            <div key={n.id} className={`toast ${k.cls}`}>
              <span className="ico"><Icon name={k.icon} size={19} /></span>
              <Link className="txt" href={n.job_id ? `/app/analyses/${n.job_id}` : "/app"} onClick={() => readOne(n)}>
                <b>{n.title}</b>
                <span>{n.body}</span>
              </Link>
              <button className="x" onClick={() => setToasts((t) => t.filter((x) => x.id !== n.id))} aria-label="Close">
                <Icon name="x" size={15} />
              </button>
            </div>
          );
        })}
      </div>
    </>
  );
}
