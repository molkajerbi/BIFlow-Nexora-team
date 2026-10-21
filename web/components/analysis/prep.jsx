"use client";
// Data preparation tabs: understanding, diagnosis, cleaning, modeling.
import { useState } from "react";
import { Dumbbell, Legend, StarSchema } from "../charts";
import { Badge, Banner, DataTable, Empty, Loading, Section, Tiles } from "../ui";
import { useApi } from "@/lib/api";
import {
  ACTION, CORRECTION, DECIDED_BY, DIMENSION, HEALTH_COLS, QUALITY_STATUS, SEM_TYPE, SEVERITY, cleanDescription, fmtInt, fmtNum,
  friendlyRule, humanText, indicatorLabel, plural, showValue, starName, testLabel,
} from "@/lib/format";

export function useTable(jobId, name, limit = 2000) {
  const { data } = useApi(`/api/jobs/${jobId}/table/${name}?limit=${limit}`);
  return data ? (data.missing ? [] : data.rows) : null;
}

// ---------------------------------------------------------------- 1. understanding
export function Understanding({ jobId, res }) {
  const contract = useTable(jobId, "contract_tables");
  const rels = useTable(jobId, "relationships");
  const cols = useTable(jobId, "contract_columns");
  const inp = res.input || {};
  const checks = res.points_to_check || [];
  if (!contract) return <Loading />;
  return (
    <>
      <Section title="What BIFlow understood from your files"
        lead="The tables and the links between them were found automatically, without any configuration.">
        <Tiles items={[
          { label: "Tables", value: fmtInt(inp.tables || contract.length), note: "one per file or sheet", accent: true },
          { label: "Rows", value: fmtInt(inp.rows), note: "read without any change" },
          { label: "Links between tables", value: fmtInt((rels || []).length), note: "detected automatically" },
          { label: "Structure recognized with certainty", value: `${Math.round(res.confidence_pct || 0)}%`,
            note: checks.length ? plural(checks.length, "point to check", "points to check") : "no doubtful point" },
        ]} />
        {checks.map((p, i) => <Banner key={i} kind="warn" title="Point to check">{String(p)}</Banner>)}
      </Section>
      <Section title="Tables">
        <div className="grid">
          {contract.map((t) => {
            const desc = cleanDescription(t.description);
            return (
              <div className="card" key={t.table}>
                <h4>{t.table}</h4>
                {desc && <p>{desc}</p>}
                <div className="meta">{fmtInt(t.lignes)} rows · {t.colonnes} columns · identifier: {t.grain || "none (several rows per value)"}</div>
              </div>
            );
          })}
        </div>
      </Section>
      {rels && rels.length > 0 && (
        <Section title="Links between the tables" lead="Each row of the first table finds its match in the second one.">
          <DataTable columns={[
            { key: "child", label: "Table" }, { key: "parent", label: "Linked to" }, { key: "fk", label: "Through the column" },
            { key: "aggregate", label: "Link type", render: (v) => (String(v) === "true" || v === true ? "aggregation (several rows)" : "direct") },
          ]} rows={rels} />
        </Section>
      )}
      {cols && (
        <details className="more">
          <summary>See the column details ({cols.length})</summary>
          <div><DataTable columns={[{ key: "table", label: "Table" }, { key: "colonne", label: "Column" },
            { key: "type", label: "Kind", render: (v) => SEM_TYPE[v] || v }]} rows={cols} max={2000} /></div>
        </details>
      )}
    </>
  );
}

