tests_view = pd.DataFrame([{"table": n, "rows": r["rows"], "columns": r["columns"], **r["tests"], "OK": r["passed"]}
                           for n, r in ETL_RESULTS.items()]).set_index("table")
test_cols = sorted(c for c in tests_view.columns if c not in {"rows", "columns", "OK"})
tests_view = tests_view[["rows", "columns", *test_cols, "OK"]]
display(tests_view.astype(object).where(tests_view.notna(), "—"))


def fanout_demo() -> pd.DataFrame:
    """Double-counting trap, looked for automatically: a "header" fact with two "child" facts
    (e.g. an order with its items AND its payments). Directly joining the two children multiplies the rows."""
    facts = {t for t, r in TABLE_ROLES.items() if r == "fact"}
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
            df = pd.DataFrame({"method": [f"direct join {a['child']} × {b['child']} (naive)",
                                          f"separate aggregation in fact_{p} (BIFlow)", "ground truth"],
                               f"sum of {m}": [float(naive or 0), float(correct or 0), silver_sum(a["child"], m)]})
            df["gap_vs_truth_%"] = (100 * (df[f"sum of {m}"] / df[f"sum of {m}"].iloc[2] - 1)).round(2)
            note = (f"Among the rows of {a['child']} that have at least one {b['child']} (sum {truth:,.2f}), "
                    "the direct join counts some rows several times.")
            AUDIT.log("etl_agent", "fanout_check", {"table": p, "children": [a["child"], b["child"]], "measure": m,
                                                    "results": df.to_dict(orient="records")})
            print(note)
            return df
    print('No pair of "child" facts: no risk of double counting in this dataset.')
    return pd.DataFrame()


fanout = fanout_demo()
fanout
