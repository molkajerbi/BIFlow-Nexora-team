tests_view = pd.DataFrame([{"table": n, "lignes": r["rows"], "colonnes": r["columns"], **r["tests"], "OK": r["passed"]}
                           for n, r in ETL_RESULTS.items()]).set_index("table")
test_cols = sorted(c for c in tests_view.columns if c not in {"lignes", "colonnes", "OK"})
tests_view = tests_view[["lignes", "colonnes", *test_cols, "OK"]]
display(tests_view.astype(object).where(tests_view.notna(), "—"))


def fanout_demo() -> pd.DataFrame:
    """Piège du double comptage, cherché automatiquement : un fait « en-tête » avec deux faits « enfants »
    (ex. une commande avec ses articles ET ses paiements). Joindre directement les deux enfants multiplie les lignes."""
    facts = {t for t, r in TABLE_ROLES.items() if r == "fait"}
    for p in facts:
        kids = [r for r in RELATIONSHIPS if r["parent"] == p and r["child"] in facts and not r["aggregate"]]
        for a, b in itertools.permutations(kids, 2):
            m = next((c for c, s in DATA_CONTRACT[a["child"]]["columns"].items() if s in NUMERIC
                      and c not in (DATA_CONTRACT[a["child"]]["grain"] or [])), None)
            col = f"{a['child']}_{m}_sum"
            if m is None or col not in WH.query(f"SELECT * FROM fact_{p} LIMIT 0").columns:
                continue
            naive = WH.query(f"SELECT SUM(x.{q(m)}) AS v FROM stg_{a['child']} x "
                             f"JOIN stg_{b['child']} y ON y.{q(b['fk'])} = x.{q(a['fk'])}")["v"].iloc[0]
            correct = WH.query(f"SELECT SUM({q(col)}) AS v FROM fact_{p}")["v"].iloc[0]
            truth = silver_sum(a["child"], m, SILVER[a["child"]][a["fk"]].isin(SILVER[b["child"]][b["fk"]]))
            df = pd.DataFrame({"méthode": [f"jointure directe {a['child']} × {b['child']} (naïve)",
                                           f"agrégation séparée dans fact_{p} (BIFlow)", "vérité terrain"],
                               f"somme de {m}": [float(naive or 0), float(correct or 0), silver_sum(a["child"], m)]})
            df["écart_vs_vérité_%"] = (100 * (df[f"somme de {m}"] / df[f"somme de {m}"].iloc[2] - 1)).round(2)
            note = (f"Parmi les lignes de {a['child']} qui ont au moins un {b['child']} (somme {truth:,.2f}), "
                    "la jointure directe compte certaines lignes plusieurs fois.")
            AUDIT.log("etl_agent", "fanout_check", {"table": p, "children": [a["child"], b["child"]], "measure": m,
                                                    "results": df.to_dict(orient="records")})
            print(note)
            return df
    print("Aucun couple de faits « enfants » : pas de risque de double comptage dans ce dataset.")
    return pd.DataFrame()


fanout = fanout_demo()
fanout
