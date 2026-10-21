DASHBOARD_CSS = r"""
:root{color-scheme:light;
--page:#eef0f3;--surface:#ffffff;--surface2:#f4f5f7;--ink:#0f1216;--ink2:#4a5059;--muted:#7d838d;--grid:#e6e8ec;--axis:#c9cdd4;
--ring:rgba(15,18,22,.08);--shadow:0 1px 2px rgba(16,24,40,.05);
--series:#2a78d6;--series-soft:#86b6ef;--wash:rgba(42,120,214,.10);--track:#e3e8f0;
--pos:#2a78d6;--neg:#eb6834;--neutral-fill:#c3c7ce;
--good:#0ca30c;--good-text:#006300;--critical:#d03b3b;--warning:#fab219;--serious:#ec835a;--chip:#eceef2;
--seq1:#cde2fb;--seq2:#9ec5f4;--seq3:#6da7ec;--seq4:#3987e5;--seq5:#256abf;--seq6:#184f95;--seq7:#0d366b;
--cat1:#2a78d6;--cat2:#eb6834;--cat3:#1baf7a;--cat4:#eda100;--cat5:#e87ba4;--cat6:#008300;--accent:#2a78d6}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])){color-scheme:dark;
--page:#0d0f12;--surface:#16191e;--surface2:#1d2127;--ink:#eef0f2;--ink2:#b4bac3;--muted:#7a818b;--grid:#252a31;--axis:#363c45;
--ring:rgba(255,255,255,.06);--shadow:0 1px 2px rgba(0,0,0,.5);
--series:#3987e5;--series-soft:#256abf;--wash:rgba(57,135,229,.16);--track:#232a33;--pos:#3987e5;--neg:#d95926;--neutral-fill:#4a4f57;
--good-text:#3ccf3c;--chip:#242930;--cat1:#3987e5;--cat2:#d95926;--cat3:#199e70;--cat4:#c98500;--cat5:#d55181;--cat6:#008300}}
:root[data-theme="dark"]{color-scheme:dark;
--page:#0d0f12;--surface:#16191e;--surface2:#1d2127;--ink:#eef0f2;--ink2:#b4bac3;--muted:#7a818b;--grid:#252a31;--axis:#363c45;
--ring:rgba(255,255,255,.06);--shadow:0 1px 2px rgba(0,0,0,.5);
--series:#3987e5;--series-soft:#256abf;--wash:rgba(57,135,229,.16);--track:#232a33;--pos:#3987e5;--neg:#d95926;--neutral-fill:#4a4f57;
--good-text:#3ccf3c;--chip:#242930;--cat1:#3987e5;--cat2:#d95926;--cat3:#199e70;--cat4:#c98500;--cat5:#d55181;--cat6:#008300}
body[data-accent="telecom"]{--accent:#9085e9} body[data-accent="banking"]{--accent:#1baf7a} body[data-accent="transport"]{--accent:#ec835a}
*{box-sizing:border-box}
html,body{margin:0;background:var(--page);color:var(--ink)}
body{font:13px/1.45 Inter,system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;-webkit-font-smoothing:antialiased}
main{max-width:1600px;margin:0 auto;padding:12px 14px 18px}
svg text{fill:var(--muted);font-size:11px;font-family:inherit}
svg text.ink2{fill:var(--ink2)} svg text.ink{fill:var(--ink)}
svg text.halo{paint-order:stroke;stroke:var(--surface);stroke-width:4px;stroke-linejoin:round}
button{font:inherit;cursor:pointer;color:inherit}
:focus-visible{outline:2px solid var(--series);outline-offset:2px}

/* ---------- top bar ---------- */
.topbar{display:flex;align-items:center;gap:16px;padding:6px 4px 12px;flex-wrap:wrap}
.brand{display:flex;align-items:center;gap:12px;min-width:0;flex:1 1 320px}
.logo{width:38px;height:38px;border-radius:11px;display:grid;place-items:center;flex:none;
background:linear-gradient(135deg,var(--series),var(--accent));color:#fff;box-shadow:0 4px 14px color-mix(in srgb,var(--series) 40%,transparent)}
.logo svg{width:20px;height:20px}
.brand h1{margin:0;font-size:19px;font-weight:700;letter-spacing:-.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.brand .meta{color:var(--muted);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
nav.tabs{display:flex;gap:2px;background:var(--surface);border:1px solid var(--ring);border-radius:12px;padding:3px;overflow-x:auto;scrollbar-width:none;max-width:100%}
nav.tabs button{border:0;background:transparent;color:var(--ink2);padding:7px 13px;border-radius:9px;font-weight:600;font-size:12.5px;
display:inline-flex;align-items:center;gap:7px;white-space:nowrap}
nav.tabs button svg{width:15px;height:15px}
nav.tabs button:hover{color:var(--ink)}
nav.tabs button.on{background:var(--series);color:#fff}
nav.tabs .count{background:rgba(255,255,255,.22);border-radius:999px;padding:0 6px;font-size:11px}
nav.tabs button:not(.on) .count{background:var(--chip);color:var(--ink2)}
.tools{display:flex;gap:6px;align-items:center}
.status{display:inline-flex;align-items:center;gap:6px;font-size:12px;font-weight:600;padding:6px 10px;border-radius:9px;background:var(--surface);border:1px solid var(--ring);white-space:nowrap}
.status i{width:8px;height:8px;border-radius:50%}
.ibtn{width:34px;height:34px;border-radius:9px;border:1px solid var(--ring);background:var(--surface);display:grid;place-items:center;color:var(--ink2)}
.ibtn:hover{color:var(--ink)} .ibtn svg{width:16px;height:16px}

/* ---------- panels ---------- */
.card{background:var(--surface);border:1px solid var(--ring);border-radius:14px;padding:14px 16px;min-width:0;box-shadow:var(--shadow);position:relative}
.ptitle{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:8px;min-height:22px}
.ptitle h3,.chead h3{margin:0;font-size:13px;font-weight:700;color:var(--ink2);letter-spacing:.01em}
.chead{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
.chead .tiny{margin-top:1px}
.tiny{color:var(--muted);font-size:11.5px}
.ghost{background:transparent;border:1px solid var(--ring);color:var(--ink2);border-radius:8px;padding:4px 9px;font-size:12px;white-space:nowrap}
.ghost:hover{color:var(--ink);background:var(--surface2)}
.plot{position:relative;margin-top:8px}
.cap{margin-top:8px;color:var(--ink2);font-size:12px;border-top:1px solid var(--grid);padding-top:8px}
.legend{display:flex;flex-wrap:wrap;gap:12px;margin-top:6px;font-size:11.5px;color:var(--ink2)}
.legend span{display:inline-flex;align-items:center;gap:6px}
.key{display:inline-block;width:9px;height:9px;border-radius:50%;flex:none}
.view{display:none}.view.on{display:block;animation:fade .25s ease}
@keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}

/* ---------- overview: 3 columns ---------- */
.ov{display:grid;grid-template-columns:300px minmax(0,1fr) 360px;gap:12px;align-items:start}
.col{display:flex;flex-direction:column;gap:12px;min-width:0}
.hero .big{font-size:40px;font-weight:700;letter-spacing:-.02em;line-height:1.05;margin-top:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hero .def{color:var(--muted);font-size:12px;margin-top:6px}
.center{display:flex;flex-direction:column;align-items:center}
.pill{display:inline-flex;align-items:center;gap:4px;font-size:12px;font-weight:700;padding:3px 9px;border-radius:7px;white-space:nowrap}
.pill svg{width:12px;height:12px}
.pill.good{background:var(--good);color:#fff}.pill.bad{background:var(--critical);color:#fff}.pill.neutral{background:var(--chip);color:var(--ink2)}
.pill small{font-weight:500;opacity:.85}
.mrow{margin-top:10px}
.mrow:first-child{margin-top:0}
.mrow .l{display:flex;justify-content:space-between;align-items:baseline;gap:8px;font-size:12px;color:var(--muted)}
.mrow .l b{font-size:17px;color:var(--ink);font-weight:700;white-space:nowrap}
.mrow .l span{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.mrow .bar{height:6px;border-radius:999px;background:var(--track);margin-top:5px;overflow:hidden}
.mrow .bar i{display:block;height:100%;border-radius:999px}
.stats{display:grid;grid-template-columns:1fr 1fr;gap:1px;background:var(--grid);border-radius:12px;overflow:hidden;border:1px solid var(--ring)}
.stat{background:var(--surface);padding:11px 12px;min-width:0}
.stat .n{color:var(--muted);font-size:11.5px;font-weight:600;line-height:1.3;height:30px;overflow:hidden}
.stat .v{font-size:19px;font-weight:700;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.stat .d{font-size:11.5px;font-weight:700;margin-top:1px}
.d.good{color:var(--good-text)}.d.bad{color:var(--critical)}.d.neutral{color:var(--muted)}
.chips{display:flex;gap:4px;overflow-x:auto;scrollbar-width:thin;min-width:0;padding-bottom:2px}
.ptitle h3{white-space:nowrap;overflow:hidden;text-overflow:ellipsis;min-width:0}
.ptitle>.tiny{white-space:nowrap;flex:none}
.chipbtn{border:1px solid var(--ring);background:var(--surface2);color:var(--ink2);padding:4px 10px;border-radius:999px;font-size:11.5px;font-weight:600;white-space:nowrap}
.chipbtn.on{background:color-mix(in srgb,var(--series) 18%,transparent);border-color:color-mix(in srgb,var(--series) 50%,transparent);color:var(--ink)}
.note{display:flex;gap:8px;align-items:flex-start;color:var(--ink2);font-size:12px;margin-top:6px}
.note svg{width:14px;height:14px;flex:none;margin-top:2px}
.headline{display:flex;align-items:center;gap:12px;padding:10px 14px}
.headline .ic{width:32px;height:32px;border-radius:9px;display:grid;place-items:center;flex:none}
.headline .ic svg{width:17px;height:17px}
.headline .tx{min-width:0;flex:1}
.headline .tx b{display:block;font-size:13.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.headline .tx span{display:block;color:var(--muted);font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.go{border:0;background:none;color:var(--series);font-weight:700;font-size:12px;display:inline-flex;align-items:center;gap:4px;white-space:nowrap}
.go svg{width:13px;height:13px}
.rows{display:flex;flex-direction:column;gap:8px}
.srow{display:grid;grid-template-columns:20px 58px minmax(0,1fr) 110px;gap:12px;align-items:center;background:var(--surface2);border-radius:11px;padding:9px 12px}
.srow .rk{color:var(--muted);font-weight:700;font-size:12px}
.srow .nm{font-weight:700;font-size:12.5px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.srow .by{color:var(--muted);font-size:11px;font-weight:500}
.srow .br{display:flex;align-items:center;gap:8px;margin-top:5px;font-size:11.5px;color:var(--ink2)}
.srow .br .t{width:96px;flex:none;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.srow .br .bar{flex:1;height:6px;border-radius:999px;background:var(--track);overflow:hidden}
.srow .br .bar i{display:block;height:100%;border-radius:999px}
.srow .br .v{width:58px;text-align:right;font-weight:700;color:var(--ink);font-variant-numeric:tabular-nums}
.srow .side{text-align:right}
.srow .side .lb{color:var(--muted);font-size:11px}
.srow .side .vv{font-size:15px;font-weight:700}
.srow .side .sub{font-size:11.5px;font-weight:700;color:var(--ink2)}
.total{display:flex;align-items:baseline;gap:8px}
.total span{color:var(--muted);font-size:12px}
.total b{font-size:34px;font-weight:700;letter-spacing:-.02em}
.stack{display:flex;gap:2px;height:10px;border-radius:999px;overflow:hidden;margin:10px 0 12px}
.mods{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px 10px}
.mod b{display:block;font-size:17px}
.mod span{display:flex;align-items:center;gap:6px;font-size:11.5px;color:var(--ink2);min-width:0}
.mod span em{font-style:normal;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ilist{display:flex;flex-direction:column;gap:8px}
.irow{display:flex;gap:10px;align-items:flex-start;padding:9px 10px;border-radius:10px;background:var(--surface2)}
.irow .ic{width:28px;height:28px;border-radius:8px;display:grid;place-items:center;flex:none}
.irow .ic svg{width:15px;height:15px}
.irow b{display:block;font-size:12.5px;line-height:1.35}
.irow span{display:block;color:var(--muted);font-size:11.5px;margin-top:2px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.t-alert{background:color-mix(in srgb,var(--critical) 16%,transparent);color:var(--critical)}
.t-opportunity{background:color-mix(in srgb,var(--good) 16%,transparent);color:var(--good-text)}
.t-finding{background:color-mix(in srgb,var(--series) 16%,transparent);color:var(--series)}

/* ---------- other views ---------- */
.g2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,460px),1fr));gap:12px;align-items:start}
.g3{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,320px),1fr));gap:12px;align-items:start}
.split{display:grid;grid-template-columns:minmax(0,1.25fr) minmax(0,1fr);gap:12px;align-items:start}
.ins{display:flex;flex-direction:column;gap:6px}
.ins .top{display:flex;align-items:center;gap:8px}
.kind{display:inline-flex;align-items:center;gap:5px;font-size:11.5px;font-weight:700;padding:3px 8px;border-radius:7px}
.kind svg{width:12px;height:12px}
.badge{font-size:11px;font-weight:600;padding:2px 7px;border-radius:6px;background:var(--chip);color:var(--ink2)}
.prio{margin-left:auto;display:flex;align-items:center;gap:6px;font-size:11px;color:var(--muted)}
.prio i{display:block;width:46px;height:5px;border-radius:999px;background:var(--track);overflow:hidden}
.prio i b{display:block;height:100%;background:var(--series)}
.ins h4{margin:2px 0 0;font-size:13.5px;line-height:1.35}
.ins p{margin:0;color:var(--ink2);font-size:12.5px}
.ins .reco{background:var(--surface2);border-radius:9px;padding:7px 9px;font-size:12px}
details summary{cursor:pointer;color:var(--muted);font-size:11.5px}
details ul{margin:6px 0 0;padding-left:16px;color:var(--ink2);font-size:11.5px}
.pulse{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:8px;margin-bottom:10px}
.pcell{display:flex;align-items:center;gap:9px;background:var(--surface2);border-radius:10px;padding:9px 10px}
.pcell .ic{width:30px;height:30px;border-radius:8px;display:grid;place-items:center;background:var(--surface)}
.pcell .ic svg{width:15px;height:15px;stroke:var(--series)}
.pcell b{font-size:17px;display:block;line-height:1.1}.pcell span{font-size:11px;color:var(--muted)}
.qstat{display:flex;align-items:center;gap:10px;padding:10px;border-radius:11px;background:var(--surface2)}
.qstat .ic{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;color:#0b0b0b;flex:none}
.qstat .ic svg{width:15px;height:15px}
.steps{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:8px}
.step{background:var(--surface2);border-radius:10px;padding:10px}
.step b{display:flex;align-items:center;gap:6px;font-size:12.5px}
.step b svg{width:14px;height:14px;stroke:var(--series)}
.step span{display:block;font-size:11.5px;color:var(--muted);margin-top:3px;overflow-wrap:anywhere}
.ctools{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:6px}
.search{flex:1;min-width:180px;display:flex;align-items:center;gap:8px;border:1px solid var(--ring);background:var(--surface2);border-radius:9px;padding:6px 10px}
.search svg{width:14px;height:14px;color:var(--muted)}
.search input{border:0;background:transparent;outline:0;color:var(--ink);font:inherit;width:100%}
.fpill{border:1px solid var(--ring);background:var(--surface2);color:var(--ink2);border-radius:999px;padding:4px 10px;font-size:12px;font-weight:600}
.fpill.on{background:var(--series);color:#fff;border-color:var(--series)}
.scroll{max-height:560px;overflow:auto}
.g2>.wide{grid-column:1/-1}
.rel{white-space:nowrap;display:inline-flex;align-items:center;gap:6px;font-weight:600;color:var(--ink2)}
.rel i{width:8px;height:8px;border-radius:50%;display:inline-block}

/* ---------- tooltips, tables ---------- */
.tip{position:fixed;pointer-events:none;background:var(--surface);border:1px solid var(--ring);border-radius:9px;padding:7px 10px;
box-shadow:0 10px 28px rgba(0,0,0,.25);font-size:12px;max-width:280px;z-index:30;display:none;color:var(--ink2)}
.tip strong{display:block;font-size:13.5px;color:var(--ink)}
.tip .tline{display:flex;align-items:center;gap:6px;margin-top:3px}
table{border-collapse:collapse;width:100%;font-size:12px}
th,td{text-align:left;padding:7px 9px;border-bottom:1px solid var(--grid);vertical-align:top}
th{color:var(--muted);font-weight:700;font-size:11px;text-transform:uppercase;letter-spacing:.05em;position:sticky;top:0;background:var(--surface)}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr:hover td{background:var(--surface2)}
.tablewrap{overflow-x:auto;margin-top:8px}
.tablewrap td{overflow-wrap:anywhere}
code{font-size:11px;white-space:pre-wrap;word-break:break-word;color:var(--ink2)}
footer{margin-top:12px;color:var(--muted);font-size:11px}
.flash{animation:flash 1.4s ease}
@keyframes flash{0%{box-shadow:0 0 0 0 color-mix(in srgb,var(--series) 60%,transparent)}100%{box-shadow:0 0 0 12px transparent}}

@media (max-width:1280px){.ov{grid-template-columns:280px minmax(0,1fr)}.ov .right{grid-column:1/-1;display:grid;grid-template-columns:1fr 1fr}}
@media (max-width:900px){.ov{grid-template-columns:1fr}.ov .right{grid-template-columns:1fr}.split{grid-template-columns:1fr}
.topbar{gap:10px}.brand{flex-basis:100%}nav.tabs{order:3;flex:1 1 100%}}
@media (max-width:520px){main{padding:10px 10px 16px}.srow{grid-template-columns:52px minmax(0,1fr);}.srow .rk{display:none}
.srow .side{grid-column:1/-1;text-align:left;display:flex;gap:12px;align-items:baseline}.srow .br .t{width:70px}.hero .big{font-size:32px}.mods{grid-template-columns:1fr 1fr}}
@media print{nav.tabs,.tools{display:none!important}.view{display:block!important;break-before:page}body{background:#fff}.card{box-shadow:none;break-inside:avoid}}
@media (prefers-reduced-motion:reduce){.view.on,.flash{animation:none}}
"""

