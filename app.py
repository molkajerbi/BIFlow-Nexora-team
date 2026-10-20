"""BIFlow — interface web : préparation des données, KPI, analyse, tableau de bord et explications.

Lancement :  streamlit run app.py   (puis ouvrir http://localhost:8501)
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from biflow import jobs
from biflow import ui

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
_V = tuple(int(x) for x in st.__version__.split(".")[:2] if x.isdigit())
WIDE = {"width": "stretch"} if _V >= (1, 49) else {"use_container_width": True}   # pleine largeur, toutes versions
st.set_page_config(page_title="BIFlow", page_icon="🔷", layout="wide", initial_sidebar_state="collapsed")
st.markdown(ui.CSS, unsafe_allow_html=True)


def md(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def go(view: str, job: str | None = None) -> None:
    st.session_state.view, st.session_state.job = view, job
    st.rerun()


def when(iso: str | None) -> str:
    try:
        d = datetime.fromisoformat(iso)
        return d.strftime("%d/%m/%Y à %H:%M")
    except (TypeError, ValueError):
        return ""


st.session_state.setdefault("view", "new")

# ---------------------------------------------------------------- barre du haut
top = st.columns([6, 1.5, 1.4], vertical_alignment="center")
with top[0]:
    md(ui.brand())
if top[1].button("Nouvelle analyse", type="primary" if st.session_state.view == "new" else "secondary",
                 **WIDE):
    go("new")
if top[2].button("Mes analyses", **WIDE):
    go("history")
md(ui.topline())


# ================================================================ PAGE : NOUVELLE ANALYSE
def page_new() -> None:
    md(ui.hero())
    models = jobs.ollama_models(OLLAMA_URL)
    md(ui.section("Nouvelle analyse", "Déposez votre jeu de données, donnez-lui un nom, puis lancez l'analyse. "
                  "Tout se déroule sur cet ordinateur."))
    md(ui.dropzone_header())
    files = st.file_uploader("Vos fichiers", accept_multiple_files=True, label_visibility="collapsed",
                             type=["csv", "tsv", "txt", "xlsx", "xls", "parquet", "json", "zip"])
    c1, c2 = st.columns([1.3, 1], vertical_alignment="bottom")
    with c1:
        default_name = (Path(files[0].name).stem if len(files) == 1 else f"Analyse de {len(files)} fichiers") if files else ""
        name = st.text_input("Nom de l'analyse", value=default_name, placeholder="ex. Ventes 2024")
    options = models or ["qwen2.5:7b"]
    model = "qwen2.5:7b" if "qwen2.5:7b" in options else options[0]     # modèle par défaut, toujours défini
    with c2:
        with st.expander("Paramètres avancés"):
            model = st.selectbox("Modèle d'IA local", options, index=options.index(model),
                                 help="Le modèle 3b est environ deux fois plus rapide, le 7b plus précis.")
    if models is None:
        md(ui.banner("Le moteur d'IA local n'est pas démarré",
                     "Ouvrez l'application Ollama sur cet ordinateur, puis rechargez la page.", "crit"))
    elif not models:
        md(ui.banner("Aucun modèle d'IA installé", "Dans un terminal : ollama pull qwen2.5:7b", "warn"))
    if st.button("Lancer l'analyse", type="primary", disabled=not files or not models, **WIDE):
        try:
            job_id = jobs.create_job([(f.name, f.getvalue()) for f in files], name, model)
        except ValueError as exc:
            md(ui.banner("Ces fichiers ne peuvent pas être analysés", str(exc), "crit"))
            return
        jobs.launch(job_id)
        go("job", job_id)
    md(ui.section("Ce qui va se passer", "Sept étapes s'enchaînent automatiquement, sans aucune intervention. Vous suivez "
                  "l'avancement et découvrez le travail de chaque agent dès qu'il a terminé. À la fin, l'assistant (bouton "
                  "rond en bas à droite) répond à toutes vos questions sur l'analyse."))
    md(ui.chain(["todo"] * len(ui.STATIONS)))


# ================================================================ PAGE : MES ANALYSES
STATUS_BADGE = {"running": ("En cours", "info"), "success": ("Terminée", "ok"), "awaiting_human": ("Incomplète", "warn"),
                "blocked": ("Bloquée", "crit"), "failed": ("Échec", "crit"), "interrupted": ("Interrompue", "crit")}


def page_history() -> None:
    history = jobs.list_jobs()
    done = sum(j["status"] == "success" for j in history)
    md(ui.page_title("Mes analyses", f"{ui.plural(len(history), 'analyse')} · {ui.plural(done, 'terminée')}. "
                     "Ouvrez une analyse pour consulter le travail de chaque agent." if history else ""))
    if st.session_state.get("flash"):
        text, kind = st.session_state.pop("flash")
        md(ui.banner(text, "", kind))
    if not history:
        md(ui.empty("Aucune analyse pour l'instant", "Déposez un premier jeu de données pour commencer."))
        return
    for j in history:
        text, kind = STATUS_BADGE.get(j["status"], (j["status"], "neutral"))
        c = st.columns([6, 1.3, 1.3], vertical_alignment="center")
        c[0].markdown(ui.job_row(j["name"], when(j.get("created")), text, kind), unsafe_allow_html=True)
        if st.session_state.get("confirm_delete") == j["id"]:
            if c[1].button("Confirmer", key=f"yes_{j['id']}", type="primary", **WIDE):
                delete_job(j["id"])
            if c[2].button("Annuler", key=f"no_{j['id']}", **WIDE):
                st.session_state.pop("confirm_delete", None)
                st.rerun()
        else:
            if c[1].button("Ouvrir", key=f"open_{j['id']}", **WIDE):
                go("job", j["id"])
            if c[2].button("Supprimer", key=f"del_{j['id']}", **WIDE):
                st.session_state.confirm_delete = j["id"]
                st.rerun()


def delete_job(job_id: str) -> None:
    """Supprime l'analyse puis revient à la liste (avec un message de confirmation)."""
    name = jobs.meta(job_id).get("name", job_id)
    ok = jobs.delete(job_id)
    st.session_state.pop("confirm_delete", None)
    st.session_state.flash = (f"L'analyse « {name} » a été supprimée." if ok else
                              f"L'analyse « {name} » n'a pas pu être supprimée entièrement : fermez les fichiers ouverts "
                              "(Excel, explorateur) puis réessayez.", "ok" if ok else "crit")
    go("history")


