"use client";
// BI tabs: KPIs, analysis (insights), dashboard.
import { useState } from "react";
import Icon from "../Icon";
import { Badge, Banner, DataTable, Empty, Loading, Section, Tiles } from "../ui";
import { useTable } from "./prep";
import { apiBase, downloadUrl, useApi } from "@/lib/api";
import { FACT_TYPE, INSIGHT_TYPE, KPI_STATUS, RELIABILITY, VALENCE, bindingLabel, fmtInt, humanText, plural, sectorText } from "@/lib/format";

// ---------------------------------------------------------------- 5. KPIs
export function Kpis({ jobId, res }) {
  const bi = res.bi || {};
  const cat = useTable(jobId, "kpi_catalog");
  const [sql, setSql] = useState(null);
  if (!cat) return <Loading />;
  const dropped = bi.dropped || {};
  const failed = bi.failed || {};
  const reasons = bi.binding_reasons || {};
  return (
    <>
      <Section title="The key indicators of your business" lead="The agent recognizes your sector, finds that sector's reference KPIs in its knowledge base, binds each one to the right columns, then computes it twice (an SQL query and a second, independent computation). A KPI is kept only if both computations give the same result and its value is plausible.">
        <Tiles items={[
          { label: "Sector recognized", value: sectorText(bi), note: bi.sector_source === "LLM" ? "chosen by the AI, verified by the code" : "chosen by the fallback rule", accent: true },
          { label: "KPIs kept", value: fmtInt(bi.kpis), note: `${fmtInt(bi.validated)} validated · ${bi.to_confirm || 0} to confirm` },
          { label: "Proposed by the AI", value: fmtInt(bi.proposed || 0), note: "in addition to the knowledge base" },
          { label: "Set aside", value: fmtInt(Object.keys(dropped).length + Object.keys(failed).length), note: "not applicable here, or test failed" },
        ]} />
        {bi.sector_reason && <Banner kind="info" title="Why this sector?">{humanText(bi.sector_reason) || bi.sector_reason}</Banner>}
      </Section>
      {cat.length ? (
        <Section title="The KPI catalog" lead="Validated: obvious columns or columns chosen by the AI, all tests passed. To confirm: KPI proposed by the AI or fallback binding, to review before sharing it.">
          <div className="grid">
            {cat.map((k) => {
              const [label, kind] = KPI_STATUS[k.status] || [k.status, "neutral"];
              const why = humanText(reasons[k.id]);
              const how = bindingLabel(k.binding);
              return (
                <div className={`card edge-${kind}`} key={k.id}>
                  <div className="row"><h4>{k.name}</h4><Badge kind={kind}>{label}</Badge></div>
                  <span className="big">{k.valeur}</span>
                  <p>{k.definition}</p>
                  <div className="meta">
                    Formula: <code>{k.formula}</code><br />
                    {how.charAt(0).toUpperCase() + how.slice(1)}{why ? ` ("${why}")` : ""}{RELIABILITY[k.reliability] ? ` · ${RELIABILITY[k.reliability]}` : ""}
                    <br /><button className="linkish" style={{ padding: 0, marginTop: ".3rem", color: "var(--blue)" }}
                      onClick={() => setSql(sql === k.id ? null : k.id)}>{sql === k.id ? "Hide the SQL query" : "Show the SQL query"}</button>
                    {sql === k.id && <pre style={{ whiteSpace: "pre-wrap", margin: ".4rem 0 0" }}><code>{k.sql}</code></pre>}
                  </div>
                </div>
              );
            })}
          </div>
        </Section>
      ) : <Empty title="No KPI can be computed">The columns in your data do not allow computing any reliable indicator.</Empty>}
      {(Object.keys(dropped).length > 0 || Object.keys(failed).length > 0) && (
        <details className="more">
          <summary>KPIs set aside, and why</summary>
          <div><DataTable columns={[{ key: "kpi", label: "KPI" }, { key: "reason", label: "Reason" }]}
            rows={[...Object.entries(dropped).map(([kpi, reason]) => ({ kpi, reason })),
              ...Object.entries(failed).map(([kpi, r]) => ({ kpi, reason: `test failed: ${r}` }))]} /></div>
        </details>
      )}
    </>
  );
}

