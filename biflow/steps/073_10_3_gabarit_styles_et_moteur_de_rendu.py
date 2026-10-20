DASHBOARD_CSS = r"""
:root{color-scheme:light;--page:#f9f9f7;--surface:#fcfcfb;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;
--axis:#c3c2b7;--ring:rgba(11,11,11,.10);--series:#2a78d6;--wash:rgba(42,120,214,.10);--good:#0ca30c;--good-text:#006300;
--critical:#d03b3b;--warning:#fab219;--neutral:#898781;--chip:#f0efec}
@media (prefers-color-scheme:dark){:root:where(:not([data-theme="light"])){color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;
--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);--series:#3987e5;
--wash:rgba(57,135,229,.14);--good-text:#0ca30c;--chip:#2c2c2a}}
:root[data-theme="dark"]{color-scheme:dark;--page:#0d0d0d;--surface:#1a1a19;--ink:#f0efec;--ink2:#c3c2b7;--muted:#898781;
--grid:#2c2c2a;--axis:#383835;--ring:rgba(255,255,255,.10);--series:#3987e5;--wash:rgba(57,135,229,.14);--good-text:#0ca30c;--chip:#2c2c2a}
*{box-sizing:border-box}
body{margin:0;background:var(--page);color:var(--ink);font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1240px;margin:0 auto;padding:24px 16px 48px}
header.top{display:flex;justify-content:space-between;gap:16px;align-items:flex-start;flex-wrap:wrap;margin-bottom:20px}
h1{font-size:22px;margin:0 0 4px;font-weight:650} h2{font-size:15px;margin:28px 0 12px;font-weight:650}
.sub{color:var(--ink2);margin:0}.meta{color:var(--muted);font-size:12px;margin-top:6px}
button{font:inherit;color:var(--ink2);background:var(--surface);border:1px solid var(--ring);border-radius:8px;padding:5px 10px;cursor:pointer}
button:hover{color:var(--ink)} button:focus-visible{outline:2px solid var(--series);outline-offset:2px}
.card{background:var(--surface);border:1px solid var(--ring);border-radius:12px;padding:16px;min-width:0}
.kpis{display:grid;grid-template-columns:minmax(260px,1.3fr) repeat(auto-fit,minmax(170px,1fr));gap:12px}
.hero .value{font-size:44px;font-weight:650;line-height:1.05;margin:6px 0;white-space:nowrap}
.hero .value.long{font-size:34px}
.tile .value{font-size:26px;font-weight:600;margin:4px 0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.label{color:var(--ink2);font-size:13px}.tiny{color:var(--muted);font-size:12px}
.delta{display:inline-flex;align-items:center;gap:4px;font-size:12.5px;font-weight:600;margin-top:2px}
.delta.good{color:var(--good-text)}.delta.bad{color:var(--critical)}.delta.neutral{color:var(--ink2)}
.spark{display:block;width:100%;height:34px}
.card.hero,.card.tile{display:flex;flex-direction:column}
.badge{display:inline-block;font-size:11px;padding:1px 7px;border-radius:999px;background:var(--chip);color:var(--ink2);margin-left:6px;vertical-align:middle}
.insights{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}
.ins{border-left:4px solid var(--neutral)} .ins.alerte{border-left-color:var(--critical)} .ins.opportunité{border-left-color:var(--good)}
.ins h3{font-size:14.5px;margin:6px 0 6px;font-weight:650}.ins p{margin:0 0 8px;color:var(--ink)}
.ins .reco{color:var(--ink2)}.kind{font-size:12px;font-weight:650;display:inline-flex;gap:6px;align-items:center;color:var(--ink2)}
details{margin-top:6px} summary{cursor:pointer;color:var(--ink2);font-size:12.5px} details ul{margin:6px 0 0;padding-left:18px;color:var(--ink2);font-size:12.5px}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:12px}
.chead{display:flex;justify-content:space-between;align-items:flex-start;gap:8px}
.chead h3{font-size:14px;margin:0;font-weight:650}.plot{position:relative;margin-top:8px}
svg text{fill:var(--muted);font-size:11px;font-family:inherit}
svg text.halo{paint-order:stroke;stroke:var(--surface);stroke-width:4px;stroke-linejoin:round}
.sparkwrap{position:relative;margin-top:auto;padding-top:8px}.sparkdot{position:absolute;width:7px;height:7px;border-radius:50%;background:var(--series);transform:translate(-50%,-50%)}
.tip{position:absolute;pointer-events:none;background:var(--surface);border:1px solid var(--ring);border-radius:8px;padding:6px 9px;
box-shadow:0 4px 14px rgba(0,0,0,.12);font-size:12.5px;max-width:260px;z-index:5;display:none}
.tip strong{display:block;font-size:14px;color:var(--ink)}.tip span{color:var(--ink2)}
table{border-collapse:collapse;width:100%;font-size:12.5px} th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--grid);vertical-align:top}
th{color:var(--ink2);font-weight:600} td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.tablewrap{overflow-x:auto;margin-top:8px} code{font-size:11.5px;white-space:pre-wrap;word-break:break-word;color:var(--ink2)}
footer{margin-top:32px;color:var(--muted);font-size:12px}
@media (max-width:640px){.kpis{grid-template-columns:1fr 1fr}.hero{grid-column:1/-1}.charts,.insights{grid-template-columns:1fr}
.hero .value{font-size:36px}.hero .value.long{font-size:30px}}
"""

