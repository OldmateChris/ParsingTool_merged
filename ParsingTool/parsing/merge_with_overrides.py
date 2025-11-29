
import pandas as pd
KEYS = ["Delivery Number", "Batch Number"]
def apply_overrides(parsed_df: pd.DataFrame, overrides_df: pd.DataFrame) -> pd.DataFrame:
    for k in KEYS:
        if k not in overrides_df.columns:
            overrides_df[k] = ""
        if k not in parsed_df.columns:
            parsed_df[k] = ""
    merged = parsed_df.merge(overrides_df, on=KEYS, how="left", suffixes=("", "__ovr"))
    for col in list(merged.columns):
        if col.endswith("__ovr"):
            base = col[:-5]
            ovr = col
            def pick(a, b):
                if pd.notna(b) and str(b).strip() != "":
                    return b
                return a
            if base in merged.columns:
                merged[base] = [pick(a, b) for a, b in zip(merged[base], merged[ovr])]
            merged.drop(columns=[ovr], inplace=True)
    return merged
