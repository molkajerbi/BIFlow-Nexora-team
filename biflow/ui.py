"""Identité visuelle et composants HTML de l'interface BIFlow (vocabulaire métier, sans jargon technique)."""
from __future__ import annotations

import html as _html
import math
import re
from string import Template

# ---------------------------------------------------------------- palette
INK, MUTED, LINE, BG, SURFACE = "#101A2C", "#5B6478", "#E4E8EF", "#F4F6FA", "#FFFFFF"
TEAL, TEAL_DARK, TEAL_SOFT = "#00897B", "#00695F", "#E3F4F1"
RAW = "#D08A2E"                                   # données brutes (« avant ») ; TEAL = données préparées (« après »)
WARN, WARN_SOFT, CRIT, CRIT_SOFT, INFO, INFO_SOFT = "#9A5B00", "#FFF4E0", "#B42318", "#FDECEA", "#3554C4", "#EAF0FF"


def esc(x) -> str:
    return _html.escape("" if x is None else str(x))


def h(markup: str) -> str:
    """HTML compact pour st.markdown : pas d'indentation (sinon Markdown en ferait un bloc de code), pas de ligne vide."""
    return "\n".join(line.strip() for line in markup.splitlines() if line.strip())


def plural(n, singular: str, plural_form: str | None = None) -> str:
    try:
        k = int(n)
    except (TypeError, ValueError):
        return f"— {plural_form or singular + 's'}"
    return f"{fmt_int(k)} {singular if k <= 1 else (plural_form or singular + 's')}"


def human_text(text) -> str:
    """Garde une justification de l'IA seulement si elle est rédigée pour un humain (pas de code ni de dictionnaire)."""
    if not isinstance(text, str) or not text.strip():
        return ""
    if re.search(r"[{}\[\]]|_[a-z]|->|fallback|superviseur", text):
        return ""
    return text.strip()


def show_value(v, quoted: bool = False) -> str:
    """Une valeur avant / après correction, lisible : « vide », un nombre sans décimales inutiles, ou un texte."""
    if v is None or (isinstance(v, float) and math.isnan(v)):
        return "vide"
    if isinstance(v, str) and re.fullmatch(r"-?\d+(\.\d+)?", v.strip()):
        v = float(v)                                  # nombre relu depuis un fichier : même écriture que les autres
    if isinstance(v, (int, float)):
        return f"{v:,.2f}".replace(",", " ").replace(".", ",").rstrip("0").rstrip(",")
    return repr(v) if quoted and isinstance(v, str) else str(v)


def fmt_int(n) -> str:
    try:
        return f"{int(n):,}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


# ---------------------------------------------------------------- vocabulaire
SEM_TYPE = {"id": "Identifiant", "category": "Catégorie", "datetime": "Date", "numeric": "Montant / mesure",
            "integer": "Nombre entier", "text": "Texte libre", "zip": "Code postal", "geo": "Coordonnée GPS"}
DIMENSION = {"complétude": "Complétude", "validité": "Validité", "format": "Mise en forme", "unicité": "Unicité",
             "intégrité": "Cohérence entre tables", "plausibilité": "Vraisemblance", "structure": "Structure",
             "cohérence": "Cohérence"}
SEVERITY = {"blocking": ("Critique", "crit"), "warning": ("À surveiller", "warn"), "info": ("Information", "info")}
ACTION = {"conserver": "Aucune action nécessaire", "signaler": "Signaler aux utilisateurs",
          "revue_humaine": "À examiner par une personne", "standardiser": "Uniformiser la mise en forme",
          "dedoublonner": "Supprimer les doublons", "agreger_avant_jointure": "Regrouper avant de croiser les tables",
          "completer_reference": "Compléter le référentiel",
          "imputer": "Estimer les valeurs manquantes", "plafonner": "Ramener les valeurs extrêmes à une limite",
          "corriger_valeur": "Remplacer les valeurs impossibles"}
CORRECTION = {"strip_whitespace": ("Espaces superflus retirés", "Les espaces en début et en fin de valeur sont supprimés."),
              "normalize_missing": ("Valeurs vides uniformisées", "« NA », « null », « - »… deviennent de vraies valeurs vides."),
              "harmonize_variants": ("Orthographes harmonisées", "Les variantes d'une même valeur (casse, accents) sont unifiées."),
              "drop_exact_duplicates": ("Doublons supprimés", "Les lignes copiées à l'identique ne sont gardées qu'une fois."),
              "impute_missing": ("Valeurs manquantes complétées", "Une case vide reçoit la valeur typique des lignes semblables "
                                 "(médiane, ou catégorie déduite des autres colonnes), sinon « Non renseigné ». "
                                 "Une valeur estimée est marquée sur sa ligne."),
              "replace_impossible": ("Valeurs impossibles remplacées", "Une valeur négative là où elle n'a pas de sens est "
                                     "remplacée par la valeur typique des lignes semblables."),
              "cap_outliers": ("Valeurs extrêmes plafonnées", "Une valeur très éloignée des autres est ramenée à la limite "
                               "haute ou basse de son groupe. La valeur d'origine reste dans le journal.")}
DECIDED_BY = {"agent": "Décidé par l'IA", "fallback": "Décidé automatiquement d'après le test", "LLM": "Analysé par l'IA",
              "politique (déblocage)": "Décidé automatiquement d'après le test"}
QUALITY_STATUS = {"ready": ("Données prêtes pour l'analyse", "ok"),
                  "ready_with_warnings": ("Données prêtes, avec quelques points à surveiller", "ok"),
                  "blocked": ("Données bloquées : un problème critique doit être résolu", "crit")}
HEALTH_COLS = {"table": "Table", "lignes": "Lignes", "colonnes": "Colonnes", "cellules_manquantes_%": "Valeurs manquantes (%)",
               "valeurs_non_conformes": "Valeurs mal formées",
               "grain_unique": "Identifiant unique", "doublons_exacts": "Lignes en double",
               "anomalies_IF": "Lignes atypiques", "extrêmes_IQR": "Valeurs extrêmes"}


HEALTH_HELP = {
    "Valeurs manquantes (%)": "Part des cases vides dans la table, toutes colonnes confondues.",
    "Valeurs mal formées": "Valeurs qui ne respectent pas le format attendu : une date illisible, du texte dans une colonne de nombres…",
    "Identifiant unique": "Oui si chaque ligne a un identifiant différent ; « — » si la table n'a pas d'identifiant.",
    "Lignes en double": "Lignes copiées à l'identique.",
    "Lignes atypiques": "Lignes dont la combinaison de valeurs est inhabituelle par rapport aux autres (détection automatique).",
    "Valeurs extrêmes": "Valeurs très éloignées des valeurs habituelles de leur colonne (plus de 3 fois l'écart normal).",
}


def test_label(key: str) -> str | None:
    if key == "grain_unique":
        return "Aucun doublon"
    if key == "row_count":
        return "Aucune ligne perdue"
    if key == "lineage_complete":
        return "Chaque ligne retrouve sa source"
    if key.startswith("sum_"):
        return f"Total « {key[4:]} » conservé"
    if key.startswith("fk_"):
        return f"Liens « {key[3:].replace('_date_key', '')} » valides"
    return None


def star_name(name: str) -> tuple[str, str]:
    """dim_customers -> ('customers', 'Axe d'analyse') ; fact_orders -> ('orders', 'Table de faits')."""
    if name == "dim_date":
        return "Calendrier", "Axe d'analyse"
    if name.startswith("dim_"):
        return name[4:], "Axe d'analyse"
    if name.startswith("fact_"):
        return name[5:], "Table de faits"
    return name, ""


def clean_description(text) -> str:
    """Description métier rédigée par l'IA, sans le rappel technique « (N lignes, rôle : …) » ajouté par le moteur."""
    if not isinstance(text, str):
        return ""
    text = re.sub(r"\s*\([^()]*rôle\s*:[^()]*\)\s*$", "", text).strip()
    return "" if re.fullmatch(r"\d+ lignes, \d+ colonnes", text) else text


def indicator_label(column: str, kind: str, calc: str) -> tuple[str, str]:
    """Nom lisible d'un indicateur calculé à partir des dates, et sa signification."""
    m = re.fullmatch(r"(.+)_to_(.+)_days", str(column))
    if m:
        return (f"Délai entre « {m.group(1)} » et « {m.group(2)} »",
                "Nombre de jours écoulés entre les deux dates, pour chaque ligne.")
    m = re.fullmatch(r"(.+)_after_(.+)", str(column))
    if m:
        share = re.search(r"\(([\d.,]+ ?%)", str(calc))
        return (f"« {m.group(1)} » après « {m.group(2)} »",
                "Vaut 1 quand la première date dépasse la seconde (un retard, par exemple)"
                + (f" : c'est le cas de {share.group(1)} des lignes." if share else "."))
    return str(column), str(calc)