DASHBOARD_JS = r"""
const D = JSON.parse(document.getElementById('dashboard-data').textContent);
const $ = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
const NS = 'http://www.w3.org/2000/svg';
const S = (tag, attrs) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); return e; };
const MONTHS = ['janv.', 'févr.', 'mars', 'avr.', 'mai', 'juin', 'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.'];
const plabel = p => MONTHS[p % 100 - 1] + ' ' + String(Math.floor(p / 100)).slice(2);
const CW = () => document.documentElement.clientWidth;
const drawWidth = card => Math.max(280, Math.round(card.clientWidth - 34));   // 1 unité de dessin = 1 pixel : textes lisibles partout
const nf = (v, d) => v.toLocaleString('fr-FR', {minimumFractionDigits: d, maximumFractionDigits: d});
function fmt(v, unit) {
  if (v == null || isNaN(v)) return '—';
  if (unit === 'percent') return nf(100 * v, 1) + ' %';
  if (unit === 'count') return nf(v, 0);
  if (unit === 'days') return nf(v, 1) + ' j';
  return nf(v, 2);
}
function tick(v, unit, step) {                       // nombre de décimales tiré du pas : jamais deux graduations identiques
  const dec = s => Math.min(4, Math.max(0, -Math.floor(Math.log10(s) + 1e-9)));
  if (Math.abs(v) < step * 1e-6) return unit === 'percent' ? '0 %' : '0';
  if (unit === 'percent') return nf(100 * v, dec(100 * step)) + ' %';
  const a = Math.max(Math.abs(v), step);
  if (a >= 1e6 && step >= 1e5) return nf(v / 1e6, dec(step / 1e6)) + ' M';
  if (a >= 1e3 && step >= 100) return nf(v / 1e3, dec(step / 1e3)) + ' k';
  return nf(v, dec(step)) + (unit === 'days' ? ' j' : '');
}
function niceTicks(lo, hi, n) {
  const span = hi - lo || Math.abs(hi) || 1, raw = span / n, mag = Math.pow(10, Math.floor(Math.log10(raw)));
  const step = [1, 2, 2.5, 5, 10].map(m => m * mag).find(s => s >= raw);
  const t0 = Math.floor(lo / step) * step, out = [];
  for (let t = t0; t <= hi + step * 0.5; t += step) out.push(+t.toFixed(10));
  return out;
}
function deltaEl(d) {
  if (!d) return null;
  const cls = d.good === null ? 'neutral' : d.good ? 'good' : 'bad';
  const e = $('div', 'delta ' + cls);
  e.appendChild($('span', null, d.up ? '▲' : '▼'));
  e.appendChild($('span', null, d.text));
  e.title = d.label;
  return e;
}
function sparkline(series) {
  const w = 160, h = 34, v = series.values, lo = Math.min(...v), hi = Math.max(...v), r = hi - lo || 1;
  const x = i => 2 + i * (w - 6) / (v.length - 1), y = val => h - 4 - (val - lo) / r * (h - 8);
  const svg = S('svg', {viewBox: `0 0 ${w} ${h}`, class: 'spark', 'aria-hidden': 'true', preserveAspectRatio: 'none'});
  svg.appendChild(S('polyline', {points: v.map((val, i) => `${x(i)},${y(val)}`).join(' '), fill: 'none', stroke: 'var(--muted)',
    'stroke-width': 1.5, 'stroke-linejoin': 'round', 'stroke-linecap': 'round', 'vector-effect': 'non-scaling-stroke'}));
  const n = v.length - 1, wrap = $('div', 'sparkwrap'), dot = $('span', 'sparkdot');   // point final en HTML : reste rond
  dot.style.left = (x(n) / w * 100) + '%';
  dot.style.top = `calc(8px + ${y(v[n])}px)`;
  wrap.append(svg, dot);
  return wrap;
}
function tableToggle(card, plot, rows, headers) {
  const btn = $('button', null, 'Tableau');
  btn.setAttribute('aria-pressed', 'false');
  const wrap = $('div', 'tablewrap'); wrap.hidden = true;
  const t = $('table'), tr = $('tr');
  headers.forEach((h, i) => { const th = $('th', i ? 'num' : null, h); tr.appendChild(th); });
  t.appendChild(tr);
  rows.forEach(r => { const row = $('tr'); r.forEach((c, i) => row.appendChild($('td', i ? 'num' : null, c))); t.appendChild(row); });
  wrap.appendChild(t); card.appendChild(wrap);
  btn.onclick = () => { const on = wrap.hidden; wrap.hidden = !on; plot.hidden = on; btn.textContent = on ? 'Graphique' : 'Tableau';
    btn.setAttribute('aria-pressed', String(on)); };
  return btn;
}
function lineChart(card, c, notes) {
  const W = drawWidth(card), H = W < 500 ? 200 : 230, L = 52, R = 14, T = 12, B = 26, v = c.series.values, p = c.series.periods, n = v.length;
  let lo = Math.min(...v), hi = Math.max(...v);
  if (c.unit === 'percent' || c.unit === 'count' || c.unit === 'currency') lo = Math.min(lo, 0);
  const ticks = niceTicks(lo, hi, 4); lo = Math.min(lo, ticks[0]); hi = Math.max(hi, ticks[ticks.length - 1]);
  const x = i => L + i * (W - L - R) / Math.max(n - 1, 1), y = val => T + (hi - val) / (hi - lo || 1) * (H - T - B);
  const plot = $('div', 'plot'), svg = S('svg', {viewBox: `0 0 ${W} ${H}`, width: '100%', role: 'img',
    'aria-label': c.name + ', ' + n + ' mois'});
  ticks.forEach(t => { svg.appendChild(S('line', {x1: L, x2: W - R, y1: y(t), y2: y(t), stroke: t === 0 ? 'var(--axis)' : 'var(--grid)', 'stroke-width': 1}));
    const lab = S('text', {x: L - 6, y: y(t) + 3.5, 'text-anchor': 'end'}); lab.textContent = tick(t, c.unit, ticks.length > 1 ? ticks[1] - ticks[0] : Math.abs(t) || 1); svg.appendChild(lab); });
  const every = Math.ceil(n / Math.max(2, Math.floor((W - L - R) / 70)));
  p.forEach((per, i) => { if ((i % every === 0 && x(n - 1) - x(i) >= 64) || i === n - 1) {   // jamais collé à la dernière étiquette
    const lab = S('text', {x: x(i), y: H - 8, 'text-anchor': i === n - 1 ? 'end' : i === 0 ? 'start' : 'middle'});
    lab.textContent = plabel(per); svg.appendChild(lab); } });
  const pts = v.map((val, i) => `${x(i)},${y(val)}`).join(' ');
  svg.appendChild(S('polygon', {points: `${x(0)},${y(Math.max(lo, 0))} ${pts} ${x(n - 1)},${y(Math.max(lo, 0))}`, fill: 'var(--wash)'}));
  svg.appendChild(S('polyline', {points: pts, fill: 'none', stroke: 'var(--series)', 'stroke-width': 2, 'stroke-linejoin': 'round', 'stroke-linecap': 'round'}));
  const byIndex = {};
  notes.forEach(f => {
    if (f.type === 'rupture' && f.start) { const i = p.indexOf(f.start); if (i >= 0) {
      svg.appendChild(S('line', {x1: x(i), x2: x(i), y1: T, y2: H - B, stroke: 'var(--ink2)', 'stroke-width': 1}));
      const lab = S('text', {x: x(i) + 4, y: T + 10}); lab.textContent = 'rupture'; svg.appendChild(lab); (byIndex[i] = byIndex[i] || []).push(f); } }
    (f.periods || []).forEach(per => { const i = p.indexOf(per); if (i < 0) return;
      svg.appendChild(S('circle', {cx: x(i), cy: y(v[i]), r: 5, fill: f.valence === 'favorable' ? 'var(--good)' : f.valence === 'défavorable' ? 'var(--critical)' : 'var(--ink2)',
        stroke: 'var(--surface)', 'stroke-width': 2}));
      (byIndex[i] = byIndex[i] || []).push(f); });
  });
  svg.appendChild(S('circle', {cx: x(n - 1), cy: y(v[n - 1]), r: 4, fill: 'var(--series)', stroke: 'var(--surface)', 'stroke-width': 2}));
  const endLab = S('text', {x: x(n - 1) - 6, y: y(v[n - 1]) - 9, 'text-anchor': 'end', class: 'halo'}); endLab.textContent = fmt(v[n - 1], c.unit);
  endLab.style.fill = 'var(--ink2)'; svg.appendChild(endLab);
  const cross = S('line', {y1: T, y2: H - B, stroke: 'var(--axis)', 'stroke-width': 1, visibility: 'hidden'}); svg.appendChild(cross);
  const dot = S('circle', {r: 4.5, fill: 'var(--series)', stroke: 'var(--surface)', 'stroke-width': 2, visibility: 'hidden'}); svg.appendChild(dot);
  const hit = S('rect', {x: L, y: T, width: W - L - R, height: H - T - B, fill: 'transparent', tabindex: 0}); svg.appendChild(hit);
  const tip = $('div', 'tip'); plot.appendChild(svg); plot.appendChild(tip);
  function show(i) {
    cross.setAttribute('x1', x(i)); cross.setAttribute('x2', x(i)); cross.setAttribute('visibility', 'visible');
    dot.setAttribute('cx', x(i)); dot.setAttribute('cy', y(v[i])); dot.setAttribute('visibility', 'visible');
    tip.replaceChildren($('strong', null, fmt(v[i], c.unit)), $('span', null, plabel(p[i])));
    (byIndex[i] || []).forEach(f => { const s = $('div', 'tiny', (f.type === 'rupture' ? 'Rupture · ' : 'Mois atypique · ') + f.texte); s.style.marginTop = '4px'; tip.appendChild(s); });
    tip.style.display = 'block';
    const bw = plot.clientWidth, px = x(i) / W * bw;
    tip.style.left = Math.min(Math.max(px + 10, 0), bw - tip.offsetWidth) + 'px'; tip.style.top = '6px';
  }
  let cur = n - 1;
  hit.addEventListener('pointermove', e => { const r = svg.getBoundingClientRect(), xx = (e.clientX - r.left) / r.width * W;
    cur = Math.max(0, Math.min(n - 1, Math.round((xx - L) / ((W - L - R) / Math.max(n - 1, 1))))); show(cur); });
  hit.addEventListener('pointerleave', () => { tip.style.display = 'none'; cross.setAttribute('visibility', 'hidden'); dot.setAttribute('visibility', 'hidden'); });
  hit.addEventListener('focus', () => show(cur));
  hit.addEventListener('blur', () => { tip.style.display = 'none'; cross.setAttribute('visibility', 'hidden'); dot.setAttribute('visibility', 'hidden'); });
  hit.addEventListener('keydown', e => { if (e.key === 'ArrowLeft') cur = Math.max(0, cur - 1); else if (e.key === 'ArrowRight') cur = Math.min(n - 1, cur + 1); else return;
    e.preventDefault(); show(cur); });
  return plot;
}
function barChart(card, f) {
  const segs = f.segments.slice(0, 12), share = f.mode === 'part';
  const vals = segs.map(s => share ? s.share : s.value), maxV = Math.max(...vals, share ? 0 : f.overall || 0) || 1;
  const rowH = 26, W = drawWidth(card), L = Math.min(150, Math.round(W * 0.3)), R = 70, H = segs.length * rowH + 22;
  const plot = $('div', 'plot'), svg = S('svg', {viewBox: `0 0 ${W} ${H}`, width: '100%', role: 'img', 'aria-label': f.label});
  const xs = val => L + Math.max(val, 0) / maxV * (W - L - R), tip = $('div', 'tip');
  if (!share && f.overall != null) {                  // trait de moyenne dessiné sous les barres
    svg.appendChild(S('line', {x1: xs(f.overall), x2: xs(f.overall), y1: 0, y2: H - 18, stroke: 'var(--ink2)', 'stroke-width': 1, 'stroke-dasharray': '3 3'}));
    const lab = S('text', {x: xs(f.overall), y: H - 4, 'text-anchor': 'middle'}); lab.textContent = 'moyenne ' + fmt(f.overall, f.unit); svg.appendChild(lab);
  }
  segs.forEach((s, i) => {
    const yy = 4 + i * rowH, val = vals[i], w = Math.max(xs(val) - L, 2), r = Math.min(4, w / 2);
    const name = S('text', {x: L - 8, y: yy + 14, 'text-anchor': 'end'}); name.textContent = String(s.g).length > L / 6.5 ? String(s.g).slice(0, Math.floor(L / 6.5) - 1) + '…' : String(s.g);
    name.style.fill = 'var(--ink2)'; svg.appendChild(name);
    svg.appendChild(S('path', {d: `M${L},${yy + 4} h${w - r} a${r},${r} 0 0 1 ${r},${r} v${16 - 2 * r} a${r},${r} 0 0 1 -${r},${r} h-${w - r} z`, fill: 'var(--series)'}));
    const lab = S('text', {x: L + w + 6, y: yy + 14, class: 'halo'}); lab.textContent = share ? fmt(val, 'percent') : fmt(val, f.unit); lab.style.fill = 'var(--ink2)'; svg.appendChild(lab);
    const hit = S('rect', {x: 0, y: yy, width: W, height: rowH, fill: 'transparent', tabindex: 0});
    const on = () => { tip.replaceChildren($('strong', null, share ? fmt(val, 'percent') + ' du total' : fmt(val, f.unit)), $('span', null, String(s.g)));
      if (s.n) tip.appendChild($('div', 'tiny', nf(s.n, 0) + ' lignes'));
      tip.style.display = 'block'; tip.style.left = Math.min(xs(val) / W * plot.clientWidth + 8, plot.clientWidth - tip.offsetWidth) + 'px';
      tip.style.top = (yy / H * plot.clientHeight) + 'px'; };
    hit.addEventListener('pointermove', on); hit.addEventListener('focus', on);
    hit.addEventListener('pointerleave', () => tip.style.display = 'none'); hit.addEventListener('blur', () => tip.style.display = 'none');
    svg.appendChild(hit);
  });
  plot.appendChild(svg); plot.appendChild(tip);
  return plot;
}
function render() {
  const root = document.getElementById('app'); root.replaceChildren();
  const head = $('header', 'top'), hl = $('div');
  hl.appendChild($('h1', null, D.title)); hl.appendChild($('p', 'sub', D.subtitle)); hl.appendChild($('div', 'meta', D.meta));
  const isDark = () => document.documentElement.getAttribute('data-theme') === 'dark'
    || (!document.documentElement.getAttribute('data-theme') && matchMedia('(prefers-color-scheme: dark)').matches);
  const theme = $('button', null, isDark() ? 'Mode clair' : 'Mode sombre');
  theme.onclick = () => { const dark = !isDark();
    document.documentElement.setAttribute('data-theme', dark ? 'dark' : 'light'); theme.textContent = dark ? 'Mode clair' : 'Mode sombre'; };
  head.append(hl, theme); root.appendChild(head);
  const kpis = $('section', 'kpis'); kpis.setAttribute('aria-label', 'Indicateurs clés');
  const tile = (c, hero) => { const t = $('div', 'card ' + (hero ? 'hero' : 'tile')), lab = $('div', 'label', c.name);
    if (c.status !== 'validé') lab.appendChild($('span', 'badge', c.status)); t.appendChild(lab);
    t.appendChild($('div', 'value' + (hero && c.display.length > 9 ? ' long' : ''), c.display)); const d = deltaEl(c.delta); if (d) t.appendChild(d);
    if (hero) t.appendChild($('div', 'tiny', c.definition));
    if (c.series) t.appendChild(sparkline(c.series)); t.title = c.formula; return t; };
  if (D.hero) kpis.appendChild(tile(D.kpis[D.hero], true));
  D.tiles.forEach(k => kpis.appendChild(tile(D.kpis[k], false)));
  root.appendChild(kpis);
  const withDelta = [D.hero, ...D.tiles].map(k => D.kpis[k] && D.kpis[k].delta).find(d => d);
  const note = $('div', 'tiny', 'Valeurs calculées sur toute la période' + (withDelta ? ' ; flèche = ' + withDelta.label + ' (en points pour un taux).' : '.'));
  note.style.marginTop = '8px'; root.appendChild(note);
  if (D.insights.length) {
    root.appendChild($('h2', null, 'Ce qu\'il faut retenir'));
    const grid = $('section', 'insights');
    D.insights.forEach(ins => { const c = $('article', 'card ins ' + ins.type);
      const icon = {alerte: '⚠', 'opportunité': '▲', constat: '●'}[ins.type] || '●';
      c.appendChild($('span', 'kind', icon + ' ' + ins.type + (ins.source === 'code' ? ' · rédigé par le code' : ' · rédigé par le LLM, vérifié')));
      c.appendChild($('h3', null, ins.titre)); c.appendChild($('p', null, ins.texte)); c.appendChild($('p', 'reco', '→ ' + ins.recommandation));
      const det = $('details'); det.appendChild($('summary', null, 'D\'où viennent ces chiffres ? (' + ins.faits.join(', ') + ')'));
      const ul = $('ul'); ins.faits.forEach(fid => { const f = D.facts[fid]; if (f) ul.appendChild($('li', null, fid + ' · ' + f.texte)); });
      det.appendChild(ul); c.appendChild(det); grid.appendChild(c); });
    root.appendChild(grid);
  }
  if (D.charts.length) {
    root.appendChild($('h2', null, 'Évolution mois par mois'));
    const grid = $('section', 'charts'); root.appendChild(grid);
    const pending = [];                               // les courbes sont dessinées une fois toutes les cartes en place
    D.charts.forEach(k => { const c = D.kpis[k], card = $('figure', 'card'); card.style.margin = 0; grid.appendChild(card);
      const h = $('div', 'chead'), title = $('div'); title.appendChild($('h3', null, c.name));
      title.appendChild($('div', 'tiny', plabel(c.series.periods[0]) + ' → ' + plabel(c.series.periods[c.series.periods.length - 1]) + ' · mois fiables'));
      h.appendChild(title); card.appendChild(h);
      const plot = $('div'); card.appendChild(plot);
      pending.push(() => plot.appendChild(lineChart(card, c, D.notes[k] || [])));
      h.appendChild(tableToggle(card, plot, c.series.periods.map((p, i) => [plabel(p), fmt(c.series.values[i], c.unit)]), ['Mois', c.name]));
      (D.notes[k] || []).forEach(f => card.appendChild($('div', 'tiny', (f.type === 'rupture' ? '│ ' : '● ') + f.texte))); });
    pending.forEach(draw => draw());
  }
  if (D.segments.length) {
    root.appendChild($('h2', null, 'Où se concentrent les écarts'));
    const grid = $('section', 'charts'); root.appendChild(grid);
    const pending = [];
    D.segments.forEach(f => { const card = $('figure', 'card'); card.style.margin = 0; grid.appendChild(card);
      const h = $('div', 'chead'), title = $('div'); title.appendChild($('h3', null, f.label + ' par ' + f.by));
      title.appendChild($('div', 'tiny', f.mode === 'part' ? 'part du total · les ' + f.segments.length + ' premiers segments'
        : (f.segments.length >= 10 ? 'les 10 segments les plus élevés' : 'valeur par segment') + ' (≥ 30 lignes), trait = moyenne'));
      h.appendChild(title); card.appendChild(h);
      const plot = $('div'); card.appendChild(plot); pending.push(() => plot.appendChild(barChart(card, f)));
      h.appendChild(tableToggle(card, plot, f.segments.map(s => [String(s.g), f.mode === 'part' ? fmt(s.share, 'percent') : fmt(s.value, f.unit)]),
        [f.by, f.mode === 'part' ? 'part du total' : f.label]));
      card.appendChild($('div', 'tiny', f.texte)); });
    pending.forEach(draw => draw());
  }
  root.appendChild($('h2', null, 'Catalogue des KPI et traçabilité'));
  const card = $('section', 'card'), wrap = $('div', 'tablewrap'), t = $('table'), hr = $('tr');
  ['KPI', 'Valeur', 'Statut', 'Liaison', 'Fiabilité', 'Formule et requête'].forEach((h, i) => hr.appendChild($('th', i === 1 ? 'num' : null, h)));
  t.appendChild(hr);
  D.catalog.forEach(k => { const r = $('tr'); r.appendChild($('td', null, k.name)); r.appendChild($('td', 'num', k.display));
    r.appendChild($('td', null, k.status)); r.appendChild($('td', null, k.binding)); r.appendChild($('td', null, k.reliability));
    const td = $('td'), det = $('details'); det.appendChild($('summary', null, k.formula)); const code = $('code', null, k.sql);
    det.appendChild(code); if (k.reason) det.appendChild($('div', 'tiny', 'Justification : ' + k.reason)); td.appendChild(det); r.appendChild(td); t.appendChild(r); });
  wrap.appendChild(t); card.appendChild(wrap); root.appendChild(card);
  const foot = $('footer'); D.footer.forEach(line => foot.appendChild($('div', null, line))); root.appendChild(foot);
}
render();
let lastW = CW(), timer = null;                    // redessine les graphiques si la largeur de l'écran change
addEventListener('resize', () => { clearTimeout(timer); timer = setTimeout(() => { if (CW() !== lastW) { lastW = CW(); render(); } }, 200); });
"""
print(f"Gabarit prêt · CSS {len(DASHBOARD_CSS):,} caractères · moteur de rendu {len(DASHBOARD_JS):,} caractères".replace(",", " "))
