from src.config.constants import STATUS_COLORS


def highlight_status(val):
    return STATUS_COLORS.get(val, '')


def style_dataframe(df, numeric_cols=None):
    if numeric_cols is None:
        numeric_cols = []

    styled = df.style

    if 'status' in df.columns:
        styled = styled.applymap(highlight_status, subset=['status'])

    for col in numeric_cols:
        if col in df.columns:
            styled = styled.format({col: '{:,.0f}'})

    return styled
