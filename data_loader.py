import pandas as pd


def load_csv(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        return df
    except Exception as e:
        raise ValueError(f"文件读取失败: {e}") from e


def detect_data_type(df):
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
