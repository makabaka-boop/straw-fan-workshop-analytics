import pandas as pd


def filter_by_date(df, start_date=None, end_date=None):
    if 'record_date' not in df.columns:
        return df

    filtered = df.copy()

    if start_date is not None:
        filtered = filtered[filtered['record_date'].dt.date >= start_date]

    if end_date is not None:
        filtered = filtered[filtered['record_date'].dt.date <= end_date]

    return filtered


def filter_by_styles(df, selected_styles):
    if not selected_styles:
        return df.iloc[0:0]
    return df[df['style_name'].isin(selected_styles)]


def filter_by_groups(df, selected_groups):
    if not selected_groups:
        return df.iloc[0:0]
    return df[df['group_no'].isin(selected_groups)]


def filter_by_helpers(df, selected_helpers):
    if not selected_helpers:
        return df.iloc[0:0]
    return df[df['helper_name'].isin(selected_helpers)]


def filter_by_statuses(df, selected_statuses):
    if not selected_statuses:
        return df.iloc[0:0]
    return df[df['status'].isin(selected_statuses)]


def apply_filters(df, date_range=None, styles=None, groups=None, helpers=None, statuses=None):
    filtered = df.copy()

    if date_range and len(date_range) == 2:
        start_date, end_date = date_range
        filtered = filter_by_date(filtered, start_date, end_date)

    if styles is not None:
        filtered = filter_by_styles(filtered, styles)

    if groups is not None:
        filtered = filter_by_groups(filtered, groups)

    if helpers is not None:
        filtered = filter_by_helpers(filtered, helpers)

    if statuses is not None:
        filtered = filter_by_statuses(filtered, statuses)

    return filtered


def get_unique_values(df, column):
    if column not in df.columns:
        return []
    return sorted(df[column].unique().tolist())


def get_date_range(df):
    if 'record_date' not in df.columns:
        return None, None

    valid_dates = df['record_date'].dropna()
    if valid_dates.empty:
        return None, None

    min_date = valid_dates.min().date()
    max_date = valid_dates.max().date()
    return min_date, max_date
