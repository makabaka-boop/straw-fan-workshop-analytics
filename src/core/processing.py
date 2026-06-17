import pandas as pd
import numpy as np

from src.config.constants import (
    STANDARD_FIELDS,
    MISSING_VALUE_INDICATORS,
    DEFAULT_NUMERIC_FILL,
    DEFAULT_STRING_FILL,
)
from src.core.mapping import reverse_mapping


def check_has_missing(value):
    if pd.isna(value):
        return False
    value_str = str(value).strip().lower()
    return value_str not in MISSING_VALUE_INDICATORS


def determine_status(has_missing, has_rework, completed_count):
    if has_missing and has_rework:
        return '缺件+返工'
    elif has_missing:
        return '缺件待补'
    elif has_rework:
        return '返工中'
    elif completed_count > 0:
        return '已完成'
    else:
        return '进行中'


def _apply_status(row):
    return determine_status(
        has_missing=row['has_missing'],
        has_rework=row['has_rework'],
        completed_count=row['completed_count']
    )


def _fill_missing_field(std_field):
    if std_field in ['completed_count', 'rework_count']:
        return DEFAULT_NUMERIC_FILL
    elif std_field == 'record_date':
        return pd.NaT
    else:
        return DEFAULT_STRING_FILL


def process_data(df, mapping, source_type='general'):
    if not mapping:
        return None

    reverse_map = reverse_mapping(mapping)
    result = pd.DataFrame()

    for std_field in STANDARD_FIELDS.keys():
        if std_field in reverse_map:
            original_col = reverse_map[std_field]
            result[std_field] = df[original_col]
        else:
            result[std_field] = _fill_missing_field(std_field)

    result['record_date'] = pd.to_datetime(result['record_date'], errors='coerce')
    result['completed_count'] = pd.to_numeric(
        result['completed_count'], errors='coerce'
    ).fillna(DEFAULT_NUMERIC_FILL).astype(int)
    result['rework_count'] = pd.to_numeric(
        result['rework_count'], errors='coerce'
    ).fillna(DEFAULT_NUMERIC_FILL).astype(int)

    for col in ['style_name', 'group_no', 'missing_parts', 'helper_name', 'note']:
        result[col] = result[col].where(result[col].notna(), '')
        result[col] = result[col].astype(str).str.strip()

    result = result[(result['style_name'] != '') & (result['style_name'] != 'nan')]

    result['source_type'] = source_type
    result['has_missing'] = result['missing_parts'].apply(check_has_missing)
    result['has_rework'] = result['rework_count'] > 0
    result['status'] = result.apply(_apply_status, axis=1)

    return result


def has_valid_dates(df):
    if 'record_date' not in df.columns:
        return False
    return df['record_date'].notna().any()
