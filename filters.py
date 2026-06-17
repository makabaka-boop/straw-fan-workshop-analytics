import pandas as pd


def filter_data(df, date_range=None, selected_styles=None, selected_groups=None,
                selected_helpers=None, selected_statuses=None):
    if df is None or df.empty:
        return df

    filtered = df.copy()

    if date_range is not None and len(date_range) == 2:
        start_date, end_date = date_range
        filtered = filtered[
            (filtered['record_date'].dt.date >= start_date) &
            (filtered['record_date'].dt.date <= end_date)
        ]

    if selected_styles is not None:
        if len(selected_styles) > 0:
            filtered = filtered[filtered['style_name'].isin(selected_styles)]
        else:
            return filtered.iloc[0:0]

    if selected_groups is not None:
        if len(selected_groups) > 0:
            filtered = filtered[filtered['group_no'].isin(selected_groups)]
        else:
            return filtered.iloc[0:0]

    if selected_helpers is not None:
        if len(selected_helpers) > 0:
            filtered = filtered[filtered['helper_name'].isin(selected_helpers)]
        else:
            return filtered.iloc[0:0]

    if selected_statuses is not None:
        if len(selected_statuses) > 0:
            filtered = filtered[filtered['status'].isin(selected_statuses)]
        else:
            return filtered.iloc[0:0]

    return filtered


def has_valid_dates(df):
    if df is None or df.empty:
        return False
    return df['record_date'].notna().any()