// ---------------------------------------------------------------- 2. diagnosis
function FindingsSummary({ report }) {
  const n = (s) => report.filter((f) => f.severity === s).length;
  const parts = [[n("blocking"), "Critical", "to fix first", "#C0362C"], [n("warning"), "To watch", "do not block the analysis", "#E0A14A"],
    [n("info"), "For information", "simple remarks", "#8A94A8"]];
  const total = report.length;
  const explained = report.filter((f) => f.source === "LLM").length;
  if (!total) return <Banner kind="ok" title="No problem found">The diagnosis found nothing unusual in your data.</Banner>;
  return (
    <div className="findings">
      <div className="big"><b>{total}</b><span>points found in your data</span></div>
      <div>
        <div className="sevbar">{parts.filter((p) => p[0]).map(([k, t, , c]) => <span key={t} style={{ flex: k, background: c }} title={`${t}: ${k}`} />)}</div>
        <div className="sevleg">{parts.map(([k, t, d, c]) => <div key={t}><i style={{ background: c }} /><b>{k}</b> {t.toLowerCase()}<small>{d}</small></div>)}</div>
        <p>The AI wrote a plain-language explanation for {explained} of these points. Every number quoted was compared with the real measurements
          {total - explained ? `; ${total - explained} explanation(s) with an inaccurate number were set aside.` : "."}</p>
      </div>
    </div>
  );
}

