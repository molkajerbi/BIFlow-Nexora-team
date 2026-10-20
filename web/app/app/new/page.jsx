"use client";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import Icon from "@/components/Icon";
import { Banner, Pipeline } from "@/components/ui";
import { uploadAnalysis } from "@/lib/api";
import { fmtSize } from "@/lib/format";
import { useSession } from "@/lib/session";

const ACCEPT = ".csv,.tsv,.txt,.xlsx,.xls,.parquet,.json,.zip";
const OK_EXT = /\.(csv|tsv|txt|xlsx|xls|parquet|json|zip)$/i;

export default function NewAnalysis() {
  const router = useRouter();
  const { health } = useSession();
  const input = useRef(null);
  const [step, setStep] = useState(1);
  const [files, setFiles] = useState([]);
  const [over, setOver] = useState(false);
  const [name, setName] = useState("");
  const [model, setModel] = useState("");
  const [sending, setSending] = useState(null);
  const [error, setError] = useState("");

  function add(list) {
    const picked = Array.from(list || []);
    const bad = picked.filter((f) => !OK_EXT.test(f.name));
    const good = picked.filter((f) => OK_EXT.test(f.name));
    setError(bad.length ? `Unsupported format: ${bad.map((f) => f.name).join(", ")}` : "");
    const names = new Set(files.map((f) => f.name));
    const next = [...files, ...good.filter((f) => !names.has(f.name))];
    setFiles(next);
    if (!name && next.length) setName(next.length === 1 ? next[0].name.replace(/\.[^.]+$/, "") : `Analysis of ${next.length} files`);
  }

  async function start() {
    setError("");
    setSending(0);
    try {
      const chosen = model || (health && health.default_model) || "qwen2.5:7b";
      const { id } = await uploadAnalysis(files, name, chosen, setSending);
      router.push(`/app/analyses/${id}`);
    } catch (e) {
      setError(e.message);
      setSending(null);
    }
  }

  const total = files.reduce((s, f) => s + f.size, 0);
  const models = (health && health.models) || [];
  const steps = ["Upload", "Review", "Analysis", "Results"];
  return (
    <>
      <div className="page-head">
        <div>
          <h1>New analysis</h1>
          <p>Drop your dataset: everything happens on this computer, with no action needed from you.</p>
        </div>
      </div>
      <div className="steps">
        {steps.map((s, i) => (
          <span key={s} style={{ display: "contents" }}>
            {i > 0 && <span className="sep" />}
            <span className={`s${step === i + 1 ? " on" : step > i + 1 ? " done" : ""}`}><i>{step > i + 1 ? "✓" : i + 1}</i>{s}</span>
          </span>
        ))}
      </div>
      {health && !health.ollama && (
        <Banner kind="crit" title="The local AI engine is not running">
          Open the Ollama app on this computer, then reload the page. The analysis needs the local AI.
        </Banner>
      )}
      <div className="panel">
        {step === 1 && (
          <>
            <div className={`drop${over ? " over" : ""}`} onClick={() => input.current && input.current.click()}
              onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
              onDrop={(e) => { e.preventDefault(); setOver(false); add(e.dataTransfer.files); }}>
              <div className="ico"><Icon name="upload" size={28} /></div>
              <b>Drag your files here</b>
              <span>or click to choose them: one or more files from the same dataset, or a zipped folder</span>
              <div className="formats">{["CSV", "Excel", "Parquet", "JSON", "TSV", "ZIP"].map((f) => <i key={f}>{f}</i>)}</div>
              <input ref={input} type="file" multiple accept={ACCEPT} hidden onChange={(e) => { add(e.target.files); e.target.value = ""; }} />
            </div>
            {files.length > 0 && (
              <ul className="files">
                {files.map((f) => (
                  <li key={f.name}>
                    <Icon name="file" size={18} />
                    <span>{f.name}</span>
                    <small>{fmtSize(f.size)}</small>
                    <button onClick={() => setFiles(files.filter((x) => x !== f))} aria-label={`Remove ${f.name}`}><Icon name="x" size={16} /></button>
                  </li>
                ))}
              </ul>
            )}
            {error && <p className="error-text" style={{ marginTop: "1rem" }}>{error}</p>}
            <div className="panel-foot">
              <span className="muted">{files.length ? `${files.length} file${files.length === 1 ? "" : "s"} · ${fmtSize(total)}` : "No files yet"}</span>
              <button className="btn primary" disabled={!files.length} onClick={() => setStep(2)}>Continue <Icon name="arrow" size={17} /></button>
            </div>
          </>
        )}
        {step === 2 && (
          <>
            <div className="field">
              <label htmlFor="name">Analysis name</label>
              <input id="name" className="input" value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g. Sales 2024" />
            </div>
            <div className="field">
              <label htmlFor="model">Local AI model</label>
              <select id="model" className="select" value={model || (health && health.default_model) || ""} onChange={(e) => setModel(e.target.value)}>
                {(models.length ? models : ["qwen2.5:7b"]).map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
              <span className="hint">The 7b is more accurate; the 3b is about twice as fast.</span>
            </div>
            <ul className="files">
              {files.map((f) => <li key={f.name}><Icon name="file" size={18} /><span>{f.name}</span><small>{fmtSize(f.size)}</small></li>)}
            </ul>
            <p className="note">
              <Icon name="clock" size={14} /> On a computer without a graphics card, a full analysis usually takes 10 to 40 minutes.
              You can close the page: the analysis keeps running, and you will find it in "My analyses".
            </p>
            {sending !== null && (
              <>
                <div className="progress-line"><span style={{ width: `${sending}%` }} /></div>
                <span className="muted">{sending < 100 ? `Uploading files… ${sending}%` : "Starting the agents…"}</span>
              </>
            )}
            {error && <p className="error-text" style={{ marginTop: "1rem" }}>{error}</p>}
            <div className="panel-foot">
              <button className="btn ghost" onClick={() => setStep(1)} disabled={sending !== null}><Icon name="back" size={16} /> Back</button>
              <button className="btn primary lg" onClick={start} disabled={sending !== null || (health && !health.ollama)}>
                <Icon name="zap" size={18} /> Start the analysis
              </button>
            </div>
          </>
        )}
      </div>
      <section className="section">
        <div className="section-head"><div><h2>What will happen</h2>
          <p className="lead">Seven steps run one after another automatically. You follow them live, and each agent's results show up as soon as it is done.</p></div></div>
        <Pipeline completed={0} status="todo" />
      </section>
    </>
  );
}
