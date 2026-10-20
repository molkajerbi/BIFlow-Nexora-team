"use client";
// Star schema diagram and "before / after" quality chart (SVG, no library).
import { fmtInt, starName } from "@/lib/format";

export function StarSchema({ star }) {
  const names = Object.keys(star || {});
  const facts = names.filter((n) => star[n].type === "fait");
  const dims = names.filter((n) => star[n].type !== "fait");
  if (!facts.length) return null;
  const left = dims.filter((_, i) => i % 2 === 0);
  const right = dims.filter((_, i) => i % 2 === 1);
  const bw = 214, bh = 58, gap = 18, width = 940;
  const rows = Math.max(facts.length, left.length, right.length, 1);
  const height = rows * (bh + gap) + 40;
  const col = (list, x) => {
    const total = list.length * (bh + gap) - gap;
    const y0 = (height - total) / 2;
    return Object.fromEntries(list.map((n, i) => [n, [x, y0 + i * (bh + gap)]]));
  };
  const pos = { ...col(left, 20), ...col(facts, (width - bw) / 2), ...col(right, width - bw - 20) };
  const edges = [];
  const seen = new Set();
  facts.forEach((f) => {
    Object.values(star[f].links || {}).forEach(([target]) => {
      const key = `${f}>${target}`;
      if (!pos[target] || seen.has(key) || target === f) return;
      seen.add(key);
      const [fx, fy] = pos[f];
      const [tx, ty] = pos[target];
      if (facts.includes(target)) {
        const x1 = fx + bw, y1 = fy + bh / 2, x2 = tx + bw, y2 = ty + bh / 2;
        edges.push(<path key={key} d={`M${x1},${y1} C${x1 + 46},${y1} ${x2 + 46},${y2} ${x2},${y2}`} stroke="#2F6BF6"
          strokeWidth="1.6" strokeDasharray="4 4" fill="none" opacity=".8" />);
        return;
      }
      const [x1, x2] = tx < fx ? [fx, tx + bw] : [fx + bw, tx];
      const y1 = fy + bh / 2, y2 = ty + bh / 2, mid = (x1 + x2) / 2;
      edges.push(<g key={key}><path d={`M${x1},${y1} C${mid},${y1} ${mid},${y2} ${x2},${y2}`} stroke="#B9C2D3" strokeWidth="1.4" fill="none" />
        <circle cx={x2} cy={y2} r="3" fill="#B9C2D3" /></g>);
    });
  });
  return (
    <div className="chart-card">
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" style={{ minWidth: 640 }} role="img" aria-label="Star schema diagram">
        <defs>
          <linearGradient id="bfFact" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0" stopColor="#14B8A6" /><stop offset="1" stopColor="#2F6BF6" />
          </linearGradient>
        </defs>
        {edges}
        {Object.entries(pos).map(([n, [x, y]]) => {
          const isFact = star[n].type === "fait";
          const label = starName(n)[0];
          const short = label.length <= 24 ? label : label.slice(0, 23) + "…";
          return (
            <g key={n}>
              <title>{label}</title>
              <rect x={x} y={y} width={bw} height={bh} rx="14" fill={isFact ? "url(#bfFact)" : "#fff"}
                stroke={isFact ? "#1E5BD6" : "#D3DAE5"} strokeWidth="1.2" />
              {!isFact && <rect x={x} y={y + 12} width="3.5" height={bh - 24} rx="1.75" fill="#14B8A6" />}
              <text x={x + 16} y={y + 25} fontSize="14" fontWeight="800" fill={isFact ? "#fff" : "#0B1324"}>{short}</text>
              <text x={x + 16} y={y + 43} fontSize="12" fill={isFact ? "#DCE8FF" : "#64748B"}>
                {isFact ? "Fact table · " : ""}{star[n].rows !== null && star[n].rows !== undefined ? `${fmtInt(star[n].rows)} rows` : ""}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

const fr = (v) => v.toFixed(1);

export function Dumbbell({ rows }) {
  if (!rows || !rows.length) return null;
  const sorted = [...rows].sort((a, b) => a[2] - b[2]);
  const lo = Math.max(0, Math.floor(Math.min(...sorted.map((r) => Math.min(r[1], r[2]))) - 2));
  const width = 940, left = 210, right = 150, step = 42, height = sorted.length * step + 46;
  const x = (v) => left + ((v - lo) / (100 - lo || 1)) * (width - left - right);
  const span = 100 - lo;
  const tick = [1, 2, 5, 10, 20, 25, 50].find((t) => span / t <= 6) || 50;
  const ticks = [];
  for (let t = Math.ceil(lo / tick) * tick; t <= 100; t += tick) ticks.push(t);
  return (
    <div className="chart-card">
      <svg viewBox={`0 0 ${width} ${height}`} width="100%" style={{ minWidth: 560 }} role="img" aria-label="Quality before and after cleaning">
        {ticks.map((t) => (
          <g key={t}>
            <line x1={x(t)} y1="14" x2={x(t)} y2={height - 26} stroke="#EEF1F6" />
            <text x={x(t)} y={height - 8} fontSize="11" fill="#64748B" textAnchor="middle">{t}</text>
          </g>
        ))}
        {sorted.map(([label, before, after], i) => {
          const y = 30 + i * step;
          const delta = after - before;
          return (
            <g key={label}>
              <text x={left - 16} y={y + 4} fontSize="13" fontWeight="700" fill="#0B1324" textAnchor="end">{label}</text>
              <line x1={x(before)} y1={y} x2={x(after)} y2={y} stroke="#C9D1E0" strokeWidth="3" strokeLinecap="round" />
              <circle cx={x(before)} cy={y} r="7.5" fill="#E0A14A" stroke="#fff" strokeWidth="2.5"><title>{`${label} before: ${before.toFixed(1)} / 100`}</title></circle>
              <circle cx={x(after)} cy={y} r="7.5" fill="#14B8A6" stroke="#fff" strokeWidth="2.5"><title>{`${label} after: ${after.toFixed(1)} / 100`}</title></circle>
              <text x={width - right + 14} y={y + 4} fontSize="12" fill="#64748B">
                {fr(before)} → <tspan fontWeight="800" fill="#0B1324">{fr(after)}</tspan>
                <tspan fill="#0F8F86" fontWeight="700">{delta >= 0.05 ? `  +${fr(delta)}` : ""}</tspan>
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

export function Legend({ items }) {
  return (
    <div className="legend">
      {items.map(([t, c]) => <span key={t}><i style={{ background: c }} />{t}</span>)}
    </div>
  );
}
