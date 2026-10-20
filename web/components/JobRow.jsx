"use client";
import Link from "next/link";
import Icon from "./Icon";
import { Badge } from "./ui";
import { STATUS, fmtDate, fmtInt } from "@/lib/format";

export default function JobRow({ job, right }) {
  const [text, kind] = STATUS[job.status] || [job.status, "neutral"];
  const ico = { ok: "check-circle", crit: "x-circle", info: "clock" }[kind] || "folder";
  return (
    <div className={`job-row ${kind}`}>
      <div className="ico"><Icon name={ico} size={20} /></div>
      <Link className="txt" href={`/app/analyses/${job.id}`}>
        <b>{job.name}</b>
        <span>{fmtDate(job.created)}{job.domain ? ` · ${job.domain}` : ""}</span>
      </Link>
      {job.status === "running" ? (
        <div className="bar" title={`${job.percent || 0} %`}><span style={{ width: `${job.percent || 2}%` }} /></div>
      ) : (
        <div className="nums">
          <div><b>{fmtInt(job.rows)}</b>rows</div>
          <div><b>{fmtInt(job.kpis)}</b>KPIs</div>
          <div><b>{fmtInt(job.insights)}</b>insights</div>
        </div>
      )}
      <Badge kind={kind}>{text}</Badge>
      {right}
    </div>
  );
}
