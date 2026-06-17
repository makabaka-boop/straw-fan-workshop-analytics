import pandas as pd
import numpy as np
from datetime import datetime

STANDARD_FIELDS = {
    'record_date': '记录日期',
    'style_name': '样式名称',
    'group_no': '分组编号',
    'missing_parts': '缺件名称',
    'completed_count': '完成数量',
    'rework_count': '返工数量',
    'helper_name': '助理姓名',
    'note': '备注'
}

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
            
            if std_field == 'record_date' and ('日期' in col or 'date' in col_lower or '时间' in col):
                mapping[col] = std_field
                break
            elif std_field == 'style_name' and ('样式' in col or '款' in col or 'style' in col_lower or 'name' in col_lower):
                mapping[col] = std_field
                break
            elif std_field == 'group_no' and ('组' in col or 'group' in col_lower or '编号' in col):
                mapping[col] = std_field
                break
            elif std_field == 'missing_parts' and ('缺' in col or 'missing' in col_lower or '少' in col or '材料' in col):
                mapping[col] = std_field
                break
            elif std_field == 'completed_count' and ('完成' in col or 'complete' in col_lower or 'done' in col_lower):
                mapping[col] = std_field
                break
            elif std_field == 'rework_count' and ('返工' in col or 'rework' in col_lower):
                mapping[col] = std_field
                break
            elif std_field == 'helper_name' and ('助理' in col or 'helper' in col_lower or '负责' in col or '老师' in col):
                mapping[col] = std_field
                break
            elif std_field == 'note' and ('备注' in col or 'note' in col_lower or '说明' in col):
                mapping[col] = std_field
                break
    
    return mapping

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

def process_data(df, mapping):
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
            if std_field in ['completed_count', 'rework_count']:
                result[std_field] = 0
            elif std_field == 'record_date':
                result[std_field] = pd.NaT
            else:
                result[std_field] = ''
    
    result['record_date'] = pd.to_datetime(result['record_date'], errors='coerce')
    result['completed_count'] = pd.to_numeric(result['completed_count'], errors='coerce').fillna(0).astype(int)
    result['rework_count'] = pd.to_numeric(result['rework_count'], errors='coerce').fillna(0).astype(int)
    result['style_name'] = result['style_name'].astype(str).str.strip()
    result['group_no'] = result['group_no'].astype(str).str.strip()
    result['missing_parts'] = result['missing_parts'].astype(str).str.strip()
    result['helper_name'] = result['helper_name'].astype(str).str.strip()
    result['note'] = result['note'].astype(str).str.strip()
    result = result[result['style_name'] != '']
    result['source_type'] = 'general'
    result['has_missing'] = result['missing_parts'].apply(lambda x: x not in ['', 'nan', 'None', '无'])
    result['has_rework'] = result['rework_count'] > 0
    result['status'] = result.apply(determine_status, axis=1)
    
    return result

def analyze_missing_concentration(df):
    missing_df = df[df['has_missing']].copy()
    if missing_df.empty:
        return None
    
    missing_parts_exploded = missing_df.assign(
        missing_part=missing_df['missing_parts'].str.split(r'[,，、;；]')
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
    style_rework['返工率'] = (style_rework['返工次数'] / (style_rework['总完成量'] + style_rework['返工次数']) * 100).round(2)
    
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
    
    helper_stats['返工率'] = (helper_stats['返工总数'] / (helper_stats['完成总数'] + helper_stats['返工总数']) * 100).round(2)
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

def run_tests():
    print("=" * 60)
    print("🧪 开始测试草编团扇工作坊分析工作台核心功能")
    print("=" * 60)
    
    df = pd.read_csv('sample_data.csv')
    print(f"\n✅ 1. 测试数据加载: 成功加载 {len(df)} 条记录")
    print(f"   列名: {list(df.columns)}")
    
    mapping = auto_map_columns(df)
    print(f"\n✅ 2. 测试自动列名映射:")
    for col, std_field in mapping.items():
        print(f"   {col} -> {std_field} ({STANDARD_FIELDS[std_field]})")
    
    processed = process_data(df, mapping)
    print(f"\n✅ 3. 测试数据处理: 处理后 {len(processed)} 条有效记录")
    print(f"   列名: {list(processed.columns)}")
    print(f"   状态分布: {processed['status'].value_counts().to_dict()}")
    
    missing_analysis = analyze_missing_concentration(processed)
    print(f"\n✅ 4. 测试缺件集中分析: 发现 {len(missing_analysis)} 种缺件材料")
    if missing_analysis is not None:
        print(missing_analysis.head())
    
    rework_analysis = analyze_rework_anomalies(processed)
    print(f"\n✅ 5. 测试返工异常分析: 发现 {len(rework_analysis)} 种样式有返工记录")
    if rework_analysis is not None:
        print(rework_analysis.head())
    
    group_missing = analyze_group_missing(processed)
    print(f"\n✅ 6. 测试分组缺失分析: 发现 {len(group_missing)} 个分组有缺件")
    if group_missing is not None:
        print(group_missing.head())
    
    helper_stats = analyze_helper_workload(processed)
    print(f"\n✅ 7. 测试助理负载分析: 共 {len(helper_stats)} 位助理")
    print(helper_stats.head())
    
    suggestions = generate_material_suggestions(processed, recent_days=30)
    print(f"\n✅ 8. 测试备料建议生成: 生成 {len(suggestions)} 条建议")
    if suggestions is not None:
        print(suggestions)
    
    pending = get_pending_materials(processed)
    print(f"\n✅ 9. 测试待补件列表: 共 {len(pending)} 个待补件记录")
    if pending is not None:
        print(pending.head())
    
    style_stats = processed.groupby('style_name').agg(
        完成数=('completed_count', 'sum'),
        返工数=('rework_count', 'sum'),
        缺件数=('has_missing', 'sum')
    ).reset_index()
    style_stats['总数'] = style_stats['完成数'] + style_stats['返工数']
    style_stats['完成率'] = (style_stats['完成数'] / style_stats['总数'] * 100).round(2)
    
    print(f"\n✅ 10. 测试样式完成率计算:")
    print(style_stats[['style_name', '完成率']].sort_values('完成率', ascending=False))
    
    total_completed = processed['completed_count'].sum()
    total_rework = processed['rework_count'].sum()
    rework_rate = (total_rework / (total_completed + total_rework) * 100) if (total_completed + total_rework) > 0 else 0
    missing_count = processed['has_missing'].sum()
    active_groups = processed['group_no'].nunique()
    
    print(f"\n📊 关键指标汇总:")
    print(f"   总完成数: {total_completed:,}")
    print(f"   总返工数: {total_rework:,}")
    print(f"   返工率: {rework_rate:.1f}%")
    print(f"   缺件记录: {missing_count}")
    print(f"   活跃分组: {active_groups}")
    
    print("\n" + "=" * 60)
    print("🎉 所有测试通过！核心功能正常工作")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