def friendly_rule(description: str) -> str:
    text = re.sub(r"^grain\s+", "Identifiant ", str(description))
    return text.replace("(appris", "(règle apprise").replace("FK", "lien")


# ---------------------------------------------------------------- icônes (traits simples, couleur = texte courant)
_ICON_PATHS = {
    "check": '<path d="M20 6 9 17l-5-5"/>',
    "check-circle": '<circle cx="12" cy="12" r="10"/><path d="m8.5 12.5 2.5 2.5 5-5.5"/>',
    "alert": '<path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z"/>'
             '<path d="M12 9v4"/><path d="M12 17h.01"/>',
    "x-circle": '<circle cx="12" cy="12" r="10"/><path d="m15 9-6 6"/><path d="m9 9 6 6"/>',
    "info": '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/>',
    "clock": '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "sparkles": '<path d="M12 3l1.8 5.4L19 10l-5.2 1.6L12 17l-1.8-5.4L5 10l5.2-1.6Z"/><path d="M19 17v4M17 19h4"/>',
    "star": '<path d="M12 2.5l2.9 6 6.6.9-4.8 4.6 1.2 6.5L12 17.4l-5.9 3.1 1.2-6.5-4.8-4.6 6.6-.9Z"/>',
    "shield": '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/>',
    "database": '<ellipse cx="12" cy="5" rx="8" ry="3"/><path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5"/>'
                '<path d="M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>',
    "lock": '<rect x="4" y="11" width="16" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>',
    "file": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><path d="M14 2v6h6"/>',
    "calendar": '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
    "cpu": '<rect x="5" y="5" width="14" height="14" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/>'
           '<path d="M9 2v3M15 2v3M9 19v3M15 19v3M19 9h3M19 15h3M2 9h3M2 15h3"/>',
    "layers": '<path d="m12 2 10 5-10 5L2 7Z"/><path d="m2 17 10 5 10-5"/><path d="m2 12 10 5 10-5"/>',
    "route": '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/>'
             '<circle cx="18" cy="5" r="3"/>',
    "inbox": '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6'
             'l-3.5-6.9A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.7 1.1Z"/>',
    "folder": '<path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.7-.9l-.8-1.2A2 2 0 0 0 7.9 3H4'
              'a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z"/>',
    "upload": '<path d="M12 16V4"/><path d="m6 10 6-6 6 6"/><path d="M4 16v3a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-3"/>',
    "chart": '<path d="M3 3v18h18"/><path d="M7 15l4-4 3 3 5-6"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1.5"/>',
    "trend": '<path d="m3 17 6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "layout": '<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M3 9h18M9 21V9"/>',
    "message": '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2Z"/><path d="M8 9h8M8 13h5"/>',
    "download": '<path d="M12 4v12"/><path d="m6 10 6 6 6-6"/><path d="M4 20h16"/>',
}


def icon(name: str, size: int = 18, stroke: float = 2) -> str:
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
            f'{_ICON_PATHS.get(name, _ICON_PATHS["info"])}</svg>')


