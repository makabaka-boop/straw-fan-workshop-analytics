import pandas as pd
from src.config import STANDARD_FIELDS

_MATCH_KEYWORDS = {
    'record_date': ['日期', 'date', '时间'],
    'style_name': ['样式', '款', 'style', 'name'],
    'group_no': ['组', 'group', '编号'],
    'missing_parts': ['缺', 'missing', '少', '材料'],
    'completed_count': ['完成', 'complete', 'done'],
    'rework_count': ['返工', 'rework'],
    'helper_name': ['助理', 'helper', '负责', '老师'],
    'note': ['备注', 'note', '说明'],
}


def detect_data_type(df: pd.DataFrame) -> str:
    cols = [c.lower() for c in df.columns]

    has_completed = any('完成' in c or 'complete' in c or 'done' in c for c in cols)
    has_rework = any('返工' in c or 'rework' in c for c in cols)
    has_missing = any('缺' in c or 'missing' in c or '少' in c for c in cols)

    if has_rework and not has_completed:
        return 'rework'
    elif has_missing and not has_completed and not has_rework:
        return 'material'
    elif has_completed:
        return 'completion'
    return 'general'


def auto_map_columns(df: pd.DataFrame) -> dict:
    mapping = {}
    df_cols = df.columns.tolist()

    for std_field, std_name in STANDARD_FIELDS.items():
        for col in df_cols:
            col_lower = col.lower()
            std_lower = std_name.lower()
            field_lower = std_field.lower()

            if col_lower == std_lower or col_lower == field_lower:
                mapping[col] = std_field
                break

            keywords = _MATCH_KEYWORDS.get(std_field, [])
            if any(kw in col_lower or kw in col for kw in keywords):
                mapping[col] = std_field
                break

    return mapping