// ---------------------------------------------------------------- 6. analysis
export function Insights({ jobId, res }) {
  const bi = res.bi || {};
  const { data } = useApi(`/api/jobs/${jobId}/insights`);
  const facts = useTable(jobId, "analysis_facts");
  if (!data) return <Loading />;
  const insights = data.insights || [];
  const inv = bi.investigations || [];
  const period = Object.values(bi.reliable_periods || {}).find((p) => p && p.length);
  const p = (x) => `${String(x % 100).padStart(2, "0")}/${Math.floor(x / 100)}`;
  const signals = (facts || []).filter((f) => f.type !== "valeur" && f.type !== "value");
  return (
    <>
      <Section title="What the analysis found" lead="Each KPI tracked month by month goes through five statistical tests: trend, recent change, year over year, unusual month, level shift. The signals kept are broken down by segment to find where the change happens. The AI writes the insights; the code re-checks every number before publishing them.">
        <Tiles items={[
          { label: "Insights published", value: fmtInt(insights.length), note: `${bi.insights_llm || 0} written by the AI`, accent: true },
          { label: "Series analyzed", value: fmtInt(bi.series), note: period ? `from ${p(period[0])} to ${p(period[1])}` : "no usable date" },
          { label: "Signals detected", value: fmtInt(bi.signals), note: "by the statistical tests" },
          { label: "Leads investigated", value: fmtInt(inv.length), note: inv.some((i) => i.source === "LLM") ? "chosen by the AI" : "chosen by the code" },
        ]} />
      </Section>
      {insights.length ? (
        <Section title="The insights" lead="From most to least important. The sources (F…) point to the measured facts.">
          <div className="grid">
            {insights.map((i) => {
              const [label, kind] = INSIGHT_TYPE[i.type] || [i.type, "neutral"];
              return (
                <div className={`card edge-${kind}`} key={i.id || i.titre}>
                  <div className="row"><h4>{i.titre}</h4><Badge kind={kind}>{label}</Badge></div>
                  <p>{i.texte}</p>
                  <div className="reco"><b>Recommendation:</b> {i.recommandation}</div>
                  <div className="meta">{i.source === "LLM" ? "Written by the AI · every number re-checked by the code" : "Written automatically from the statistical tests"} · sources: {(i.faits || []).join(", ")}</div>
                </div>
              );
            })}
          </div>
        </Section>
      ) : <Empty title="No notable signal" icon="trend">The series are too short or stable: no clear change was detected.</Empty>}
      {inv.length > 0 && (
        <Section title="The leads investigated" lead="To explain a signal, the agent picks the most telling breakdown dimension.">
          <div className="grid">
            {inv.map((i, k) => (
              <div className="card" key={k}>
                <div className="row"><h4>Signal {i.fait} broken down by "{i.axe}"</h4><Badge kind="violet">{i.source === "LLM" ? "AI" : "code"}</Badge></div>
                <p>{humanText(i.pourquoi) || "Most discriminating dimension for this signal."}</p>
                <div className="meta">{i["résultat"] ? `New fact: ${i["résultat"]}` : "Nothing significant"}</div>
              </div>
            ))}
          </div>
        </Section>
      )}
      {signals.length > 0 && (
        <details className="more">
          <summary>See all measured facts ({signals.length})</summary>
          <div><DataTable columns={[{ key: "id", label: "Fact" }, { key: "type", label: "Type", render: (v) => FACT_TYPE[v] || v },
            { key: "texte", label: "Finding" }, { key: "valence", label: "Reading", render: (v) => VALENCE[v] || v }]} rows={signals} /></div>
        </details>
      )}
    </>
  );
}

// ---------------------------------------------------------------- 7. dashboard
export function Dashboard({ jobId }) {
  return (
    <Section title="Your dashboard" lead="Generated automatically by the Dashboard Generator Agent. Every value comes from the KPI catalog. The file also works offline: download it and open it in any browser."
      right={<div className="actions">
        <a className="btn sm" href={`${apiBase()}/api/jobs/${jobId}/dashboard`} target="_blank" rel="noreferrer"><Icon name="layout" size={15} /> Full screen</a>
        <a className="btn sm primary" href={downloadUrl(jobId, "dashboard")}><Icon name="download" size={15} /> Download</a>
      </div>}>
      <iframe className="dash-frame" src={`${apiBase()}/api/jobs/${jobId}/dashboard`} title="BIFlow dashboard" />
    </Section>
  );
}
