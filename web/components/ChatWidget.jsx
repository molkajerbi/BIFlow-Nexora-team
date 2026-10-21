"use client";
// BIFlow assistant: round button in the corner of the screen that opens the conversation with the notebook's XAI agent.
// It answers about the whole analysis (data, cleaning, KPIs, insights, dashboard) and how the code decides.
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import Icon from "./Icon";
import { Spinner } from "./ui";
import { api } from "@/lib/api";
import { markdownToHtml } from "@/lib/markdown";

function Answer({ turn }) {
  const verified = turn.mode === "LLM (vérifié)" || turn.mode === "LLM (verified)";
  const refused = turn.refus_llm || turn.llm_rejections || [];
  return (
    <div className="msg-a">
      <div dangerouslySetInnerHTML={{ __html: markdownToHtml(turn["réponse"] || turn.answer) }} />
      <div className="msg-meta">
        <Icon name={verified ? "shield" : "list"} size={12} />
        {verified ? "Rephrased by the AI · numbers verified by the code" : "Answer from the system rules"}
        {refused.length ? " · rephrasing rejected by the code" : ""}
        {turn.sources && turn.sources.length ? ` · sources: ${turn.sources.join(", ")}` : ""}
      </div>
    </div>
  );
}

export default function ChatWidget() {
  const pathname = usePathname() || "";
  const [open, setOpen] = useState(false);
  const [jobs, setJobs] = useState(null);
  const [jobId, setJobId] = useState(null);
  const [chat, setChat] = useState(null);
  const [pending, setPending] = useState(null);
  const [text, setText] = useState("");
  const [useLlm, setUseLlm] = useState(true);
  const [error, setError] = useState("");
  const body = useRef(null);
  const current = (/^\/app\/analyses\/([^/]+)/.exec(pathname) || [])[1];

  useEffect(() => {
    if (!open) return;
    api("/api/chat/jobs").then((d) => {
      setJobs(d.jobs);
      setJobId((id) => {
        const ids = d.jobs.map((j) => j.id);
        if (id && ids.includes(id)) return id;
        return ids.includes(current) ? current : ids[0] || null;
      });
    }).catch((e) => setError(e.message));
  }, [open, current]);

  useEffect(() => {
    if (!open || !jobId) return;
    setChat(null);
    setError("");
    api(`/api/jobs/${jobId}/chat`).then(setChat).catch((e) => setError(e.message));
  }, [open, jobId]);

  useEffect(() => {
    if (body.current) body.current.scrollTop = body.current.scrollHeight;
  }, [chat, pending, open]);

  async function ask(question) {
    const q = (question || "").trim();
    if (!q || pending) return;
    setText("");
    setPending(q);
    setError("");
    try {
      const d = await api(`/api/jobs/${jobId}/chat`, { method: "POST", body: { question: q, use_llm: useLlm } });
      setChat((c) => ({ ...c, history: [...(c?.history || []), d.turn] }));
    } catch (e) {
      setError(e.message);
    }
    setPending(null);
  }

  async function clear() {
    await api(`/api/jobs/${jobId}/chat`, { method: "DELETE" }).catch(() => {});
    setChat((c) => ({ ...c, history: [] }));
  }

  const job = (jobs || []).find((j) => j.id === jobId);
  const history = (chat && chat.history) || [];
  return (
    <>
      {open && (
        <div className="chat" role="dialog" aria-label="BIFlow assistant">
          <div className="chat-top">
            <div className="ai"><Icon name="bot" size={21} /></div>
            <div style={{ minWidth: 0 }}>
              <b>BIFlow assistant</b>
              <span>{job ? `Analysis "${job.name}"` : "Explains every decision"}</span>
            </div>
            {jobs && jobs.length > 1 && (
              <select value={jobId || ""} onChange={(e) => setJobId(e.target.value)} aria-label="Analysis">
                {jobs.map((j) => <option key={j.id} value={j.id}>{j.name}</option>)}
              </select>
            )}
          </div>
          <div className="chat-body" ref={body}>
            {jobs && !jobs.length && (
              <div className="chat-hello">
                The assistant answers as soon as an analysis is finished. Start an analysis: I will then be able to explain
                every decision of the agents, with evidence.
              </div>
            )}
            {jobs && jobs.length > 0 && !chat && !error && <div className="typing"><Spinner size={15} /> Preparing the assistant…</div>}
            {chat && !history.length && !pending && (
              <>
                <div className="chat-hello">
                  Hello! I know each of the {chat.decisions || ""} decisions made during this analysis and the code rules
                  that produced them. Ask me <b>why</b>, <b>how</b>, <b>who decided</b>, or <b>what if…?</b>
                </div>
                <div className="chat-sugg">
                  {(chat.suggestions || []).map((q) => <button key={q} onClick={() => ask(q)}>{q}</button>)}
                </div>
              </>
            )}
            {history.map((t, i) => (
              <div key={i} style={{ display: "contents" }}>
                <div className="msg-q">{t.question}</div>
                <Answer turn={t} />
              </div>
            ))}
            {pending && (
              <>
                <div className="msg-q">{pending}</div>
                <div className="typing"><Spinner size={15} /> Finding the decision and preparing the explanation…</div>
              </>
            )}
            {error && <div className="chat-hello" style={{ color: "var(--crit)" }}>{error}</div>}
          </div>
          <div className="chat-foot">
            <form className="chat-form" onSubmit={(e) => { e.preventDefault(); ask(text); }}>
              <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Ask your question…"
                disabled={!chat || !!pending} aria-label="Your question" />
              <button disabled={!chat || !!pending || !text.trim()} aria-label="Send"><Icon name="send" size={18} /></button>
            </form>
            <div className="chat-opts">
              <label className="switch" title="On: more natural answer, every number verified by the code. Off: instant answer from the rules.">
                <input type="checkbox" checked={useLlm} onChange={(e) => setUseLlm(e.target.checked)} />
                <i /> Rephrase with the AI
              </label>
              {history.length > 0 && <button className="linkish" onClick={clear}>Clear the conversation</button>}
            </div>
          </div>
        </div>
      )}
      <button className="fab" onClick={() => setOpen(!open)} aria-label={open ? "Close the assistant" : "Open the BIFlow assistant"}
        title={open ? "Close the assistant" : "Ask the assistant a question"}>
        {!open && <span className="pulse" />}
        <Icon name={open ? "x" : "message"} size={26} />
      </button>
    </>
  );
}
