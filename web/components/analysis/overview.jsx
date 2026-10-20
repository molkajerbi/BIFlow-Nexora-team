"use client";
// Overview of an analysis: status, key figures, work of each agent, downloads.
import Icon from "../Icon";
import { Banner, Section, Tiles } from "../ui";
import { downloadUrl } from "@/lib/api";
import { fmtInt, plural, sectorText } from "@/lib/format";

function AgentCard({ n, icon, name, head, detail, done }) {
  return (
    <div className={`card${done ? " edge-ok" : ""}`}>
      <div className="row" style={{ alignItems: "center", justifyContent: "flex-start", gap: ".6rem" }}>
        <span style={{ width: 34, height: 34, borderRadius: 11, display: "flex", alignItems: "center", justifyContent: "center",
          background: done ? "var(--grad)" : "var(--bg)", color: done ? "#fff" : "#97a1b3" }}>
          <Icon name={done ? "check" : icon} size={17} stroke={done ? 2.6 : 2} />
        </span>
        <small style={{ color: "var(--muted)", fontWeight: 800, fontSize: ".72rem", letterSpacing: ".05em", textTransform: "uppercase" }}>
          Agent {n} · {name}
        </small>
      </div>
      <h4 style={{ marginTop: ".6rem", color: done ? "var(--ink)" : "#97a1b3" }}>{head}</h4>
      <p style={{ color: "var(--muted)", fontSize: ".86rem", margin: ".2rem 0 0" }}>{detail}</p>
    </div>
  );
}

export default function Overview({ job, onRelaunch }) {
  const { result: res, status, completed, downloads, meta } = job;
  const bi = res.bi || {};
  const xai = res.xai || {};
  const inp = res.input || {};
  const q = res.quality || {};
  const prof = res.profiler || {};
  const etl = res.etl || {};
  const running = status === "running";
  const todo = (after) => (running && completed >= after ? "running…" : running ? "waiting for the previous step" : "not run");
  const agents = [
    [1, "search", "Understanding", completed >= 1, plural(inp.tables, "table recognized", "tables recognized"), `${fmtInt(inp.rows)} rows read, without any change`],
    [2, "activity", "Diagnosis", completed >= 3 && prof.findings !== undefined, plural(prof.findings, "point found", "points found"),
      `${fmtInt(prof.interpreted_by_llm)} explained in plain language by the AI`],
    [3, "sparkles", "Cleaning", completed >= 4 && q.corrections_applied !== undefined, plural(q.corrections_applied, "correction applied", "corrections applied"),
      `${plural(q.cells_changed, "cell corrected", "cells corrected")}, each one traced`],
    [4, "star", "Modeling", completed >= 5 && etl.tables_built !== undefined, `${fmtInt(etl.tables_built)} tables built`, "star schema tested table by table"],
    [5, "target", "KPIs", completed >= 8 && bi.kpis !== undefined, plural(bi.kpis, "KPI computed", "KPIs computed"), `sector: ${sectorText(bi).toLowerCase()}`],
    [6, "trend", "Analysis", completed >= 9 && bi.insights !== undefined, plural(bi.insights, "insight published", "insights published"),
      `${plural(bi.series, "monthly series analyzed", "monthly series analyzed")}`],
    [7, "layout", "Dashboard", completed >= 10 && !!bi.dashboard, "Dashboard ready", bi.dashboard_title || ""],
    [8, "bot", "Explanations", !!xai.ready && !running, plural(xai.decisions, "decision explained", "decisions explained"), "ask the assistant \"why?\""],
  ];
  return (
    <>
      {status === "success" && (
        <Banner kind="ok" title="Your analysis is ready">
          Data prepared, KPIs computed and verified, dashboard generated. The assistant (round button at the bottom right) answers your questions about every decision.
        </Banner>
      )}
      {status === "blocked" && (
        <Banner kind="crit" title="Analysis stopped for safety">
          A critical problem in the data prevents building a reliable model. Check the Cleaning tab, or ask the assistant why.
        </Banner>
      )}
      {["failed", "interrupted"].includes(status) && (
        <Banner kind={bi.error && completed >= 6 ? "warn" : "crit"}
          title={bi.error && completed >= 6 ? "Your data is ready, but the BI analysis stopped" : "The analysis stopped before the end"}>
          {bi.error && completed >= 6 ? "The preparation is finished and can be downloaded. " : ""}
          If the AI engine was closed or the computer went to sleep, reopen Ollama and run the analysis again: the answers already computed by the AI are reused, so the new run is faster.
          <div style={{ marginTop: ".7rem" }}><button className="btn sm primary" onClick={onRelaunch}><Icon name="refresh" size={15} /> Run the analysis again</button></div>
          {(res.error || bi.error) && <details className="more" style={{ marginBottom: 0 }}><summary>Details for the technical team</summary>
            <div><pre style={{ whiteSpace: "pre-wrap", margin: 0 }}><code>{bi.error || res.error}</code></pre></div></details>}
        </Banner>
      )}
      {completed >= 1 && (
        <Tiles items={[
          { label: "Domain identified", value: res.domain || "being analyzed", note: "inferred by the AI", accent: true },
          { label: "Tables read", value: fmtInt(inp.tables), note: `${fmtInt(inp.rows)} rows in total` },
          ...(bi.kpis !== undefined ? [{ label: "KPIs computed", value: fmtInt(bi.kpis), note: `sector: ${sectorText(bi).toLowerCase()}` }] : []),
          ...(bi.insights !== undefined ? [{ label: "Insights published", value: fmtInt(bi.insights), note: plural(bi.signals, "signal detected", "signals detected") }] : []),
        ]} />
      )}
      <Section title="What each agent did" lead="Open the matching tab to see the details.">
        <div className="grid" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(250px, 1fr))" }}>
          {agents.map(([n, icon, name, done, head, detail]) => (
            <AgentCard key={n} n={n} icon={icon} name={name} done={done} head={done ? head : "—"} detail={done ? detail : todo(n)} />
          ))}
        </div>
      </Section>
      {!running && (downloads.zip || downloads.warehouse || downloads.dashboard) && (
        <Section title="Download" lead="All deliverables (star schema, clean data, KPIs, analysis, dashboard, decision ledger), the database alone or the dashboard alone.">
          <div className="actions">
            {downloads.zip && <a className="btn primary" href={downloadUrl(meta.id, "zip")}><Icon name="download" size={17} /> All deliverables (.zip)</a>}
            {downloads.warehouse && <a className="btn" href={downloadUrl(meta.id, "warehouse")}><Icon name="database" size={17} /> Star schema database ({downloads.warehouse_mb} MB)</a>}
            {downloads.dashboard && <a className="btn" href={downloadUrl(meta.id, "dashboard")}><Icon name="layout" size={17} /> Dashboard (.html)</a>}
          </div>
        </Section>
      )}
    </>
  );
}
