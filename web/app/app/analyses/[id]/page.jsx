"use client";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Dashboard, Insights, Kpis } from "@/components/analysis/bi";
import Overview from "@/components/analysis/overview";
import { Cleaning, Diagnostic, Model, Understanding } from "@/components/analysis/prep";
import Icon from "@/components/Icon";
import { Badge, Banner, Empty, Loading, Modal, Pipeline, Spinner, Tabs } from "@/components/ui";
import { api, useApi } from "@/lib/api";
import { STATUS, fmtDate, fmtDuration } from "@/lib/format";

const TABS = [
  ["overview", "Overview", "home", 0],
  ["understanding", "Understanding", "search", 1],
  ["diagnostic", "Diagnosis", "activity", 3],
  ["cleaning", "Cleaning", "sparkles", 4],
  ["model", "Modeling", "star", 5],
  ["kpis", "KPIs", "target", 8],
  ["insights", "Analysis", "trend", 9],
  ["dashboard", "Dashboard", "layout", 10],
];

function Working({ job }) {
  const p = job.progress || {};
  return (
    <div className="working">
      <Spinner size={30} />
      <h2>The agents are working on your data</h2>
      <p>{fmtDuration(p.elapsed_s)} elapsed. You can close this page: the analysis keeps running on your computer, and each result shows up here as soon as it is ready.</p>
      <div className="big-bar"><span style={{ width: `${p.percent || 2}%` }} /></div>
      <Pipeline completed={job.completed} status="running" />
      {p.cell && <div className="now"><Icon name="cpu" size={15} /><span>Right now: {p.cell}</span></div>}
    </div>
  );
}

export default function AnalysisPage() {
  const { id } = useParams();
  const router = useRouter();
  const [tab, setTab] = useState("overview");
  const [every, setEvery] = useState(3000);
  const { data: job, error, refresh } = useApi(`/api/jobs/${id}`, { every });
  const [confirm, setConfirm] = useState(null);
  const [actionError, setActionError] = useState("");

  useEffect(() => {
    if (job) setEvery(job.status === "running" ? 3000 : 0);
  }, [job]);

  async function act(kind) {
    setConfirm(null);
    setActionError("");
    try {
      if (kind === "delete") {
        await api(`/api/jobs/${id}`, { method: "DELETE" });
        router.push("/app/analyses");
        return;
      }
      await api(`/api/jobs/${id}/${kind}`, { method: "POST" });
      setEvery(3000);
      refresh();
    } catch (e) {
      setActionError(e.message);
    }
  }

  if (error && !job) return <Empty title="Analysis not found" icon="search">{error.message}<br /><br /><Link className="btn" href="/app/analyses">My analyses</Link></Empty>;
  if (!job) return <Loading />;
  const { meta, status, completed, result } = job;
  const [label, kind] = STATUS[status] || [status, "neutral"];
  const running = status === "running";
  const available = (min) => completed >= min || (min === 4 && status === "blocked");
  return (
    <>
      <Link className="crumb" href="/app/analyses"><Icon name="back" size={14} /> My analyses</Link>
      <div className="page-head">
        <div>
          <h1>{meta.name}</h1>
          <div className="facts">
            <span><Icon name="calendar" size={15} /> Started on {fmtDate(meta.created)}</span>
            <span><Icon name="cpu" size={15} /> Local AI: {meta.model}</span>
            <Badge kind={kind}>{label}{running && job.progress && job.progress.percent ? ` · ${job.progress.percent}%` : ""}</Badge>
          </div>
        </div>
        <div className="actions">
          {running && <button className="btn sm" onClick={() => setConfirm("stop")}><Icon name="stop" size={15} /> Stop</button>}
          {!running && <button className="btn sm" onClick={() => setConfirm("relaunch")}><Icon name="refresh" size={15} /> Run again</button>}
          <button className="btn sm danger-ghost" onClick={() => setConfirm("delete")}><Icon name="trash" size={15} /> Delete</button>
        </div>
      </div>
      {actionError && <Banner kind="crit" title={actionError} />}
      {running ? <Working job={job} /> : <div style={{ marginBottom: "1rem" }}><Pipeline completed={completed} status={status} compact /></div>}
      <Tabs value={tab} onChange={setTab}
        tabs={TABS.map(([key, l, icon, min]) => ({ key, label: l, icon, disabled: !available(min) }))} />
      {tab === "overview" && <Overview job={job} onRelaunch={() => act("relaunch")} />}
      {tab === "understanding" && <Understanding jobId={id} res={result} />}
      {tab === "diagnostic" && <Diagnostic jobId={id} />}
      {tab === "cleaning" && <Cleaning jobId={id} res={result} />}
      {tab === "model" && <Model jobId={id} />}
      {tab === "kpis" && <Kpis jobId={id} res={result} />}
      {tab === "insights" && <Insights jobId={id} res={result} />}
      {tab === "dashboard" && <Dashboard jobId={id} />}
      <Modal open={!!confirm} onClose={() => setConfirm(null)}
        title={{ stop: "Stop the analysis?", relaunch: "Run the analysis again?", delete: "Delete this analysis?" }[confirm] || ""}
        actions={<>
          <button className="btn" onClick={() => setConfirm(null)}>Cancel</button>
          <button className={`btn ${confirm === "relaunch" ? "primary" : "danger"}`} onClick={() => act(confirm)}>
            {{ stop: "Stop", relaunch: "Run again", delete: "Delete" }[confirm]}
          </button>
        </>}>
        {confirm === "stop" && "The agents stop right away. You can run the analysis again later: the answers already computed by the AI will be reused."}
        {confirm === "relaunch" && "The analysis starts again from your original files. The current results and the conversation with the assistant will be replaced."}
        {confirm === "delete" && `"${meta.name}" and all its results will be permanently deleted from this computer.`}
      </Modal>
    </>
  );
}
