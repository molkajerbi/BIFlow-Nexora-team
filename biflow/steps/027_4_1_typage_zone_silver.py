def convert_types(table: str) -> tuple[pd.DataFrame, list[dict], pd.DataFrame]:
    """Converts each column according to its semantic type. A value that cannot be converted becomes NA and is traced."""
    df = RAW.get(table)
    report, failures = [], []
    for col, sem in DATA_CONTRACT[table]["columns"].items():
        s = df[col]
        if sem == "datetime":
            converted = pd.to_datetime(s, format=dt_format(table, col), errors="coerce")
        elif sem in {"numeric", "geo"}:
            converted = _to_float(s).astype("Float64")
        elif sem == "integer":
            x = _to_float(s)
            converted = x.where(np.floor(x) == x).astype("Int64")      # 2.5 n'est pas un entier : NA
        else:
            converted = s                                              # id, zip, category, text : restent du texte
        failed = s.notna() & converted.isna()
        if failed.any():
            failures.append(df.loc[failed, ["_source_row_id"]].assign(table=table, column=col, raw_value=s[failed]))
        df[col] = converted
        report.append({"table": table, "column": col, "semantic_type": sem, "dtype": str(converted.dtype),
                       "non_null": int(s.notna().sum()), "failed": int(failed.sum())})
    failures_df = pd.concat(failures, ignore_index=True) if failures else pd.DataFrame(
        columns=["_source_row_id", "table", "column", "raw_value"])
    return df, report, failures_df


SILVER, type_report, type_failures = {}, [], []
for t in DATA_CONTRACT:
    SILVER[t], rep, fail = convert_types(t)
    type_report += rep
    type_failures.append(fail)
TYPE_REPORT = pd.DataFrame(type_report)
TYPE_FAILURES = pd.concat(type_failures, ignore_index=True)

AUDIT.log("quality_agent", "types_converted",
          {"columns": len(TYPE_REPORT), "failed_values": int(TYPE_REPORT["failed"].sum()),
           "dtypes": TYPE_REPORT.groupby("dtype").size().to_dict()})
print(f"{len(TYPE_REPORT)} typed columns · {int(TYPE_REPORT['failed'].sum())} value(s) that could not be converted")
TYPE_REPORT.groupby(["semantic_type", "dtype"]).agg(columns=("column", "size"), failures=("failed", "sum"))
