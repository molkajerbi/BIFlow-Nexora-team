import Link from "next/link";
import Icon from "@/components/Icon";
import PublicNav, { PublicFooter } from "@/components/PublicNav";

const STEPS = [
  ["upload", "1 · Drop your files", "CSV, Excel, Parquet, JSON or a zipped folder: one or more tables from the same dataset. No configuration, no schema to write."],
  ["cpu", "2 · The agents get to work", "They understand your tables, diagnose quality, clean without losing anything, build a star schema, then compute and analyze your KPIs."],
  ["message", "3 · Explore and ask why", "Verified KPIs, quantified insights, an interactive dashboard, and an assistant that answers \"why?\" about every decision, with evidence."],
];

const AGENTS = [
  ["search", "Domain & Contract Agent", "Understanding", "Reads your files and recognizes the business domain, the type of each column, the identifiers and the links between tables."],
  ["activity", "Profiler Agent", "Diagnosis", "Measures missing values, duplicates, anomalies and extreme values, then explains each finding in plain language."],
  ["sparkles", "Data Quality Agent", "Cleaning", "Tests every correction in a sandbox before deciding: formats, duplicates, missing, impossible and extreme values."],
  ["star", "ETL Agent", "Modeling", "Builds a star schema (facts and dimensions) and checks every table: no rows lost, totals preserved."],
  ["target", "BI Semantic & KPI Agent", "KPIs", "Finds your sector's KPIs in its knowledge base (RAG), binds each one to the right columns and computes it twice."],
  ["trend", "BI Analyst Agent", "Analysis", "Five statistical tests per series: trend, recent change, year over year, unusual month, level shift. Then it finds where it happens."],
  ["layout", "Dashboard Generator Agent", "Dashboard", "Composes a standalone dashboard: headline figure, tiles, trends, breakdowns and insights."],
  ["bot", "XAI Agent", "Explanations", "Answers your questions about any decision: why, who decided, and what would have changed it."],
];

const GUARANTEES = [
  ["shield", "The LLM proposes, the code verifies", "Every AI answer is checked: an explanation that quotes a number missing from the measurements is rejected, sent back to the AI, then replaced by a rule if needed."],
  ["lock", "Nothing is lost, everything is traced", "Your raw files are never modified. Every correction keeps the original value, and a chained audit log proves no step was rewritten."],
  ["info", "Honest limits", "On a computer without a graphics card, an analysis takes several minutes. Reference KPIs cover retail, telecom, banking and transport; elsewhere, BIFlow switches to generic mode."],
];

const DELIVERABLES = [
  ["database", "A star schema", "a database ready for your BI tools"],
  ["shield", "Clean data", "nothing lost, every correction traced"],
  ["target", "A KPI catalog", "every value computed twice"],
  ["trend", "Quantified insights", "each one with a recommendation"],
  ["layout", "A dashboard", "a file that opens anywhere, even offline"],
  ["message", "An explainable assistant", "\"why?\" about every decision"],
];