# ---------------------------------------------------------------- feuille de style
_CSS = Template("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
:root { --ink:$INK; --muted:$MUTED; --line:$LINE; --bg:$BG; --surface:$SURFACE; --teal:$TEAL; --teal-dark:$TEAL_DARK;
  --teal-soft:$TEAL_SOFT; --shadow-sm:0 1px 2px rgba(16,26,44,.05); --shadow:0 1px 2px rgba(16,26,44,.04), 0 8px 24px -12px rgba(16,26,44,.14);
  --shadow-lg:0 2px 4px rgba(16,26,44,.04), 0 18px 40px -18px rgba(16,26,44,.28); }
html, body, .stApp, .stMarkdown, p, li, label, h1, h2, h3, h4, button, input, textarea, select,
[data-testid="stMarkdownContainer"], [data-baseweb="select"] { font-family: 'Manrope', system-ui, -apple-system, 'Segoe UI', sans-serif; }
/* les icônes de Streamlit gardent leur police d'icônes */
[data-testid="stIconMaterial"], .material-symbols-rounded, span[class*="material-symbols"] {
  font-family: 'Material Symbols Rounded' !important; }
header[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer, [data-testid="stDecoration"],
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] { display: none !important; }
.stApp { background: radial-gradient(1200px 420px at 85% -120px, rgba(0,137,123,.09), transparent 70%), $BG; color: $INK; }
.block-container { max-width: 1200px; padding-top: 1.1rem; padding-bottom: 3rem; }
h1, h2, h3, h4 { color: $INK; letter-spacing: -0.015em; }
::selection { background: $TEAL_SOFT; }

/* ---------- boutons */
.stButton > button, [data-testid="stDownloadButton"] > button, [data-testid="stFormSubmitButton"] > button {
  border-radius: 12px; font-weight: 700; padding: .58rem 1.25rem; border: 1px solid $LINE; min-height: 2.6rem;
  background: $SURFACE; color: $INK; box-shadow: var(--shadow-sm);
  transition: background .15s, border-color .15s, box-shadow .15s, transform .15s; }
.stButton > button:hover, [data-testid="stDownloadButton"] > button:hover {
  border-color: $TEAL; color: $TEAL_DARK; box-shadow: var(--shadow); transform: translateY(-1px); }
.stButton > button:active, [data-testid="stDownloadButton"] > button:active { transform: translateY(0); }
.stButton > button:focus-visible, [data-testid="stDownloadButton"] > button:focus-visible,
[data-testid="stFormSubmitButton"] > button:focus-visible { outline: 3px solid ${TEAL}55; outline-offset: 2px; }
button[kind="primary"], [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: linear-gradient(180deg, #0A9A8B 0%, $TEAL 100%) !important; border-color: $TEAL_DARK !important;
  color: #fff !important; box-shadow: 0 1px 0 rgba(255,255,255,.18) inset, 0 8px 20px -10px $TEAL !important; }
button[kind="primary"]:hover, [data-testid="stBaseButton-primary"]:hover,
[data-testid="stBaseButton-primaryFormSubmit"]:hover { background: $TEAL_DARK !important; color: #fff !important; }
button[kind="primary"] p, [data-testid="stBaseButton-primary"] p { color: #fff !important; }
button[kind="tertiary"], [data-testid="stBaseButton-tertiary"] { background: transparent !important; border: none !important;
  box-shadow: none !important; color: $MUTED !important; }
button[kind="tertiary"]:hover, [data-testid="stBaseButton-tertiary"]:hover { color: $CRIT !important; transform: none !important; }
button:disabled { opacity: .45; box-shadow: none !important; transform: none !important; }

/* ---------- champs de saisie */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"] {
  border-radius: 12px !important; border-color: $LINE !important; background: $SURFACE !important; }
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within { border-color: $TEAL !important;
  box-shadow: 0 0 0 3px ${TEAL}22 !important; }
[data-testid="stWidgetLabel"] p, .stTextInput label p, .stSelectbox label p { font-weight: 700; font-size: .88rem; color: $INK; }

/* ---------- zone de dépôt */
[data-testid="stFileUploader"] > label { display:none; }
[data-testid="stFileUploaderDropzone"], section[data-testid="stFileUploadDropzone"] {
  border: 2px dashed ${TEAL}66; background: $SURFACE; border-radius: 0 0 22px 22px; border-top: none;
  padding: 1rem 1.6rem 1.8rem; justify-content: center; transition: background .15s; }
[data-testid="stFileUploaderDropzone"]:hover { background: #F7FCFB; }
[data-testid="stFileUploaderDropzone"] button { border-radius: 10px !important; border: 1px solid $TEAL !important;
  color: $TEAL_DARK !important; font-weight: 700 !important; background: $SURFACE !important; }
[data-testid="stFileUploaderFile"] { background: $TEAL_SOFT; border-radius: 12px; padding: .35rem .7rem; }
.bf-drop { border: 2px dashed ${TEAL}66; border-bottom: none; border-radius: 22px 22px 0 0; background: $SURFACE;
  padding: 2rem 1.6rem .3rem; text-align: center; margin-top: .2rem; }
.bf-drop .ico { width:64px; height:64px; border-radius:20px; margin:0 auto .9rem; color:$TEAL_DARK;
  background: linear-gradient(145deg, $TEAL_SOFT, #CDEDE7); display:flex; align-items:center; justify-content:center;
  box-shadow: 0 10px 24px -14px $TEAL; }
.bf-drop b { display:block; font-size:1.2rem; font-weight:800; color:$INK; }
.bf-drop span { color:$MUTED; font-size:.93rem; }
.bf-formats { display:flex; gap:.4rem; justify-content:center; flex-wrap:wrap; margin-top:.9rem; }
.bf-formats i { font-style:normal; font-size:.74rem; font-weight:700; color:$MUTED; background:$BG;
  border:1px solid $LINE; padding:.16rem .6rem; border-radius:999px; }

/* ---------- onglets */
[data-baseweb="tab-list"], [data-testid="stTabs"] [role="tablist"] { gap: .25rem; border-bottom: none !important;
  box-shadow: var(--shadow-sm) !important; flex-wrap: wrap; margin: .2rem 0 .8rem; background: $SURFACE;
  border: 1px solid $LINE; border-radius: 16px; padding: .3rem; width: fit-content; max-width: 100%; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"],
[data-testid="stTabs"] [role="tablist"] + div:empty { display: none !important; }
button[data-baseweb="tab"], [data-testid="stTabs"] [role="tab"] { border-radius: 12px !important;
  padding: .5rem 1.05rem !important; background: transparent !important; border: none !important;
  height: auto !important; margin: 0 !important; box-shadow: none !important; transition: background .15s; }
button[data-baseweb="tab"] p, [data-testid="stTabs"] [role="tab"] p { font-weight: 700; font-size: .9rem; color: $MUTED; }
button[data-baseweb="tab"]:hover, [data-testid="stTabs"] [role="tab"]:hover { background: $BG !important; }
button[data-baseweb="tab"]:hover p, [data-testid="stTabs"] [role="tab"]:hover p { color: $INK; }
button[data-baseweb="tab"][aria-selected="true"], [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
  background: $INK !important; box-shadow: 0 6px 16px -8px $INK !important; }
button[data-baseweb="tab"][aria-selected="true"] p, [data-testid="stTabs"] [role="tab"][aria-selected="true"] p { color: #fff !important; }

/* ---------- conteneurs Streamlit */
[data-testid="stExpander"] details { border-radius: 14px; border-color: $LINE; background: $SURFACE; box-shadow: var(--shadow-sm); }
[data-testid="stExpander"] summary p { font-weight: 700; }
[data-testid="stDataFrame"] { border-radius: 14px; overflow: hidden; border: 1px solid $LINE; box-shadow: var(--shadow-sm); background: $SURFACE; }
[data-testid="stForm"] { border-radius: 18px; border-color: $LINE; background: $SURFACE; box-shadow: var(--shadow); }
[data-testid="stCaptionContainer"] { color: $MUTED; }

/* ---------- barre du haut */
.bf-brand { display:flex; align-items:center; gap:.75rem; }
.bf-brand b { font-size:1.3rem; font-weight:800; letter-spacing:-.03em; color:$INK; }
.bf-brand b em { font-style:normal; color:$TEAL; }
.bf-brand span { color:$MUTED; font-size:.82rem; font-weight:600; }
.bf-brand .tag { margin-left:.4rem; font-size:.68rem; font-weight:800; letter-spacing:.06em; text-transform:uppercase;
  color:$TEAL_DARK; background:$TEAL_SOFT; border-radius:999px; padding:.12rem .5rem; vertical-align:3px; }
.bf-topline { height:1px; background:linear-gradient(90deg, transparent, $LINE 12%, $LINE 88%, transparent); margin:.5rem 0 .2rem; }

/* ---------- héros (page d'accueil) */
.bf-hero { position:relative; overflow:hidden; display:grid; grid-template-columns: 1.35fr 1fr; gap:2.2rem; align-items:center;
  margin:1.1rem 0 1.6rem; padding:2.6rem 2.6rem; border-radius:28px; color:#fff;
  background: radial-gradient(600px 300px at 100% 0%, rgba(0,191,165,.35), transparent 65%),
              radial-gradient(500px 260px at 0% 110%, rgba(61,90,254,.22), transparent 60%),
              linear-gradient(135deg, #0E1A2E 0%, #13243B 55%, #0C2A33 100%);
  box-shadow: var(--shadow-lg); }
.bf-hero::after { content:""; position:absolute; inset:0; pointer-events:none; opacity:.35;
  background-image: radial-gradient(rgba(255,255,255,.18) 1px, transparent 1px); background-size: 22px 22px;
  mask-image: linear-gradient(90deg, transparent 40%, #000); -webkit-mask-image: linear-gradient(90deg, transparent 40%, #000); }
.bf-hero > * { position:relative; z-index:1; }
.bf-eyebrow { display:inline-flex; align-items:center; gap:.45rem; font-size:.75rem; font-weight:800; letter-spacing:.08em;
  text-transform:uppercase; color:#7FE3D5; background:rgba(0,191,165,.12); border:1px solid rgba(127,227,213,.25);
  border-radius:999px; padding:.3rem .75rem; }
.bf-hero h1 { color:#fff; font-size:2.65rem; line-height:1.1; font-weight:800; margin:1rem 0 .9rem; letter-spacing:-.03em; }
.bf-hero h1 span { background: linear-gradient(90deg, #5EEAD4, #34D3BE); -webkit-background-clip:text; background-clip:text; color:transparent; }
.bf-hero p { font-size:1.04rem; color:#B9C4D6; line-height:1.65; margin:0; max-width:560px; }
.bf-trust { display:flex; flex-wrap:wrap; gap:.5rem 1.2rem; margin-top:1.4rem; }
.bf-trust span { display:inline-flex; align-items:center; gap:.4rem; font-size:.86rem; font-weight:700; color:#DCE4F0; }
.bf-trust svg { color:#5EEAD4; }
.bf-deliver { background: rgba(255,255,255,.06); border:1px solid rgba(255,255,255,.12); border-radius:20px; padding:1.1rem;
  backdrop-filter: blur(6px); }
.bf-deliver > small { display:block; font-size:.72rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase;
  color:#8FA0B8; margin:0 0 .7rem .2rem; }
.bf-deliver div.it { display:flex; gap:.8rem; align-items:center; padding:.65rem .7rem; border-radius:14px; }
.bf-deliver div.it + div.it { border-top:1px solid rgba(255,255,255,.07); }
.bf-deliver i { flex:0 0 38px; height:38px; border-radius:12px; display:flex; align-items:center; justify-content:center;
  background: rgba(94,234,212,.14); color:#5EEAD4; }
.bf-deliver b { display:block; color:#fff; font-size:.95rem; }
.bf-deliver span { display:block; color:#93A3BA; font-size:.8rem; }

/* ---------- titres de section */
.bf-section { display:flex; align-items:center; gap:.6rem; font-size:1.18rem; font-weight:800; margin: 2rem 0 .5rem; color:$INK;
  letter-spacing:-.015em; }
.bf-section::before { content:""; width:4px; height:1.15rem; border-radius:4px; background: linear-gradient(180deg, #2BC4B0, $TEAL); }
.bf-lead { color:$MUTED; margin:0 0 1rem; line-height:1.6; max-width: 820px; font-size:.95rem; }
.bf-page { padding:1.6rem 0 .6rem; }
.bf-page h1 { font-size:2rem; font-weight:800; margin:0; letter-spacing:-.03em; }
.bf-page p { color:$MUTED; margin:.35rem 0 0; }
.bf-muted { color:$MUTED; }

/* ---------- chaîne d'étapes */
.bf-chain { display:grid; grid-template-columns: repeat(7, 1fr); margin: .6rem 0 1.2rem; padding:1.5rem .4rem 1.3rem;
  background:$SURFACE; border:1px solid $LINE; border-radius:22px; box-shadow: var(--shadow); }
.bf-station { position:relative; padding: 0 .45rem; text-align:center; }
.bf-station::before { content:""; position:absolute; top:25px; left:calc(-50% + 30px); width:calc(100% - 60px); height:3px;
  border-radius:3px; background:$LINE; }
.bf-station:first-child::before { display:none; }
.bf-station.done::before, .bf-station.error::before, .bf-station.wait::before { background:$TEAL; }
.bf-station.active::before { background: linear-gradient(90deg, $TEAL, ${TEAL}55); }
.bf-dot { position:relative; z-index:1; width:52px; height:52px; margin:0 auto .7rem; border-radius:16px;
  display:flex; align-items:center; justify-content:center; background:$BG; border:1.5px solid $LINE; color:#97A1B3;
  transition: all .2s; }
.bf-station.done .bf-dot { background: linear-gradient(145deg, #12A493, $TEAL); border-color:$TEAL; color:#fff;
  box-shadow: 0 8px 18px -10px $TEAL; }
.bf-station.active .bf-dot { background:$SURFACE; border:2px solid $TEAL; color:$TEAL_DARK; animation: bf-pulse 1.8s ease-in-out infinite; }
.bf-station.wait .bf-dot { border-color:$WARN; color:$WARN; background:$WARN_SOFT; }
.bf-station.error .bf-dot { border-color:$CRIT; color:$CRIT; background:$CRIT_SOFT; }
.bf-station b { display:block; font-size:.98rem; font-weight:800; color:$INK; }
.bf-station small { display:block; color:$MUTED; font-size:.8rem; line-height:1.4; margin-top:.2rem; min-height:2.8em; }
.bf-station em { display:inline-flex; align-items:center; gap:.3rem; margin-top:.55rem; font-style:normal; font-size:.72rem;
  font-weight:800; letter-spacing:.02em; color:$MUTED; background:$BG; border-radius:999px; padding:.15rem .6rem; }
.bf-station.done em { color:$TEAL_DARK; background:$TEAL_SOFT; }
.bf-station.active em { color:#fff; background:$TEAL; }
.bf-station.wait em { color:$WARN; background:$WARN_SOFT; } .bf-station.error em { color:$CRIT; background:$CRIT_SOFT; }
@keyframes bf-pulse { 0%,100% { box-shadow:0 0 0 4px ${TEAL}22; } 50% { box-shadow:0 0 0 11px ${TEAL}0D; } }
@media (prefers-reduced-motion: reduce) { .bf-station.active .bf-dot { animation:none; } }

/* ---------- en-tête d'une analyse */
.bf-job { padding: 1.4rem 0 .2rem; }
.bf-crumb { display:flex; align-items:center; gap:.4rem; font-size:.8rem; font-weight:700; color:$MUTED; letter-spacing:.02em; }
.bf-crumb svg { color:$TEAL; }
.bf-job h2 { margin:.35rem 0 0; font-size:1.95rem; font-weight:800; letter-spacing:-.03em; line-height:1.15; overflow-wrap:anywhere; }
.bf-job .facts { display:flex; flex-wrap:wrap; gap:.4rem 1.1rem; margin-top:.55rem; }
.bf-job .facts span { display:inline-flex; align-items:center; gap:.4rem; color:$MUTED; font-size:.86rem; font-weight:600; }
.bf-chip { display:inline-flex; align-items:center; gap:.65rem; padding:.45rem .95rem; border-radius:999px;
  background:$SURFACE; border:1px solid $LINE; font-size:.84rem; font-weight:700; color:$MUTED; box-shadow: var(--shadow-sm); }
.bf-chipline { display:flex; justify-content:flex-end; margin:.2rem 0 -.2rem; }
.bf-chip .led { width:8px; height:8px; border-radius:50%; background:#97A1B3; }
.bf-chip.running .led { background:$TEAL; box-shadow:0 0 0 4px ${TEAL}22; animation: bf-blink 1.4s ease-in-out infinite; }
.bf-chip.success .led { background:$TEAL; } .bf-chip.crit .led { background:$CRIT; } .bf-chip.warn .led { background:$WARN; }
.bf-chip b { color:$INK; font-variant-numeric: tabular-nums; }
.bf-chip i { display:block; width:110px; height:6px; border-radius:9px; background:$LINE; overflow:hidden; }
.bf-chip i span { display:block; height:100%; background: linear-gradient(90deg, #2BC4B0, $TEAL); border-radius:9px; transition: width .6s; }
@keyframes bf-blink { 50% { opacity:.45; } }

/* ---------- indicateurs chiffrés */
.bf-kpis { display:grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap:.9rem; margin:.5rem 0 1.1rem; }
.bf-kpi { position:relative; overflow:hidden; background:$SURFACE; border:1px solid $LINE; border-radius:18px; padding:1.1rem 1.2rem 1rem;
  box-shadow: var(--shadow); }
.bf-kpi small { display:block; color:$MUTED; font-size:.78rem; font-weight:800; letter-spacing:.04em; text-transform:uppercase; }
.bf-kpi b { display:block; font-size:1.85rem; font-weight:800; margin:.35rem 0 .15rem; color:$INK; letter-spacing:-.02em;
  font-variant-numeric: tabular-nums; line-height:1.15; }
.bf-kpi span { color:$MUTED; font-size:.82rem; }
.bf-kpi.long b { font-size:1.12rem; line-height:1.35; letter-spacing:-.005em; }
.bf-kpi.accent { border-color:transparent; color:#fff;
  background: radial-gradient(260px 140px at 100% 0%, rgba(0,191,165,.38), transparent 70%), linear-gradient(135deg, #0E1A2E, #15283F); }
.bf-kpi.accent small { color:#8FE3D6; } .bf-kpi.accent span { color:#AAB6C8; } .bf-kpi.accent b { color:#fff; }

/* ---------- badges */
.bf-badge { display:inline-flex; align-items:center; gap:.35rem; padding:.2rem .62rem; border-radius:999px;
  font-size:.74rem; font-weight:800; white-space:nowrap; letter-spacing:.01em; }
.bf-badge.dot::before { content:""; width:6px; height:6px; border-radius:50%; background:currentColor; }
.bf-badge.ok { background:$TEAL_SOFT; color:$TEAL_DARK; } .bf-badge.warn { background:$WARN_SOFT; color:$WARN; }
.bf-badge.crit { background:$CRIT_SOFT; color:$CRIT; } .bf-badge.info { background:$INFO_SOFT; color:$INFO; }
.bf-badge.neutral { background:#EEF1F6; color:$MUTED; }

/* ---------- cartes */
.bf-grid { display:grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap:.9rem; }
.bf-card { position:relative; background:$SURFACE; border:1px solid $LINE; border-radius:18px; padding:1.05rem 1.2rem 1rem;
  box-shadow: var(--shadow-sm); transition: box-shadow .18s, transform .18s, border-color .18s; }
.bf-card:hover { box-shadow: var(--shadow); transform: translateY(-2px); border-color:#D3D9E3; }
.bf-card:has(.bf-badge.crit) { box-shadow: inset 4px 0 0 $CRIT, var(--shadow-sm); }
.bf-card:has(.bf-badge.warn) { box-shadow: inset 4px 0 0 #E0A14A, var(--shadow-sm); }
.bf-card:has(.bf-badge.ok) { box-shadow: inset 4px 0 0 $TEAL, var(--shadow-sm); }
.bf-card h4 { margin:0 0 .35rem; font-size:1rem; font-weight:800; letter-spacing:-.01em; }
.bf-card p { margin:.35rem 0 0; color:#2A3447; line-height:1.55; font-size:.93rem; }
.bf-card .meta { color:$MUTED; font-size:.8rem; margin-top:.7rem; padding-top:.6rem; border-top:1px dashed $LINE; line-height:1.55; }
.bf-card .row { display:flex; justify-content:space-between; align-items:flex-start; gap:.4rem .6rem; flex-wrap:wrap; }
.bf-card h4, .bf-card .meta, .bf-card p { overflow-wrap:anywhere; min-width:0; }
.bf-swap { display:flex; align-items:center; gap:.5rem; margin-top:.7rem; font-size:.84rem; flex-wrap:wrap; color:$MUTED; }
.bf-swap code { background:#FBF3E6; color:#7A4A0E; padding:.15rem .5rem; border-radius:8px; font-family:inherit; font-weight:600; }
.bf-swap code.after { background:$TEAL_SOFT; color:$TEAL_DARK; }

/* ---------- bandeaux */
.bf-banner { border-radius:18px; padding:1.05rem 1.25rem; display:flex; gap:.95rem; align-items:flex-start; margin:.7rem 0 1.1rem;
  border:1px solid transparent; }
.bf-banner .ico { flex:0 0 38px; height:38px; border-radius:12px; display:flex; align-items:center; justify-content:center; }
.bf-banner.ok { background:#EEF8F6; border-color:#CBEAE4; } .bf-banner.ok .ico { background:$TEAL; color:#fff; }
.bf-banner.warn { background:#FFF8EC; border-color:#F6DFB5; } .bf-banner.warn .ico { background:#E0A14A; color:#fff; }
.bf-banner.crit { background:#FEF2F1; border-color:#F7CFCB; } .bf-banner.crit .ico { background:$CRIT; color:#fff; }
.bf-banner.info { background:#F1F5FF; border-color:#D5DFFB; } .bf-banner.info .ico { background:$INFO; color:#fff; }
.bf-banner b { display:block; font-size:1rem; font-weight:800; margin-top:.05rem; } .bf-banner span { color:#4A5468; font-size:.92rem; line-height:1.55; }

/* ---------- état vide */
.bf-empty { text-align:center; padding:2.6rem 1rem; color:$MUTED; background:$SURFACE; border:1.5px dashed $LINE; border-radius:20px; }
.bf-empty .ico { width:52px; height:52px; border-radius:16px; margin:0 auto .8rem; display:flex; align-items:center;
  justify-content:center; background:$BG; color:#97A1B3; }
.bf-empty b { display:block; color:$INK; font-size:1.05rem; margin-bottom:.3rem; }

/* ---------- légendes, schémas */
.bf-legend { display:flex; gap:1.3rem; font-size:.85rem; color:$MUTED; margin:.4rem 0 .2rem; font-weight:600; }
.bf-legend i { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:.4rem; vertical-align:-1px; }
.bf-star { background:$SURFACE; border:1px solid $LINE; border-radius:20px; padding:.9rem; overflow-x:auto; box-shadow: var(--shadow); }

/* ---------- diagnostic : synthèse */
.bf-findings { display:grid; grid-template-columns: 190px 1fr; gap:1.6rem; align-items:center; background:$SURFACE;
  border:1px solid $LINE; border-radius:20px; padding:1.4rem 1.6rem; margin:.4rem 0 1.1rem; box-shadow: var(--shadow); }
.bf-findings .big { border-right:1px solid $LINE; padding-right:1.2rem; }
.bf-findings .big b { display:block; font-size:3.1rem; font-weight:800; line-height:1; color:$INK; letter-spacing:-.04em; }
.bf-findings .big span { color:$MUTED; font-size:.85rem; font-weight:600; }
.bf-bar { display:flex; gap:3px; height:12px; border-radius:99px; overflow:hidden; background:$LINE; }
.bf-leg { display:grid; grid-template-columns: repeat(3, minmax(0,1fr)); gap:.6rem; margin:.9rem 0 .7rem; font-size:.9rem; }
.bf-leg > div { background:$BG; border-radius:12px; padding:.55rem .75rem; }
.bf-leg i { display:inline-block; width:10px; height:10px; border-radius:3px; margin-right:.4rem; }
.bf-leg small { display:block; color:$MUTED; font-size:.77rem; margin-left:1.05rem; }
.bf-findings p { margin:0; color:$MUTED; font-size:.85rem; line-height:1.55; }

/* ---------- cartes « agents » */
.bf-agents { display:grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap:.9rem; margin:.4rem 0 1.1rem; }
.bf-agent { position:relative; display:flex; flex-direction:column; gap:.55rem; background:$SURFACE; border:1px solid $LINE;
  border-radius:18px; padding:1.1rem 1.15rem; box-shadow: var(--shadow-sm); }
.bf-agent.done { box-shadow: var(--shadow); }
.bf-agent .top { display:flex; align-items:center; gap:.6rem; }
.bf-agent em { font-style:normal; flex:0 0 34px; height:34px; border-radius:11px; display:flex; align-items:center;
  justify-content:center; background:$BG; color:#97A1B3; }
.bf-agent.done em { background: linear-gradient(145deg, #12A493, $TEAL); color:#fff; }
.bf-agent small { color:$MUTED; font-size:.75rem; font-weight:800; letter-spacing:.05em; text-transform:uppercase; }
.bf-agent b { display:block; font-size:1.08rem; font-weight:800; color:$INK; letter-spacing:-.01em; }
.bf-agent span { color:$MUTED; font-size:.84rem; line-height:1.45; }
.bf-agent.todo b { color:#97A1B3; }

/* ---------- liste des analyses */
.bf-row { display:flex; align-items:center; gap:1rem; background:$SURFACE; border:1px solid $LINE; border-radius:16px;
  padding:.8rem 1rem; box-shadow: var(--shadow-sm); }
.bf-row .ico { flex:0 0 42px; height:42px; border-radius:12px; display:flex; align-items:center; justify-content:center;
  background:$BG; color:$MUTED; }
.bf-row.ok .ico { background:$TEAL_SOFT; color:$TEAL_DARK; } .bf-row.crit .ico { background:$CRIT_SOFT; color:$CRIT; }
.bf-row.info .ico { background:$INFO_SOFT; color:$INFO; } .bf-row.warn .ico { background:$WARN_SOFT; color:$WARN; }
.bf-row .txt { flex:1; min-width:0; }
.bf-row .txt b { display:block; font-size:1rem; font-weight:800; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.bf-row .txt span { color:$MUTED; font-size:.82rem; }

/* ---------- pied de page */
.bf-footer { margin-top:3rem; padding-top:1.2rem; border-top:1px solid $LINE; display:flex; justify-content:space-between;
  flex-wrap:wrap; gap:.6rem; color:#8A94A8; font-size:.8rem; font-weight:600; }
.bf-footer span { display:inline-flex; align-items:center; gap:.4rem; }

@media (max-width: 900px) {
  .bf-hero { grid-template-columns: 1fr; padding:2rem 1.5rem; }
  .bf-hero h1 { font-size: 2rem; }
}
@media (max-width: 1100px) { .bf-chain { grid-template-columns: repeat(4, 1fr); row-gap:1.4rem; } .bf-station:nth-child(5)::before { display:none; } }
@media (max-width: 760px) {
  .bf-findings { grid-template-columns: 1fr; } .bf-findings .big { border-right:none; padding-right:0; }
  .bf-leg { grid-template-columns: 1fr; }
  .bf-chain { grid-template-columns: 1fr; gap:.9rem; padding:1.2rem; }
  .bf-station { display:grid; grid-template-columns: 52px 1fr; text-align:left; gap:.1rem .9rem; }
  .bf-station::before { display:none; }
  .bf-dot { margin:0; grid-row: span 3; }
  .bf-station small { min-height:0; }
  .bf-station em { justify-self:start; }
}
</style>
""")
CSS = _CSS.substitute(INK=INK, MUTED=MUTED, LINE=LINE, BG=BG, SURFACE=SURFACE, TEAL=TEAL, TEAL_DARK=TEAL_DARK,
                      TEAL_SOFT=TEAL_SOFT, WARN=WARN, WARN_SOFT=WARN_SOFT, CRIT=CRIT, CRIT_SOFT=CRIT_SOFT,
                      INFO=INFO, INFO_SOFT=INFO_SOFT)

LOGO = f"""<svg width="38" height="38" viewBox="0 0 34 34" aria-hidden="true">
<defs><linearGradient id="bfg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#16243A"/><stop offset="1" stop-color="{INK}"/></linearGradient></defs>
<rect width="34" height="34" rx="10" fill="url(#bfg)"/>
<path d="M8 22 L15 13 L20 19 L26 10" stroke="{TEAL}" stroke-width="2.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
<circle cx="8" cy="22" r="2.6" fill="#fff"/><circle cx="15" cy="13" r="2.6" fill="#fff"/>
<circle cx="20" cy="19" r="2.6" fill="#fff"/><circle cx="26" cy="10" r="2.8" fill="#5EEAD4"/></svg>"""


def brand() -> str:
    return h(f'<div class="bf-brand">{LOGO}<div><b>BI<em>Flow</em></b><span class="tag">Nexora</span><br>'
             f'<span>De la donnée brute à la décision expliquée</span></div></div>')


def topline() -> str:
    return '<div class="bf-topline"></div>'


def hero() -> str:
    """Bandeau d'accueil : promesse, garanties et ce que l'utilisateur obtient."""
    trust = "".join(f'<span>{icon(i, 16, 2.4)}{esc(t)}</span>' for i, t in
                    (("lock", "100 % local, rien ne quitte l'ordinateur"), ("cpu", "IA intégrée, sans clé"),
                     ("route", "Chaque modification est tracée")))
    deliver = "".join(f'<div class="it"><i>{icon(i, 20)}</i><div><b>{esc(t)}</b><span>{esc(d)}</span></div></div>' for i, t, d in
                      (("star", "Des données prêtes", "nettoyées sans perte et organisées en modèle en étoile"),
                       ("target", "Des KPI vérifiés", "adaptés à votre métier, chaque valeur calculée deux fois"),
                       ("layout", "Un tableau de bord", "graphiques, constats et recommandations"),
                       ("message", "Un assistant qui explique", "posez « pourquoi ? » à tout moment, réponse avec preuves")))
    return h(f'<div class="bf-hero"><div><span class="bf-eyebrow">{icon("sparkles", 14, 2.4)} Agents d\'IA pour la BI</span>'
             f'<h1>De vos fichiers bruts à des <span>décisions expliquées</span>.</h1>'
             f'<p>Déposez vos fichiers : des agents d\'IA les préparent, calculent les indicateurs de votre métier, détectent '
             f'ce qui change, construisent un tableau de bord et expliquent chacune de leurs décisions.</p>'
             f'<div class="bf-trust">{trust}</div></div>'
             f'<div class="bf-deliver"><small>Ce que vous obtenez</small>{deliver}</div></div>')


def page_title(title: str, subtitle: str = "") -> str:
    return h(f'<div class="bf-page"><h1>{esc(title)}</h1>{f"<p>{esc(subtitle)}</p>" if subtitle else ""}</div>')


def job_header(name: str, created: str, model: str | None = None) -> str:
    facts = f'<span>{icon("calendar", 15)}Lancée le {esc(created)}</span>'
    if model:
        facts += f'<span>{icon("cpu", 15)}IA locale : {esc(model)}</span>'
    return h(f'<div class="bf-job"><div class="bf-crumb">{icon("folder", 14)} Mes analyses</div>'
             f'<h2>{esc(name)}</h2><div class="facts">{facts}</div></div>')


def job_row(name: str, created: str, status_text: str, kind: str) -> str:
    ico = {"ok": "check-circle", "crit": "x-circle", "warn": "alert", "info": "clock"}.get(kind, "folder")
    return h(f'<div class="bf-row {kind}"><div class="ico">{icon(ico, 20)}</div><div class="txt"><b>{esc(name)}</b>'
             f'<span>Lancée le {esc(created)}</span></div>{badge(status_text, kind)}</div>')


def footer() -> str:
    return h(f'<div class="bf-footer"><span>{icon("lock", 14)} Vos données restent sur cet ordinateur</span>'
             f'<span>BIFlow · équipe Nexora · ESPRIT</span></div>')


# ---------------------------------------------------------------- la chaîne d'étapes
STATIONS = [
    ("Compréhension", "lit vos fichiers et repère les tables et leurs liens"),
    ("Diagnostic", "examine la qualité de chaque colonne"),
    ("Nettoyage", "corrige ce qui peut l'être sans risque"),
    ("Modélisation", "construit et livre le modèle en étoile"),
    ("Indicateurs", "choisit, calcule et vérifie les KPI de votre métier"),
    ("Analyse", "détecte ce qui change et rédige les constats"),
    ("Tableau de bord", "assemble un tableau de bord interactif"),
]
STATION_ICONS = ["search", "activity", "sparkles", "star", "target", "trend", "layout"]
STATION_DONE_AT = [1, 3, 4, 6, 8, 9, 10]            # étape du moteur après laquelle chaque station est terminée


def station_states(completed_step: int, status: str) -> list[str]:
    """État de chaque station de la chaîne (un seul pipeline, de la lecture des fichiers au tableau de bord)."""
    n = len(STATIONS)
    states = ["done" if completed_step >= s else "todo" for s in STATION_DONE_AT]
    if status == "running":
        nxt = next((i for i, s in enumerate(states) if s == "todo"), None)
        if nxt is not None:
            states[nxt] = "active"
    elif status == "blocked":
        states = ["done", "done", "error"] + ["todo"] * (n - 3)
    elif status in ("failed", "interrupted"):
        nxt = next((i for i, s in enumerate(states) if s == "todo"), n - 1)
        states[nxt] = "error"
    elif status == "success":
        states = ["done"] * n
    return states


def chain(states: list[str]) -> str:
    label = {"done": "Terminé", "active": "En cours…", "todo": "À venir", "wait": "En attente", "error": "Arrêté"}
    cells = []
    for (name, role), state, ico in zip(STATIONS, states, STATION_ICONS):
        mark = icon("check", 22, 2.6) if state == "done" else icon("x-circle" if state == "error" else
                                                                     "alert" if state == "wait" else ico, 22)
        cells.append(f'<div class="bf-station {state}" role="listitem"><div class="bf-dot">{mark}</div><b>{name}</b>'
                     f'<small>{role}</small><em>{label[state]}</em></div>')
    return h(f'<div class="bf-chain" role="list">{"".join(cells)}</div>')


def progress_chip(percent: int, status: str) -> str:
    text = {"running": "Analyse en cours", "success": "Analyse terminée", "awaiting_human": "Analyse incomplète",
            "blocked": "Analyse arrêtée", "failed": "Analyse interrompue", "interrupted": "Analyse interrompue"}.get(status, "")
    cls = {"running": "running", "success": "success", "blocked": "crit", "failed": "crit", "interrupted": "crit",
           "awaiting_human": "warn"}.get(status, "")
    if status not in ("running", "success"):
        return h(f'<div class="bf-chipline"><div class="bf-chip {cls}" role="status"><span class="led"></span>{text}</div></div>')
    return h(f'<div class="bf-chipline"><div class="bf-chip {cls}" role="status" aria-live="polite"><span class="led"></span>'
             f'{text} <b>{percent} %</b><i><span style="width:{percent}%"></span></i></div></div>')


# ---------------------------------------------------------------- petits composants
def kpis(items: list[tuple]) -> str:
    """items : (libellé, valeur, note[, 'accent'])"""
    tiles = []
    for it in items:
        label, value, note = it[:3]
        cls = " accent" if len(it) > 3 and it[3] == "accent" else ""
        cls += " long" if len(str(value)) > 16 else ""
        tiles.append(f'<div class="bf-kpi{cls}"><small>{esc(label)}</small><b>{esc(value)}</b><span>{esc(note)}</span></div>')
    return h(f'<div class="bf-kpis">{"".join(tiles)}</div>')


def badge(text: str, kind: str = "neutral", with_icon: bool = True) -> str:
    return f'<span class="bf-badge {kind}{" dot" if with_icon else ""}">{esc(text)}</span>'


_BANNER_ICONS = {"ok": "check", "warn": "alert", "crit": "x-circle", "info": "info", "⏳": "clock"}


def banner(title: str, text: str, kind: str = "ok", icon_name: str | None = None, **legacy) -> str:
    """Bandeau d'information. icon_name : une icône de la bibliothèque (ex. « clock »)."""
    name = icon_name or legacy.get("icon")
    name = _BANNER_ICONS.get(name, name) if name else _BANNER_ICONS.get(kind, "info")
    body = f'<span>{esc(text)}</span>' if text else ""
    return h(f'<div class="bf-banner {kind}"><div class="ico">{icon(name, 20, 2.4)}</div><div><b>{esc(title)}</b>'
             f'{body}</div></div>')


def empty(title: str, text: str) -> str:
    return h(f'<div class="bf-empty"><div class="ico">{icon("inbox", 24)}</div><b>{esc(title)}</b>{esc(text)}</div>')


def section(title: str, lead: str | None = None) -> str:
    return h(f'<div class="bf-section">{esc(title)}</div>' + (f'<div class="bf-lead">{esc(lead)}</div>' if lead else ""))


def cards(items: list[str]) -> str:
    return h(f'<div class="bf-grid">{"".join(items)}</div>')


def legend(items: list[tuple[str, str]]) -> str:
    return h('<div class="bf-legend">' + "".join(f'<span><i style="background:{c}"></i>{esc(t)}</span>' for t, c in items)
             + "</div>")


def findings_summary(crit: int, warn: int, info: int, explained: int) -> str:
    """Le diagnostic en une phrase, avec une barre qui montre la répartition par importance."""
    total = crit + warn + info
    if not total:
        return banner("Aucun problème relevé", "Le diagnostic n'a trouvé aucune particularité dans vos données.", "ok")
    parts = [(crit, "Critiques", "à corriger en priorité", CRIT), (warn, "À surveiller", "n'empêchent pas l'analyse", "#E0A14A"),
             (info, "Pour information", "simples remarques", "#8A94A8")]
    bar = "".join(f'<span style="flex:{n};background:{c}" title="{esc(t)} : {n}"></span>' for n, t, _, c in parts if n)
    legend_items = "".join(f'<div><i style="background:{c}"></i><b>{n}</b> {esc(t.lower())}<small>{esc(d)}</small></div>'
                           for n, t, d, c in parts)
    rejected = total - explained
    note = (f"L'IA a rédigé une explication en français pour {explained} de ces points. Chaque chiffre cité a été "
            f"comparé aux mesures réelles"
            + (f" ; {rejected} explication{'s' if rejected > 1 else ''} contenant un chiffre inexact "
               f"{'ont été écartées' if rejected > 1 else 'a été écartée'} et remplacée{'s' if rejected > 1 else ''} "
               f"par « à examiner »." if rejected else "."))
    return h(f'<div class="bf-findings"><div class="big"><b>{total}</b><span>points relevés dans vos données</span></div>'
             f'<div class="body"><div class="bf-bar">{bar}</div><div class="bf-leg">{legend_items}</div>'
             f'<p>{esc(note)}</p></div></div>')


def agent_cards(items: list[tuple[int, str, str, str, str]]) -> str:
    """Résumé du travail de chaque agent : (numéro, agent, résultat principal, détail, état)."""
    icons = {1: "search", 2: "activity", 3: "sparkles", 4: "star", 5: "target", 6: "trend", 7: "layout"}
    cells = []
    for n, name, headline, detail, state in items:
        mark = icon("check", 18, 2.6) if state == "done" else icon(icons.get(n, "info"), 18)
        cells.append(f'<div class="bf-agent {state}"><div class="top"><em>{mark}</em><small>Agent {n} · {esc(name)}</small></div>'
                     f'<b>{esc(headline)}</b><span>{esc(detail)}</span></div>')
    return h(f'<div class="bf-agents">{"".join(cells)}</div>')


# ---------------------------------------------------------------- schéma en étoile
def star_svg(star: dict) -> str:
    """Faits au centre, axes d'analyse répartis à gauche et à droite, liens dessinés."""
    facts = [n for n, t in star.items() if t["type"] == "fait"]
    dims = [n for n, t in star.items() if t["type"] != "fait"]
    if not facts:
        return ""
    left, right = dims[::2], dims[1::2]
    bw, bh, gap = 214, 58, 18
    rows = max(len(facts), len(left), len(right), 1)
    height = rows * (bh + gap) + 40
    width = 940
    xl, xc, xr = 20, (width - bw) // 2, width - bw - 20

    def column(names, x):
        total = len(names) * (bh + gap) - gap
        y0 = (height - total) / 2
        return {n: (x, y0 + i * (bh + gap)) for i, n in enumerate(names)}

    pos = {**column(left, xl), **column(facts, xc), **column(right, xr)}
    edges, seen = [], set()
    for f in facts:
        for target, _ in (star[f].get("links") or {}).values():
            if target not in pos or (f, target) in seen or target == f:
                continue
            seen.add((f, target))
            fx, fy = pos[f]
            tx, ty = pos[target]
            if target in facts:                      # fait -> fait : arc pointillé à droite des faits
                x1, y1, x2, y2 = fx + bw, fy + bh / 2, tx + bw, ty + bh / 2
                edges.append(f'<path d="M{x1},{y1} C{x1 + 46},{y1} {x2 + 46},{y2} {x2},{y2}" stroke="{TEAL}" '
                             f'stroke-width="1.6" stroke-dasharray="4 4" fill="none" opacity=".8"/>')
                continue
            if tx < fx:
                x1, x2 = fx, tx + bw
            else:
                x1, x2 = fx + bw, tx
            y1, y2 = fy + bh / 2, ty + bh / 2
            mid = (x1 + x2) / 2
            edges.append(f'<path d="M{x1},{y1} C{mid},{y1} {mid},{y2} {x2},{y2}" stroke="#B9C2D3" stroke-width="1.4" fill="none"/>'
                         f'<circle cx="{x2}" cy="{y2}" r="3" fill="#B9C2D3"/>')
    boxes = []
    for n, (x, y) in pos.items():
        label, _ = star_name(n)
        rows_txt = f"{fmt_int(star[n].get('rows'))} lignes" if star[n].get("rows") is not None else ""
        is_fact = star[n]["type"] == "fait"
        fill, stroke, color, sub = ("url(#bf-fact)", TEAL_DARK, "#fff", "#CDEFEA") if is_fact else (SURFACE, "#D3DAE5", INK, MUTED)
        short = label if len(label) <= 24 else label[:23] + "…"
        accent = "" if is_fact else f'<rect x="{x}" y="{y + 12}" width="3.5" height="{bh - 24}" rx="1.75" fill="{TEAL}"/>'
        boxes.append(f'<g><title>{esc(label)}</title><rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="14" fill="{fill}" '
                     f'stroke="{stroke}" stroke-width="1.2" filter="url(#bf-shadow)"/>{accent}'
                     f'<text x="{x + 16}" y="{y + 25}" font-size="14" font-weight="800" fill="{color}">{esc(short)}</text>'
                     f'<text x="{x + 16}" y="{y + 43}" font-size="12" fill="{sub}">{"Table de faits · " if is_fact else ""}'
                     f'{rows_txt}</text></g>')
    defs = (f'<defs><linearGradient id="bf-fact" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#12A493"/>'
            f'<stop offset="1" stop-color="{TEAL_DARK}"/></linearGradient>'
            f'<filter id="bf-shadow" x="-10%" y="-20%" width="120%" height="160%"><feDropShadow dx="0" dy="3" stdDeviation="4" '
            f'flood-color="#101A2C" flood-opacity=".10"/></filter></defs>')
    svg = (f'<svg viewBox="0 0 {width} {height}" width="100%" style="min-width:640px;font-family:Manrope,system-ui,sans-serif" '
           f'role="img" aria-label="Schéma du modèle en étoile">{defs}{"".join(edges)}{"".join(boxes)}</svg>')
    return h(f'<div class="bf-star">{svg}</div>')


def dumbbell(rows: list[tuple[str, float, float]]) -> str:
    """Qualité par aspect : point « avant » (ambre) relié au point « après » (vert), échelle commune."""
    if not rows:
        return ""
    rows = sorted(rows, key=lambda r: r[2])
    lo = max(0.0, math.floor(min(min(b, a) for _, b, a in rows) - 2))
    width, left, right, step = 940, 210, 150, 42
    height = len(rows) * step + 46
    x = lambda v: left + (v - lo) / (100 - lo or 1) * (width - left - right)
    span = 100 - lo
    tick_step = next(t for t in (1, 2, 5, 10, 20, 25, 50) if span / t <= 6)
    ticks = [v for v in range(int(math.ceil(lo / tick_step) * tick_step), 101, tick_step)]
    parts = [f'<line x1="{x(t):.1f}" y1="14" x2="{x(t):.1f}" y2="{height - 26}" stroke="#EEF1F6"/>'
             f'<text x="{x(t):.1f}" y="{height - 8}" font-size="11" fill="{MUTED}" text-anchor="middle">{t:.0f}</text>'
             for t in ticks]
    for i, (label, before, after) in enumerate(rows):
        y = 30 + i * step
        parts.append(f'<text x="{left - 16}" y="{y + 4}" font-size="13" font-weight="700" fill="{INK}" text-anchor="end">'
                     f'{esc(label)}</text>')
        parts.append(f'<line x1="{x(before):.1f}" y1="{y}" x2="{x(after):.1f}" y2="{y}" stroke="#C9D1E0" stroke-width="3" '
                     f'stroke-linecap="round"/>')
        for v, c, t in ((before, RAW, "avant"), (after, TEAL, "après")):
            parts.append(f'<circle cx="{x(v):.1f}" cy="{y}" r="7.5" fill="{c}" stroke="#fff" stroke-width="2.5">'
                         f'<title>{esc(label)} {t} : {v:.1f} / 100</title></circle>')
        delta = after - before
        parts.append(f'<text x="{width - right + 14}" y="{y + 4}" font-size="12" fill="{MUTED}">{before:.1f} → '
                     f'<tspan font-weight="800" fill="{INK}">{after:.1f}</tspan>'
                     f'<tspan fill="{TEAL_DARK}" font-weight="700">{f"  +{delta:.1f}" if delta >= 0.05 else ""}</tspan></text>')
    svg = (f'<svg viewBox="0 0 {width} {height}" width="100%" style="min-width:560px;font-family:Manrope,system-ui,sans-serif" '
           f'role="img" aria-label="Score de qualité par aspect, avant et après nettoyage">{"".join(parts)}</svg>')
    return h(f'<div class="bf-star">{svg}</div>')


# ---------------------------------------------------------------- partie 2 : KPI, analyse, dashboard
SECTOR = {"commerce": "Commerce et e-commerce", "télécom": "Télécommunications", "banque": "Banque et finance",
          "transport": "Transport et mobilité"}
KPI_STATUS = {"validé": ("Validé", "ok"), "validé (humain)": ("Validé", "ok"), "à confirmer": ("À confirmer", "warn")}
BINDING = {"évidente": "colonnes évidentes, choisies automatiquement", "LLM": "colonnes choisies par l'IA, puis vérifiées",
           "proposée par l'agent": "KPI proposé par l'IA, calculé et testé"}
RELIABILITY = {"fiable": "données fiables", "à surveiller": "quelques lignes signalées", "fragile": "beaucoup de lignes signalées"}
INSIGHT_TYPE = {"alerte": ("Alerte", "crit"), "opportunité": ("Opportunité", "ok"), "constat": ("Constat", "info")}
FACT_TYPE = {"tendance": "Tendance", "variation récente": "Variation récente", "sur un an": "Comparaison sur un an",
             "anomalie": "Mois atypique", "rupture": "Changement de niveau", "segment": "Écart entre segments",
             "contribution": "Explication d'une variation", "valeur": "Valeur globale"}
CSS_BI = """<style>
.bf-kpicard b.v { display:block; font-size:1.75rem; font-weight:800; letter-spacing:-.02em; margin:.15rem 0 .1rem;
  font-variant-numeric: tabular-nums; color:#101A2C; }
.bf-kpicard code, .bf-insight code { font-family: ui-monospace, Consolas, monospace; font-size:.76rem; background:#F4F6FA;
  border:1px solid #E4E8EF; border-radius:8px; padding:.1rem .4rem; overflow-wrap:anywhere; }
.bf-insight .reco { margin-top:.7rem; padding:.6rem .8rem; border-radius:12px; background:#EEF8F6; color:#00695F;
  font-size:.9rem; line-height:1.5; }
.bf-insight .reco b { color:#00695F; }
.bf-dash { border:1px solid #E4E8EF; border-radius:20px; overflow:hidden; box-shadow:0 1px 2px rgba(16,26,44,.04),
  0 8px 24px -12px rgba(16,26,44,.14); background:#fff; }
.bf-now { display:flex; justify-content:flex-end; gap:.5rem; color:#5B6478; font-size:.82rem; font-weight:600; margin:.3rem .2rem 0; }
.bf-now b { color:#101A2C; }
/* assistant : bouton rond dans le coin + fenêtre de discussion juste au-dessus */
.st-key-bf_chat_fab { position:fixed !important; right:26px; bottom:26px; z-index:10000; width:auto !important; }
.st-key-bf_chat_fab button { width:60px !important; height:60px !important; min-height:60px !important; border-radius:50% !important;
  padding:0 !important; border:none !important; color:#fff !important;
  background: linear-gradient(145deg, #14B3A0, #00695F) !important; box-shadow: 0 14px 30px -10px rgba(0,105,95,.8) !important; }
.st-key-bf_chat_fab button:hover { transform: translateY(-2px) scale(1.05) !important; }
.st-key-bf_chat_fab button p { font-size:1.55rem !important; color:#fff !important; line-height:1 !important; }
.st-key-bf_chat_panel { position:fixed !important; right:26px; bottom:100px; z-index:9999; width:min(420px, calc(100vw - 32px)) !important;
  max-height:calc(100vh - 130px); overflow-y:auto; overflow-x:hidden; background:#fff; border:1px solid #E4E8EF; border-radius:22px;
  box-shadow: 0 30px 60px -20px rgba(16,26,44,.45), 0 4px 12px rgba(16,26,44,.08); padding:0 14px 12px !important; gap:.55rem !important;
  animation: bf-pop .18s ease-out; }
@keyframes bf-pop { from { opacity:0; transform: translateY(12px) scale(.98); } to { opacity:1; transform:none; } }
.st-key-bf_chat_panel [data-testid="stChatMessage"] { padding:.55rem .7rem; border-radius:14px; background:#F4F6FA; gap:.55rem; }
.st-key-bf_chat_panel [data-testid="stChatMessage"] p, .st-key-bf_chat_panel [data-testid="stChatMessage"] li { font-size:.88rem; line-height:1.5; }
.st-key-bf_chat_panel [data-testid="stChatInput"] { border-radius:14px; }
.st-key-bf_chat_panel .stButton > button { min-height:2.1rem; padding:.35rem .8rem; font-size:.84rem; text-align:left;
  justify-content:flex-start; border-radius:12px; font-weight:600; color:#00695F; background:#F2FAF8; border-color:#CBEAE4; }
.st-key-bf_chat_panel [data-baseweb="select"] > div { min-height:2.2rem; }
.bf-chat-top { margin:0 -14px .1rem; padding:16px 18px 14px; display:flex; gap:.75rem; align-items:center; color:#fff;
  background: radial-gradient(240px 120px at 100% 0%, rgba(94,234,212,.35), transparent 70%), linear-gradient(135deg, #0E1A2E, #13303A); }
.bf-chat-top i { flex:0 0 40px; height:40px; border-radius:13px; display:flex; align-items:center; justify-content:center;
  background: linear-gradient(145deg, #14B3A0, #00897B); color:#fff; box-shadow: 0 8px 18px -8px #00897B; }
.bf-chat-top b { display:block; font-size:1rem; font-weight:800; }
.bf-chat-top span { display:flex; align-items:center; gap:.35rem; color:#AAB6C8; font-size:.8rem; }
.bf-chat-top span::before { content:""; width:7px; height:7px; border-radius:50%; background:#5EEAD4; }
.bf-chat-note { background:#F1F5FF; color:#2A3447; border-radius:14px; padding:.7rem .85rem; font-size:.86rem; line-height:1.5; }
.bf-chat-q { display:flex; justify-content:flex-end; }
.bf-chat-q div { max-width:85%; background: linear-gradient(145deg, #12A493, #00897B); color:#fff; padding:.55rem .85rem;
  border-radius:16px 16px 4px 16px; font-size:.88rem; line-height:1.45; box-shadow: 0 6px 14px -8px #00897B; overflow-wrap:anywhere; }
</style>"""


def binding_label(source) -> str:
    s = str(source or "")
    return BINDING.get(s, "choisi par la règle de secours" if s.startswith("repli") else s)


def kpi_card(name: str, value: str, status: str, definition: str, formula: str, how: str, reliability: str | None) -> str:
    label, kind = KPI_STATUS.get(status, (status, "neutral"))
    rel = RELIABILITY.get(str(reliability), "")
    return (f'<div class="bf-card bf-kpicard"><div class="row"><h4>{esc(name)}</h4>{badge(label, kind)}</div>'
            f'<b class="v">{esc(value)}</b><p>{esc(definition)}</p>'
            f'<div class="meta">Calcul : <code>{esc(formula)}</code><br>{esc(how[0].upper() + how[1:] if how else "")}'
            f'{" · " + esc(rel) if rel else ""}</div></div>')


def insight_card(title: str, text: str, reco: str, kind: str, facts: list, source: str) -> str:
    label, cls = INSIGHT_TYPE.get(kind, (kind, "neutral"))
    who = "Rédigé par l'IA · chaque chiffre a été revérifié par le code" if source == "LLM" else \
        "Rédigé automatiquement à partir des tests statistiques"
    return (f'<div class="bf-card bf-insight"><div class="row"><h4>{esc(title)}</h4>{badge(label, cls)}</div>'
            f'<p>{esc(text)}</p><div class="reco"><b>Recommandation :</b> {esc(reco)}</div>'
            f'<div class="meta">{esc(who)} · sources : {esc(", ".join(facts))}</div></div>')


UPLOAD_ICON = icon("upload", 30, 2)


def dropzone_header() -> str:
    formats = "".join(f"<i>{f}</i>" for f in ("CSV", "Excel", "Parquet", "JSON", "TSV", "ZIP"))
    return h(f'<div class="bf-drop"><div class="ico">{UPLOAD_ICON}</div><b>Glissez vos fichiers ici</b>'
             f'<span>un ou plusieurs fichiers d’un même jeu de données, ou un dossier compressé</span>'
             f'<div class="bf-formats">{formats}</div></div>')

CSS += CSS_BI


def chat_header(title: str, subtitle: str) -> str:
    return h(f'<div class="bf-chat-top"><i>{icon("message", 20)}</i><div><b>{esc(title)}</b>'
             f'<span>{esc(subtitle)}</span></div></div>')


def chat_note(text: str) -> str:
    return h(f'<div class="bf-chat-note">{esc(text)}</div>')


def chat_bubble(text: str) -> str:
    """Question de l'utilisateur, à droite."""
    return h(f'<div class="bf-chat-q"><div>{esc(text)}</div></div>')


def now_line(cell: str | None, elapsed: int | None) -> str:
    """Ce que fait le pipeline en ce moment (rassure pendant les longs appels au LLM)."""
    if not cell:
        return ""
    m, s = divmod(int(elapsed or 0), 60)
    return h(f'<div class="bf-now">En ce moment : <b>{esc(cell)}</b> · {m} min {s:02d} s écoulées</div>')