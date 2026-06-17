import pandas as pd
import numpy as np
from src.config import (
    STANDARD_FIELDS,
    MISSING_PART_EMPTY_VALUES,
    NUMERIC_FIELDS,
    STRING_FIELDS,
    DEFAULT_SOURCE_TYPE,
)


def check_has_missing(value) -> bool:
    if pd.isna(value):
        return False
    value_str = str(value).strip().lower()
    return value_str not in MISSING_PART_EMPTY_VALUES


def determine_status(row: pd.Series) -> str:
    has_missing = row['has_missing']
    has_rework = row['has_rework']
    completed = row['completed_count']

    if has_missing and has_rework:
        return '缺件+返工'
    elif has_missing:
        return '缺件待补'
    elif has_rework:
        return '返工中'
    elif completed > 0:
        return '已完成'
    else:
        return '进行中'


def _compute_status_vectorized(df: pd.DataFrame) -> pd.Series:
    conditions = [
        df['has_missing'] & df['has_rework'],
        df['has_missing'] & ~df['has_rework'],
        ~df['has_missing'] & df['has_rework'],
        (~df['has_missing'] & ~df['has_rework']) & (df['completed_count'] > 0),
    ]
    choices = ['缺件+返工', '缺件待补', '返工中', '已完成']
    return np.select(conditions, choices, default='进行中')


def process_data(df: pd.DataFrame, mapping: dict, source_type: str = DEFAULT_SOURCE_TYPE) -> pd.DataFrame | None:
    if not mapping:
        return None

    reverse_map = {v: k for k, v in mapping.items()}
    result = pd.DataFrame()

    for std_field in STANDARD_FIELDS.keys():
        if std_field in reverse_map:
            original_col = reverse_map[std_field]
            result[std_field] = df[original_col]
        else:
            if std_field in NUMERIC_FIELDS:
                result[std_field] = 0
            elif std_field == 'record_date':
                result[std_field] = pd.NaT
            else:
                result[std_field] = ''

    result['record_date'] = pd.to_datetime(result['record_date'], errors='coerce')

    for col in NUMERIC_FIELDS:
        result[col] = pd.to_numeric(result[col], errors='coerce').fillna(0).astype(int)

    for col in STRING_FIELDS:
        result[col] = result[col].astype(str).str.strip()

    result = result[result['style_name'] != '']

    result['source_type'] = source_type
    result['has_missing'] = result['missing_parts'].apply(check_has_missing)
    result['has_rework'] = result['rework_count'] > 0
    result['status'] = _compute_status_vectorized(result)

    return result


def filter_data(
    df: pd.DataFrame,
    date_range: tuple | None = None,
    selected_styles: list | None = None,
    selected_groups: list | None = None,
    selected_helpers: list | None = None,
    selected_statuses: list | None = None,
) -> pd.DataFrame:
    filtered = df.copy()

    if date_range is not None and len(date_range) == 2:
        start_date, end_date = date_range
        filtered = filtered[
            (filtered['record_date'].dt.date >= start_date) &
            (filtered['record_date'].dt.date <= end_date)
        ]

    filters = [
        ('style_name', selected_styles),
        ('group_no', selected_groups),
        ('helper_name', selected_helpers),
        ('status', selected_statuses),
    ]

    for col, selected in filters:
        if selected is None:
            continue
        if len(selected) > 0:
            filtered = filtered[filtered[col].isin(selected)]
        else:
            filtered = filtered.iloc[0:0]

    return filtered


def has_valid_dates(df: pd.DataFrame) -> bool:
    return bool(df['record_date'].notna().any())