export default function Home() {
  return (
    <div className="public">
      <PublicNav />
      <main className="wrap">
        <section className="hero">
          <div>
            <span className="eyebrow"><Icon name="sparkles" size={14} stroke={2.4} /> Eight AI agents for Business Intelligence</span>
            <h1>Your raw data. <span>Explained decisions.</span></h1>
            <p className="sub">
              Drop your files: BIFlow prepares them, builds a star schema, computes your business KPIs, detects what
              changes and delivers a dashboard. And for every decision, you can ask why.
            </p>
            <div className="hero-cta">
              <Link className="btn primary lg" href="/signup">Analyze my data <Icon name="arrow" size={18} /></Link>
              <a className="btn lg" href="#how">See how it works</a>
            </div>
            <div className="hero-note">
              <span><Icon name="lock" size={15} /> 100% local</span>
              <span><Icon name="cpu" size={15} /> Built-in AI, no API key</span>
              <span><Icon name="route" size={15} /> Every change traced</span>
            </div>
          </div>
          <div className="demo" aria-label="Example result">
            <div className="demo-head"><span>Example result</span><span className="badge ok dot">Analysis finished</span></div>
            <div className="demo-kpis">
              <div className="demo-kpi"><small>Revenue</small><b>357,826</b><i className="down">▼ −20.3% over 3 months</i></div>
              <div className="demo-kpi"><small>Average basket</small><b>119.28</b><i className="up">▲ +2.1%</i></div>
              <div className="demo-kpi"><small>Delivery time</small><b>13.0 d</b><i className="down">▲ +2.8%</i></div>
              <div className="demo-kpi"><small>Buying customers</small><b>2,600</b><i className="up">computed twice</i></div>
            </div>
            <div className="demo-insight">
              <b>Alert · Negative reviews are rising</b>
              <p>Share of negative reviews: from 17.3% to 23.0% in the "RJ" region, which explains 57% of the increase.</p>
            </div>
            <div className="demo-chat">
              <div className="q">Why the median for this column?</div>
              <div className="a">Because 12% of the values are extreme: the mean would be pulled up. Decided by the AI, verified by the code [D042].</div>
            </div>
            <div className="demo-foot">Example figures. Yours will come from your own data.</div>
          </div>
        </section>
      </main>

      <section className="block alt" id="how">
        <div className="wrap">
          <h2 className="title">A folder of files in. An explained dashboard out.</h2>
          <p className="intro">You write no query, no rule, no schema: the agent chain does it all, and you follow every step live.</p>
          <div className="features">
            {STEPS.map(([ico, t, d]) => (
              <div className="feature" key={t}>
                <div className="fi"><Icon name={ico} size={22} /></div>
                <h3>{t}</h3>
                <p>{d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="block" id="agents">
        <div className="wrap agents">
          <div className="sticky-card">
            <h2 className="title">Eight agents, one chain that checks itself.</h2>
            <p className="intro">This is the pipeline behind every analysis, fully automatic: no human validation is needed.</p>
            <div className="principle">
              <h3>The AI proposes. The code verifies.</h3>
              <p>The language model (qwen2.5 via Ollama, on your machine) chooses and writes. The code tests, computes and checks every number before accepting it.</p>
              <ul>
                <li><i><Icon name="check" size={15} stroke={2.6} /></i>Every KPI computed in SQL, then recomputed another way: both must match.</li>
                <li><i><Icon name="check" size={15} stroke={2.6} /></i>Every correction tested in a sandbox before being applied.</li>
                <li><i><Icon name="check" size={15} stroke={2.6} /></i>Every insight cites its facts: an invented number is rejected.</li>
              </ul>
            </div>
          </div>
          <ol className="timeline">
            {AGENTS.map(([ico, name, role, d]) => (
              <li key={name}>
                <span className="n"><Icon name={ico} size={17} /></span>
                <b>{name}<small>{role}</small></b>
                <p>{d}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="block alt" id="guarantees">
        <div className="wrap">
          <h2 className="title">What it does well, and its limits.</h2>
          <p className="intro">A decision tool should say what it knows, how it knows it, and what it doesn't know.</p>
          <div className="features">
            {GUARANTEES.map(([ico, t, d]) => (
              <div className="feature" key={t}>
                <div className="fi"><Icon name={ico} size={22} /></div>
                <h3>{t}</h3>
                <p>{d}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="block">
        <div className="wrap">
          <h2 className="title">What you get at the end.</h2>
          <p className="intro">Everything downloads in one click: a zip with all deliverables, the star schema database alone, or the dashboard alone.</p>
          <div className="deliverables">
            {DELIVERABLES.map(([ico, t, d]) => (
              <div className="deliverable" key={t}>
                <i><Icon name={ico} size={20} /></i>
                <div><b>{t}</b><span>{d}</span></div>
              </div>
            ))}
          </div>
          <div className="cta">
            <h2>Ready to make your data talk?</h2>
            <p>A free account, a folder of files, and the agents take care of the rest.</p>
            <Link className="btn lg" href="/signup"><Icon name="user-plus" size={18} /> Create my free account</Link>
          </div>
        </div>
      </section>
      <PublicFooter />
    </div>
  );
}