DASHBOARD_JS = r"""
(() => {
'use strict';
const D = JSON.parse(document.getElementById('dashboard-data').textContent);
const app = document.getElementById('app');

/* ---------- utilities ---------- */
const $ = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const NS = 'http://www.w3.org/2000/svg';
const S = (tag, attrs, parent) => {
  const e = document.createElementNS(NS, tag);
  for (const k in attrs || {}) if (attrs[k] != null) e.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(e);
  return e;
};
const T = (parent, x, y, text, attrs) => { const t = S('text', {x, y, ...(attrs || {})}, parent); t.textContent = text; return t; };
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTHS_LONG = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const plabel = p => MONTHS[p % 100 - 1] + ' ' + String(Math.floor(p / 100)).slice(2);
const plong = p => MONTHS_LONG[p % 100 - 1] + ' ' + Math.floor(p / 100);
const nf = (v, d) => v.toLocaleString('en-US', {minimumFractionDigits: d, maximumFractionDigits: d});
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const mean = a => a.reduce((s, x) => s + x, 0) / a.length;
function fmt(v, unit) {
  if (v == null || isNaN(v)) return '—';
  if (unit === 'percent') return nf(100 * v, 1) + '%';
  if (unit === 'count') return nf(v, 0);
  if (unit === 'days') return nf(v, 1) + ' d';
  return nf(v, 2);
}
function fmtShort(v, unit) {
  if (v == null || isNaN(v)) return '—';
  if (unit === 'percent') { const p = 100 * v; return nf(p, Math.abs(p) < 10 && p !== Math.round(p) ? 1 : 0) + '%'; }
  const a = Math.abs(v);
  const sfx = unit === 'days' ? ' d' : '';
  if (a >= 1e9) return nf(v / 1e9, 1) + ' bn' + sfx;
  if (a >= 1e6) return nf(v / 1e6, a >= 1e7 ? 0 : 1) + ' M' + sfx;
  if (a >= 1e4) return nf(v / 1e3, 0) + ' k' + sfx;
  if (a >= 1e3) return nf(v / 1e3, 1) + ' k' + sfx;
  if (unit === 'count') return nf(v, 0) + sfx;
  return nf(v, a < 10 ? (a < 1 ? 2 : 1) : 0) + sfx;
}
function fmtTick(v, unit, step) {
  if (Math.abs(v) < 1e-12) return '0';
  if (unit === 'percent') { const d = clamp(-Math.floor(Math.log10(100 * step) + 1e-9), 0, 2); return nf(100 * v, d) + '%'; }
  const a = Math.abs(v);
  if (a >= 1e3) return fmtShort(v, unit === 'days' ? 'number' : unit);
  const d = clamp(-Math.floor(Math.log10(step) + 1e-9), 0, 3);
  return nf(v, d);
}
const signed = (v, unit) => (v > 0 ? '+' : v < 0 ? '−' : '') + fmtShort(Math.abs(v), unit);
function niceTicks(lo, hi, n) {
  if (hi === lo) { hi = lo + (Math.abs(lo) || 1); lo = lo - (Math.abs(lo) || 1) * 0; }
  const raw = (hi - lo) / Math.max(1, n), mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= raw) || 10 * mag;
  const a = Math.floor(lo / step) * step, b = Math.ceil(hi / step) * step, out = [];
  for (let v = a; v <= b + step / 2; v += step) out.push(+v.toFixed(10));
  return out;
}
const shorten = (s, n) => (s.length > n ? s.slice(0, Math.max(1, n - 1)) + '…' : s);
const charsFor = px => Math.max(3, Math.floor(px / 6.4));

/* ---------- icons (strokes) ---------- */
const ICONS = {
  up: 'M7 17L17 7M9 7h8v8', down: 'M7 7l10 10M17 9v8H9', flat: 'M5 12h14',
  alert: 'M12 3.5l9 16H3zM12 10v4.5M12 17.2v.01', bulb: 'M9 18h6M10 21h4M12 3a6 6 0 0 0-4 10.5c.8.8 1 1.5 1 2.5h6c0-1 .2-1.7 1-2.5A6 6 0 0 0 12 3z',
  eye: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12zM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6z',
  trend: 'M3 17l6-6 4 4 8-8M15 7h6v6', calendar: 'M4 6h16v14H4zM4 10h16M8 3v4M16 3v4', pulse: 'M3 12h4l3-8 4 16 3-8h4',
  layers: 'M12 3l9 5-9 5-9-5zM3 13l9 5 9-5', shield: 'M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6zM9 12l2 2 4-4',
  book: 'M4 5a2 2 0 0 1 2-2h14v16H6a2 2 0 0 0-2 2zM4 5v16', grid: 'M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z',
  moon: 'M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z', print: 'M6 9V3h12v6M6 18H4v-7h16v7h-2M8 14h8v7H8z',
  db: 'M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zM4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3',
  check: 'M5 12l5 5 9-10', target: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 11.5v1',
  coin: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM15 9h-4a2 2 0 0 0 0 4h2a2 2 0 0 1 0 4H9M12 6v2M12 16v2',
  users: 'M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21c0-4 3-6 7-6s7 2 7 6M16 3.5a4 4 0 0 1 0 7.5M18 15c2.5.6 4 2.5 4 6',
  clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 7v5l3 2', hash: 'M5 9h14M5 15h14M10 4L8 20M16 4l-2 16',
  search: 'M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14zM21 21l-5-5', table: 'M4 5h16v14H4zM4 10h16M4 15h16M10 5v14',
  chart: 'M4 20V4M4 20h16M8 16v-5M12 16V8M16 16v-3', jump: 'M7 7h10v10M7 17L17 7', info: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18zM12 11v6M12 7.5v.01',
  spark: 'M12 3l2.2 6.3L21 12l-6.8 2.7L12 21l-2.2-6.3L3 12l6.8-2.7z', flag: 'M5 21V4h11l-2 4 2 4H5',
  split: 'M12 3a9 9 0 1 0 9 9h-9z M14 3.2A9 9 0 0 1 20.8 10H14z', link: 'M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1',
};
const icon = (name, cls) => {
  const s = S('svg', {viewBox: '0 0 24 24', fill: 'none', stroke: 'currentColor', 'stroke-width': 1.8, 'stroke-linecap': 'round',
                      'stroke-linejoin': 'round', 'aria-hidden': 'true'});
  if (cls) s.setAttribute('class', cls);
  S('path', {d: ICONS[name] || ICONS.info}, s);
  return s;
};
const UNIT_ICON = {percent: 'target', currency: 'coin', count: 'users', days: 'clock', number: 'chart'};
const TYPE_ICON = {alert: 'alert', opportunity: 'bulb', finding: 'eye'};
const SIG_ICON = {trend: 'trend', 'year over year': 'calendar', anomaly: 'pulse', 'level shift': 'flag', 'recent change': 'spark'};

/* ---------- tooltip ---------- */
const tip = $('div', 'tip'); tip.style.position = 'fixed'; tip.setAttribute('role', 'status'); document.body.appendChild(tip);
function showTip(ev, title, lines) {
  tip.replaceChildren($('strong', null, title));
  for (const l of lines || []) {
    if (l == null) continue;
    if (typeof l === 'string') { const s = $('span', null, l); s.style.display = 'block'; tip.appendChild(s); continue; }
    const row = $('div', 'tline'); const k = $('i', 'key'); k.style.background = l.color; row.append(k, $('span', null, l.text)); tip.appendChild(row);
  }
  tip.style.display = 'block';
  const r = tip.getBoundingClientRect(), vw = document.documentElement.clientWidth, vh = window.innerHeight;
  let x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + r.width > vw - 8) x = ev.clientX - r.width - 14;
  if (y + r.height > vh - 8) y = ev.clientY - r.height - 14;
  tip.style.left = Math.max(8, x) + 'px'; tip.style.top = Math.max(8, y) + 'px';
}
const hideTip = () => { tip.style.display = 'none'; };
function hover(el, title, lines) {
  el.addEventListener('pointermove', e => showTip(e, typeof title === 'function' ? title() : title, typeof lines === 'function' ? lines() : lines));
  el.addEventListener('pointerleave', hideTip);
}
window.addEventListener('scroll', hideTip, {passive: true});

/* ---------- theme ---------- */
const root = document.documentElement;
try { const saved = localStorage.getItem('biflow-theme'); if (saved) root.dataset.theme = saved; } catch (e) { /* storage unavailable */ }
const isDark = () => root.dataset.theme ? root.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches;
document.body.dataset.accent = D.accent || 'generic';

/* ---------- building blocks ---------- */
const DRAWS = [];
function table(headers, rows, numeric) {
  const t = $('table'), tr = $('tr');
  headers.forEach((h, i) => tr.appendChild($('th', numeric && numeric.includes(i) ? 'num' : null, h)));
  const th = $('thead'); th.appendChild(tr); t.appendChild(th);
  const tb = $('tbody');
  for (const r of rows) { const row = $('tr'); r.forEach((c, i) => row.appendChild($('td', numeric && numeric.includes(i) ? 'num' : null, c))); tb.appendChild(row); }
  t.appendChild(tb);
  return t;
}
function plotCard({id, title, sub, draw, rows, headers, numeric, caption, legend, cls}) {
  const card = $('div', 'card' + (cls ? ' ' + cls : ''));
  if (id) card.id = id;
  const head = $('div', 'chead'), tt = $('div');
  tt.appendChild($('h3', null, title));
  if (sub) tt.appendChild($('div', 'tiny', sub));
  head.appendChild(tt);
  const plot = $('div', 'plot'), wrap = $('div', 'tablewrap');
  if (rows) {
    const b = $('button', 'ghost'); b.type = 'button';
    const setLabel = on => { b.replaceChildren(icon(on ? 'chart' : 'table'), document.createTextNode(on ? ' Chart' : ' Table')); b.setAttribute('aria-pressed', on); };
    setLabel(false);
    b.style.display = 'inline-flex'; b.style.alignItems = 'center'; b.style.gap = '5px';
    b.querySelectorAll('svg').forEach(s => { s.style.width = '14px'; s.style.height = '14px'; });
    b.addEventListener('click', () => {
      const on = wrap.hidden; wrap.hidden = !on; plot.hidden = on; if (legendEl) legendEl.hidden = on; setLabel(on);
      b.querySelectorAll('svg').forEach(s => { s.style.width = '14px'; s.style.height = '14px'; });
    });
    head.appendChild(b);
    wrap.appendChild(table(headers, rows, numeric)); wrap.hidden = true;
  }
  card.appendChild(head); card.appendChild(plot);
  let legendEl = null;
  if (legend) { legendEl = $('div', 'legend'); for (const l of legend) { const s = $('span'); const k = $('i', 'key'); if (l.style) Object.assign(k.style, l.style); else k.style.background = l.color; s.append(k, document.createTextNode(l.text)); legendEl.appendChild(s); } card.appendChild(legendEl); }
  if (rows) card.appendChild(wrap);
  if (caption) card.appendChild($('div', 'cap', caption));
  let lastW = 0;
  const run = force => { const w = Math.floor(plot.clientWidth); if (!w || (!force && w === lastW)) return; lastW = w; plot.replaceChildren(); draw(plot, w); };
  DRAWS.push(run);
  return card;
}
function section(id, kicker, title, text, iconName) {
  const s = $('section', 'block'); s.id = id;
  const h = $('div', 'shead'), l = $('div');
  l.appendChild($('div', 'k', kicker)); l.appendChild($('h2', null, title));
  if (text) l.appendChild($('p', null, text));
  h.appendChild(l); s.appendChild(h);
  NAV.push({id, label: kicker, icon: iconName});
  return s;
}
function deltaChip(d) {
  if (!d) return null;
  const cls = d.good === true ? 'good' : d.good === false ? 'bad' : 'neutral';
  const c = $('span', 'delta ' + cls);
  c.append(icon(d.up === true ? 'up' : d.up === false ? 'down' : 'flat'), document.createTextNode(d.text));
  c.title = d.label || '';
  return c;
}
function svgBox(plot, w, h, label) {
  const svg = S('svg', {viewBox: `0 0 ${w} ${h}`, width: w, height: h, role: 'img', 'aria-label': label || ''}, plot);
  svg.style.display = 'block'; svg.style.overflow = 'visible';
  return svg;
}
// bar rounded (4 px) on the value side, anchored on the baseline
function vbar(x, w, y0, y1, r) {
  const h = Math.abs(y1 - y0); r = Math.min(r, h, w / 2);
  if (h < 0.5) return `M${x},${y0}h${w}`;
  if (y1 < y0) return `M${x},${y0}V${y1 + r}Q${x},${y1} ${x + r},${y1}H${x + w - r}Q${x + w},${y1} ${x + w},${y1 + r}V${y0}Z`;
  return `M${x},${y0}V${y1 - r}Q${x},${y1} ${x + r},${y1}H${x + w - r}Q${x + w},${y1} ${x + w},${y1 - r}V${y0}Z`;
}
function hbar(y, h, x0, x1, r) {
  const w = Math.abs(x1 - x0); r = Math.min(r, w, h / 2);
  if (w < 0.5) return `M${x0},${y}v${h}`;
  if (x1 > x0) return `M${x0},${y}H${x1 - r}Q${x1},${y} ${x1},${y + r}V${y + h - r}Q${x1},${y + h} ${x1 - r},${y + h}H${x0}Z`;
  return `M${x0},${y}H${x1 + r}Q${x1},${y} ${x1},${y + r}V${y + h - r}Q${x1},${y + h} ${x1 + r},${y + h}H${x0}Z`;
}
const arc = (cx, cy, r, a0, a1) => {
  const p = a => [cx + r * Math.cos(a), cy + r * Math.sin(a)];
  const [x0, y0] = p(a0), [x1, y1] = p(a1);
  return `M${x0},${y0}A${r},${r} 0 ${a1 - a0 > Math.PI ? 1 : 0} 1 ${x1},${y1}`;
};
const NAV = [];
let GID = 0;
function grad(svg, color, a0, a1) {
  const id = 'bfg' + (++GID), defs = S('defs', {}, svg), lg = S('linearGradient', {id, x1: 0, y1: 0, x2: 0, y2: 1}, defs);
  S('stop', {offset: '0%', style: `stop-color:${color};stop-opacity:${a0}`}, lg);
  S('stop', {offset: '100%', style: `stop-color:${color};stop-opacity:${a1}`}, lg);
  return `url(#${id})`;
}
const KP = D.kpis || {};
const withSeries = Object.keys(KP).filter(k => KP[k].series && KP[k].series.periods && KP[k].series.periods.length > 1);
const valence = v => (v === 'favorable' ? 'var(--pos)' : v === 'unfavorable' ? 'var(--neg)' : 'var(--neutral-fill)');

/* ---------- small shapes ---------- */
function sparkLine(plot, w, h, k, opts) {
  const s = k.series, v = s.values, n = v.length;
  const svg = svgBox(plot, w, h, 'Trend of ' + k.name);
  svg.setAttribute('class', 'spark');
  const pad = opts && opts.labels ? 16 : 3;
  const lo = Math.min(...v), hi = Math.max(...v), span = hi - lo || 1;
  const x = i => 3 + i * (w - 6) / Math.max(1, n - 1), y = val => pad + (h - 2 * pad) * (1 - (val - lo) / span);
  const line = v.map((val, i) => (i ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(val).toFixed(1)).join('');
  S('path', {d: line + `L${x(n - 1)},${h}L${x(0)},${h}Z`, style: `fill:${grad(svg, 'var(--series)', 0.35, 0)}`}, svg);
  S('path', {d: line, style: 'fill:none;stroke:var(--series);stroke-width:2;stroke-linejoin:round;stroke-linecap:round'}, svg);
  const last = n - 1;
  S('circle', {cx: x(last), cy: y(v[last]), r: 4, style: 'fill:var(--series);stroke:var(--surface);stroke-width:2'}, svg);
  if (opts && opts.labels) {
    const imax = v.indexOf(hi), imin = v.indexOf(lo);
    for (const [i, lab] of [[imax, 'max ' + fmtShort(hi, k.unit)], [imin, 'min ' + fmtShort(lo, k.unit)]]) {
      if (i === last) continue;
      S('circle', {cx: x(i), cy: y(v[i]), r: 3, style: 'fill:var(--surface);stroke:var(--series);stroke-width:2'}, svg);
      const anchor = x(i) < 40 ? 'start' : x(i) > w - 40 ? 'end' : 'middle';
      T(svg, x(i), i === imax ? y(v[i]) - 8 : (y(v[i]) + 16 > h ? y(v[i]) - 8 : y(v[i]) + 16), lab, {'text-anchor': anchor, class: 'halo'});
    }
  }
  const hit = S('rect', {x: 0, y: 0, width: w, height: h, fill: 'transparent'}, svg);
  const dot = S('circle', {r: 4, style: 'fill:var(--surface);stroke:var(--ink);stroke-width:2;display:none'}, svg);
  hit.addEventListener('pointermove', e => {
    const r = svg.getBoundingClientRect(), i = clamp(Math.round((e.clientX - r.left - 3) / ((r.width - 6) / Math.max(1, n - 1))), 0, n - 1);
    dot.setAttribute('cx', x(i)); dot.setAttribute('cy', y(v[i])); dot.style.display = '';
    showTip(e, fmt(v[i], k.unit), [plong(s.periods[i])]);
  });
  hit.addEventListener('pointerleave', () => { dot.style.display = 'none'; hideTip(); });
}
function sparkColumns(plot, w, h, k) {
  const s = k.series, v = s.values, n = v.length;
  const svg = svgBox(plot, w, h, 'Trend of ' + k.name);
  const hi = Math.max(...v, 0), bw = w / n, gap = Math.min(2, bw * 0.25);
  v.forEach((val, i) => {
    const bh = Math.max(1.5, (h - 2) * (val / (hi || 1)));
    const p = S('path', {d: vbar(i * bw + gap / 2, bw - gap, h, h - bh, 2),
                         style: `fill:var(--series);opacity:${i === n - 1 ? 1 : 0.55}`}, svg);
    hover(p, fmt(val, k.unit), [plong(s.periods[i])]);
  });
}
function meterBar(parent, v) {
  const m = $('div', 'meter'), i = $('i'); i.style.width = clamp(100 * v, 0, 100) + '%'; m.appendChild(i);
  m.setAttribute('role', 'meter'); m.setAttribute('aria-valuemin', 0); m.setAttribute('aria-valuemax', 100); m.setAttribute('aria-valuenow', Math.round(100 * v));
  parent.appendChild(m);
}
function gauge(plot, w, k) {
  const h = Math.min(170, w * 0.55), r = Math.min(w / 2 - 8, h - 14), cx = w / 2, cy = r + 8;
  const svg = svgBox(plot, w, cy + 26, 'Gauge ' + k.name);
  const v = clamp(k.value || 0, 0, 1);
  S('path', {d: arc(cx, cy, r, Math.PI, 2 * Math.PI), style: 'fill:none;stroke:var(--track);stroke-width:16;stroke-linecap:round'}, svg);
  if (v > 0) S('path', {d: arc(cx, cy, r, Math.PI, Math.PI + Math.max(0.02, v) * Math.PI), style: 'fill:none;stroke:var(--series);stroke-width:16;stroke-linecap:round'}, svg);
  T(svg, cx, cy - 8, fmt(k.value, 'percent'), {'text-anchor': 'middle', class: 'ink', style: 'font-size:28px;font-weight:700'});
  T(svg, cx - r, cy + 20, '0%', {'text-anchor': 'middle'});
  T(svg, cx + r, cy + 20, '100%', {'text-anchor': 'middle'});
}

/* ---------- annotated time chart ---------- */
function timeChart(plot, w, kid, opts) {
  const k = KP[kid], s = k.series, P = s.periods, V = s.values, n = V.length, unit = k.unit;
  const notes = (D.notes && D.notes[kid]) || [];
  const mode = opts.mode, h = opts.h || 270;
  let lo = Math.min(...V), hi = Math.max(...V);
  if (mode === 'columns' || (lo >= 0 && lo < 0.4 * hi)) lo = Math.min(0, lo);
  const pad = (hi - lo) * 0.08 || Math.abs(hi) * 0.1 || 1;
  const ticks = niceTicks(mode === 'columns' ? lo : lo - (lo === 0 ? 0 : pad), hi + pad, 4);
  const y0v = ticks[0], y1v = ticks[ticks.length - 1];
  const tstep = ticks[1] - ticks[0];
  const labW = Math.max(...ticks.map(t => fmtTick(t, unit, tstep).length)) * 6.6 + 10;
  const m = {l: labW, r: 46, t: 26, b: 30}, iw = w - m.l - m.r, ih = h - m.t - m.b;
  const bw = iw / n, x = i => m.l + (i + 0.5) * bw, y = v => m.t + ih * (1 - (v - y0v) / (y1v - y0v || 1));
  const idx = p => P.indexOf(p);
  const svg = svgBox(plot, w, h, (mode === 'columns' ? 'Column chart' : 'Line chart') + ' of ' + k.name);
  // subtle grid + axis
  for (const t of ticks) {
    S('line', {x1: m.l, x2: w - m.r, y1: y(t), y2: y(t), style: `stroke:var(--grid);stroke-width:1${t === 0 ? ';stroke:var(--axis)' : ''}`}, svg);
    T(svg, m.l - 8, y(t) + 4, fmtTick(t, unit, tstep), {'text-anchor': 'end'});
  }
  const every = Math.max(1, Math.ceil(56 / bw));
  P.forEach((p, i) => { if (i % every === 0) T(svg, x(i), h - 10, plabel(p), {'text-anchor': 'middle'}); });
  // compared windows ("year over year"): very light bands
  const yoy = notes.find(nt => nt.type === 'year over year' && nt.windows);
  if (yoy) {
    yoy.windows.forEach((wd, j) => {
      const a = idx(wd[0]), b = idx(wd[1]); if (a < 0 || b < 0) return;
      S('rect', {x: x(a) - bw / 2, y: m.t, width: (b - a + 1) * bw, height: ih, rx: 6, style: `fill:var(--ink);opacity:${j ? 0.06 : 0.035}`}, svg);
      if ((b - a + 1) * bw >= 64) T(svg, x(a) - bw / 2 + 4, m.t - 8, j ? 'recent' : 'one year before', {class: 'ink2', style: 'font-size:10.5px;font-weight:600'});
    });
  }
  // marks
  if (mode === 'columns') {
    const bwid = Math.min(24, bw * 0.68), base = y(Math.max(0, y0v));
    const cg = grad(svg, 'var(--series)', 1, 0.55);
    V.forEach((v, i) => S('path', {d: vbar(x(i) - bwid / 2, bwid, base, y(v), 4), style: `fill:${cg}`}, svg));
  } else {
    const line = V.map((v, i) => (i ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(v).toFixed(1)).join('');
    S('path', {d: line + `L${x(n - 1)},${y(y0v)}L${x(0)},${y(y0v)}Z`, style: `fill:${grad(svg, 'var(--series)', 0.42, 0.02)}`}, svg);
    S('path', {d: line, style: 'fill:none;stroke:var(--series);stroke-width:2;stroke-linejoin:round;stroke-linecap:round'}, svg);
    if (mode === 'dots' && bw >= 14) V.forEach((v, i) => S('circle', {cx: x(i), cy: y(v), r: 3, style: 'fill:var(--series);stroke:var(--surface);stroke-width:2'}, svg));
  }
  if (opts.avg) {
    const mv = mean(V);
    S('line', {x1: m.l, x2: w - m.r, y1: y(mv), y2: y(mv), style: 'stroke:var(--cat4);stroke-width:1.5;stroke-dasharray:5 4'}, svg);
    T(svg, m.l + 6, y(mv) - 6, 'average ' + fmtShort(mv, unit), {class: 'halo', style: 'fill:var(--cat4);font-size:10.5px;font-weight:600'});
  }
  // trend: average levels of the first and last windows
  const trend = notes.find(nt => nt.type === 'trend' && nt.windows);
  if (trend) {
    const pts = trend.windows.map(wd => { const a = idx(wd[0]), b = idx(wd[1]); return a < 0 || b < 0 ? null : [(x(a) + x(b)) / 2, y(mean(V.slice(a, b + 1)))]; });
    if (pts[0] && pts[1]) {
      S('line', {x1: pts[0][0], y1: pts[0][1], x2: pts[1][0], y2: pts[1][1], style: 'stroke:var(--ink2);stroke-width:1.5;stroke-dasharray:5 4'}, svg);
      pts.forEach(p => S('circle', {cx: p[0], cy: p[1], r: 4, style: 'fill:var(--surface);stroke:var(--ink2);stroke-width:2'}, svg));
      T(svg, pts[1][0], pts[1][1] - 10, 'trend', {'text-anchor': 'end', class: 'ink2 halo', style: 'font-size:10.5px;font-weight:600'});
    }
  }
  // level shift: vertical line + levels before / after
  for (const rp of notes.filter(nt => nt.type === 'level shift' && nt.start)) {
    const c = idx(rp.start); if (c < 0) continue;
    const xc = x(c) - bw / 2;
    S('line', {x1: xc, x2: xc, y1: m.t, y2: m.t + ih, style: 'stroke:var(--ink);stroke-width:1.5;stroke-dasharray:3 3'}, svg);
    const before = V.slice(0, c), after = V.slice(c);
    if (before.length) S('line', {x1: m.l, x2: xc, y1: y(mean(before)), y2: y(mean(before)), style: 'stroke:var(--neutral-fill);stroke-width:2'}, svg);
    if (after.length) S('line', {x1: xc, x2: w - m.r, y1: y(mean(after)), y2: y(mean(after)), style: `stroke:${valence(rp.valence)};stroke-width:2`}, svg);
    T(svg, xc + 6, m.t + 12, 'level shift · ' + plabel(rp.start), {class: 'ink halo', style: 'font-size:10.5px;font-weight:600'});
  }
  // anomalies: ring + label
  for (const an of notes.filter(nt => nt.type === 'anomaly')) {
    for (const p of an.periods || []) {
      const i = idx(p); if (i < 0) continue;
      S('circle', {cx: x(i), cy: y(V[i]), r: 8, style: `fill:none;stroke:${valence(an.valence)};stroke-width:2`}, svg);
      S('circle', {cx: x(i), cy: y(V[i]), r: 3.5, style: `fill:${valence(an.valence)}`}, svg);
      const above = y(V[i]) - m.t > 26;
      T(svg, x(i), above ? y(V[i]) - 14 : y(V[i]) + 22, 'atypical · ' + fmtShort(V[i], unit),
        {'text-anchor': x(i) > w - 70 ? 'end' : x(i) < m.l + 50 ? 'start' : 'middle', class: 'ink halo', style: 'font-size:10.5px;font-weight:600'});
    }
  }
  // last value, labelled directly
  const lx = x(n - 1) + (mode === 'columns' ? Math.min(12, bw * 0.34) + 4 : 8), ly = y(V[n - 1]) + 4;
  if (!notes.some(nt => nt.type === 'anomaly' && (nt.periods || []).includes(P[n - 1])))
    T(svg, lx, ly, fmtShort(V[n - 1], unit), {'text-anchor': 'start', class: 'ink halo', style: 'font-weight:700'});
  // hover: vertical line following the mouse
  const cross = S('line', {y1: m.t, y2: m.t + ih, style: 'stroke:var(--axis);stroke-width:1;display:none'}, svg);
  const dot = S('circle', {r: 5, style: 'fill:var(--series);stroke:var(--surface);stroke-width:2;display:none'}, svg);
  const hit = S('rect', {x: m.l, y: m.t, width: iw, height: ih, fill: 'transparent'}, svg);
  hit.addEventListener('pointermove', e => {
    const r = svg.getBoundingClientRect(), px = (e.clientX - r.left) * (w / r.width);
    const i = clamp(Math.floor((px - m.l) / bw), 0, n - 1);
    cross.setAttribute('x1', x(i)); cross.setAttribute('x2', x(i)); cross.style.display = '';
    dot.setAttribute('cx', x(i)); dot.setAttribute('cy', y(V[i])); dot.style.display = '';
    const extra = notes.filter(nt => (nt.periods || []).includes(P[i])).map(nt => ({color: valence(nt.valence), text: nt.type}));
    const prev = i > 0 ? V[i - 1] : null;
    showTip(e, fmt(V[i], unit), [plong(P[i]), prev != null && prev !== 0 && unit !== 'percent' ? 'vs previous month: ' + (V[i] >= prev ? '+' : '−') + nf(Math.abs(100 * (V[i] / prev - 1)), 1) + '%' : null,
                                 prev != null && unit === 'percent' ? 'vs previous month: ' + (V[i] >= prev ? '+' : '−') + nf(Math.abs(100 * (V[i] - prev)), 1) + ' pt' : null, ...extra]);
  });
  hit.addEventListener('pointerleave', () => { cross.style.display = 'none'; dot.style.display = 'none'; hideTip(); });
}

/* ---------- heatmap (seasonality) ---------- */
function heatmap(plot, w, hm) {
  const years = [...new Set(hm.periods.map(p => Math.floor(p / 100)))];
  const val = {}; hm.periods.forEach((p, i) => { val[p] = hm.values[i]; });
  const lo = Math.min(...hm.values), hi = Math.max(...hm.values);
  const sumable = hm.unit === 'count' || hm.unit === 'currency';
  const labW = 46, totW = sumable && w > 520 ? 70 : 0;
  const cw = Math.min(64, (w - labW - totW) / 12), ch = Math.max(26, Math.min(40, cw * 0.62));
  const gw = labW + cw * 12 + totW;
  const h = 22 + years.length * ch + (totW ? 22 : 0);
  const svg = svgBox(plot, gw, h, 'Seasonality of ' + hm.name);
  plot.style.overflowX = 'auto';
  MONTHS.forEach((mo, j) => T(svg, labW + j * cw + cw / 2, 12, cw < 34 ? mo[0].toUpperCase() : mo, {'text-anchor': 'middle'}));
  if (totW) T(svg, gw - 4, 12, 'total', {'text-anchor': 'end'});
  const bin = v => clamp(Math.floor(7 * (v - lo) / ((hi - lo) || 1)), 0, 6) + 1;
  years.forEach((yr, r) => {
    const yy = 22 + r * ch;
    T(svg, labW - 10, yy + ch / 2 + 4, String(yr), {'text-anchor': 'end', class: 'ink2', style: 'font-weight:600'});
    let tot = 0, cnt = 0;
    for (let j = 0; j < 12; j++) {
      const p = yr * 100 + j + 1, v = val[p], xx = labW + j * cw;
      if (v == null) { S('rect', {x: xx + 1, y: yy + 1, width: cw - 2, height: ch - 2, rx: 4, style: 'fill:none;stroke:var(--grid);stroke-dasharray:3 3'}, svg); continue; }
      tot += v; cnt++;
      const b = bin(v);
      const c = S('rect', {x: xx + 1, y: yy + 1, width: cw - 2, height: ch - 2, rx: 4, style: `fill:var(--seq${b})`}, svg);
      if (cw >= 46) T(svg, xx + cw / 2, yy + ch / 2 + 4, fmtShort(v, hm.unit), {'text-anchor': 'middle', style: `font-size:10.5px;font-weight:600;fill:${b >= 4 ? '#ffffff' : '#0d366b'}`});
      hover(c, fmt(v, hm.unit), [plong(p)]);
    }
    if (totW && cnt) T(svg, gw - 4, yy + ch / 2 + 4, fmtShort(tot, hm.unit) + (cnt < 12 ? '*' : ''), {'text-anchor': 'end', class: 'ink', style: 'font-weight:600'});
  });
  if (totW) T(svg, gw - 4, h - 4, '* incomplete year within the reliable period', {'text-anchor': 'end', style: 'font-size:10.5px'});
}

/* ---------- breakdowns ---------- */
function donut(plot, w, seg) {
  const items = seg.segments.map(s => ({g: s.g, v: s.share}));
  const rest = 1 - items.reduce((a, s) => a + s.v, 0);
  if (rest > 0.005) items.push({g: 'Others', v: rest, other: true});
  const side = w >= 460;
  const R = Math.min(side ? 110 : w / 2 - 12, 110), r0 = R * 0.62;
  const cx = side ? R + 6 : w / 2, cy = R + 6, h = side ? 2 * R + 12 : 2 * R + 12 + items.length * 24 + 8;
  const svg = svgBox(plot, w, h, 'Breakdown of ' + seg.label + ' by ' + seg.by);
  let a = -Math.PI / 2;
  items.forEach((it, i) => {
    const a1 = a + it.v * 2 * Math.PI, col = it.other ? 'var(--neutral-fill)' : `var(--cat${i + 1})`;
    const big = a1 - a > Math.PI ? 1 : 0, p = (rr, t) => [cx + rr * Math.cos(t), cy + rr * Math.sin(t)];
    const [x0, y0] = p(R, a), [x1, y1] = p(R, a1), [x2, y2] = p(r0, a1), [x3, y3] = p(r0, a);
    const d = it.v >= 0.9999 ? `M${cx - R},${cy}a${R},${R} 0 1 0 ${2 * R},0a${R},${R} 0 1 0 ${-2 * R},0M${cx - r0},${cy}a${r0},${r0} 0 1 1 ${2 * r0},0a${r0},${r0} 0 1 1 ${-2 * r0},0`
      : `M${x0},${y0}A${R},${R} 0 ${big} 1 ${x1},${y1}L${x2},${y2}A${r0},${r0} 0 ${big} 0 ${x3},${y3}Z`;
    const path = S('path', {d, style: `fill:${col};stroke:var(--surface);stroke-width:2;stroke-linejoin:round`}, svg);
    hover(path, it.g, [nf(100 * it.v, 1) + '% of total']);
    a = a1;
  });
  const top = items[0];
  T(svg, cx, cy - 2, nf(100 * top.v, 1) + '%', {'text-anchor': 'middle', class: 'ink', style: 'font-size:22px;font-weight:700'});
  T(svg, cx, cy + 18, shorten(top.g, charsFor(r0 * 1.6)), {'text-anchor': 'middle', class: 'ink2'});
  const lx = side ? 2 * R + 40 : 12, ly = side ? cy - items.length * 13 + 6 : 2 * R + 30, lw = side ? w - lx : w - 24;
  items.forEach((it, i) => {
    const yy = ly + i * 26;
    S('rect', {x: lx, y: yy - 10, width: 12, height: 12, rx: 3, style: `fill:${it.other ? 'var(--neutral-fill)' : `var(--cat${i + 1})`}`}, svg);
    T(svg, lx + 20, yy, shorten(it.g, charsFor(lw - 90)), {class: 'ink2'});
    T(svg, lx + lw - 4, yy, nf(100 * it.v, 1) + '%', {'text-anchor': 'end', class: 'ink', style: 'font-weight:600'});
    S('line', {x1: lx, x2: lx + lw - 4, y1: yy + 9, y2: yy + 9, style: 'stroke:var(--grid)'}, svg);
  });
}
function squarify(items, x, y, w, h) {
  const out = [], total = items.reduce((a, b) => a + b.v, 0) || 1;
  let rest = items.map(it => ({...it, a: it.v / total * w * h}));
  const worst = (row, side) => { const s = row.reduce((a, b) => a + b.a, 0); return Math.max(...row.map(r => Math.max(side * side * r.a / (s * s), (s * s) / (side * side * r.a)))); };
  while (rest.length) {
    const side = Math.min(w, h); let row = [rest[0]], i = 1;
    while (i < rest.length && worst([...row, rest[i]], side) <= worst(row, side)) { row.push(rest[i]); i++; }
    const s = row.reduce((a, b) => a + b.a, 0), thick = s / side;
    let off = 0;
    for (const r of row) {
      const len = r.a / thick;
      out.push(w >= h ? {...r, x, y: y + off, w: thick, h: len} : {...r, x: x + off, y, w: len, h: thick});
      off += len;
    }
    if (w >= h) { x += thick; w -= thick; } else { y += thick; h -= thick; }
    rest = rest.slice(i);
  }
  return out;
}
function treemap(plot, w, seg) {
  const items = seg.segments.map(s => ({g: s.g, v: s.share}));
  const rest = 1 - items.reduce((a, s) => a + s.v, 0);
  if (rest > 0.005) items.push({g: 'Others', v: rest, other: true});
  const h = Math.min(320, Math.max(220, w * 0.5));
  const svg = svgBox(plot, w, h, 'Breakdown of ' + seg.label + ' by ' + seg.by);
  const mx = Math.max(...items.filter(i => !i.other).map(i => i.v));
  for (const c of squarify(items, 0, 0, w, h)) {
    const b = c.other ? 0 : clamp(Math.round(3 + 4 * c.v / mx), 3, 7);
    const r = S('rect', {x: c.x + 1, y: c.y + 1, width: Math.max(0, c.w - 2), height: Math.max(0, c.h - 2), rx: 6, style: `fill:${c.other ? 'var(--neutral-fill)' : `var(--seq${b})`}`}, svg);
    hover(r, c.g, [nf(100 * c.v, 1) + '% of total']);
    if (c.w > 60 && c.h > 36) {
      const ink = b >= 4 ? '#ffffff' : '#0b0b0b';
      T(svg, c.x + 10, c.y + 20, shorten(c.g, charsFor(c.w - 20)), {style: `fill:${ink};font-weight:600;font-size:12px`});
      T(svg, c.x + 10, c.y + 36, nf(100 * c.v, 1) + '%', {style: `fill:${ink};font-size:11px`});
    }
  }
}
function divergingBars(plot, w, seg) {
  const items = seg.segments.slice().sort((a, b) => b.value - a.value), avg = seg.overall;
  const labW = Math.min(170, Math.max(80, w * 0.26)), valW = 64;
  const rowH = 30, h = 30 + items.length * rowH;
  const svg = svgBox(plot, w, h, seg.label + ' by ' + seg.by + ': gap to the average');
  const ext = Math.max(...items.map(s => Math.abs(s.value - avg))) || 1;
  const x0 = labW + (w - labW - valW) / 2, half = (w - labW - valW) / 2 - 8, x = v => x0 + half * (v - avg) / ext;
  S('line', {x1: x0, x2: x0, y1: 18, y2: h, style: 'stroke:var(--axis);stroke-width:1'}, svg);
  T(svg, x0, 12, 'average ' + fmt(avg, seg.unit), {'text-anchor': 'middle', class: 'ink2', style: 'font-weight:600'});
  items.forEach((s, i) => {
    const yy = 26 + i * rowH, up = s.value >= avg;
    T(svg, labW - 10, yy + 15, shorten(s.g, charsFor(labW - 14)), {'text-anchor': 'end', class: 'ink2'});
    S('path', {d: hbar(yy + 4, 16, x0, x(s.value), 4), style: `fill:${up ? 'var(--pos)' : 'var(--neg)'}`}, svg);
    T(svg, w - 4, yy + 15, fmt(s.value, seg.unit), {'text-anchor': 'end', class: 'ink', style: 'font-weight:600'});
    const hit = S('rect', {x: 0, y: yy, width: w, height: rowH, fill: 'transparent'}, svg);
    hover(hit, s.g, [fmt(s.value, seg.unit), (up ? '+' : '−') + fmtShort(Math.abs(s.value - avg), seg.unit === 'percent' ? 'number' : seg.unit).replace(/%$/, '') + (seg.unit === 'percent' ? ' pt' : '') + ' vs average',
                     s.n != null ? nf(s.n, 0) + ' rows' : null]);
  });
}
function lollipop(plot, w, seg) {
  const items = seg.segments.slice().sort((a, b) => b.value - a.value), avg = seg.overall;
  const labW = Math.min(170, Math.max(80, w * 0.26)), valW = 64, rowH = 30, h = 30 + items.length * rowH;
  const svg = svgBox(plot, w, h, seg.label + ' by ' + seg.by);
  const hi = Math.max(...items.map(s => s.value), avg), top = niceTicks(0, hi, 4).pop();
  const x = v => labW + (w - labW - valW - 6) * v / (top || 1);
  for (const t of niceTicks(0, top, 4)) { S('line', {x1: x(t), x2: x(t), y1: 20, y2: h, style: 'stroke:var(--grid)'}, svg); T(svg, x(t), 12, fmtShort(t, seg.unit), {'text-anchor': 'middle'}); }
  S('line', {x1: x(avg), x2: x(avg), y1: 18, y2: h, style: 'stroke:var(--ink2);stroke-width:1.5;stroke-dasharray:4 3'}, svg);
  items.forEach((s, i) => {
    const yy = 26 + i * rowH + 12, up = s.value >= avg;
    T(svg, labW - 10, yy + 4, shorten(s.g, charsFor(labW - 14)), {'text-anchor': 'end', class: 'ink2'});
    S('line', {x1: x(0), x2: x(s.value), y1: yy, y2: yy, style: 'stroke:var(--track);stroke-width:4;stroke-linecap:round'}, svg);
    S('circle', {cx: x(s.value), cy: yy, r: 7, style: `fill:${up ? 'var(--pos)' : 'var(--neg)'};stroke:var(--surface);stroke-width:2`}, svg);
    T(svg, w - 4, yy + 4, fmt(s.value, seg.unit), {'text-anchor': 'end', class: 'ink', style: 'font-weight:600'});
    const hit = S('rect', {x: 0, y: yy - 14, width: w, height: rowH, fill: 'transparent'}, svg);
    hover(hit, s.g, [fmt(s.value, seg.unit) + ' (average ' + fmt(avg, seg.unit) + ')', s.n != null ? nf(s.n, 0) + ' rows' : null]);
  });
  const lab = T(svg, x(avg) + 5, h - 4, 'average', {class: 'ink2 halo', style: 'font-size:10.5px;font-weight:600'});
  if (x(avg) > w - valW - 60) { lab.setAttribute('text-anchor', 'end'); lab.setAttribute('x', x(avg) - 5); }
}
function waterfall(plot, w, br) {
  const steps = br.steps.slice(), known = steps.reduce((a, s) => a + s.delta, 0), other = br.end - br.start - known;
  if (Math.abs(other) > 1e-9 * Math.max(1, Math.abs(br.end))) steps.push({g: 'Others', delta: other, other: true});
  const cols = [{g: 'start', total: br.start, per: br.from}, ...steps, {g: 'end', total: br.end, per: br.to}];
  let run = br.start; const bars = cols.map(c => { if (c.total != null) return {...c, a: 0, b: c.total}; const a = run; run += c.delta; return {...c, a, b: run}; });
  const lo = Math.min(0, ...bars.map(b => Math.min(b.a, b.b))), hi = Math.max(...bars.map(b => Math.max(b.a, b.b)));
  const ticks = niceTicks(lo, hi, 4), t0 = ticks[0], t1 = ticks[ticks.length - 1];
  const tstep = ticks[1] - ticks[0];
  const labW = Math.max(...ticks.map(t => fmtTick(t, br.unit, tstep).length)) * 6.6 + 10;
  const h = 290, m = {l: labW, r: 8, t: 22, b: 44}, iw = w - m.l - m.r, ih = h - m.t - m.b, band = iw / cols.length;
  const y = v => m.t + ih * (1 - (v - t0) / (t1 - t0 || 1));
  const svg = svgBox(plot, w, h, 'Waterfall of ' + br.label);
  for (const t of ticks) { S('line', {x1: m.l, x2: w - m.r, y1: y(t), y2: y(t), style: 'stroke:var(--grid)'}, svg); T(svg, m.l - 8, y(t) + 4, fmtTick(t, br.unit, tstep), {'text-anchor': 'end'}); }
  const bwid = Math.min(40, band * 0.62);
  bars.forEach((b, i) => {
    const cx = m.l + band * (i + 0.5), total = b.total != null;
    const col = total ? 'var(--ink2)' : b.other ? 'var(--neutral-fill)' : b.delta >= 0 ? 'var(--pos)' : 'var(--neg)';
    const [ya, yb] = [y(b.a), y(b.b)];
    const d = total ? vbar(cx - bwid / 2, bwid, y(Math.max(0, t0)), yb, 4)
                    : `M${cx - bwid / 2},${Math.min(ya, yb)}h${bwid}v${Math.max(1.5, Math.abs(yb - ya))}h${-bwid}Z`;
    const p = S('path', {d, style: `fill:${col}${total ? ';opacity:.85' : ''}`, rx: 3}, svg);
    if (i < bars.length - 1) S('line', {x1: cx + bwid / 2, x2: cx + band - bwid / 2, y1: yb, y2: yb, style: 'stroke:var(--axis);stroke-dasharray:2 2'}, svg);
    const lab = total ? fmtShort(b.b, br.unit) : signed(b.delta, br.unit);
    T(svg, cx, Math.min(ya, yb) - 6, lab, {'text-anchor': 'middle', class: 'ink halo', style: `font-weight:${total ? 700 : 600};font-size:10.5px`});
    const nm = shorten(b.g, charsFor(band - 2));
    T(svg, cx, h - m.b + 16, nm, {'text-anchor': 'middle', class: total ? 'ink2' : null, style: total ? 'font-weight:600' : null});
    hover(p, total ? b.g + ' · ' + b.per : b.g, [total ? 'level: ' + fmt(b.b, br.unit) : 'contribution: ' + signed(b.delta, br.unit), total ? null : 'cumulative: ' + fmt(b.b, br.unit)]);
  });
  T(svg, m.l, h - 6, shorten('monthly averages · ' + br.from + ' → ' + br.to, charsFor(iw)), {style: 'font-size:10.5px'});
}

/* ---------- signal timeline ---------- */
function signalTimeline(plot, w, sigs) {
  const all = [...new Set(withSeries.flatMap(k => KP[k].series.periods))].sort((a, b) => a - b);
  for (const s of sigs) for (const wd of s.windows || []) for (const p of wd) if (!all.includes(p)) all.push(p);
  all.sort((a, b) => a - b);
  const groups = []; for (const s of sigs) { let g = groups.find(x => x.kpi === s.kpi); if (!g) groups.push(g = {kpi: s.kpi, name: s.name, items: []}); g.items.push(s); }
  const labW = Math.min(170, Math.max(96, w * 0.22)), m = {l: labW, r: 14, t: 28};
  const rows = groups.reduce((a, g) => a + 1 + g.items.length, 0), rowH = 24, h = m.t + rows * rowH + 8;
  const svg = svgBox(plot, w, h, 'Timeline of statistical signals');
  const n = all.length, bw = (w - m.l - m.r) / n, x = p => m.l + (all.indexOf(p) + 0.5) * bw;
  const years = [...new Set(all.map(p => Math.floor(p / 100)))];
  for (const yr of years) {
    const first = all.find(p => Math.floor(p / 100) === yr), xx = x(first) - bw / 2;
    S('line', {x1: xx, x2: xx, y1: m.t - 18, y2: h, style: 'stroke:var(--grid)'}, svg);
    T(svg, xx + 4, m.t - 8, String(yr), {class: 'ink2', style: 'font-weight:700'});
  }
  let r = 0;
  for (const g of groups) {
    const gy = m.t + r * rowH;
    T(svg, 0, gy + 16, shorten(g.name, charsFor(w - 10)), {class: 'ink', style: 'font-weight:700'});
    r++;
    for (const s of g.items) {
      const yy = m.t + r * rowH + rowH / 2, col = valence(s.valence);
      S('rect', {x: m.l, y: yy - rowH / 2 + 2, width: w - m.l - m.r, height: rowH - 4, rx: 6, style: 'fill:var(--surface2)'}, svg);
      const tl = T(svg, 12, yy + 4, s.type, {class: 'ink2'});
      tl.style.fontSize = '11.5px';
      const W = (s.windows || []).filter(wd => all.includes(wd[0]) && all.includes(wd[1]));
      if (s.type === 'trend' && W.length === 2) {
        S('line', {x1: x(W[0][0]), x2: x(W[1][1]), y1: yy, y2: yy, style: `stroke:${col};stroke-width:2;opacity:.45`}, svg);
      }
      if (s.type !== 'anomaly') W.forEach((wd, j) => S('path', {d: hbar(yy - 4, 8, x(wd[0]) - bw / 2 + 1, x(wd[1]) + bw / 2 - 1, 4), style: `fill:${col};opacity:${j ? 1 : 0.5}`}, svg));
      if (s.type === 'year over year' && W.length === 2)
        S('path', {d: `M${x(W[0][1]) + bw / 2},${yy}Q${(x(W[0][1]) + x(W[1][0])) / 2},${yy - 12} ${x(W[1][0]) - bw / 2},${yy}`, style: `fill:none;stroke:${col};stroke-width:1.5;stroke-dasharray:3 3`}, svg);
      for (const p of s.periods || []) if (all.includes(p)) {
        if (s.type === 'level shift') S('line', {x1: x(p) - bw / 2, x2: x(p) - bw / 2, y1: yy - 9, y2: yy + 9, style: `stroke:${col};stroke-width:3;stroke-linecap:round`}, svg);
        else S('circle', {cx: x(p), cy: yy, r: 6, style: `fill:${col};stroke:var(--surface);stroke-width:2`}, svg);
      }
      if (s.direction === 'increase' || s.direction === 'decrease') {
        const lastP = W.length ? W[W.length - 1][1] : (s.periods || [])[0];
        if (lastP && all.includes(lastP)) {
          const tx = Math.min(x(lastP) + bw / 2 + 9, w - m.r - 2), up = s.direction === 'increase';
          S('path', {d: up ? `M${tx - 5},${yy + 3}L${tx},${yy - 4}L${tx + 5},${yy + 3}Z` : `M${tx - 5},${yy - 3}L${tx},${yy + 4}L${tx + 5},${yy - 3}Z`, style: `fill:${col}`}, svg);
        }
      }
      const hit = S('rect', {x: 0, y: yy - rowH / 2, width: w, height: rowH, fill: 'transparent'}, svg);
      hover(hit, s.name + ' · ' + s.type, [s.text]);
      r++;
    }
  }
}

/* ---------- quality ---------- */
function dumbbell(plot, w, dims) {
  const names = Object.keys(dims), vals = names.flatMap(d => [dims[d].before, dims[d].after]).filter(v => v != null);
  const lo = Math.max(0, Math.floor((Math.min(...vals) - 3) / 10) * 10);
  const labW = Math.min(130, w * 0.3), m = {l: labW, r: 52, t: 22}, rowH = 30, h = m.t + names.length * rowH + 6;
  const svg = svgBox(plot, w, h, 'Quality scores before and after preparation');
  const x = v => m.l + (w - m.l - m.r) * (v - lo) / (100 - lo || 1);
  const dt = niceTicks(lo, 100, 4).filter(t => t >= lo && t <= 100);
  for (const t of dt) { S('line', {x1: x(t), x2: x(t), y1: m.t - 6, y2: h, style: 'stroke:var(--grid)'}, svg); T(svg, x(t), 10, fmtTick(t, 'number', dt[1] - dt[0]), {'text-anchor': 'middle'}); }
  names.forEach((d, i) => {
    const yy = m.t + i * rowH + rowH / 2, b = dims[d].before, a = dims[d].after;
    T(svg, labW - 10, yy + 4, d, {'text-anchor': 'end', class: 'ink2'});
    if (b != null) S('line', {x1: x(b), x2: x(a), y1: yy, y2: yy, style: 'stroke:var(--track);stroke-width:4;stroke-linecap:round'}, svg);
    if (b != null && Math.abs(a - b) > 0.05) S('circle', {cx: x(b), cy: yy, r: 6, style: 'fill:var(--neutral-fill);stroke:var(--surface);stroke-width:2'}, svg);
    S('circle', {cx: x(a), cy: yy, r: 7, style: 'fill:var(--series);stroke:var(--surface);stroke-width:2'}, svg);
    T(svg, w - 4, yy + 4, nf(a, 1), {'text-anchor': 'end', class: 'ink', style: 'font-weight:700'});
    const hit = S('rect', {x: 0, y: yy - rowH / 2, width: w, height: rowH, fill: 'transparent'}, svg);
    hover(hit, d, [b != null ? 'before preparation: ' + nf(b, 2) + ' / 100' : null, 'after preparation: ' + nf(a, 2) + ' / 100']);
  });
}
function ring(plot, w, score) {
  const R = 64, h = 2 * R + 16, cx = w / 2, cy = R + 8;
  const svg = svgBox(plot, w, h, 'Average quality score');
  S('circle', {cx, cy, r: R, style: 'fill:none;stroke:var(--track);stroke-width:12'}, svg);
  const v = clamp(score / 100, 0, 1);
  if (v > 0) S('path', {d: v >= 0.9999 ? `M${cx},${cy - R}a${R},${R} 0 1 1 0,${2 * R}a${R},${R} 0 1 1 0,${-2 * R}` : arc(cx, cy, R, -Math.PI / 2, -Math.PI / 2 + v * 2 * Math.PI),
                    style: 'fill:none;stroke:var(--series);stroke-width:12;stroke-linecap:round'}, svg);
  T(svg, cx, cy + 6, nf(score, 1), {'text-anchor': 'middle', class: 'ink', style: 'font-size:26px;font-weight:700'});
  T(svg, cx, cy + 24, 'out of 100', {'text-anchor': 'middle'});
}

/* ================= page construction ================= */
if (!root.dataset.theme) root.dataset.theme = 'dark';                 // dark by default; a button to switch
document.body.dataset.accent = D.accent || 'generic';
const Q = D.quality || {}, ST = D.stats || {};
const SEG = D.segments || [], BR = D.bridges || [], SIG = D.signals || [];
const INS = (D.insights || []).slice().sort((a, b) => (b.priority || 0) - (a.priority || 0));
const isSeries = k => KP[k] && KP[k].series && KP[k].series.values && KP[k].series.values.length > 1;
const isRate = k => KP[k] && KP[k].unit === 'percent' && KP[k].value != null && KP[k].value >= 0 && KP[k].value <= 1;
const kidByName = name => Object.keys(KP).find(k => KP[k].name === name);

// deferred drawing: the real width is only known once the panel is visible
function later(el, fn) {
  DRAWS.push(force => {
    const w = Math.floor(el.clientWidth); if (!w) return;
    if (!force && el._w === w) return;
    el._w = w; el.replaceChildren(); fn(el, w);
  });
  return el;
}
function panel(title, right, cls) {
  const p = $('div', 'card' + (cls ? ' ' + cls : ''));
  if (title != null) {
    const h = $('div', 'ptitle'); h.appendChild($('h3', null, title));
    if (right) h.appendChild(right);
    p.appendChild(h);
  }
  return p;
}
function pill(d) {
  if (!d) return null;
  const cls = d.good === true ? 'good' : d.good === false ? 'bad' : 'neutral';
  const c = $('span', 'pill ' + cls);
  c.append(icon(d.up === true ? 'up' : d.up === false ? 'down' : 'flat'), document.createTextNode(d.text));
  c.title = d.label || '';
  return c;
}
function dtext(d) {
  if (!d) return $('div', 'd neutral', ' ');
  const cls = d.good === true ? 'good' : d.good === false ? 'bad' : 'neutral';
  const e = $('div', 'd ' + cls, (d.up === true ? '▲ ' : d.up === false ? '▼ ' : '') + d.text);
  e.title = d.label || ''; return e;
}
// progress ring (rate) with a crown of tick marks
function ringGauge(plot, w, v, opts) {
  const size = Math.min(w, opts.size || 210), R = size / 2 - (opts.ticks ? 20 : 8), cx = w / 2, cy = size / 2;
  const svg = svgBox(plot, w, size, opts.label || '');
  const val = clamp(v, 0, 1), sw = opts.stroke || 12;
  if (opts.ticks) {
    const n = 72;
    for (let i = 0; i < n; i++) {
      const a = -Math.PI / 2 + i * 2 * Math.PI / n, on = i / n < val, r1 = R + sw / 2 + 6, r2 = r1 + (i % 6 === 0 ? 7 : 4);
      S('line', {x1: cx + r1 * Math.cos(a), y1: cy + r1 * Math.sin(a), x2: cx + r2 * Math.cos(a), y2: cy + r2 * Math.sin(a),
                 style: `stroke:${on ? 'var(--series)' : 'var(--axis)'};stroke-width:1.5;opacity:${on ? 1 : 0.7}`}, svg);
    }
  }
  S('circle', {cx, cy, r: R, style: `fill:none;stroke:var(--track);stroke-width:${sw}`}, svg);
  if (val > 0) {
    const g = grad(svg, 'var(--series)', 1, 0.75);
    S('path', {d: val >= 0.9999 ? `M${cx},${cy - R}a${R},${R} 0 1 1 0,${2 * R}a${R},${R} 0 1 1 0,${-2 * R}` : arc(cx, cy, R, -Math.PI / 2, -Math.PI / 2 + val * 2 * Math.PI),
               style: `fill:none;stroke:${opts.color || g};stroke-width:${sw};stroke-linecap:round`}, svg);
  }
  T(svg, cx, cy + (opts.sub ? 4 : opts.fs ? opts.fs / 3 : 10), opts.text, {'text-anchor': 'middle', class: 'ink', style: `font-size:${opts.fs || 34}px;font-weight:700`});
  if (opts.sub) T(svg, cx, cy + 22, opts.sub, {'text-anchor': 'middle'});
  return svg;
}
function halfGauge(plot, w, v, text) {
  const r = Math.min(w / 2 - 14, 92), cx = w / 2, cy = r + 10, h = cy + 22;
  const svg = svgBox(plot, w, h, 'Gauge');
  S('path', {d: arc(cx, cy, r, Math.PI, 2 * Math.PI), style: 'fill:none;stroke:var(--track);stroke-width:22'}, svg);
  const val = clamp(v, 0, 1);
  if (val > 0) S('path', {d: arc(cx, cy, r, Math.PI, Math.PI + Math.max(0.01, val) * Math.PI), style: `fill:none;stroke:${grad(svg, 'var(--series)', 1, 0.8)};stroke-width:22`}, svg);
  const a = Math.PI + val * Math.PI;
  S('line', {x1: cx + (r - 14) * Math.cos(a), y1: cy + (r - 14) * Math.sin(a), x2: cx + (r + 14) * Math.cos(a), y2: cy + (r + 14) * Math.sin(a), style: 'stroke:var(--ink);stroke-width:3;stroke-linecap:round'}, svg);
  T(svg, cx, cy - 10, text, {'text-anchor': 'middle', class: 'ink', style: 'font-size:28px;font-weight:700'});
  T(svg, cx - r, cy + 18, '0%', {'text-anchor': 'middle'});
  T(svg, cx + r, cy + 18, '100%', {'text-anchor': 'middle'});
}
const TYPE_LABEL = {alert: 'Alert', opportunity: 'Opportunity', finding: 'Finding'};
function kindTag(type) { const k = $('span', 'kind t-' + type); k.append(icon(TYPE_ICON[type] || 'eye'), document.createTextNode(TYPE_LABEL[type] || type)); return k; }

/* ---------- top bar ---------- */
const topbar = $('header', 'topbar');
const brand = $('div', 'brand'), logo = $('div', 'logo'); logo.appendChild(icon('chart'));
const bt = $('div'); bt.style.minWidth = '0';
bt.append($('h1', null, D.title || 'Dashboard'),
          $('div', 'meta', [D.domain, D.period ? D.period[0] + ' → ' + D.period[1] + ' (' + D.months + ' months)' : null, ST.validated + '/' + ST.kpis + ' KPIs verified'].filter(Boolean).join('  ·  ')));
brand.append(logo, bt);
const tabs = $('nav', 'tabs'); tabs.setAttribute('role', 'tablist');
const tools = $('div', 'tools');
const QS = {ready: ['var(--good)', 'Data ready'], ready_with_warnings: ['var(--warning)', 'Ready with warnings']}[Q.status] || ['var(--critical)', 'Data to review'];
const stat = $('span', 'status'); const sdot = $('i'); sdot.style.background = QS[0]; stat.append(sdot, document.createTextNode(QS[1])); tools.appendChild(stat);
const themeBtn = $('button', 'ibtn'); themeBtn.type = 'button'; themeBtn.title = 'Light / dark theme'; themeBtn.setAttribute('aria-label', themeBtn.title); themeBtn.appendChild(icon('moon'));
themeBtn.addEventListener('click', () => { root.dataset.theme = isDark() ? 'light' : 'dark'; try { localStorage.setItem('biflow-theme', root.dataset.theme); } catch (e) { /* ignored */ } drawAll(true); });
const printBtn = $('button', 'ibtn'); printBtn.type = 'button'; printBtn.title = 'Print'; printBtn.setAttribute('aria-label', 'Print'); printBtn.appendChild(icon('print'));
printBtn.addEventListener('click', () => window.print());
tools.append(themeBtn, printBtn);
topbar.append(brand, tabs, tools);
app.appendChild(topbar);

const VIEWS = [];
function view(id, label, ic, count) {
  const v = $('section', 'view'); v.id = 'v-' + id; v.setAttribute('role', 'tabpanel');
  const b = $('button'); b.type = 'button'; b.setAttribute('role', 'tab'); b.append(icon(ic), document.createTextNode(label));
  if (count) b.appendChild($('span', 'count', String(count)));
  b.addEventListener('click', () => show(id));
  tabs.appendChild(b); app.appendChild(v); VIEWS.push({id, v, b});
  return v;
}
let CURV = 'ov';
function show(id) {
  CURV = id;
  for (const x of VIEWS) { const on = x.id === id; x.v.classList.toggle('on', on); x.b.classList.toggle('on', on); x.b.setAttribute('aria-selected', on); }
  hideTip(); requestAnimationFrame(() => drawAll(false));
}

/* =============== view 1: overview (a single screen) =============== */
const V1 = view('ov', 'Overview', 'grid');
const ov = $('div', 'ov'); V1.appendChild(ov);
const left = $('div', 'col left'), mid = $('div', 'col mid'), right = $('div', 'col right');
ov.append(left, mid, right);
const tiles = (D.tiles || []).filter(k => KP[k]);
const hero = KP[D.hero];

// --- left column: main KPI
if (hero) {
  const p = panel(hero.name, null, 'hero'); p.id = 'tile-' + D.hero;
  if (isRate(D.hero)) {
    const g = $('div'); p.appendChild(g);
    later(g, (el, w) => ringGauge(el, w, hero.value, {ticks: true, text: hero.display, size: 220, label: hero.name}));
    const c = $('div', 'center'); const pl = pill(hero.delta); if (pl) c.appendChild(pl); c.appendChild($('div', 'tiny', hero.definition || '')).style.textAlign = 'center'; p.appendChild(c);
  } else {
    p.appendChild($('div', 'big', hero.display));
    const r = $('div'); r.style.cssText = 'display:flex;align-items:center;gap:8px;margin-top:6px;flex-wrap:wrap';
    const pl = pill(hero.delta); if (pl) { r.appendChild(pl); r.appendChild($('span', 'tiny', 'vs previous 3 months')); }
    p.appendChild(r);
    if (isSeries(D.hero)) { const g = $('div'); g.style.marginTop = '12px'; p.appendChild(g); later(g, (el, w) => sparkLine(el, w, 92, hero, {labels: true})); }
    else {
      const seg = SEG.find(x => x.label === hero.name && x.mode === 'share');
      if (seg) {
        p.appendChild($('div', 'tiny', 'Breakdown by ' + seg.by)).style.marginTop = '14px';
        const items = seg.segments.map(x => ({g: x.g, v: x.share})); const rest = 1 - items.reduce((a, x) => a + x.v, 0); if (rest > 0.005) items.push({g: 'Others', v: rest, other: true});
        const st = $('div', 'stack'); const lg = $('div', 'legend');
        items.slice(0, 6).forEach((it, i) => { const col = it.other ? 'var(--neutral-fill)' : `var(--cat${i + 1})`; const sg = $('div'); sg.style.cssText = `flex:${it.v};background:${col}`; hover(sg, it.g, [nf(100 * it.v, 1) + '%']); st.appendChild(sg);
          const sp = $('span'); const k = $('i', 'key'); k.style.background = col; sp.append(k, document.createTextNode(it.g + ' ' + nf(100 * it.v, 0) + '%')); lg.appendChild(sp); });
        p.append(st, lg);
      }
      p.appendChild($('div', 'def', hero.definition || ''));
    }
  }
  left.appendChild(p);
}
// --- rates: a half-circle gauge + bars
const rates = tiles.filter(isRate), others = tiles.filter(k => !isRate(k));
if (rates.length) {
  const k0 = rates[0], g0 = KP[k0];
  const p = panel(g0.name); p.id = 'tile-' + k0;
  const g = $('div'); p.appendChild(g); later(g, (el, w) => halfGauge(el, w, g0.value, g0.display));
  const c = $('div', 'center'); const pl = pill(g0.delta); if (pl) c.appendChild(pl); p.appendChild(c);
  left.appendChild(p);
}
if (rates.length > 1) {
  const p = panel('Key rates');
  rates.slice(1, 5).forEach((k, i) => {
    const r = $('div', 'mrow'); r.id = 'tile-' + k;
    const l = $('div', 'l'); l.append($('span', null, KP[k].name), $('b', null, KP[k].display));
    const bar = $('div', 'bar'), f = $('i'); f.style.width = clamp(100 * KP[k].value, 0, 100) + '%'; f.style.background = [`var(--cat3)`, `var(--cat2)`, `var(--cat5)`, `var(--cat4)`][i]; bar.appendChild(f);
    r.append(l, bar); r.title = KP[k].definition || ''; p.appendChild(r);
  });
  left.appendChild(p);
}
const statKs = [...others, ...rates.slice(5)];
if (statKs.length) {
  const grid = $('div', 'stats');
  statKs.slice(0, 6).forEach(k => {
    const c = $('div', 'stat'); c.id = 'tile-' + k; c.title = KP[k].definition || '';
    c.append($('div', 'n', KP[k].name), $('div', 'v', KP[k].display), dtext(KP[k].delta));
    grid.appendChild(c);
  });
  if (statKs.slice(0, 6).length % 2) { const c = $('div', 'stat'); c.append($('div', 'n', 'Statistical facts'), $('div', 'v', String(ST.facts)), $('div', 'd neutral', ST.insights + ' insights')); grid.appendChild(c); }
  left.appendChild(grid);
}

// --- central column: current priority
if (INS.length) {
  const top = INS[0], p = $('div', 'card headline');
  const ic = $('div', 'ic t-' + top.type); ic.appendChild(icon(TYPE_ICON[top.type] || 'eye'));
  const tx = $('div', 'tx'); tx.append($('b', null, top.title), $('span', null, top.recommendation || top.text));
  const go = $('button', 'go'); go.type = 'button'; go.append(document.createTextNode(INS.length + ' insights'), icon('arrow'));
  go.addEventListener('click', () => show('ins'));
  p.append(ic, tx, go); mid.appendChild(p);
}
// --- main chart (tabbed)
const mainKs = [...new Set([D.hero, ...(D.charts || [])].filter(isSeries))];
const allSeries = Object.keys(KP).filter(isSeries);
if (mainKs.length < 2) for (const k of allSeries) if (!mainKs.includes(k) && mainKs.length < 4) mainKs.push(k);
if (mainKs.length) {
  const chips = $('div', 'chips');
  const p = panel('Trend', chips); p.id = 'main-chart';
  const plot = $('div', 'plot'), notes = $('div'); p.append(plot, notes);
  let cur = mainKs[0];
  const modeOf = k => (KP[k].unit === 'count' || KP[k].unit === 'currency') && KP[k].series.values.length <= 40 && Math.min(...KP[k].series.values) >= 0 ? 'columns' : 'area';
  const render = () => {
    plot._w = 0; drawAll(false);
    notes.replaceChildren();
    for (const n of ((D.notes || {})[cur] || []).slice(0, 2)) {
      const r = $('div', 'note'); const ic = icon(SIG_ICON[n.type] || 'info'); ic.style.color = n.valence === 'favorable' ? 'var(--good-text)' : n.valence === 'unfavorable' ? 'var(--critical)' : 'var(--muted)';
      r.append(ic, $('span', null, n.text)); notes.appendChild(r);
    }
  };
  mainKs.forEach(k => {
    const b = $('button', 'chipbtn' + (k === cur ? ' on' : ''), KP[k].name); b.type = 'button'; b.title = KP[k].definition || '';
    b.addEventListener('click', () => { cur = k; chips.querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); render(); });
    chips.appendChild(b);
  });
  later(plot, (el, w) => timeChart(el, w, cur, {mode: modeOf(cur), h: 270}));
  mid.appendChild(p);
  render();
  p.focusKpi = k => { const b = [...chips.children].find(x => x.textContent === KP[k].name); if (b) b.click(); };
} else if (SEG.some(s => s.mode === 'level')) {
  const ns = SEG.filter(s => s.mode === 'level'), chips = $('div', 'chips');
  const p = panel('Comparison by segment', chips); p.id = 'main-chart';
  const plot = $('div', 'plot'), cap = $('div', 'cap'); p.append(plot, cap);
  let cur = ns[0];
  const lolli = s => s.unit === 'percent' && s.segments.length <= 8 && s.segments.every(x => x.value >= 0);
  later(plot, (el, w) => (lolli(cur) ? lollipop : divergingBars)(el, w, cur));
  const render = () => { plot._w = 0; drawAll(false); cap.textContent = cur.text; };
  ns.slice(0, 4).forEach((s, i) => { const b = $('button', 'chipbtn' + (i ? '' : ' on'), s.label); b.type = 'button';
    b.addEventListener('click', () => { cur = s; chips.querySelectorAll('button').forEach(x => x.classList.toggle('on', x === b)); render(); }); chips.appendChild(b); });
  cap.textContent = cur.text;
  mid.appendChild(p);
}
// --- rows: segments (or insights, or series)
function segRow(s, i) {
  const r = $('div', 'srow');
  const ring = $('div');
  const part = s.mode === 'share', items = part ? s.segments.slice().sort((a, b) => b.share - a.share) : s.segments.slice().sort((a, b) => b.value - a.value);
  const hi = items[0], lo = items[items.length - 1];
  const ringV = part ? hi.share : s.unit === 'percent' ? hi.value : null;
  later(ring, (el, w) => ringGauge(el, w, ringV == null ? 1 : ringV, {size: 58, stroke: 6, fs: 13, text: ringV == null ? fmtShort(hi.value, s.unit) : nf(100 * ringV, 0) + '%',
                                                                         color: ringV == null ? 'var(--axis)' : null, label: s.label}));
  const body = $('div'); body.style.minWidth = '0';
  const nm = $('div', 'nm'); nm.append(document.createTextNode(s.label + ' '), $('span', 'by', 'by ' + s.by)); body.appendChild(nm);
  const second = part ? items[1] : lo;
  const scale = part ? 1 : Math.max(...items.map(x => Math.abs(x.value))) || 1;
  [[hi, part ? 'var(--cat1)' : 'var(--pos)'], [second, part ? 'var(--cat2)' : 'var(--neg)']].forEach(([x, col]) => {
    if (!x) return;
    const br = $('div', 'br'); const t = $('span', 't', x.g); t.title = x.g;
    const bar = $('div', 'bar'), f = $('i'); f.style.width = clamp(100 * (part ? x.share : Math.abs(x.value)) / scale, 1, 100) + '%'; f.style.background = col; bar.appendChild(f);
    br.append(t, bar, $('span', 'v', part ? nf(100 * x.share, 1) + '%' : fmt(x.value, s.unit))); body.appendChild(br);
  });
  const side = $('div', 'side');
  if (part) { const top3 = items.slice(0, 3).reduce((a, x) => a + x.share, 0); side.append($('div', 'lb', items.length >= 3 ? 'Top 3' : 'Top ' + items.length), $('div', 'vv', nf(100 * top3, 0) + '%'), $('div', 'sub', 'of total')); }
  else { side.append($('div', 'lb', 'Average'), $('div', 'vv', fmt(s.overall, s.unit)), $('div', 'sub', lo.value > 0 ? 'ratio ×' + nf(hi.value / lo.value, 1) : 'gap ' + fmtShort(hi.value - lo.value, s.unit))); }
  r.append($('div', 'rk', String(i + 1)), ring, body, side);
  hover(r, s.label + ' by ' + s.by, [s.text]);
  return r;
}
{
  let p;
  if (SEG.length) {
    const go = $('button', 'go'); go.type = 'button'; go.append(document.createTextNode('Analyses'), icon('arrow')); go.addEventListener('click', () => show('an'));
    p = panel('Gaps between segments', go);
    const rows = $('div', 'rows'); SEG.slice(0, 4).forEach((s, i) => rows.appendChild(segRow(s, i))); p.appendChild(rows);
  } else if (D.heatmap) {
    const hm = D.heatmap;
    p = panel('Seasonality · ' + hm.name, $('span', 'tiny', 'darker = higher'));
    const g = $('div', 'plot'); p.appendChild(g); later(g, (el, w) => heatmap(el, w, hm));
  } else if (INS.length > 1) {
    p = panel('Key takeaways');
    const l = $('div', 'ilist'); INS.slice(1, 5).forEach(x => l.appendChild(insRow(x))); p.appendChild(l);
  } else if (allSeries.length) {
    p = panel('All series');
    const g = $('div'); g.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:10px';
    allSeries.forEach(k => { const c = $('div'); c.style.cssText = 'background:var(--surface2);border-radius:10px;padding:10px';
      c.append($('div', 'tiny', KP[k].name)); const v = $('b', null, fmtShort(KP[k].series.values.at(-1), KP[k].unit)); v.style.fontSize = '17px'; c.appendChild(v);
      const s = $('div'); s.style.marginTop = '6px'; c.appendChild(s); later(s, (el, w) => sparkLine(el, w, 36, KP[k])); g.appendChild(c); });
    p.appendChild(g);
  }
  if (p) mid.appendChild(p);
}
function insRow(x) {
  const r = $('div', 'irow'); const ic = $('div', 'ic t-' + x.type); ic.appendChild(icon(TYPE_ICON[x.type] || 'eye'));
  const t = $('div'); t.style.minWidth = '0'; t.append($('b', null, x.title), $('span', null, x.text)); r.append(ic, t);
  r.style.cursor = 'pointer'; r.addEventListener('click', () => show('ins'));
  return r;
}

// --- right column: distribution
{
  const ps = SEG.find(s => s.mode === 'share');
  if (ps) {
    const p = panel(ps.label + ' by ' + ps.by);
    const kid = kidByName(ps.label);
    const t = $('div', 'total'); t.append($('span', null, 'Total'), $('b', null, kid ? KP[kid].display : '—')); p.appendChild(t);
    const items = ps.segments.map(x => ({g: x.g, v: x.share})); const rest = 1 - items.reduce((a, x) => a + x.v, 0); if (rest > 0.005) items.push({g: 'Others', v: rest, other: true});
    const st = $('div', 'stack'), mods = $('div', 'mods');
    items.slice(0, 6).forEach((it, i) => {
      const col = it.other ? 'var(--neutral-fill)' : `var(--cat${i + 1})`;
      const sg = $('div'); sg.style.cssText = `flex:${it.v};background:${col};min-width:3px`; hover(sg, it.g, [nf(100 * it.v, 1) + '% of total']); st.appendChild(sg);
      const m = $('div', 'mod'); const sp = $('span'); const k = $('i', 'key'); k.style.background = col; const em = $('em', null, it.g); em.title = it.g; sp.append(k, em);
      m.append($('b', null, nf(100 * it.v, 1) + '%'), sp); mods.appendChild(m);
    });
    p.append(st, mods); right.appendChild(p);
  } else if (INS.length) {
    const p = panel('Insights by type');
    const t = $('div', 'total'); t.append($('span', null, 'Total'), $('b', null, String(INS.length))); p.appendChild(t);
    const st = $('div', 'stack'), mods = $('div', 'mods');
    ['alert', 'opportunity', 'finding'].forEach(ty => {
      const n = INS.filter(x => x.type === ty).length; if (!n) return;
      const col = ty === 'alert' ? 'var(--critical)' : ty === 'opportunity' ? 'var(--good)' : 'var(--series)';
      const sg = $('div'); sg.style.cssText = `flex:${n};background:${col}`; st.appendChild(sg);
      const m = $('div', 'mod'); const sp = $('span'); const k = $('i', 'key'); k.style.background = col; sp.append(k, $('em', null, TYPE_LABEL[ty])); m.append($('b', null, String(n)), sp); mods.appendChild(m);
    });
    p.append(st, mods); right.appendChild(p);
  } else {
    const dims = Q.dimensions || {}, names = Object.keys(dims);
    const p = panel('Data quality');
    if (names.length) { const g = $('div'); p.appendChild(g); const avg = mean(names.map(d => dims[d].after)); later(g, (el, w) => ringGauge(el, w, avg / 100, {size: 150, stroke: 10, fs: 26, text: nf(avg, 1), sub: 'score / 100'})); }
    p.appendChild($('div', 'tiny', QS[1] + ' · ' + (Q.open_rules || 0) + ' open rule(s)')).style.textAlign = 'center';
    right.appendChild(p);
  }
}
// --- right column: second curve (dotted average) or list of insights
{
  const second = allSeries.find(k => KP[k].unit === 'percent' && !mainKs.includes(k)) || allSeries.find(k => !mainKs.includes(k))
              || allSeries.find(k => KP[k].unit === 'percent' && k !== mainKs[0]) || allSeries.find(k => k !== mainKs[0]);
  if (second) {
    const p = panel(KP[second].name, $('span', 'tiny', 'latest: ' + fmtShort(KP[second].series.values.at(-1), KP[second].unit)));
    const g = $('div', 'plot'); p.appendChild(g); later(g, (el, w) => timeChart(el, w, second, {mode: 'area', h: 210, avg: true}));
    right.appendChild(p);
  }
  if (INS.length && (SEG.length || !second)) {
    const p = panel('Key takeaways');
    const l = $('div', 'ilist'); INS.slice(1, second ? 3 : 5).forEach(x => l.appendChild(insRow(x)));
    if (l.children.length) { p.appendChild(l); right.appendChild(p); }
  }
}

/* =============== view 2: insights and signals =============== */
if (INS.length || SIG.length) {
  const V2 = view('ins', 'Insights', 'bulb', INS.length || null);
  const sp = $('div', SIG.length && INS.length ? 'split' : ''); V2.appendChild(sp);
  if (INS.length) {
    const g = $('div', 'g2'); g.style.gridTemplateColumns = 'repeat(auto-fit,minmax(min(100%,300px),1fr))';
    const maxP = Math.max(...INS.map(i => i.priority || 0)) || 1;
    for (const x of INS) {
      const c = $('article', 'card ins'), top = $('div', 'top');
      top.append(kindTag(x.type), $('span', 'badge', x.source === 'LLM' ? 'verified LLM' : 'computed'));
      const pr = $('span', 'prio'), bar = $('i'), fb = $('b'); fb.style.width = Math.round(100 * (x.priority || 0) / maxP) + '%'; bar.appendChild(fb); pr.append(document.createTextNode('priority'), bar); top.appendChild(pr);
      c.append(top, $('h4', null, x.title), $('p', null, x.text));
      if (x.recommendation) { const r = $('p', 'reco'); r.append($('b', null, 'Action: '), document.createTextNode(x.recommendation)); c.appendChild(r); }
      const row = $('div'); row.style.cssText = 'display:flex;gap:12px;align-items:center;flex-wrap:wrap';
      const k = (x.kpis || []).find(isSeries);
      if (k) { const b = $('button', 'go'); b.type = 'button'; b.append(icon('jump'), document.createTextNode('View the chart'));
        b.addEventListener('click', () => { show('ov'); const mc = document.getElementById('main-chart'); if (mc && mc.focusKpi) mc.focusKpi(k); if (mc) { mc.scrollIntoView({behavior: 'smooth', block: 'center'}); mc.classList.remove('flash'); void mc.offsetWidth; mc.classList.add('flash'); } });
        row.appendChild(b); }
      if ((x.facts || []).length) { const det = $('details'); det.appendChild($('summary', null, 'Source facts (' + x.facts.join(', ') + ')'));
        const ul = $('ul'); x.facts.forEach(f => ul.appendChild($('li', null, f + ' · ' + ((D.facts || {})[f] || {}).text))); det.appendChild(ul); row.appendChild(det); }
      c.appendChild(row); g.appendChild(c);
    }
    sp.appendChild(g);
  }
  if (SIG.length) {
    const col = $('div', 'col');
    const pu = $('div', 'pulse');
    [...new Set(SIG.map(x => x.type))].forEach(t => { const n = SIG.filter(x => x.type === t).length; const c = $('div', 'pcell'), ic = $('div', 'ic'); ic.appendChild(icon(SIG_ICON[t] || 'spark'));
      const tx = $('div'); tx.append($('b', null, String(n)), $('span', null, t)); c.append(ic, tx); pu.appendChild(c); });
    const card = plotCard({title: 'Signal timeline', sub: 'hover over a row to read the finding', draw: (p, w) => signalTimeline(p, w, SIG),
      headers: ['Indicator', 'Type', 'Valence', 'Finding'], rows: SIG.map(x => [x.name, x.type, x.valence || '—', x.text]),
      legend: [{color: 'var(--pos)', text: 'favorable'}, {color: 'var(--neg)', text: 'unfavorable'}, {color: 'var(--neutral-fill)', text: 'neutral'}]});
    card.insertBefore(pu, card.children[1]);
    col.appendChild(card); sp.appendChild(col);
  }
}

/* =============== view 3: detailed analyses =============== */
if (SEG.length || BR.length || D.heatmap || allSeries.length) {
  const V3 = view('an', 'Analyses', 'chart');
  const g = $('div', 'g2'); V3.appendChild(g);
  const hm = D.heatmap;
  if (hm) {
    const sw = []; for (let b = 1; b <= 7; b++) sw.push({color: `var(--seq${b})`, text: b === 1 ? fmtShort(Math.min(...hm.values), hm.unit) : b === 7 ? fmtShort(Math.max(...hm.values), hm.unit) : ''});
    g.appendChild(plotCard({cls: 'wide', title: 'Seasonality · ' + hm.name, sub: 'years × months, darker = higher', draw: (p, w) => heatmap(p, w, hm),
      headers: ['Month', 'Value'], numeric: [1], rows: hm.periods.map((p, i) => [plong(p), fmt(hm.values[i], hm.unit)]), legend: sw}));
  }
  for (const br of BR) {
    g.appendChild(plotCard({title: 'Waterfall · ' + br.label, sub: 'what explains the change, by ' + br.by, draw: (p, w) => waterfall(p, w, br),
      headers: ['Step', 'Contribution'], numeric: [1], rows: [[br.from, fmt(br.start, br.unit)], ...br.steps.map(x => [x.g, signed(x.delta, br.unit)]), [br.to, fmt(br.end, br.unit)]],
      legend: [{color: 'var(--ink2)', text: 'level'}, {color: 'var(--pos)', text: 'increase'}, {color: 'var(--neg)', text: 'decrease'}, {color: 'var(--neutral-fill)', text: 'others'}], caption: br.text}));
  }
  for (const s of SEG) {
    let draw, rows, headers, legend = null;
    if (s.mode === 'share') {
      const n = s.segments.length + (1 - s.segments.reduce((a, x) => a + x.share, 0) > 0.005 ? 1 : 0);
      draw = n <= 6 ? (p, w) => donut(p, w, s) : (p, w) => treemap(p, w, s);
      headers = [s.by, 'Share']; rows = s.segments.map(x => [x.g, nf(100 * x.share, 1) + '%']);
    } else {
      const lolli = s.unit === 'percent' && s.segments.length <= 8 && s.segments.every(x => x.value >= 0);
      draw = lolli ? (p, w) => lollipop(p, w, s) : (p, w) => divergingBars(p, w, s);
      headers = [s.by, 'Value', 'Rows']; rows = s.segments.map(x => [x.g, fmt(x.value, s.unit), x.n != null ? nf(x.n, 0) : '—']);
      legend = [{color: 'var(--pos)', text: 'above average'}, {color: 'var(--neg)', text: 'below'}];
    }
    g.appendChild(plotCard({title: s.label + ' by ' + s.by, sub: s.mode === 'share' ? 'share of total' : 'gap to the average', draw, headers, rows, numeric: [1, 2], legend, caption: s.text}));
  }
  const rest = allSeries.filter(k => !mainKs.includes(k));
  if (rest.length) {
    const p = panel('Other monthly series');
    const mg = $('div'); mg.style.cssText = 'display:grid;grid-template-columns:repeat(auto-fill,minmax(170px,1fr));gap:10px';
    rest.forEach(k => { const c = $('div'); c.style.cssText = 'background:var(--surface2);border-radius:10px;padding:10px';
      c.append($('div', 'tiny', KP[k].name)); const v = $('b', null, fmtShort(KP[k].series.values.at(-1), KP[k].unit)); v.style.fontSize = '17px'; c.appendChild(v);
      const s = $('div'); s.style.marginTop = '6px'; c.appendChild(s); later(s, (el, w) => sparkLine(el, w, 36, KP[k])); mg.appendChild(c); });
    p.appendChild(mg); g.appendChild(p);
  }
}

/* =============== view 4: quality and catalog =============== */
{
  const V4 = view('qa', 'Quality & KPIs', 'shield');
  const sp = $('div', 'split'); V4.appendChild(sp);
  const lc = $('div', 'col');
  const dims = Q.dimensions || {}, names = Object.keys(dims);
  const qp = panel('Data status');
  const qs = $('div', 'qstat'), qi = $('span', 'ic'); qi.style.background = QS[0]; qi.appendChild(icon(Q.status === 'ready' ? 'check' : 'alert'));
  const qt = $('div'); qt.append($('b', null, QS[1]), $('div', 'tiny', (Q.open_rules || 0) + ' quality rule(s) still open')); qs.append(qi, qt); qp.appendChild(qs);
  if (names.length) {
    const row = $('div'); row.style.cssText = 'display:grid;grid-template-columns:160px minmax(0,1fr);gap:12px;align-items:center;margin-top:10px';
    const rg = $('div'); const avg = mean(names.map(d => dims[d].after));
    later(rg, (el, w) => ringGauge(el, w, avg / 100, {size: 150, stroke: 10, fs: 26, text: nf(avg, 1), sub: 'score / 100'}));
    const db = $('div'); later(db, (el, w) => dumbbell(el, w, dims));
    row.append(rg, db); qp.appendChild(row);
    const lg = $('div', 'legend'); [['var(--neutral-fill)', 'before preparation'], ['var(--series)', 'after']].forEach(([c, t]) => { const s = $('span'); const k = $('i', 'key'); k.style.background = c; s.append(k, document.createTextNode(t)); lg.appendChild(s); });
    qp.appendChild(lg);
  }
  const fl = Object.entries(Q.flagged || {});
  if (fl.length) { const tw = $('div', 'tablewrap'); tw.appendChild(table(['Table', 'Flagged rows'], fl.map(([t, v]) => [t, nf(v, 1) + '%']), [1])); qp.appendChild(tw); }
  lc.appendChild(qp);
  const tp = panel('Chain of trust', $('span', 'tiny', 'the LLM proposes, the code verifies, everything is traced'));
  const steps = $('div', 'steps');
  const hashes = ((D.footer || [])[2] || '').replace(/^Fingerprints: /, '');
  [['book', 'Catalog', ST.kpis + ' KPIs with formula and SQL'], ['check', 'Double calculation', ST.validated + ' KPIs confirmed'],
   ['pulse', 'Facts', ST.facts + ' statistical facts'], ['bulb', 'Insights', ST.insights + (ST.insights_llm ? ' (incl. ' + ST.insights_llm + ' verified LLM)' : ' computed')],
   ['link', 'Audit SHA-256', hashes]].forEach(([ic, t, d]) => { const s = $('div', 'step'); const b = $('b'); b.append(icon(ic), document.createTextNode(t)); s.append(b, $('span', null, d)); steps.appendChild(s); });
  tp.appendChild(steps); lc.appendChild(tp);
  sp.appendChild(lc);
  // catalog
  const CAT = D.catalog || [];
  const cp = panel('Indicator catalog');
  const tl = $('div', 'ctools'); const sr = $('label', 'search'); const inp = $('input'); inp.type = 'search'; inp.placeholder = 'Search…'; inp.setAttribute('aria-label', 'Search the catalog');
  sr.append(icon('search'), inp); tl.appendChild(sr);
  let filter = 'all';
  const pills = [['all', 'All'], ['ok', 'Validated'], ['other', 'To review']].map(([k, l]) => { const b = $('button', 'fpill' + (k === 'all' ? ' on' : ''), l); b.type = 'button'; b.dataset.k = k; tl.appendChild(b); return b; });
  const cnt = $('span', 'tiny'); tl.appendChild(cnt); cp.appendChild(tl);
  const wrap = $('div', 'tablewrap scroll'), t = $('table'), th = $('thead'), hr = $('tr');
  ['Indicator', 'Value', 'Status', 'Formula and SQL'].forEach((h, i) => hr.appendChild($('th', i === 1 ? 'num' : null, h))); th.appendChild(hr); t.appendChild(th);
  const tb = $('tbody'); t.appendChild(tb); wrap.appendChild(t); cp.appendChild(wrap);
  const trs = CAT.map(r => {
    const tr = $('tr'), n = $('td'); n.append($('b', null, r.name), $('div', 'tiny', r.definition || ''));
    const ok = (r.status || '').startsWith('validated');
    const s = $('td'); const rel = $('span', 'rel'); const d = $('i'); d.style.background = ok ? 'var(--good)' : 'var(--warning)'; rel.append(d, document.createTextNode(r.status || '—')); s.appendChild(rel);
    s.appendChild($('div', 'tiny', r.reliability || ''));
    const f = $('td'); const det = $('details'); det.appendChild($('summary', null, shorten(r.formula || 'details', 38)));
    det.append($('div', 'tiny', 'Formula'), $('code', null, r.formula || '—'), $('div', 'tiny', 'SQL query'), $('code', null, r.sql || '—')); f.appendChild(det);
    tr.append(n, $('td', 'num', r.display), s, f);
    tr.dataset.text = (r.name + ' ' + r.id + ' ' + (r.definition || '') + ' ' + (r.formula || '')).toLowerCase(); tr.dataset.ok = ok ? 'ok' : 'other';
    tb.appendChild(tr); return tr;
  });
  const apply = () => { const q = inp.value.trim().toLowerCase(); let n = 0;
    for (const tr of trs) { const v = (!q || tr.dataset.text.includes(q)) && (filter === 'all' || tr.dataset.ok === filter); tr.hidden = !v; n += v; }
    cnt.textContent = n + ' / ' + trs.length; };
  inp.addEventListener('input', apply);
  pills.forEach(b => b.addEventListener('click', () => { filter = b.dataset.k; pills.forEach(x => x.classList.toggle('on', x === b)); apply(); }));
  apply();
  sp.appendChild(cp);
  const ft = $('footer'); (D.footer || []).forEach(l => ft.appendChild($('div', null, l))); V4.appendChild(ft);
}

/* ---------- drawing ---------- */
function drawAll(force) { DRAWS.forEach(f => { try { f(force); } catch (e) { console.error(e); } }); }
show('ov');
let rt; window.addEventListener('resize', () => { clearTimeout(rt); rt = setTimeout(() => drawAll(false), 120); });
window.addEventListener('beforeprint', () => { VIEWS.forEach(x => x.v.classList.add('on')); drawAll(true); });
window.addEventListener('afterprint', () => show(CURV));
})();
"""

print(f"Template ready · CSS {len(DASHBOARD_CSS):,} characters · rendering engine {len(DASHBOARD_JS):,} characters")
