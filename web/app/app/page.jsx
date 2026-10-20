"use client";
import Link from "next/link";
import Icon from "@/components/Icon";
import JobRow from "@/components/JobRow";
import { Banner, Empty, Loading, Section, Tiles } from "@/components/ui";
import { useApi } from "@/lib/api";
import { firstName, fmtInt } from "@/lib/format";
import { useSession } from "@/lib/session";

export default function Overview() {
  const { user, health } = useSession();
  const { data, error } = useApi("/api/stats", { every: 5000 });
  return (
    <>
      <div className="welcome">
        <div>
          <h1>Hello {firstName(user.name)}</h1>
          <p>Drop a dataset: the agents prepare it, compute your KPIs and explain every decision to you.</p>
        </div>
        <Link className="btn lg" href="/app/new" style={{ background: "#fff", border: "none", color: "var(--ink)" }}>
          <Icon name="plus" size={18} stroke={2.4} /> New analysis
        </Link>
      </div>
      {health && !health.ollama && (
        <Banner kind="crit" title="The local AI engine is not running">
          Open the Ollama app on this computer (recommended model: <code>ollama pull qwen2.5:7b</code>), then reload the page.
        </Banner>
      )}
      {error && <Banner kind="crit" title="Could not load your statistics">{error.message}</Banner>}
      {!data ? <Loading /> : (
        <>
          <Tiles items={[
            { label: "Analyses", value: fmtInt(data.analyses), note: `${data.finished} finished · ${data.running} running`, accent: true },
            { label: "KPIs computed", value: fmtInt(data.kpis), note: "each one verified by a second computation" },
            { label: "Insights published", value: fmtInt(data.insights), note: "numbers re-checked by the code" },
            { label: "Explainable decisions", value: fmtInt(data.decisions), note: "ask the assistant \"why?\"" },
          ]} />
          <Section title="Your latest analyses" lead="Open an analysis to see the work of each agent."
            right={data.analyses ? <Link className="btn sm" href="/app/analyses">See all <Icon name="chevron" size={15} /></Link> : null}>
            {data.recent.length ? data.recent.map((j) => <JobRow key={j.id} job={j} />) : (
              <Empty title="No analyses yet" icon="upload">
                Start your first analysis: one CSV or Excel file is enough. <br /><br />
                <Link className="btn primary" href="/app/new"><Icon name="plus" size={16} /> New analysis</Link>
              </Empty>
            )}
          </Section>
          <Section title="What the agents do for you">
            <div className="deliverables">
              {[["search", "Understand", "tables, columns, links, domain"], ["sparkles", "Clean", "nothing lost, every correction traced"],
                ["target", "Measure", "your sector's KPIs, verified"], ["trend", "Analyze", "trends, shifts, segments"],
                ["layout", "Show", "a standalone dashboard"], ["message", "Explain", "\"why?\" about every decision"]].map(([i, t, d]) => (
                <div className="deliverable" key={t}><i><Icon name={i} size={20} /></i><div><b>{t}</b><span>{d}</span></div></div>
              ))}
            </div>
          </Section>
        </>
      )}
    </>
  );
}
