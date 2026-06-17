from config import STANDARD_FIELDS, COLUMN_KEYWORDS


def _match_column_by_keywords(col, std_field):
    col_lower = col.lower()
    std_lower = STANDARD_FIELDS[std_field].lower()
    field_lower = std_field.lower()

    if col_lower == std_lower or col_lower == field_lower:
        return True

    keywords = COLUMN_KEYWORDS.get(std_field, [])
    return any(kw in col_lower or kw in col for kw in keywords)


def auto_map_columns(df):
    mapping = {}
    df_cols = df.columns.tolist()

    for std_field in STANDARD_FIELDS:
        for col in df_cols:
            if _match_column_by_keywords(col, std_field):
                mapping[col] = std_field
                break

    return mapping
