import pandas as pd

from config import STANDARD_FIELDS, NUMERIC_FIELDS, STRING_FIELDS, MISSING_NEGATIVE_VALUES


def check_has_missing(x):
    if pd.isna(x):
        return False
    x_str = str(x).strip().lower()
    return x_str not in MISSING_NEGATIVE_VALUES


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


def _determine_status_row(row):
    return determine_status(row['has_missing'], row['has_rework'], row['completed_count'])


def process_data(df, mapping, source_type='general'):
    if not mapping:
        return None

    processed = df.copy()
    reverse_map = {v: k for k, v in mapping.items()}
    result = pd.DataFrame()

    for std_field in STANDARD_FIELDS:
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
    result['status'] = result.apply(_determine_status_row, axis=1)

    return result
