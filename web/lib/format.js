// Number/date formatting and business vocabulary (no technical jargon).
// The keys of the maps below are the values written by the pipeline (the notebook): they must not change.

export function fmtInt(n) {
  const k = Number(n);
  if (n === null || n === undefined || Number.isNaN(k)) return "—";
  return Math.round(k).toLocaleString("en-US");
}

export function fmtNum(n, digits = 1) {
  const k = Number(n);
  if (n === null || n === undefined || Number.isNaN(k)) return "—";
  return k.toLocaleString("en-US", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function plural(n, singular, pluralForm) {
  const k = Number(n);
  if (n === null || n === undefined || Number.isNaN(k)) return `— ${pluralForm || singular + "s"}`;
  return `${fmtInt(k)} ${k === 1 ? singular : pluralForm || singular + "s"}`;
}

export function fmtDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" }) +
    " at " + d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

export function fmtDay(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  return d.toLocaleDateString("en-US", { month: "long", day: "numeric", year: "numeric" });
}

/** "just now", "5 min ago", "2 h ago", then the date. */
export function fmtAgo(iso) {
  const t = new Date(iso).getTime();
  if (!t) return "";
  const s = Math.max(0, (Date.now() - t) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return fmtDate(iso);
}

export function fmtDuration(seconds) {
  const s = Math.max(0, Math.round(Number(seconds) || 0));
  const m = Math.floor(s / 60);
  return m ? `${m} min ${String(s % 60).padStart(2, "0")} s` : `${s} s`;
}

export function fmtSize(bytes) {
  if (bytes > 1e9) return `${fmtNum(bytes / 1e9)} GB`;
  if (bytes > 1e6) return `${fmtNum(bytes / 1e6)} MB`;
  return `${fmtNum(bytes / 1e3, 0)} KB`;
}

export function initials(name) {
  return (name || "?").split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join("");
}

export function firstName(name) {
  return (name || "").split(/\s+/)[0] || "";
}

/** Keeps an AI justification only if it is written for a human (no code, no dictionary). */
export function humanText(text) {
  if (typeof text !== "string" || !text.trim()) return "";
  if (/[{}[\]]|_[a-z]|->|fallback|superviseur|supervisor/.test(text)) return "";
  return text.trim();
}

export function showValue(v) {
  if (v === null || v === undefined || v === "" || (typeof v === "number" && Number.isNaN(v))) return "empty";
  if (typeof v === "string" && /^-?\d+(\.\d+)?$/.test(v.trim())) v = Number(v);
  if (typeof v === "number") return v.toLocaleString("en-US", { maximumFractionDigits: 2 });
  return String(v);
}

export const STATUS = {
  running: ["Running", "info"],
  success: ["Finished", "ok"],
  blocked: ["Blocked", "crit"],
  failed: ["Stopped", "crit"],
  interrupted: ["Interrupted", "crit"],
};

export const SEM_TYPE = {
  id: "Identifier", category: "Category", datetime: "Date", numeric: "Amount / measure", integer: "Whole number",
  text: "Free text", zip: "Postal code", geo: "GPS coordinate",
};
export const DIMENSION = {
  "complétude": "Completeness", "validité": "Validity", format: "Formatting", "unicité": "Uniqueness",
  "intégrité": "Consistency across tables", "plausibilité": "Plausibility", structure: "Structure", "cohérence": "Consistency",
  completeness: "Completeness", validity: "Validity", uniqueness: "Uniqueness", integrity: "Consistency across tables",
  plausibility: "Plausibility", consistency: "Consistency",
};
export const SEVERITY = { blocking: ["Critical", "crit"], warning: ["To watch", "warn"], info: ["Information", "info"] };
export const ACTION = {
  conserver: "No action needed", signaler: "Flag to users", revue_humaine: "To be reviewed by a person",
  standardiser: "Standardize the formatting", dedoublonner: "Remove duplicates",
  agreger_avant_jointure: "Aggregate before joining the tables", completer_reference: "Complete the reference table",
  imputer: "Estimate the missing values", plafonner: "Cap extreme values to a limit",
  corriger_valeur: "Replace impossible values",
  keep: "No action needed", flag: "Flag to users", human_review: "To be reviewed by a person", standardize: "Standardize the formatting",
  deduplicate: "Remove duplicates", aggregate_before_join: "Aggregate before joining the tables",
  complete_reference: "Complete the reference table", impute: "Estimate the missing values", cap: "Cap extreme values to a limit",
  fix_value: "Replace impossible values",
};
export const CORRECTION = {
  strip_whitespace: ["Extra spaces removed", "Spaces at the start and end of values are removed."],
  normalize_missing: ["Empty values standardized", "\"NA\", \"null\", \"-\"… become real empty values."],
  harmonize_variants: ["Spellings harmonized", "Variants of the same value (case, accents) are unified."],
  drop_exact_duplicates: ["Duplicates removed", "Rows copied identically are kept only once."],
  impute_missing: ["Missing values filled in", "An empty cell gets the typical value of similar rows (median, or a category inferred from the other columns), otherwise \"Not provided\". An estimated value is flagged on its row."],
  replace_impossible: ["Impossible values replaced", "A negative value where it makes no sense is replaced by the typical value of similar rows."],
  cap_outliers: ["Extreme values capped", "A value very far from the others is brought back to its group's limit. The original value stays in the log."],
};
export const DECIDED_BY = {
  agent: "Decided by the AI", fallback: "Decided automatically from the test", LLM: "Analyzed by the AI",
  "politique (déblocage)": "Decided automatically from the test", "policy (unblocking)": "Decided automatically from the test",
};
export const QUALITY_STATUS = {
  ready: ["Data ready for analysis", "ok"],
  ready_with_warnings: ["Data ready, with a few points to watch", "ok"],
  blocked: ["Data blocked: a critical problem must be solved", "crit"],
};
export const HEALTH_COLS = {
  rows: "Rows", columns: "Columns", "missing_cells_%": "Missing values (%)", invalid_values: "Malformed values",
  unique_grain: "Unique identifier", exact_duplicates: "Duplicate rows", IF_anomalies: "Unusual rows", IQR_extremes: "Extreme values",
  table: "Table", lignes: "Rows", colonnes: "Columns", "cellules_manquantes_%": "Missing values (%)",
  valeurs_non_conformes: "Malformed values", grain_unique: "Unique identifier", doublons_exacts: "Duplicate rows",
  anomalies_IF: "Unusual rows", "extrêmes_IQR": "Extreme values",
};
export const SECTOR = {
  commerce: "Retail and e-commerce", "télécom": "Telecommunications", banque: "Banking and finance", transport: "Transport and mobility",
  telecom: "Telecommunications", banking: "Banking and finance",
};
export const KPI_STATUS = {
  "validé": ["Validated", "ok"], "validé (humain)": ["Validated", "ok"], "à confirmer": ["To confirm", "warn"],
  validated: ["Validated", "ok"], "validated (human)": ["Validated", "ok"], "to confirm": ["To confirm", "warn"],
};
export const RELIABILITY = {
  fiable: "reliable data", "à surveiller": "a few rows flagged", fragile: "many rows flagged",
  reliable: "reliable data", "to monitor": "a few rows flagged",
};
export const INSIGHT_TYPE = {
  alerte: ["Alert", "crit"], "opportunité": ["Opportunity", "ok"], constat: ["Finding", "info"],
  alert: ["Alert", "crit"], opportunity: ["Opportunity", "ok"], finding: ["Finding", "info"],
};
export const FACT_TYPE = {
  tendance: "Trend", "variation récente": "Recent change", "sur un an": "Year over year", anomalie: "Unusual month",
  rupture: "Level shift", segment: "Gap between segments", contribution: "Driver of a change", valeur: "Overall value",
  trend: "Trend", "recent change": "Recent change", "year over year": "Year over year", anomaly: "Unusual month",
  "level shift": "Level shift", value: "Overall value",
};
export const VALENCE = {
  favorable: "Favorable", "défavorable": "Unfavorable", neutre: "Neutral", unfavorable: "Unfavorable", neutral: "Neutral",
};

export function bindingLabel(source) {
  const s = String(source || "");
  if (s === "évidente" || s === "obvious") return "obvious columns, chosen automatically";
  if (s === "LLM") return "columns chosen by the AI, then verified";
  if (s === "proposée par l'agent" || s === "proposed by the agent") return "KPI proposed by the AI, computed and tested";
  return s.startsWith("repli") || s.startsWith("fallback") ? "chosen by the fallback rule" : s;
}

export function sectorText(bi) {
  const s = (bi && bi.sectors) || [];
  return s.length ? s.map((x) => SECTOR[x] || x).join(", ") : "Generic";
}

export function starName(name) {
  if (name === "dim_date") return ["Calendar", "Dimension"];
  if (name.startsWith("dim_")) return [name.slice(4), "Dimension"];
  if (name.startsWith("fact_")) return [name.slice(5), "Fact table"];
  return [name, ""];
}

export function testLabel(key) {
  if (key === "grain_unique") return "No duplicates";
  if (key === "row_count") return "No rows lost";
  if (key === "lineage_complete") return "Every row traces back to its source";
  if (key.startsWith("sum_")) return `Total "${key.slice(4)}" preserved`;
  if (key.startsWith("fk_")) return `Links "${key.slice(3).replace("_date_key", "")}" valid`;
  return null;
}

export function indicatorLabel(column, kind, calc) {
  let m = /^(.+)_to_(.+)_days$/.exec(String(column));
  if (m) return [`Delay between "${m[1]}" and "${m[2]}"`, "Number of days between the two dates, for each row."];
  m = /^(.+)_after_(.+)$/.exec(String(column));
  if (m) {
    const share = /\(([\d.,]+ ?%)/.exec(String(calc));
    return [`"${m[1]}" after "${m[2]}"`, "Equals 1 when the first date is later than the second (a delay, for example)" +
      (share ? `: this is the case for ${share[1]} of the rows.` : ".")];
  }
  return [String(column), String(calc)];
}

export function cleanDescription(text) {
  if (typeof text !== "string") return "";
  const t = text.replace(/\s*\([^()]*(rôle|role)\s*:[^()]*\)\s*$/, "").trim();
  return /^\d+ (lignes|rows), \d+ (colonnes|columns)$/.test(t) ? "" : t;
}

export function friendlyRule(description) {
  return String(description || "").replace(/^grain\s+/, "Identifier ").replace("(appris", "(learned rule").replace("FK", "link");
}

export const STATIONS = [
  ["Understanding", "reads your files and finds the tables and their links", "search"],
  ["Diagnosis", "checks the quality of every column", "activity"],
  ["Cleaning", "fixes what can be fixed safely", "sparkles"],
  ["Modeling", "builds and delivers the star schema", "star"],
  ["KPIs", "chooses, computes and verifies your business KPIs", "target"],
  ["Analysis", "detects what changes and writes the insights", "trend"],
  ["Dashboard", "assembles an interactive dashboard", "layout"],
];
const DONE_AT = [1, 3, 4, 6, 8, 9, 10];

export function stationStates(completed, status) {
  const n = STATIONS.length;
  let states = DONE_AT.map((s) => (completed >= s ? "done" : "todo"));
  if (status === "running") {
    const nxt = states.indexOf("todo");
    if (nxt >= 0) states[nxt] = "active";
  } else if (status === "blocked") {
    states = ["done", "done", "error", ...Array(n - 3).fill("todo")];
  } else if (status === "failed" || status === "interrupted") {
    const nxt = states.indexOf("todo");
    states[nxt >= 0 ? nxt : n - 1] = "error";
  } else if (status === "success") {
    states = Array(n).fill("done");
  }
  return states;
}
