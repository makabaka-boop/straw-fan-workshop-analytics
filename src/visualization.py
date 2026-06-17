import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_style_completion_chart(style_stats: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        style_stats,
        y='style_name',
        x='完成率',
        orientation='h',
        title='各样式完成率排行',
        color='完成率',
        color_continuous_scale='RdYlGn',
        text='完成率',
        hover_data={'完成数': True, '返工数': True, '缺件数': True}
    )
    fig.update_layout(xaxis_range=[0, 100])
    return fig


def create_daily_rework_chart(daily_stats: pd.DataFrame) -> go.Figure:
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(x=daily_stats['日期'], y=daily_stats['返工数'], name='返工数量', marker_color='#ff9800'),
        secondary_y=False,
    )

    fig.add_trace(
        go.Scatter(
            x=daily_stats['日期'],
            y=daily_stats['返工率'],
            name='返工率(%)',
            mode='lines+markers',
            line=dict(color='#f44336', width=2)
        ),
        secondary_y=True,
    )

    fig.update_layout(title='每日返工趋势', barmode='group')
    fig.update_yaxes(title_text="返工数量", secondary_y=False)
    fig.update_yaxes(title_text="返工率(%)", secondary_y=True, range=[0, 100])
    return fig


def create_missing_parts_chart(missing_analysis: pd.DataFrame, top_n: int = 10) -> go.Figure:
    data = missing_analysis.reset_index().head(top_n)
    fig = px.bar(
        data,
        x='missing_part',
        y='出现次数',
        title=f'Top {top_n} 缺件材料',
        color='出现次数',
        color_continuous_scale='Reds',
        text='出现次数',
        hover_data={'涉及分组': True, '涉及样式': True}
    )
    fig.update_layout(xaxis_title='材料名称')
    return fig


def create_helper_workload_chart(helper_stats: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        helper_stats.reset_index(),
        x='helper_name',
        y=['完成总数', '返工总数'],
        title='各助理完成与返工数量对比',
        barmode='stack',
        color_discrete_map={'完成总数': '#4caf50', '返工总数': '#ff9800'}
    )
    fig.update_layout(xaxis_title='助理姓名', yaxis_title='数量')
    return fig


def create_helper_rework_rate_chart(helper_stats: pd.DataFrame) -> go.Figure:
    fig = px.bar(
        helper_stats.reset_index(),
        x='helper_name',
        y='返工率',
        title='各助理返工率',
        color='返工率',
        color_continuous_scale='RdYlGn_r',
        text='返工率'
    )
    fig.update_layout(yaxis_range=[0, 100])
    return fig


def style_dataframe(df: pd.DataFrame, numeric_cols: list | None = None):
    if numeric_cols is None:
        numeric_cols = []

    def highlight_status(val):
        if val == '缺件待补':
            return 'background-color: #ffeb3b; color: #333'
        elif val == '返工中':
            return 'background-color: #ff9800; color: white'
        elif val == '缺件+返工':
            return 'background-color: #f44336; color: white'
        elif val == '已完成':
            return 'background-color: #4caf50; color: white'
        return ''

    styled = df.style

    if 'status' in df.columns:
        styled = styled.applymap(highlight_status, subset=['status'])

    for col in numeric_cols:
        if col in df.columns:
            styled = styled.format({col: '{:,.0f}'})

    return styled
