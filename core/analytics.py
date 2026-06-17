import pandas as pd
from config.constants import MISSING_PART_SPLIT_PATTERN


def analyze_missing_concentration(df):
    missing_df = df[df['has_missing']].copy()
    if missing_df.empty:
        return None

    missing_parts_exploded = missing_df.assign(
        missing_part=missing_df['missing_parts'].str.split(MISSING_PART_SPLIT_PATTERN)
    ).explode('missing_part')

    missing_parts_exploded['missing_part'] = missing_parts_exploded['missing_part'].str.strip()
    missing_parts_exploded = missing_parts_exploded[missing_parts_exploded['missing_part'] != '']

    part_stats = missing_parts_exploded.groupby('missing_part').agg(
        出现次数=('missing_part', 'count'),
        涉及分组=('group_no', 'nunique'),
        涉及样式=('style_name', 'nunique')
    ).sort_values('出现次数', ascending=False)

    return part_stats


def analyze_rework_anomalies(df):
    rework_df = df[df['rework_count'] > 0].copy()
    if rework_df.empty:
        return None

    style_rework = rework_df.groupby('style_name').agg(
        返工次数=('rework_count', 'sum'),
        涉及记录数=('rework_count', 'count'),
        平均返工量=('rework_count', 'mean')
    ).sort_values('返工次数', ascending=False)

    total_completed = df.groupby('style_name')['completed_count'].sum()
    style_rework['总完成量'] = total_completed
    style_rework['返工率'] = (
        style_rework['返工次数'] / (style_rework['总完成量'] + style_rework['返工次数']) * 100
    ).round(2)

    return style_rework


def analyze_group_missing(df):
    group_missing = df[df['has_missing']].groupby('group_no').agg(
        缺件记录数=('has_missing', 'sum'),
        涉及样式=('style_name', 'nunique'),
        缺件详情=('missing_parts', lambda x: '; '.join(x.unique()))
    ).sort_values('缺件记录数', ascending=False)

    return group_missing


def analyze_helper_workload(df):
    helper_stats = df.groupby('helper_name').agg(
        负责记录数=('helper_name', 'count'),
        完成总数=('completed_count', 'sum'),
        返工总数=('rework_count', 'sum'),
        涉及分组=('group_no', 'nunique'),
        涉及样式=('style_name', 'nunique'),
        缺件记录=('has_missing', 'sum')
    ).sort_values('完成总数', ascending=False)

    helper_stats['返工率'] = (
        helper_stats['返工总数'] / (helper_stats['完成总数'] + helper_stats['返工总数']) * 100
    ).round(2)
    helper_stats = helper_stats.fillna(0)

    return helper_stats


def generate_material_suggestions(df, recent_days=30):
    if df.empty:
        return None

    df = df.copy()
    max_date = df['record_date'].max()
    if pd.isna(max_date):
        recent_df = df
    else:
        cutoff = max_date - pd.Timedelta(days=recent_days)
        recent_df = df[df['record_date'] >= cutoff]

    if recent_df.empty:
        recent_df = df

    missing_analysis = analyze_missing_concentration(recent_df)
    rework_analysis = analyze_rework_anomalies(recent_df)

    suggestions = []

    if missing_analysis is not None and len(missing_analysis) > 0:
        top_missing = missing_analysis.head(5)
        for part, row in top_missing.iterrows():
            suggestions.append({
                '类型': '高频缺件',
                '材料/样式': part,
                '问题描述': f"近{recent_days}天出现{row['出现次数']}次缺件，涉及{row['涉及分组']}个分组",
                '建议措施': f'建议增加{part}的备料量30%-50%',
                '优先级': '高' if row['出现次数'] >= 5 else '中'
            })

    if rework_analysis is not None and len(rework_analysis) > 0:
        high_rework = rework_analysis[rework_analysis['返工率'] > 10].head(3)
        for style, row in high_rework.iterrows():
            suggestions.append({
                '类型': '高返工样式',
                '材料/样式': style,
                '问题描述': f"返工率达{row['返工率']}%，共返工{row['返工次数']}件",
                '建议措施': '建议提前检查材料质量，增加技术指导',
                '优先级': '高' if row['返工率'] > 20 else '中'
            })

    style_demand = recent_df.groupby('style_name').agg(
        总需求量=('completed_count', 'sum'),
        返工量=('rework_count', 'sum')
    ).sort_values('总需求量', ascending=False)

    if len(style_demand) > 0:
        for style, row in style_demand.head(3).iterrows():
            total = row['总需求量'] + row['返工量']
            buffer = int(total * 0.2)
            suggestions.append({
                '类型': '热门样式',
                '材料/样式': style,
                '问题描述': f"近{recent_days}天需求{row['总需求量']}件，返工{row['返工量']}件",
                '建议措施': f'建议额外准备{buffer}件材料作为缓冲',
                '优先级': '中'
            })

    return pd.DataFrame(suggestions)


def get_pending_materials(df):
    pending = df[df['has_missing']].copy()
    if pending.empty:
        return None

    pending_list = pending.groupby(['group_no', 'style_name', 'missing_parts']).agg(
        记录日期=('record_date', 'max'),
        完成数量=('completed_count', 'sum'),
        助理=('helper_name', 'first'),
        备注=('note', 'first')
    ).reset_index()

    pending_list = pending_list.sort_values('记录日期', ascending=False)
    return pending_list


def calculate_style_stats(df):
    style_stats = df.groupby('style_name').agg(
        完成数=('completed_count', 'sum'),
        返工数=('rework_count', 'sum'),
        缺件数=('has_missing', 'sum')
    ).reset_index()

    style_stats['总数'] = style_stats['完成数'] + style_stats['返工数']
    style_stats['完成率'] = (style_stats['完成数'] / style_stats['总数'] * 100).round(2)
    style_stats = style_stats.sort_values('完成率', ascending=True)

    return style_stats


def calculate_daily_stats(df):
    daily_df = df.copy()
    daily_df = daily_df.dropna(subset=['record_date'])

    if len(daily_df) == 0:
        return None

    daily_df['日期'] = daily_df['record_date'].dt.date

    daily_stats = daily_df.groupby('日期').agg(
        完成数=('completed_count', 'sum'),
        返工数=('rework_count', 'sum')
    ).reset_index()

    daily_stats['返工率'] = (
        daily_stats['返工数'] / (daily_stats['完成数'] + daily_stats['返工数']) * 100
    ).round(2)

    return daily_stats


def calculate_summary_metrics(df):
    total_completed = df['completed_count'].sum()
    total_rework = df['rework_count'].sum()
    rework_rate = (total_rework / (total_completed + total_rework) * 100) if (total_completed + total_rework) > 0 else 0
    missing_count = df['has_missing'].sum()
    active_groups = df['group_no'].nunique()

    return {
        'total_completed': total_completed,
        'total_rework': total_rework,
        'rework_rate': rework_rate,
        'missing_count': missing_count,
        'active_groups': active_groups,
    }