# ================================================================ PAGE : UNE ANALYSE
def load_result(job_id: str) -> tuple[dict, int, str]:
    """(résultats disponibles, dernière étape terminée, statut)"""
    status = jobs.status(job_id)
    res = jobs.result(job_id)
    prog = jobs.progress(job_id)
    try:
        partial = json.loads((jobs.JOBS_DIR / job_id / "results" / "partial.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        partial = {}
    if res is None:
        res = partial
    elif res.get("status") != "success" and partial:
        res = {**partial, **{k: v for k, v in res.items() if v is not None}}   # arrêt : on garde ce qui était déjà prêt
    completed = 13 if status in ("success",) else int(prog.get("completed_step") or res.get("completed_step") or 0)
    return res, completed, status


def page_job(job_id: str) -> None:
    meta = jobs.meta(job_id)
    if not meta:
        go("history")
    res, completed, status = load_result(job_id)
    running = status == "running"

    head = st.columns([5, 2], vertical_alignment="center")
    with head[0]:
        md(ui.job_header(meta.get("name"), when(meta.get("created")), meta.get("model")))

    def live() -> None:
        r, done, s = load_result(job_id)
        pct = int(jobs.progress(job_id).get("percent") or (100 if s != "running" else 0))
        md(ui.progress_chip(pct, s))
        md(ui.chain(ui.station_states(done, s)))
        if s == "running":
            p = jobs.progress(job_id)
            md(ui.now_line(p.get("cell"), p.get("elapsed_s")))
        seen = st.session_state.get(f"seen_{job_id}")
        if seen is not None and seen != (done, s):
            st.session_state[f"seen_{job_id}"] = (done, s)
            st.rerun()                                # une étape vient de finir : on affiche ses résultats
        st.session_state[f"seen_{job_id}"] = (done, s)

    with head[1]:
        quiet = "tertiary" if _V >= (1, 41) else "secondary"
        if running and st.button("Arrêter l'analyse", type=quiet, **WIDE):
            jobs.stop(job_id)
            st.rerun()
        if st.session_state.get("confirm_delete") == job_id:
            b = st.columns(2)
            if b[0].button("Confirmer", key=f"yes_{job_id}", type="primary", **WIDE):
                delete_job(job_id)
            if b[1].button("Annuler", key=f"no_{job_id}", **WIDE):
                st.session_state.pop("confirm_delete", None)
                st.rerun()
        elif st.button("Supprimer l'analyse", key=f"del_{job_id}", type=quiet, **WIDE):
            st.session_state.confirm_delete = job_id
            st.rerun()
    if running and hasattr(st, "fragment"):
        st.fragment(live, run_every=3)()
    else:
        live()

    tabs = st.tabs(["Vue d'ensemble", "1  Compréhension", "2  Diagnostic", "3  Nettoyage", "4  Modélisation",
                    "5  Indicateurs", "6  Analyse", "7  Tableau de bord"])
    with tabs[0]:
        tab_overview(job_id, meta, res, completed, status)
    with tabs[1]:
        if completed >= 1:
            tab_understanding(job_id, res)
        else:
            pending("La compréhension des données")
    with tabs[2]:
        if completed >= 3:
            tab_diagnostic(job_id)
        else:
            pending("Le diagnostic")
    with tabs[3]:
        if completed >= 4 or status == "blocked":
            tab_cleaning(job_id, res)
        else:
            pending("Le nettoyage")
    with tabs[4]:
        if completed >= 5:
            tab_model(job_id, res)
        else:
            pending("La modélisation")
    with tabs[5]:
        if completed >= 8 and jobs.table(job_id, "kpi_catalog") is not None:
            tab_kpis(job_id, res)
        else:
            pending("Les indicateurs (KPI)", status, completed)
    with tabs[6]:
        if completed >= 9 and (res.get("bi") or {}).get("insights") is not None:
            tab_analysis(job_id, res)
        else:
            pending("L'analyse", status, completed)
    with tabs[7]:
        if completed >= 10 and (res.get("bi") or {}).get("dashboard"):
            tab_dashboard(job_id, res)
        else:
            pending("Le tableau de bord", status, completed)

    if running and not hasattr(st, "fragment"):      # anciennes versions de Streamlit : rafraîchissement complet
        time.sleep(3)
        st.rerun()


def pending(what: str, status: str = "running", completed: int = 0) -> None:
    if status in ("running", "success") or not status:
        md(ui.empty(f"{what} s'affichera ici", "Les résultats apparaissent automatiquement dès que l'agent a terminé."))
    elif status == "blocked" or completed < 6:
        md(ui.empty(f"{what} : non disponible", "Cette étape demande des données préparées sans problème critique."))
    else:
        md(ui.empty(f"{what} : non disponible", "L'analyse s'est arrêtée avant cette étape (voir la vue d'ensemble)."))


def relaunch(job_id: str, meta: dict) -> None:
    """Relance une analyse (100 % automatique) en repartant des mêmes fichiers."""
    import shutil
    for old in ("result.json", "decision.json", "progress.json"):
        (jobs.JOBS_DIR / job_id / old).unlink(missing_ok=True)
    for folder in ("results", "chat"):                # résultats et conversation de l'analyse précédente
        shutil.rmtree(jobs.JOBS_DIR / job_id / folder, ignore_errors=True)
    jobs.launch(job_id)


# ---------------------------------------------------------------- vue d'ensemble
def tab_overview(job_id: str, meta: dict, res: dict, completed: int, status: str) -> None:
    bi = res.get("bi") or {}
    if status == "running":
        md(ui.banner("Analyse en cours", "Chaque étape publie ses résultats dans son onglet dès qu'elle est terminée. "
                     "Vous pouvez fermer cette page : l'analyse continue sur votre ordinateur.", "info", icon_name="clock"))
    elif status == "success":
        md(ui.banner("Votre analyse est prête", "Données préparées, indicateurs calculés et vérifiés, tableau de bord généré. "
                     "L'assistant (bouton rond en bas à droite) répond à vos questions sur chaque décision.", "ok"))
    elif status == "blocked":
        md(ui.banner("Analyse arrêtée par sécurité", "Un problème critique dans les données empêche de construire un "
                     "modèle fiable. Consultez l'onglet Nettoyage, ou demandez pourquoi à l'assistant (bouton en bas à droite).", "crit"))
    elif bi.get("error") and completed >= 6:
        md(ui.banner("Vos données sont prêtes, mais l'analyse BI s'est arrêtée",
                     "La préparation est terminée et téléchargeable. L'étape des indicateurs ou de l'analyse n'a pas pu "
                     "aller au bout : si le moteur d'IA a été fermé, rouvrez Ollama puis relancez l'analyse.", "warn"))
        if st.button("Relancer l'analyse", type="primary"):
            relaunch(job_id, meta)
            st.rerun()
        with st.expander("Détail pour l'équipe technique"):
            st.code(bi["error"], language=None)
    else:
        md(ui.banner("L'analyse s'est arrêtée avant la fin", "L'ordinateur s'est peut-être mis en veille, ou le moteur "
                     "d'IA a été fermé. Vérifiez qu'Ollama est ouvert, puis relancez l'analyse.", "crit"))
        if st.button("Relancer l'analyse", type="primary"):
            relaunch(job_id, meta)
            st.rerun()
        with st.expander("Détail pour l'équipe technique (fin du journal d'exécution)"):
            if res.get("error"):
                st.code(res["error"], language=None)
            st.code(jobs.log_tail(job_id, 40) or "journal vide", language=None)

    inp = res.get("input") or {}
    q = res.get("quality") or {}
    star = jobs.star_schema(job_id) or {}
    if completed >= 1:
        items = [("Domaine identifié", res.get("domain") or "en cours d'analyse", "déduit par l'IA", "accent"),
                 ("Tables lues", ui.fmt_int(inp.get("tables")), f"{ui.fmt_int(inp.get('rows'))} lignes au total")]
        if completed >= 4 and "corrections_applied" in q:
            items.append(("Corrections appliquées", ui.fmt_int(q.get("corrections_applied")),
                          f"{ui.plural(q.get('cells_changed'), 'cellule')} · {ui.plural(q.get('rows_changed'), 'ligne')}"))
        if completed >= 5 and star:
            n_facts = sum(t["type"] == "fait" for t in star.values())
            items.append(("Modèle en étoile", f"{n_facts} + {len(star) - n_facts}", "tables de faits + axes d'analyse"))
        md(ui.kpis(items))
        if completed >= 8 and bi.get("kpis") is not None:
            items = [("Métier reconnu", sector_text(bi), "KPI de référence adaptés", "accent"),
                     ("KPI calculés", ui.fmt_int(bi.get("kpis")), f"dont {ui.plural(bi.get('validated'), 'validé')}")]
            if bi.get("insights") is not None:
                items.append(("Constats publiés", ui.fmt_int(bi.get("insights")),
                              f"{ui.plural(bi.get('signals'), 'signal détecté', 'signaux détectés')}"))
            xai = res.get("xai") or {}
            if xai.get("ready"):
                items.append(("Décisions expliquables", ui.fmt_int(xai.get("decisions")), "demandez « pourquoi ? » à l'assistant"))
            md(ui.kpis(items))

    if completed >= 1:
        md(ui.section("Ce que chaque agent a fait", "Ouvrez l'onglet correspondant pour voir le détail."))
        md(ui.agent_cards(agent_summary(job_id, res, completed, status, star)))

    review = res.get("review") or {}
    set_aside = review.get("set_aside") or review.get("escalated") or {}
    if set_aside:
        n = len(set_aside)
        text = ("Une correction n'a pas été appliquée car elle présentait un risque pour vos données."
                if n == 1 else f"{n} corrections n'ont pas été appliquées car elles présentaient un risque pour vos données.")
        md(ui.banner("Corrections mises de côté par prudence",
                     text + " Les problèmes concernés restent signalés dans l'onglet 3 Nettoyage.", "warn"))

    if status != "running" and completed >= 6:
        md(ui.section("Télécharger", "Tous les livrables (modèle en étoile, données nettoyées, KPI, analyse, tableau de bord, "
                      "registre des décisions), la base de données seule ou le tableau de bord seul."))
        c = st.columns(3)
        zip_path = jobs.JOBS_DIR / job_id / "biflow_outputs.zip"
        if zip_path.exists():
            c[0].download_button("Tous les livrables (.zip)", zip_path.read_bytes(),
                                 file_name=f"biflow_{job_id}.zip", mime="application/zip", type="primary", **WIDE)
        out_dir = res.get("output_dir")
        for wh in (Path(out_dir).glob("biflow_star.*") if out_dir else []):
            c[1].download_button(f"Base du modèle en étoile ({wh.stat().st_size / 1e6:.1f} Mo)", wh.read_bytes(),
                                 file_name=wh.name, **WIDE,
                                 help="Un seul fichier qui contient toutes les tables du modèle en étoile, prêt à être "
                                      "interrogé en SQL ou ouvert dans un outil de BI.")
        dash = jobs.dashboard_html(job_id)
        if dash:
            c[2].download_button("Tableau de bord (.html)", dash.encode("utf-8"), file_name=f"dashboard_{job_id}.html",
                                 mime="text/html", **WIDE, help="Fichier autonome : il s'ouvre dans n'importe quel navigateur, "
                                                                "même sans connexion.")


def sector_text(bi: dict) -> str:
    sectors = bi.get("sectors") or []
    return ", ".join(ui.SECTOR.get(s, s) for s in sectors) if sectors else "Générique"


def agent_summary(job_id: str, res: dict, completed: int, status: str, star: dict) -> list[tuple]:
    """Une carte par agent : ce qu'il a produit, en une phrase."""
    inp = res.get("input") or {}
    rels = jobs.table(job_id, "relationships")
    report = jobs.table(job_id, "profiling_report")
    scores = jobs.table(job_id, "quality_scores")
    tests = jobs.table(job_id, "etl_tests")
    q = res.get("quality") or {}
    bi = res.get("bi") or {}
    xai = res.get("xai") or {}
    waiting = "en attente de l'étape précédente"

    def todo(n: int, name: str, after: int) -> tuple:
        busy = status == "running" and completed >= after
        return n, name, "en cours…" if busy else "—", waiting if status == "running" else "non exécuté", "todo"

    items = [(1, "Compréhension", f"{ui.fmt_int(inp.get('tables'))} tables reconnues",
              f"{ui.fmt_int(inp.get('rows'))} lignes lues, "
              f"{ui.plural(0 if rels is None else len(rels), 'lien détecté', 'liens détectés')}", "done")]
    if completed >= 3 and report is not None:
        crit = int((report["severity"] == "blocking").sum())
        items.append((2, "Diagnostic", ui.plural(len(report), "point relevé", "points relevés"),
                      f"dont {ui.plural(crit, 'critique', 'critiques')}, chacun expliqué en français", "done"))
    else:
        items.append(todo(2, "Diagnostic", 1))
    if completed >= 4 and scores is not None and "corrections_applied" in q:
        sc = scores.rename(columns={scores.columns[0]: "dimension"})
        items.append((3, "Nettoyage", f"Qualité {sc['avant'].mean():.1f} → {sc['après'].mean():.1f} / 100",
                      f"{ui.plural(q.get('corrections_applied'), 'correction appliquée', 'corrections appliquées')}, "
                      "chacune tracée", "done"))
    else:
        items.append(todo(3, "Nettoyage", 3))
    if completed >= 5 and star:
        n_facts = sum(t["type"] == "fait" for t in star.values())
        ok = int(tests["OK"].astype(str).eq("True").sum()) if tests is not None else 0
        items.append((4, "Modélisation", f"{n_facts} tables de faits, {len(star) - n_facts} axes",
                      f"{ok} / {0 if tests is None else len(tests)} tables validées par les contrôles", "done"))
    else:
        items.append(todo(4, "Modélisation", 4))
    if completed >= 8 and bi.get("kpis") is not None:
        items.append((5, "Indicateurs", f"{ui.plural(bi.get('kpis'), 'KPI calculé', 'KPI calculés')}",
                      f"métier : {sector_text(bi).lower()} · chaque valeur calculée deux fois", "done"))
    else:
        items.append(todo(5, "Indicateurs", 6))
    if completed >= 9 and bi.get("insights") is not None:
        items.append((6, "Analyse", ui.plural(bi.get("insights"), "constat publié", "constats publiés"),
                      f"{ui.plural(bi.get('series'), 'série mensuelle analysée', 'séries mensuelles analysées')}, "
                      "chiffres vérifiés", "done"))
    else:
        items.append(todo(6, "Analyse", 8))
    if completed >= 10 and bi.get("dashboard"):
        items.append((7, "Tableau de bord", "Tableau de bord prêt", bi.get("dashboard_title") or "", "done"))
    else:
        items.append(todo(7, "Tableau de bord", 9))
    return items


# ---------------------------------------------------------------- 1. compréhension
def tab_understanding(job_id: str, res: dict) -> None:
    contract = jobs.table(job_id, "contract_tables")
    rels = jobs.table(job_id, "relationships")
    inp = res.get("input") or {}
    md(ui.section("Ce que BIFlow a compris de vos fichiers",
                  "Les tables et les liens entre elles ont été repérés automatiquement, sans aucune configuration."))
    md(ui.kpis([("Tables", ui.fmt_int(inp.get("tables") or (0 if contract is None else len(contract))), "une par fichier ou feuille"),
                ("Lignes", ui.fmt_int(inp.get("rows")), "lues sans aucune modification"),
                ("Liens entre tables", ui.fmt_int(0 if rels is None else len(rels)), "détectés automatiquement"),
                ("Structure reconnue avec certitude", f"{res.get('confidence_pct') or 0:.0f} %",
                 "aucun point douteux" if not res.get("points_to_check") else
                 ui.plural(len(res["points_to_check"]), "point à vérifier", "points à vérifier"))]))
    for point in res.get("points_to_check") or []:
        md(ui.banner("Point à vérifier", str(point), "warn"))
    if contract is not None:
        items = []
        for t in contract.itertuples():
            desc = ui.clean_description(t.description)
            ident = t.grain if isinstance(t.grain, str) and t.grain else "aucun (plusieurs lignes par valeur)"
            items.append(f'<div class="bf-card"><h4>{ui.esc(t.table)}</h4>'
                         f'{"<p>" + ui.esc(desc) + "</p>" if desc else ""}'
                         f'<div class="meta">{ui.fmt_int(t.lignes)} lignes · {t.colonnes} colonnes · identifiant : {ui.esc(ident)}</div></div>')
        md(ui.section("Tables"))
        md(ui.cards(items))
    if rels is not None and len(rels):
        md(ui.section("Liens entre les tables", "Chaque ligne de la première table retrouve sa correspondance dans la seconde."))
        view = pd.DataFrame({"Table": rels["child"], "Reliée à": rels["parent"], "Par la colonne": rels["fk"],
                             "Type de lien": rels.get("aggregate", pd.Series(False, index=rels.index)).map(
                                 lambda a: "regroupement (plusieurs lignes)" if str(a) == "True" else "direct")})
        st.dataframe(view, hide_index=True, **WIDE)
    cols = jobs.table(job_id, "contract_columns")
    if cols is not None:
        with st.expander("Voir le détail des colonnes"):
            st.dataframe(pd.DataFrame({"Table": cols["table"], "Colonne": cols["colonne"],
                                       "Nature": cols["type"].map(lambda s: ui.SEM_TYPE.get(s, s))}),
                         hide_index=True, **WIDE)


# ---------------------------------------------------------------- 2. diagnostic
def tab_diagnostic(job_id: str) -> None:
    report = jobs.table(job_id, "profiling_report")
    health = jobs.table(job_id, "health_map")
    md(ui.section("Le diagnostic de vos données",
                  "BIFlow a passé chaque colonne au crible : valeurs vides, doublons, valeurs anormales, liens cassés… "
                  "Chaque point relevé est ensuite expliqué par l'IA en langage simple. Une explication n'est gardée "
                  "que si tous ses chiffres correspondent aux mesures réelles."))
    if report is not None and len(report):
        sev = report["severity"].value_counts()
        md(ui.findings_summary(int(sev.get("blocking", 0)), int(sev.get("warning", 0)), int(sev.get("info", 0)),
                               int((report["source"] == "LLM").sum())))
    if health is not None:
        md(ui.section("État de santé par table", "Passez la souris sur le titre d'une colonne pour voir sa définition."))
        view = health.drop(columns=["colonnes_avec_manquants"], errors="ignore").rename(columns=ui.HEALTH_COLS)
        if "Identifiant unique" in view:
            view["Identifiant unique"] = view["Identifiant unique"].map(
                lambda v: "Oui" if str(v) == "True" else ("Non" if str(v) == "False" else "—"))
        cfg = {name: st.column_config.Column(name, help=text) for name, text in ui.HEALTH_HELP.items() if name in view}
        if "Valeurs manquantes (%)" in view:
            cfg["Valeurs manquantes (%)"] = st.column_config.ProgressColumn(
                "Valeurs manquantes (%)", min_value=0, max_value=100, format="%.1f %%",
                help=ui.HEALTH_HELP["Valeurs manquantes (%)"])
        if "Table" in view:
            view = view.set_index("Table")                # la colonne Table reste visible quand on fait défiler
        st.dataframe(view, **WIDE, column_config=cfg)
    if report is None or not len(report):
        return
    md(ui.section("Le détail des points relevés", "Pour chaque point : ce qui a été mesuré, l'explication de l'IA et la "
                  "recommandation. Filtrez par table ou par importance."))
    c = st.columns([1, 1])
    table = c[0].selectbox("Table", ["Toutes les tables"] + sorted(report["table"].dropna().unique().tolist()),
                           key=f"diag_table_{job_id}")
    level = c[1].selectbox("Importance", ["Toutes", "Critique", "À surveiller", "Information"], key=f"diag_level_{job_id}")
    rev = {v[0]: k for k, v in ui.SEVERITY.items()}
    view = report if table == "Toutes les tables" else report[report["table"] == table]
    view = view if level == "Toutes" else view[view["severity"] == rev[level]]
    order = {"blocking": 0, "warning": 1, "info": 2}
    view = view.assign(_o=view["severity"].map(order)).sort_values(["_o", "table"])
    items = []
    for f in view.head(60).itertuples():
        label, kind = ui.SEVERITY.get(f.severity, (f.severity, "neutral"))
        where = f.table if not isinstance(f.colonne, str) or f.colonne in ("", "*") else f"{f.table} › {f.colonne}"
        text = f.interpretation if isinstance(f.interpretation, str) and not f.interpretation.startswith("Non interprété") \
            else "À examiner : ce point n'a pas pu être expliqué automatiquement."
        items.append(f'<div class="bf-card"><div class="row"><h4>{ui.esc(where)}</h4>{ui.badge(label, kind)}</div>'
                     f'<p>{ui.esc(text)}</p><div class="meta">{ui.esc(ui.DIMENSION.get(f.dimension, f.dimension))} · '
                     f'mesuré : {ui.esc(f.constat)}<br>Recommandation : '
                     f'<b>{ui.esc(ui.ACTION.get(f.action, f.action))}</b></div></div>')
    md(ui.cards(items) if items else ui.empty("Aucun constat pour ce filtre", "Essayez une autre table ou importance."))
    if len(view) > 60:
        st.caption(f"60 constats affichés sur {len(view)}. Utilisez les filtres pour affiner.")


# ---------------------------------------------------------------- 3. nettoyage
def tab_cleaning(job_id: str, res: dict) -> None:
    scores = jobs.table(job_id, "quality_scores")
    plan = jobs.table(job_id, "cleaning_plan")
    applied = jobs.table(job_id, "corrections_applied")
    changes = jobs.table(job_id, "cell_changes_sample")
    dismissed = jobs.table(job_id, "dismissed")
    rules = jobs.table(job_id, "rules_after")
    q = res.get("quality") or {}
    md(ui.section("Le nettoyage de vos données",
                  "L'agent corrige les formats, retire les doublons, estime les valeurs manquantes, remplace les valeurs "
                  "impossibles et ramène les valeurs extrêmes à une limite. Chaque correction est d'abord testée sur une "
                  "copie, et la valeur d'origine reste toujours dans le journal."))
    qs = res.get("quality_status") or q.get("quality_status")
    if qs in ui.QUALITY_STATUS:
        text, kind = ui.QUALITY_STATUS[qs]
        md(ui.banner(text, "Chaque ligne garde la trace de ce qui la concerne.", kind))
    remaining = rules[rules["violations"] > 0] if rules is not None else pd.DataFrame()
    if scores is not None:
        scores = scores.rename(columns={scores.columns[0]: "dimension"})
        before, after = scores["avant"].mean(), scores["après"].mean()
        md(ui.kpis([("Score de qualité", f"{after:.1f} / 100", f"contre {before:.1f} avant nettoyage", "accent"),
                    ("Cellules corrigées", ui.fmt_int(q.get("cells_changed", 0)), "corrigées ou estimées"),
                    ("Lignes en double retirées", ui.fmt_int(q.get("rows_changed", 0)), "copies exactes"),
                    ("Points à surveiller", ui.fmt_int(len(remaining)), "signalés, jamais supprimés")]))
        md(ui.section("Qualité par aspect, avant et après",
                      "Pour chaque aspect, la part des lignes qui passent tous les contrôles (moyenne des tables). "
                      "Un aspect qui ne bouge pas est un problème qui ne se corrige pas sans risque : il reste signalé."))
        md(ui.legend([("Avant nettoyage", ui.RAW), ("Après nettoyage", ui.TEAL)]))
        md(ui.dumbbell([(ui.DIMENSION.get(r.dimension, r.dimension), float(r.avant), float(r.après))
                        for r in scores.itertuples()]))
    if plan is not None and len(plan):
        md(ui.section("Corrections appliquées"))
        effects = {} if applied is None else dict(zip(applied["id"], applied["effect"]))
        items = []
        for p in plan.itertuples():
            title, explain = ui.CORRECTION.get(p.correction, (p.correction, ""))
            where = p.table if p.colonne == "*" else f"{p.table} › {p.colonne}"
            if p.id in effects:
                effect = ui.plural(effects[p.id], "ligne retirée", "lignes retirées") \
                    if p.correction == "drop_exact_duplicates" else ui.plural(effects[p.id], "cellule corrigée", "cellules corrigées")
                kind = "ok"
            else:
                effect, kind = "non appliquée", "neutral"
            why = ui.human_text(p.justification) if p.décidé_par == "agent" else ""
            swap = ""
            if changes is not None and len(changes) and p.correction != "drop_exact_duplicates":
                ex = changes[changes["correction"] == p.id].head(1)
                for e in ex.itertuples():
                    old, new = ui.show_value(e.before, quoted=True), ui.show_value(e.after)
                    if old.strip("'") != new:                     # un exemple qui montre vraiment le changement
                        swap = (f'<div class="bf-swap"><code>{ui.esc(old)}</code>'
                                f'devient<code class="after">{ui.esc(new)}</code></div>')
            items.append(f'<div class="bf-card"><div class="row"><h4>{ui.esc(title)}</h4>{ui.badge(effect, kind)}</div>'
                         f'<p>{ui.esc(explain)}</p>{swap}<div class="meta">{ui.esc(where)} · '
                         f'{ui.esc(ui.DECIDED_BY.get(p.décidé_par, p.décidé_par))}'
                         f'{"<br>« " + ui.esc(why) + " »" if why else ""}</div></div>')
        md(ui.cards(items))
    if dismissed is not None and len(dismissed):
        md(ui.section("Corrections écartées par l'IA", "Ces problèmes restent signalés dans les données, sans être modifiés."))
        md(ui.cards([f'<div class="bf-card"><h4>{ui.esc(d.table)}</h4><p>'
                     f'{ui.esc(ui.human_text(d.justification) or "L’IA a jugé que cette correction n’était pas utile.")}</p></div>'
                     for d in dismissed.itertuples()]))
    if len(remaining):
        md(ui.section("Points encore à surveiller", "Ils sont marqués ligne par ligne dans les données livrées."))
        st.dataframe(pd.DataFrame({
            "Table": remaining["table"], "Aspect": remaining["dimension"].map(lambda d: ui.DIMENSION.get(d, d)),
            "Contrôle": remaining["description"].map(ui.friendly_rule), "Lignes concernées": remaining["violations"],
            "Importance": remaining["severity"].map(lambda s: ui.SEVERITY.get(s, (s,))[0])}),
            hide_index=True, **WIDE)


# ---------------------------------------------------------------- 4. modélisation
def tab_model(job_id: str, res: dict) -> None:
    star = jobs.star_schema(job_id) or {}
    tests = jobs.table(job_id, "etl_tests")
    derived = jobs.table(job_id, "derived_indicators")
    md(ui.section("Le modèle en étoile", "Vos données sont organisées comme les outils de BI l'attendent : des tables de "
                  "faits (les événements) reliées à des axes d'analyse (qui, quoi, où, quand)."))
    n_facts = sum(t["type"] == "fait" for t in star.values())
    passed = int(tests["OK"].astype(str).eq("True").sum()) if tests is not None else 0
    md(ui.kpis([("Tables de faits", ui.fmt_int(n_facts), "les événements à analyser", "accent"),
                ("Axes d'analyse", ui.fmt_int(len(star) - n_facts), "dont le calendrier"),
                ("Tables validées", f"{passed} / {0 if tests is None else len(tests)}", "tous leurs contrôles sont réussis"),
                ("Indicateurs calculés", ui.fmt_int(0 if derived is None else len(derived)), "délais et retards, à partir des dates")]))
    if star:
        md(ui.star_svg(star))
        md(ui.legend([("Table de faits", ui.TEAL), ("Axe d'analyse", "#C9D1E0")]))
    if tests is not None and len(tests):
        md(ui.section("Contrôles de cohérence", "Après la construction de chaque table : pas de doublon, pas de ligne "
                      "perdue, totaux conservés, liens valides."))
        rows = []
        for t in tests.to_dict(orient="records"):
            checks = {k: v for k, v in t.items() if ui.test_label(k) and str(v) in ("True", "False")}
            ok = sum(str(v) == "True" for v in checks.values())
            label, kind = ui.star_name(t["table"])
            rows.append({"Table": label, "Type": kind, "Lignes": t["lignes"], "Contrôles réussis": f"{ok} / {len(checks)}",
                         "État": "✓ Valide" if str(t["OK"]) == "True" else "✗ À revoir"})
        st.dataframe(pd.DataFrame(rows), hide_index=True, **WIDE)
        with st.expander("Voir chaque contrôle"):
            detail = [{"Table": ui.star_name(t["table"])[0], "Contrôle": ui.test_label(k),
                       "Résultat": "✓ réussi" if str(v) == "True" else "✗ échec"}
                      for t in tests.to_dict(orient="records") for k, v in t.items()
                      if ui.test_label(k) and str(v) in ("True", "False")]
            st.dataframe(pd.DataFrame(detail), hide_index=True, **WIDE)
    if derived is not None and len(derived):
        md(ui.section("Indicateurs calculés automatiquement",
                      "De nouvelles colonnes créées à partir des dates de vos données, prêtes pour vos tableaux de bord."))
        items = []
        for d in derived.itertuples():
            title, meaning = ui.indicator_label(d.colonne, d.type, d.calcul)
            items.append(f'<div class="bf-card"><div class="row"><h4>{ui.esc(title)}</h4>'
                         f'{ui.badge("délai en jours" if "délai" in str(d.type) else "oui / non", "info", with_icon=False)}</div>'
                         f'<p>{ui.esc(meaning)}</p><div class="meta">Table {ui.esc(d.table)} · nouvelle colonne '
                         f'{ui.esc(d.colonne)}</div></div>')
        md(ui.cards(items))
    run_dir = res.get("run_dir")
    folder = Path(run_dir) / "warehouse" if run_dir else None
    if star and folder and folder.exists():
        md(ui.section("Aperçu des tables"))
        names = [n for n in star if (folder / f"{n}.csv").exists()]
        if names:
            choice = st.selectbox("Table", names, key=f"preview_{job_id}",
                                  format_func=lambda n: f"{ui.star_name(n)[0]} ({ui.star_name(n)[1].lower()})")
            df = pd.read_csv(folder / f"{choice}.csv", nrows=300)
            df = df.drop(columns=[c for c in df.columns if c in ("_source_row_id", "_dq_flags", "is_unknown_member")])
            st.dataframe(df, hide_index=True, **WIDE)


# ---------------------------------------------------------------- 5. indicateurs (KPI)
def tab_kpis(job_id: str, res: dict) -> None:
    bi = res.get("bi") or {}
    cat = jobs.table(job_id, "kpi_catalog")
    md(ui.section("Les indicateurs clés de votre activité",
                  "L'agent reconnaît votre métier, retrouve dans sa base de connaissances les KPI de référence de ce métier, "
                  "relie chacun aux bonnes colonnes, puis le calcule deux fois (une requête SQL et un second calcul "
                  "indépendant). Un KPI n'est gardé que si les deux calculs donnent le même résultat et que sa valeur est "
                  "plausible."))
    dropped, failed = bi.get("dropped") or {}, bi.get("failed") or {}
    md(ui.kpis([("Métier reconnu", sector_text(bi), "choisi par l'IA, vérifié par le code" if bi.get("sector_source") == "LLM"
                 else "choisi par la règle de secours", "accent"),
                ("KPI retenus", ui.fmt_int(bi.get("kpis")), f"{ui.plural(bi.get('validated'), 'validé')} · "
                                                            f"{bi.get('to_confirm') or 0} à confirmer"),
                ("Proposés par l'IA", ui.fmt_int(bi.get("proposed") or 0), "en plus de la base de connaissances"),
                ("Écartés", ui.fmt_int(len(dropped) + len(failed)), "sans objet ici, ou test échoué")]))
    if bi.get("sector_reason"):
        md(ui.banner("Pourquoi ce métier ?", ui.human_text(bi["sector_reason"]) or bi["sector_reason"], "info"))
    if cat is None or not len(cat):
        md(ui.empty("Aucun KPI calculable", "Les colonnes de vos données ne permettent de calculer aucun indicateur fiable."))
        return
    md(ui.section("Le catalogue de KPI", "« Validé » : colonnes évidentes ou choisies par l'IA, tous les tests réussis. "
                  "« À confirmer » : KPI proposé par l'IA ou liaison de secours ; à relire avant de le diffuser."))
    reasons = bi.get("binding_reasons") or {}
    items = []
    for k in cat.to_dict(orient="records"):
        how = ui.binding_label(k.get("binding"))
        why = ui.human_text(reasons.get(k["id"]))
        items.append(ui.kpi_card(k["name"], k["valeur"], k["status"], k.get("definition") or "", k.get("formula") or "",
                                 how + (f" (« {why} »)" if why else ""), k.get("reliability")))
    md(ui.cards(items))
    with st.expander("Voir la requête SQL de chaque KPI"):
        choice = st.selectbox("KPI", cat["name"].tolist(), key=f"sql_{job_id}")
        st.code(cat.loc[cat["name"] == choice, "sql"].iloc[0], language="sql")
    if dropped or failed:
        with st.expander("KPI écartés, et pourquoi"):
            rows = [{"KPI": k, "Raison": r} for k, r in dropped.items()] + \
                   [{"KPI": k, "Raison": f"test non réussi : {r}"} for k, r in failed.items()]
            st.dataframe(pd.DataFrame(rows), hide_index=True, **WIDE)


# ---------------------------------------------------------------- 6. analyse
def tab_analysis(job_id: str, res: dict) -> None:
    bi = res.get("bi") or {}
    insights = jobs.insights(job_id)
    facts = jobs.table(job_id, "analysis_facts")
    md(ui.section("Ce que l'analyse a découvert",
                  "Chaque KPI suivi mois par mois passe par cinq tests statistiques : tendance, variation récente, comparaison "
                  "sur un an, mois atypique, changement de niveau. Les signaux retenus sont ensuite découpés par segment pour "
                  "trouver où se situe le changement. L'IA rédige les constats ; le code revérifie chaque chiffre avant de "
                  "les publier."))
    period = next((p for p in (bi.get("reliable_periods") or {}).values() if p), None)
    inv = bi.get("investigations") or []
    md(ui.kpis([("Constats publiés", ui.fmt_int(len(insights)), f"dont {bi.get('insights_llm') or 0} rédigés par l'IA", "accent"),
                ("Séries analysées", ui.fmt_int(bi.get("series")), f"de {period[0] % 100:02d}/{period[0] // 100} à "
                                                                   f"{period[1] % 100:02d}/{period[1] // 100}" if period
                 else "aucune date exploitable"),
                ("Signaux détectés", ui.fmt_int(bi.get("signals")), "par les tests statistiques"),
                ("Pistes creusées", ui.fmt_int(len(inv)), "choisies par l'IA" if any(i.get("source") == "LLM" for i in inv)
                 else "choisies par le code")]))
    if insights:
        md(ui.section("Les constats", "Du plus important au moins important. Les sources (F…) renvoient aux faits mesurés."))
        md(ui.cards([ui.insight_card(i["titre"], i["texte"], i["recommandation"], i.get("type"), i.get("faits") or [],
                                     i.get("source")) for i in insights]))
    else:
        md(ui.empty("Aucun signal marquant", "Les séries sont trop courtes ou stables : aucun changement net n'a été détecté."))
    if inv:
        md(ui.section("Les pistes creusées", "Pour expliquer un signal, l'agent choisit l'axe de découpage le plus parlant."))
        md(ui.cards([f'<div class="bf-card"><div class="row"><h4>Signal {ui.esc(i["fait"])} découpé par '
                     f'« {ui.esc(i["axe"])} »</h4>{ui.badge("IA" if i.get("source") == "LLM" else "code", "info")}</div>'
                     f'<p>{ui.esc(ui.human_text(i["pourquoi"]) or "Axe le plus discriminant pour ce signal.")}</p>'
                     f'<div class="meta">{"Nouveau fait : " + ui.esc(i["résultat"]) if i.get("résultat") else "Rien de significatif"}'
                     f'</div></div>' for i in inv]))
    if facts is not None and len(facts):
        with st.expander("Voir tous les faits mesurés"):
            view = facts[facts["type"] != "valeur"] if (facts["type"] != "valeur").any() else facts
            st.dataframe(pd.DataFrame({"Fait": view["id"], "Type": view["type"].map(lambda t: ui.FACT_TYPE.get(t, t)),
                                       "Constat": view["texte"], "Lecture": view["valence"]}), hide_index=True, **WIDE)


# ---------------------------------------------------------------- 7. tableau de bord
def tab_dashboard(job_id: str, res: dict) -> None:
    html = jobs.dashboard_html(job_id)
    md(ui.section("Votre tableau de bord", "Généré automatiquement : le chiffre principal, les indicateurs clés, leur "
                  "évolution mois par mois, les constats et les découpages. Chaque valeur vient du catalogue de KPI. "
                  "Le fichier fonctionne aussi hors ligne : téléchargez-le et ouvrez-le dans votre navigateur."))
    if not html:
        md(ui.empty("Tableau de bord introuvable", "Le fichier a peut-être été déplacé ou supprimé."))
        return
    st.download_button("Télécharger le tableau de bord (.html)", html.encode("utf-8"), file_name=f"dashboard_{job_id}.html",
                       mime="text/html", type="primary")
    if hasattr(st, "iframe"):                          # Streamlit récent
        st.iframe(html, height=1600)
    else:                                              # anciennes versions
        components.html(html, height=1600, scrolling=True)


# ---------------------------------------------------------------- 8. explications (agent XAI)
@st.cache_resource(show_spinner=False, max_entries=4)
def chat_session(job_id: str, finished_at: str):
    """Agent XAI de l'analyse, reconstruit une seule fois (code du notebook + registre exporté par le run)."""
    from biflow.llm import OllamaLLM
    from biflow.xai_chat import XAISession
    llm = OllamaLLM(model_id=jobs.meta(job_id).get("model"), url=OLLAMA_URL, cache_dir=jobs.ROOT / "biflow_cache")
    return XAISession(jobs.JOBS_DIR / job_id, llm=llm)


def chat_jobs() -> list[dict]:
    """Analyses terminées dont l'explicabilité est construite (l'assistant peut en parler)."""
    return [j for j in jobs.list_jobs() if j["status"] != "running"
            and ((jobs.result(j["id"]) or {}).get("xai") or {}).get("ready")]


def chat_widget() -> None:
    """Assistant BIFlow : bouton rond dans le coin, qui ouvre une fenêtre de discussion juste au-dessus.
    Il répond à toute question sur l'analyse (données, nettoyage, KPI, constats, tableau de bord) et sur la façon dont
    le code décide, à partir du registre des décisions et des règles lues dans le code (agent XAI du notebook)."""
    st.session_state.setdefault("chat_open", False)
    try:
        fab = st.container(key="bf_chat_fab")
    except TypeError:                                  # Streamlit trop ancien pour placer le bouton dans le coin
        fab = st.container()
    if fab.button("✕" if st.session_state.chat_open else "💬", key="bf_chat_toggle",
                  help="Fermer l'assistant" if st.session_state.chat_open else "Poser une question à l'assistant BIFlow"):
        st.session_state.chat_open = not st.session_state.chat_open
        st.rerun()
    if not st.session_state.chat_open:
        return
    try:
        panel = st.container(key="bf_chat_panel")
    except TypeError:
        panel = st.container()
    with panel:
        chat_panel()


def chat_panel() -> None:
    choices = chat_jobs()
    current = st.session_state.get("job") if st.session_state.get("view") == "job" else None
    if not choices:
        md(ui.chat_header("Assistant BIFlow", "Disponible dès qu'une analyse est terminée"))
        running = current and jobs.status(current) == "running"
        md(ui.chat_note("Votre analyse est en cours. Dès qu'elle sera terminée, je pourrai répondre à toutes vos "
                        "questions : pourquoi telle correction, tel KPI, telle alerte…" if running else
                        "Lancez une première analyse : je pourrai ensuite répondre à toutes vos questions sur ce qu'ont "
                        "fait les agents, et pourquoi."))
        return
    ids = [j["id"] for j in choices]
    names = {j["id"]: j["name"] for j in choices}
    job_id = st.session_state.get("chat_job")
    if job_id not in ids:
        job_id = current if current in ids else ids[0]
    md(ui.chat_header("Assistant BIFlow", f"Analyse « {names[job_id]} »"))
    if len(ids) > 1:
        job_id = st.selectbox("Analyse", ids, index=ids.index(job_id), format_func=names.get, key="chat_job",
                              label_visibility="collapsed")
    res = jobs.result(job_id) or {}
    try:
        with st.spinner("Préparation de l'assistant…"):
            session = chat_session(job_id, str(res.get("finished_at")))
    except Exception as exc:
        md(ui.chat_note(f"L'assistant n'a pas pu démarrer : {exc}"))
        return
    box = st.container(height=390, border=False)
    question = st.chat_input("Posez votre question…", key="chat_input")
    row = st.columns([3, 1.2], vertical_alignment="center")
    toggle = getattr(st, "toggle", st.checkbox)
    with row[0]:
        use_llm = toggle("Reformuler avec l'IA", value=True, key="chat_llm",
                         help="Activé : réponse plus naturelle, chaque chiffre vérifié par le code (quelques secondes "
                              "de plus). Désactivé : réponse immédiate construite par les règles.")
    if session.history and row[1].button("Effacer", key="chat_clear", type="tertiary" if _V >= (1, 41) else "secondary"):
        session.clear()
        st.rerun()
    with box:
        if not session.history and not question:
            md(ui.chat_note("Bonjour ! Je connais chaque décision prise pendant cette analyse et les règles du code qui "
                            "les ont produites. Demandez-moi pourquoi, comment, qui a décidé, ou « et si… ? »"))
            demo = [q for q in (res.get("xai") or {}).get("demo_questions") or [] if q][:5]
            for i, q in enumerate(demo):
                if st.button(q, key=f"chat_demo_{i}", **WIDE):
                    question = q
        for turn in session.history:
            md(ui.chat_bubble(turn["question"]))
            show_answer(turn)
        if question:
            md(ui.chat_bubble(question))
            with st.spinner("Je retrouve la décision et je prépare l'explication…"):
                turn = session.ask(question, use_llm=use_llm)
            show_answer(turn)


def show_answer(turn: dict) -> None:
    with st.chat_message("assistant", avatar="✨"):
        st.markdown(turn["réponse"])
        mode = ("Reformulé par l'IA · chiffres vérifiés par le code" if turn.get("mode") == "LLM (vérifié)"
                else "Réponse des règles du système")
        refused = " · reformulation refusée par le code" if turn.get("refus_llm") else ""
        st.caption(f"{mode}{refused} · sources : {', '.join(turn.get('sources') or []) or '—'}")


# ---------------------------------------------------------------- routage
view = st.session_state.view
if view == "job" and st.session_state.get("job"):
    page_job(st.session_state.job)
elif view == "history":
    page_history()
else:
    page_new()
md(ui.footer())
chat_widget()