export function Diagnostic({ jobId }) {
  const report = useTable(jobId, "profiling_report");
  const health = useTable(jobId, "health_map");
  const [table, setTable] = useState("");
  const [level, setLevel] = useState("");
  if (!report) return <Loading />;
  const order = { blocking: 0, warning: 1, info: 2 };
  const view = report.filter((f) => (!table || f.table === table) && (!level || f.severity === level))
    .sort((a, b) => (order[a.severity] ?? 3) - (order[b.severity] ?? 3));
  const healthCols = health && health.length ? Object.keys(health[0]).filter((k) => k !== "colonnes_avec_manquants" && k !== "columns_with_missing") : [];
  return (
    <>
      <Section title="The diagnosis of your data" lead="BIFlow screened every column: empty values, duplicates, abnormal values, broken links… Each point found is then explained by the AI in plain language. An explanation is kept only if all its numbers match the real measurements.">
        <FindingsSummary report={report} />
      </Section>
      {healthCols.length > 0 && (
        <Section title="Health by table">
          <DataTable columns={healthCols.map((k) => ({
            key: k, label: HEALTH_COLS[k] || k,
            render: (v) => (k === "grain_unique" ? (String(v) === "true" || v === true ? "Yes" : String(v) === "false" || v === false ? "No" : "—")
              : k === "cellules_manquantes_%" && v !== null ? `${Number(v).toFixed(1)}%` : v === null ? "—" : String(v)),
          }))} rows={health} />
        </Section>
      )}
      <Section title="The points found, in detail" lead="For each point: what was measured, the AI's explanation and the recommendation.">
        <div className="filters">
          <select className="select" value={table} onChange={(e) => setTable(e.target.value)}>
            <option value="">All tables</option>
            {[...new Set(report.map((f) => f.table))].sort().map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <select className="select" value={level} onChange={(e) => setLevel(e.target.value)}>
            <option value="">All levels</option>
            <option value="blocking">Critical</option><option value="warning">To watch</option><option value="info">Information</option>
          </select>
        </div>
        {view.length ? (
          <div className="grid">
            {view.slice(0, 60).map((f) => {
              const [label, kind] = SEVERITY[f.severity] || [f.severity, "neutral"];
              const where = !f.colonne || f.colonne === "*" ? f.table : `${f.table} › ${f.colonne}`;
              const text = f.interpretation && !/^(Non interprété|Not interpreted)/.test(String(f.interpretation)) ? f.interpretation
                : "To review: this point could not be explained automatically.";
              return (
                <div className={`card edge-${kind}`} key={f.id}>
                  <div className="row"><h4>{where}</h4><Badge kind={kind}>{label}</Badge></div>
                  <p>{text}</p>
                  <div className="meta">{DIMENSION[f.dimension] || f.dimension} · measured: {f.constat}<br />
                    Recommendation: <b>{ACTION[f.action] || f.action}</b></div>
                </div>
              );
            })}
          </div>
        ) : <Empty title="Nothing for this filter">Try another table or level.</Empty>}
        {view.length > 60 && <p className="note">60 points shown out of {view.length}. Use the filters to narrow down.</p>}
      </Section>
    </>
  );
}

// ---------------------------------------------------------------- 3. cleaning
export function Cleaning({ jobId, res }) {
  const scores = useTable(jobId, "quality_scores");
  const plan = useTable(jobId, "cleaning_plan");
  const applied = useTable(jobId, "corrections_applied");
  const changes = useTable(jobId, "cell_changes_sample");
  const dismissed = useTable(jobId, "dismissed");
  const rules = useTable(jobId, "rules_after");
  if (!scores || !plan) return <Loading />;
  const q = res.quality || {};
  const qs = res.quality_status || q.quality_status;
  const remaining = (rules || []).filter((r) => Number(r.violations) > 0);
  const effects = Object.fromEntries((applied || []).map((a) => [a.id, a.effect]));
  const dim = (r) => r.dimension || r.index;
  const avg = (k) => (scores.length ? scores.reduce((s, r) => s + Number(r[k] || 0), 0) / scores.length : 0);
  return (
    <>
      <Section title="The cleaning of your data" lead="The agent fixes formats, removes duplicates, estimates missing values, replaces impossible values and caps extreme values. Each correction is first tested on a copy, and the original value always stays in the log.">
        {QUALITY_STATUS[qs] && <Banner kind={QUALITY_STATUS[qs][1]} title={QUALITY_STATUS[qs][0]}>Every row keeps a trace of what concerns it.</Banner>}
        {scores.length > 0 && (
          <Tiles items={[
            { label: "Quality score", value: `${fmtNum(avg("après"))} / 100`, note: `versus ${fmtNum(avg("avant"))} before cleaning`, accent: true },
            { label: "Cells corrected", value: fmtInt(q.cells_changed || 0), note: "corrected or estimated" },
            { label: "Duplicate rows removed", value: fmtInt(q.rows_changed || 0), note: "exact copies" },
            { label: "Points to watch", value: fmtInt(remaining.length), note: "flagged, never deleted" },
          ]} />
        )}
      </Section>
      {scores.length > 0 && (
        <Section title="Quality by aspect, before and after" lead="For each aspect, the share of rows that pass all checks (average over the tables).">
          <Legend items={[["Before cleaning", "#E0A14A"], ["After cleaning", "#14B8A6"]]} />
          <Dumbbell rows={scores.map((r) => [DIMENSION[dim(r)] || dim(r), Number(r["avant"]), Number(r["après"])])} />
        </Section>
      )}
      {plan.length > 0 && (
        <Section title="Corrections applied">
          <div className="grid">
            {plan.map((p) => {
              const [title, explain] = CORRECTION[p.correction] || [p.correction, ""];
              const where = p.colonne === "*" ? p.table : `${p.table} › ${p.colonne}`;
              const done = p.id in effects;
              const effect = !done ? "not applied" : p.correction === "drop_exact_duplicates"
                ? plural(effects[p.id], "row removed", "rows removed") : plural(effects[p.id], "cell corrected", "cells corrected");
              const ex = (changes || []).find((c) => c.correction === p.id && showValue(c.before) !== showValue(c.after));
              const why = p["décidé_par"] === "agent" ? humanText(p.justification) : "";
              return (
                <div className={`card edge-${done ? "ok" : "neutral"}`} key={p.id}>
                  <div className="row"><h4>{title}</h4><Badge kind={done ? "ok" : "neutral"}>{effect}</Badge></div>
                  <p>{explain}</p>
                  {ex && p.correction !== "drop_exact_duplicates" && (
                    <div className="swap"><code>{showValue(ex.before)}</code>becomes<code className="after">{showValue(ex.after)}</code></div>
                  )}
                  <div className="meta">{where} · {DECIDED_BY[p["décidé_par"]] || p["décidé_par"]}{why ? <><br />"{why}"</> : null}</div>
                </div>
              );
            })}
          </div>
        </Section>
      )}
      {dismissed && dismissed.length > 0 && (
        <Section title="Corrections set aside by the AI" lead="These problems stay flagged in the data, without being changed.">
          <div className="grid">
            {dismissed.map((d, i) => (
              <div className="card" key={i}><h4>{d.table}</h4><p>{humanText(d.justification) || "The AI judged that this correction was not useful."}</p></div>
            ))}
          </div>
        </Section>
      )}
      {remaining.length > 0 && (
        <Section title="Points still to watch" lead="They are flagged row by row in the delivered data.">
          <DataTable columns={[
            { key: "table", label: "Table" }, { key: "dimension", label: "Aspect", render: (v) => DIMENSION[v] || v },
            { key: "description", label: "Check", render: friendlyRule }, { key: "violations", label: "Rows concerned" },
            { key: "severity", label: "Level", render: (v) => (SEVERITY[v] || [v])[0] },
          ]} rows={remaining} />
        </Section>
      )}
    </>
  );
}

// ---------------------------------------------------------------- 4. modeling
function Preview({ jobId, names }) {
  const [choice, setChoice] = useState(names[0]);
  const { data } = useApi(choice ? `/api/jobs/${jobId}/preview/${choice}` : null);
  return (
    <Section title="Table preview" lead="The first 200 rows of each star schema table.">
      <div className="filters">
        <select className="select" value={choice} onChange={(e) => setChoice(e.target.value)}>
          {names.map((n) => <option key={n} value={n}>{starName(n)[0]} ({starName(n)[1].toLowerCase()})</option>)}
        </select>
      </div>
      {data ? <DataTable columns={data.columns.map((c) => ({ key: c, label: c }))} rows={data.rows} /> : <Loading />}
    </Section>
  );
}

export function Model({ jobId }) {
  const { data: star } = useApi(`/api/jobs/${jobId}/star`);
  const tests = useTable(jobId, "etl_tests");
  const derived = useTable(jobId, "derived_indicators");
  if (!star || !tests) return <Loading />;
  const names = Object.keys(star);
  const nFacts = names.filter((n) => star[n].type === "fait").length;
  const passed = tests.filter((t) => String(t.OK) === "true" || t.OK === true).length;
  return (
    <>
      <Section title="The star schema" lead="Your data is organized the way BI tools expect it: fact tables (the events) linked to dimensions (who, what, where, when).">
        <Tiles items={[
          { label: "Fact tables", value: fmtInt(nFacts), note: "the events to analyze", accent: true },
          { label: "Dimensions", value: fmtInt(names.length - nFacts), note: "including the calendar" },
          { label: "Tables validated", value: `${passed} / ${tests.length}`, note: "all their checks passed" },
          { label: "Indicators computed", value: fmtInt((derived || []).length), note: "delays and lateness, from the dates" },
        ]} />
        <StarSchema star={star} />
        <Legend items={[["Fact table", "#2F6BF6"], ["Dimension", "#C9D1E0"]]} />
      </Section>
      {tests.length > 0 && (
        <Section title="Consistency checks" lead="After building each table: no duplicates, no rows lost, totals preserved, valid links.">
          <DataTable columns={[
            { key: "table", label: "Table", render: (v) => starName(v)[0] }, { key: "type", label: "Type", render: (v, r) => starName(r.table)[1] },
            { key: "lignes", label: "Rows", render: fmtInt },
            { key: "checks", label: "Checks passed", render: (v, r) => {
              const keys = Object.keys(r).filter((k) => testLabel(k) && ["true", "false"].includes(String(r[k])));
              return `${keys.filter((k) => String(r[k]) === "true").length} / ${keys.length}`;
            } },
            { key: "OK", label: "Status", render: (v) => (String(v) === "true" ? "✓ Valid" : "✗ To review") },
          ]} rows={tests} />
        </Section>
      )}
      {derived && derived.length > 0 && (
        <Section title="Indicators computed automatically" lead="New columns created from the dates in your data, ready for your dashboards.">
          <div className="grid">
            {derived.map((d) => {
              const [title, meaning] = indicatorLabel(d.colonne, d.type, d.calcul);
              return (
                <div className="card" key={`${d.table}.${d.colonne}`}>
                  <div className="row"><h4>{title}</h4><Badge kind="info" dot={false}>{/délai|duration|delay/.test(String(d.type)) ? "delay in days" : "yes / no"}</Badge></div>
                  <p>{meaning}</p>
                  <div className="meta">Table {d.table} · new column {d.colonne}</div>
                </div>
              );
            })}
          </div>
        </Section>
      )}
      {names.length > 0 && <Preview jobId={jobId} names={names} />}
    </>
  );
}
