"use client";
// Shared interface components: logo, badges, banners, tiles, tables, confirmation dialog, agent chain.
import { useEffect } from "react";
import Icon from "./Icon";
import { STATIONS, stationStates } from "@/lib/format";

export function Logo({ size = 34, light = false }) {
  return (
    <span className={`logo${light ? " light" : ""}`}>
      <svg width={size} height={size} viewBox="0 0 34 34" aria-hidden="true">
        <defs>
          <linearGradient id="bfLogo" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#14B8A6" />
            <stop offset=".55" stopColor="#2F6BF6" />
            <stop offset="1" stopColor="#7C5CFC" />
          </linearGradient>
        </defs>
        <rect width="34" height="34" rx="10" fill="url(#bfLogo)" />
        <path d="M8 22 L15 13 L20 19 L26 10" stroke="#fff" strokeWidth="2.6" fill="none" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="8" cy="22" r="2.4" fill="#fff" /><circle cx="15" cy="13" r="2.4" fill="#fff" />
        <circle cx="20" cy="19" r="2.4" fill="#fff" /><circle cx="26" cy="10" r="2.7" fill="#fff" />
      </svg>
      <b>BI<em>Flow</em></b>
    </span>
  );
}

export function Badge({ kind = "neutral", children, dot = true }) {
  return <span className={`badge ${kind}${dot ? " dot" : ""}`}>{children}</span>;
}

export function Banner({ kind = "info", title, children, icon }) {
  const ico = icon || { ok: "check", warn: "alert", crit: "x-circle", info: "info" }[kind] || "info";
  return (
    <div className={`banner ${kind}`}>
      <div className="ico"><Icon name={ico} size={19} stroke={2.4} /></div>
      <div><b>{title}</b>{children ? <div className="txt">{children}</div> : null}</div>
    </div>
  );
}

export function Empty({ title, children, icon = "inbox" }) {
  return (
    <div className="empty">
      <div className="ico"><Icon name={icon} size={24} /></div>
      <b>{title}</b>
      {children ? <p>{children}</p> : null}
    </div>
  );
}

export function Section({ title, lead, children, right }) {
  return (
    <section className="section">
      <div className="section-head">
        <div>
          <h2>{title}</h2>
          {lead ? <p className="lead">{lead}</p> : null}
        </div>
        {right}
      </div>
      {children}
    </section>
  );
}

export function Tiles({ items }) {
  return (
    <div className="tiles">
      {items.map((it, i) => (
        <div key={i} className={`tile${it.accent ? " accent" : ""}${String(it.value).length > 16 ? " long" : ""}`}>
          <small>{it.label}</small>
          <b>{it.value}</b>
          {it.note ? <span>{it.note}</span> : null}
        </div>
      ))}
    </div>
  );
}

export function Spinner({ size = 18 }) {
  return <span className="spinner" style={{ width: size, height: size }} aria-label="Loading" />;
}

export function Loading({ children = "Loading…" }) {
  return <div className="loading"><Spinner /> {children}</div>;
}

export function Modal({ open, title, children, onClose, actions }) {
  useEffect(() => {
    if (!open) return undefined;
    const onKey = (e) => e.key === "Escape" && onClose && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="modal-back" onMouseDown={onClose}>
      <div className="modal" role="dialog" aria-modal="true" onMouseDown={(e) => e.stopPropagation()}>
        <h3>{title}</h3>
        <div className="modal-body">{children}</div>
        <div className="modal-actions">{actions}</div>
      </div>
    </div>
  );
}

export function Pipeline({ completed, status, compact = false }) {
  const states = stationStates(completed, status);
  const label = { done: "Done", active: "Running…", todo: "Upcoming", error: "Stopped" };
  return (
    <div className={`pipeline${compact ? " compact" : ""}`} role="list">
      {STATIONS.map(([name, role, ico], i) => {
        const s = states[i];
        return (
          <div key={name} className={`station ${s}`} role="listitem">
            <div className="dot">
              <Icon name={s === "done" ? "check" : s === "error" ? "x-circle" : ico} size={compact ? 18 : 21} stroke={s === "done" ? 2.6 : 2} />
            </div>
            <b>{name}</b>
            {!compact && <small>{role}</small>}
            <em>{label[s]}</em>
          </div>
        );
      })}
    </div>
  );
}

/** Simple table: columns = [{key, label, render?}] */
export function DataTable({ columns, rows, max = 300 }) {
  if (!rows || !rows.length) return <Empty title="No rows to show" />;
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>{columns.map((c) => <th key={c.key} title={c.help || ""}>{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.slice(0, max).map((r, i) => (
            <tr key={i}>
              {columns.map((c) => (
                <td key={c.key}>{c.render ? c.render(r[c.key], r) : r[c.key] === null || r[c.key] === undefined ? "—" : String(r[c.key])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function Tabs({ tabs, value, onChange }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button key={t.key} role="tab" aria-selected={value === t.key} className={value === t.key ? "on" : ""}
          onClick={() => onChange(t.key)} disabled={t.disabled}>
          {t.icon ? <Icon name={t.icon} size={15} /> : null}
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function Avatar({ name, size = 36, picture }) {
  const ini = (name || "?").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("");
  if (picture) {
    return <img className="avatar" src={picture} alt="" referrerPolicy="no-referrer" style={{ width: size, height: size, objectFit: "cover" }} />;
  }
  return <span className="avatar" style={{ width: size, height: size, fontSize: size * 0.38 }}>{ini}</span>;
}
