"use client";
import Link from "next/link";
import { useState } from "react";
import Icon from "@/components/Icon";
import JobRow from "@/components/JobRow";
import { Banner, Empty, Loading, Modal } from "@/components/ui";
import { api, useApi } from "@/lib/api";
import { fmtInt, plural } from "@/lib/format";

export default function Analyses() {
  const { data, error, refresh } = useApi("/api/jobs", { every: 5000 });
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("all");
  const [toDelete, setToDelete] = useState(null);
  const [flash, setFlash] = useState(null);

  async function remove() {
    const job = toDelete;
    setToDelete(null);
    try {
      await api(`/api/jobs/${job.id}`, { method: "DELETE" });
      setFlash(["ok", `The analysis "${job.name}" was deleted.`]);
    } catch (e) {
      setFlash(["crit", e.message]);
    }
    refresh();
  }

  const jobs = (data && data.jobs) || [];
  const shown = jobs.filter((j) => (status === "all" || j.status === status ||
    (status === "stopped" && ["failed", "blocked", "interrupted"].includes(j.status))) &&
    (!q || `${j.name} ${j.domain || ""}`.toLowerCase().includes(q.toLowerCase())));
  return (
    <>
      <div className="page-head">
        <div>
          <h1>My analyses</h1>
          <p>{data ? `${plural(jobs.length, "analysis", "analyses")} · ${fmtInt(jobs.filter((j) => j.status === "success").length)} finished` : ""}</p>
        </div>
        <Link className="btn primary" href="/app/new"><Icon name="plus" size={17} stroke={2.4} /> New analysis</Link>
      </div>
      {flash && <Banner kind={flash[0]} title={flash[1]} />}
      {error && <Banner kind="crit" title="Could not load your analyses">{error.message}</Banner>}
      <div className="toolbar">
        <input className="input" placeholder="Search by name or domain…" value={q} onChange={(e) => setQ(e.target.value)} />
        <select className="select" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="all">All statuses</option>
          <option value="success">Finished</option>
          <option value="running">Running</option>
          <option value="stopped">Stopped</option>
        </select>
      </div>
      {!data ? <Loading /> : shown.length ? shown.map((j) => (
        <JobRow key={j.id} job={j} right={
          <button className="btn ghost sm" onClick={() => setToDelete(j)} aria-label={`Delete ${j.name}`} title="Delete">
            <Icon name="trash" size={16} />
          </button>} />
      )) : (
        <Empty title={jobs.length ? "No matching analysis" : "No analyses yet"} icon="search">
          {jobs.length ? "Try another word or another status." : "Drop a first dataset to get started."}
        </Empty>
      )}
      <Modal open={!!toDelete} title="Delete this analysis?" onClose={() => setToDelete(null)}
        actions={<>
          <button className="btn" onClick={() => setToDelete(null)}>Cancel</button>
          <button className="btn danger" onClick={remove}><Icon name="trash" size={16} /> Delete</button>
        </>}>
        "{toDelete && toDelete.name}" and all its results (star schema, KPIs, dashboard, conversation) will be
        permanently deleted from this computer.
      </Modal>
    </>
  );
}
