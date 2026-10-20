METHOD_CARDS = [   # (étape, titre, fonctions qui décident, seuils, mots-clés)
    (1, "Lecture des fichiers et contrat de données", ["sniff", "infer_type", "infer_relationships", "infer_roles", "validate_contract"],
     [], ["type de colonne", "format", "grain", "identifiant", "table de faits", "dimension", "lien", "relation"]),
    (2, "Outils du Profiler : mesures de qualité", ["cramers_v", "screening"], [],
     ["valeurs manquantes", "anomalies", "doublons", "isolation forest", "iqr", "cramer"]),
    (3, "Domaine et interprétation des constats par le LLM", ["understand_domain", "validate_decision", "is_grounded"],
     ["BLOCKING_ALLOWED"], ["domaine", "métier", "interprétation", "gravité", "constat"]),
    (4, "Règles de qualité et score", ["run_rules", "learned_business_rules", "learned_cross_table_rules", "dq_scores"], [],
     ["règle de qualité", "score de qualité", "dimension de qualité", "dama"]),
    (4, "Valeurs manquantes, impossibles et extrêmes", ["missing_method", "protected_columns", "category_fill", "fences",
                                                       "outlier_policy"], ["MAX_IMPUTE_PCT", "MAX_OUTLIER_PCT", "OUTLIER_K"],
     ["valeurs manquantes", "imputation", "médiane", "remplir", "valeur extrême", "plafonner", "valeur impossible"]),
    (4, "Corrections : tester, décider, valider, appliquer", ["simulate_correction", "run_quality_agent", "allowed_decisions",
                                                             "assess_risk", "review_plan", "plan_in_order", "apply_correction"],
     ["MAX_ROWS_REMOVED_PCT"], ["correction", "bac à sable", "risque", "nettoyage", "doublons"]),
    (5, "Modèle en étoile et indicateurs de temps", ["derive_time_indicators", "design_star_schema", "extracted_dimensions",
                                                    "test_table"], [], ["modèle en étoile", "etl", "délai", "retard", "calendrier"]),
    (6, "Orchestration de la préparation", ["graph_node", "run_data_preparation"], [], ["orchestrateur", "langgraph", "nœud"]),
    (7, "Secteur métier et KPI de référence (RAG)", ["sector_supported"], ["MIN_SECTOR_KPIS", "MIN_SECTOR_COVERAGE",
                                                                           "MIN_SECTOR_COLUMNS"],
     ["secteur", "rag", "recherche sémantique", "base de connaissances", "embeddings"]),
    (8, "Liaison, calcul et tests des KPI", ["auto_params", "validate_binding", "run_sql", "check_bounds", "name_mismatch"], [],
     ["kpi", "liaison", "formule", "sql", "double calcul", "bornes"]),
    (9, "Signaux statistiques, segments et insights", ["analyse_series", "mann_kendall", "theil_sen", "robust_z", "dimensions",
                                                      "twin_axis", "check_insight", "repair_citations"], ["WINDOW"],
     ["tendance", "anomalie", "rupture", "variation récente", "sur un an", "signal", "segment", "insight", "mann kendall"]),
    (10, "Mise en page du dashboard", ["validate_layout"], ["MAX_TILES", "MAX_CHARTS", "MAX_SEGMENTS"],
     ["dashboard", "tableau de bord", "tuile", "graphique"]),
    (11, "Orchestration de la partie 2", ["run_stage", "run_bi_insight"], [], ["orchestrateur", "reprise"]),
    (12, "Explicabilité (cet agent)", ["xai_search", "rule_answer", "verify_explanation"], [], ["explication", "xai", "chat"]),
]


def method_records() -> list[dict]:
    out = []
    for i, (step, title, fns, consts, keywords) in enumerate(METHOD_CARDS, 1):
        rules = [f"{fn} : {doc(fn)}" for fn in fns if doc(fn)]
        values = {c: xai_num(globals()[c]) if not isinstance(globals()[c], (set, list, tuple)) else ", ".join(map(str, globals()[c]))
                  for c in consts if c in globals()}
        out.append({"id": f"M{i:02d}", "étape": step, "agent": XAI_STEPS.get(step, ""), "sujet": "méthode", "objet": title,
                    "décision": f"comment fonctionne : {title.lower()}", "pourquoi": " ".join(rules), "preuves": values,
                    "décidé_par": "règle du code", "contrefactuel": None, "refus": [], "termes": [title, *keywords], "audit": []})
    return out


METHODS = method_records()        # complété en 12.4 (les fonctions de l'agent XAI y sont définies)
pd.DataFrame([{"id": m["id"], "étape": m["étape"], "règles de": m["objet"], "fonctions documentées": m["pourquoi"].count(" : "),
               "seuils": ", ".join(f"{k} = {v}" for k, v in m["preuves"].items()) or "—"} for m in METHODS])
