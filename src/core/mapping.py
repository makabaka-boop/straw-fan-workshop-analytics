import pandas as pd

from src.config.constants import STANDARD_FIELDS, FIELD_KEYWORDS


def auto_map_columns(df):
    mapping = {}
    df_cols = df.columns.tolist()

    for std_field, std_name in STANDARD_FIELDS.items():
        keywords = FIELD_KEYWORDS.get(std_field, [])

        for col in df_cols:
            col_lower = col.lower()
            std_lower = std_name.lower()
            field_lower = std_field.lower()

            if col_lower == std_lower or col_lower == field_lower:
                mapping[col] = std_field
                break

            if any(kw.lower() in col_lower for kw in keywords):
                mapping[col] = std_field
                break

    return mapping


def detect_data_type(df):
    cols = [c.lower() for c in df.columns]

    has_completed = any(
        kw in c
        for c in cols
        for kw in ['完成', 'complete', 'done']
    )
    has_rework = any(
        kw in c
        for c in cols
        for kw in ['返工', 'rework']
    )
    has_missing = any(
        kw in c
        for c in cols
        for kw in ['缺', 'missing', '少']
    )

    if has_rework and not has_completed:
        return 'rework'
    elif has_missing and not has_completed and not has_rework:
        return 'material'
    elif has_completed:
        return 'completion'
    return 'general'


def reverse_mapping(mapping):
    return {v: k for k, v in mapping.items()}
