import pandas as pd
import numpy as np
from config.constants import (
    STANDARD_FIELDS,
    MISSING_PART_EMPTY_VALUES,
    FIELD_MAPPING_KEYWORDS,
    DATA_TYPE_DETECTION_KEYWORDS,
    NUMERIC_FIELDS,
    STRING_FIELDS,
)


def detect_data_type(df):
    cols = [c.lower() for c in df.columns]

    has_completed = any(
        kw in c for c in cols for kw in DATA_TYPE_DETECTION_KEYWORDS['completed']
    )
    has_rework = any(
        kw in c for c in cols for kw in DATA_TYPE_DETECTION_KEYWORDS['rework']
    )
    has_missing = any(
        kw in c for c in cols for kw in DATA_TYPE_DETECTION_KEYWORDS['missing']
    )

    if has_rework and not has_completed:
        return 'rework'
    elif has_missing and not has_completed and not has_rework:
        return 'material'
    elif has_completed:
        return 'completion'
    return 'general'


def auto_map_columns(df):
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

            keywords = FIELD_MAPPING_KEYWORDS.get(std_field, [])
            if any(kw in col_lower or kw in col for kw in keywords):
                mapping[col] = std_field
                break

    return mapping


def check_has_missing(x):
    if pd.isna(x):
        return False
    x_str = str(x).strip().lower()
    return x_str not in MISSING_PART_EMPTY_VALUES


def determine_status(row):
    if row['has_missing'] and row['has_rework']:
        return '缺件+返工'
    elif row['has_missing']:
        return '缺件待补'
    elif row['has_rework']:
        return '返工中'
    elif row['completed_count'] > 0:
        return '已完成'
    else:
        return '进行中'


def process_data(df, mapping, source_type='general'):
    if not mapping:
        return None

    processed = df.copy()
    reverse_map = {v: k for k, v in mapping.items()}
    result = pd.DataFrame()

    for std_field in STANDARD_FIELDS.keys():
        if std_field in reverse_map:
            original_col = reverse_map[std_field]
            result[std_field] = processed[original_col]
        else:
            if std_field in NUMERIC_FIELDS:
                result[std_field] = 0
            elif std_field == 'record_date':
                result[std_field] = pd.NaT
            else:
                result[std_field] = ''

    result['record_date'] = pd.to_datetime(result['record_date'], errors='coerce')

    for field in NUMERIC_FIELDS:
        result[field] = pd.to_numeric(result[field], errors='coerce').fillna(0).astype(int)

    for field in STRING_FIELDS:
        result[field] = result[field].astype(str).str.strip()

    result = result[result['style_name'] != '']

    result['source_type'] = source_type
    result['has_missing'] = result['missing_parts'].apply(check_has_missing)
    result['has_rework'] = result['rework_count'] > 0
    result['status'] = result.apply(determine_status, axis=1)

    return result


def filter_data(df, date_range=None, selected_styles=None, selected_groups=None,
                selected_helpers=None, selected_statuses=None):
    filtered = df.copy()

    if date_range is not None and len(date_range) == 2:
        start_date, end_date = date_range
        has_valid_dates = filtered['record_date'].notna().any()
        if has_valid_dates:
            filtered = filtered[
                (filtered['record_date'].dt.date >= start_date) &
                (filtered['record_date'].dt.date <= end_date)
            ]

    if selected_styles is not None:
        if len(selected_styles) > 0:
            filtered = filtered[filtered['style_name'].isin(selected_styles)]
        else:
            filtered = filtered.iloc[0:0]

    if selected_groups is not None:
        if len(selected_groups) > 0:
            filtered = filtered[filtered['group_no'].isin(selected_groups)]
        else:
            filtered = filtered.iloc[0:0]

    if selected_helpers is not None:
        if len(selected_helpers) > 0:
            filtered = filtered[filtered['helper_name'].isin(selected_helpers)]
        else:
            filtered = filtered.iloc[0:0]

    if selected_statuses is not None:
        if len(selected_statuses) > 0:
            filtered = filtered[filtered['status'].isin(selected_statuses)]
        else:
            filtered = filtered.iloc[0:0]

    return filtered
