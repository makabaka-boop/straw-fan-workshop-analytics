import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, date
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings
warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="草编团扇工作坊分析工作台",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

FIELD_TYPES = {
    'record_date': 'datetime',
    'style_name': 'string',
    'group_no': 'string',
    'missing_parts': 'string',
    'completed_count': 'numeric',
    'rework_count': 'numeric',
    'helper_name': 'string',
    'note': 'string'
}

def init_session_state():
    if 'raw_data' not in st.session_state:
        st.session_state.raw_data = None
    if 'processed_data' not in st.session_state:
        st.session_state.processed_data = None
    if 'column_mapping' not in st.session_state:
        st.session_state.column_mapping = {}
    if 'data_type' not in st.session_state:
        st.session_state.data_type = None

def load_csv(uploaded_file):
    try:
        df = pd.read_csv(uploaded_file)
        return df
    except Exception as e:
        st.error(f"文件读取失败: {e}")
        return None

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

def manual_mapping_ui(df):
    st.subheader("📋 列名映射配置")
    st.info("请将CSV文件中的列名映射到标准字段，未映射的列将被忽略")
    
    mapping = {}
    df_cols = ['--- 不映射 ---'] + df.columns.tolist()
    auto_mapped = auto_map_columns(df)
    
    for std_field, std_name in STANDARD_FIELDS.items():
        field_type = FIELD_TYPES[std_field]
        type_hint = f" ({field_type})"
        
        default_idx = 0
        for col, mapped_field in auto_mapped.items():
            if mapped_field == std_field:
                if col in df_cols:
                    default_idx = df_cols.index(col)
                    break
        
        selected = st.selectbox(
            f"{std_name}{type_hint}",
            df_cols,
            index=default_idx,
            key=f"map_{std_field}"
        )
        
        if selected != '--- 不映射 ---':
            mapping[selected] = std_field
    
    return mapping

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
    
    result['source_type'] = st.session_state.get('data_type', 'general')
    def check_has_missing(x):
        if pd.isna(x):
            return False
        x_str = str(x).strip().lower()
        return x_str not in ['', 'nan', 'none', '无', '没有', '无缺件', '0', '-', '/', 'n/a', 'null']
    
    result['has_missing'] = result['missing_parts'].apply(check_has_missing)
    result['has_rework'] = result['rework_count'] > 0
    result['status'] = result.apply(determine_status, axis=1)
    
    return result

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

def style_dataframe(df, numeric_cols=None):
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

def main():
    init_session_state()
    
    st.title("🎭 草编团扇工作坊分析工作台")
    st.markdown("---")
    
    with st.sidebar:
        st.header("📁 数据上传")
        
        data_type = st.selectbox(
            "数据类型",
            ['材料发放记录', '完成清单', '返工台账', '综合数据'],
            index=3
        )
        type_map = {'材料发放记录': 'material', '完成清单': 'completion', '返工台账': 'rework', '综合数据': 'general'}
        st.session_state.data_type = type_map[data_type]
        
        uploaded_file = st.file_uploader("上传CSV文件", type=['csv'])
        
        if uploaded_file is not None:
            df = load_csv(uploaded_file)
            if df is not None:
                st.session_state.raw_data = df
                st.success(f"成功加载 {len(df)} 条记录")
                
                with st.expander("🔍 查看原始数据"):
                    st.dataframe(df.head(10), use_container_width=True)
                
                mapping = manual_mapping_ui(df)
                st.session_state.column_mapping = mapping
                
                if st.button("✅ 确认映射并处理数据", type="primary"):
                    processed = process_data(df, mapping)
                    if processed is not None:
                        st.session_state.processed_data = processed
                        st.success(f"数据处理完成，共 {len(processed)} 条有效记录")
        
        st.markdown("---")
        st.header("🔍 数据筛选")
        
        df = st.session_state.processed_data
        filtered_df = df.copy() if df is not None else None
        
        if filtered_df is not None and not filtered_df.empty:
            has_valid_dates = filtered_df['record_date'].notna().any()
            if has_valid_dates:
                min_date = filtered_df['record_date'].dropna().min().date()
                max_date = filtered_df['record_date'].dropna().max().date()
                date_range = st.date_input(
                    "日期范围",
                    value=(min_date, max_date),
                    min_value=min_date,
                    max_value=max_date
                )
                use_date_filter = True
            else:
                st.info("ℹ️ 数据中未检测到有效日期，已跳过日期筛选")
                use_date_filter = False
            
            styles = sorted(filtered_df['style_name'].unique().tolist())
            selected_styles = st.multiselect("样式名称", styles, default=styles)
            
            groups = sorted(filtered_df['group_no'].unique().tolist())
            selected_groups = st.multiselect("分组编号", groups, default=groups)
            
            helpers = sorted(filtered_df['helper_name'].unique().tolist())
            selected_helpers = st.multiselect("助理姓名", helpers, default=helpers)
            
            statuses = sorted(filtered_df['status'].unique().tolist())
            selected_statuses = st.multiselect("状态", statuses, default=statuses)
            
            if use_date_filter and len(date_range) == 2:
                start_date, end_date = date_range
                filtered_df = filtered_df[
                    (filtered_df['record_date'].dt.date >= start_date) &
                    (filtered_df['record_date'].dt.date <= end_date)
                ]
            
            if len(selected_styles) > 0:
                filtered_df = filtered_df[filtered_df['style_name'].isin(selected_styles)]
            else:
                filtered_df = filtered_df.iloc[0:0]
            if len(selected_groups) > 0:
                filtered_df = filtered_df[filtered_df['group_no'].isin(selected_groups)]
            else:
                filtered_df = filtered_df.iloc[0:0]
            if len(selected_helpers) > 0:
                filtered_df = filtered_df[filtered_df['helper_name'].isin(selected_helpers)]
            else:
                filtered_df = filtered_df.iloc[0:0]
            if len(selected_statuses) > 0:
                filtered_df = filtered_df[filtered_df['status'].isin(selected_statuses)]
            else:
                filtered_df = filtered_df.iloc[0:0]
            
            st.session_state.filtered_data = filtered_df
            
            st.info(f"筛选后共 {len(filtered_df)} 条记录")
        
        if st.button("🔄 重置数据"):
            st.session_state.raw_data = None
            st.session_state.processed_data = None
            st.session_state.column_mapping = {}
            st.rerun()
    
    if filtered_df is None or filtered_df.empty:
        st.info("👈 请在左侧上传CSV文件开始分析")
        
        st.markdown("""
        ### 📖 使用说明
        
        **支持的字段：**
        - `record_date` - 记录日期
        - `style_name` - 样式名称
        - `group_no` - 分组编号
        - `missing_parts` - 缺件名称
        - `completed_count` - 完成数量
        - `rework_count` - 返工数量
        - `helper_name` - 助理姓名
        - `note` - 备注
        
        **功能特点：**
        - 📊 多维度看板展示
        - 🔍 智能异常检测
        - 💡 备料建议分析
        - 🎯 实时状态追踪
        """)
        return
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 总览看板",
        "⚠️ 异常分析",
        "👥 助理负载",
        "📋 待补件列表",
        "💡 备料建议"
    ])
    
    with tab1:
        st.header("📊 总览看板")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            total_completed = filtered_df['completed_count'].sum()
            st.metric("总完成数", f"{total_completed:,}")
        with col2:
            total_rework = filtered_df['rework_count'].sum()
            st.metric("总返工数", f"{total_rework:,}")
        with col3:
            rework_rate = (total_rework / (total_completed + total_rework) * 100) if (total_completed + total_rework) > 0 else 0
            st.metric("返工率", f"{rework_rate:.1f}%")
        with col4:
            missing_count = filtered_df['has_missing'].sum()
            st.metric("缺件记录", f"{missing_count}")
        with col5:
            active_groups = filtered_df['group_no'].nunique()
            st.metric("活跃分组", f"{active_groups}")
        
        st.markdown("---")
        
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("📈 不同样式完成率")
            
            style_stats = filtered_df.groupby('style_name').agg(
                完成数=('completed_count', 'sum'),
                返工数=('rework_count', 'sum'),
                缺件数=('has_missing', 'sum')
            ).reset_index()
            
            style_stats['总数'] = style_stats['完成数'] + style_stats['返工数']
            style_stats['完成率'] = (style_stats['完成数'] / style_stats['总数'] * 100).round(2)
            style_stats = style_stats.sort_values('完成率', ascending=True)
            
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
            st.plotly_chart(fig, use_container_width=True)
        
        with col_right:
            st.subheader("📉 返工趋势")
            
            daily_rework = filtered_df.copy()
            daily_rework = daily_rework.dropna(subset=['record_date'])
            
            if len(daily_rework) > 0:
                daily_rework['日期'] = daily_rework['record_date'].dt.date
                
                daily_stats = daily_rework.groupby('日期').agg(
                    完成数=('completed_count', 'sum'),
                    返工数=('rework_count', 'sum')
                ).reset_index()
                
                daily_stats['返工率'] = (daily_stats['返工数'] / (daily_stats['完成数'] + daily_stats['返工数']) * 100).round(2)
                
                fig = make_subplots(specs=[[{"secondary_y": True}]])
                
                fig.add_trace(
                    go.Bar(x=daily_stats['日期'], y=daily_stats['返工数'], name='返工数量', marker_color='#ff9800'),
                    secondary_y=False,
                )
                
                fig.add_trace(
                    go.Scatter(x=daily_stats['日期'], y=daily_stats['返工率'], name='返工率(%)', mode='lines+markers', line=dict(color='#f44336', width=2)),
                    secondary_y=True,
                )
                
                fig.update_layout(title='每日返工趋势', barmode='group')
                fig.update_yaxes(title_text="返工数量", secondary_y=False)
                fig.update_yaxes(title_text="返工率(%)", secondary_y=True, range=[0, 100])
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("ℹ️ 数据中未检测到有效日期，无法展示返工趋势图")
        
        st.markdown("---")
        
        st.subheader("🔻 材料缺口分析")
        
        missing_analysis = analyze_missing_concentration(filtered_df)
        if missing_analysis is not None and len(missing_analysis) > 0:
            col_m1, col_m2 = st.columns([1.5, 1])
            
            with col_m1:
                fig = px.bar(
                    missing_analysis.reset_index().head(10),
                    x='missing_part',
                    y='出现次数',
                    title='Top 10 缺件材料',
                    color='出现次数',
                    color_continuous_scale='Reds',
                    text='出现次数',
                    hover_data={'涉及分组': True, '涉及样式': True}
                )
                fig.update_layout(xaxis_title='材料名称')
                st.plotly_chart(fig, use_container_width=True)
            
            with col_m2:
                st.dataframe(
                    missing_analysis,
                    use_container_width=True,
                    height=400
                )
        else:
            st.success("✅ 当前数据中未发现缺件记录")
    
    with tab2:
        st.header("⚠️ 异常分析")
        
        st.subheader("🔴 缺件集中分析")
        missing_analysis = analyze_missing_concentration(filtered_df)
        if missing_analysis is not None and len(missing_analysis) > 0:
            high_freq = missing_analysis[missing_analysis['出现次数'] >= 3]
            if len(high_freq) > 0:
                st.warning(f"⚠️ 发现 {len(high_freq)} 种高频缺件材料（出现≥3次）")
                for part, row in high_freq.iterrows():
                    st.error(f"🔴 **{part}**: 出现{row['出现次数']}次，涉及{row['涉及分组']}个分组，{row['涉及样式']}种样式")
            st.dataframe(missing_analysis, use_container_width=True)
        else:
            st.success("✅ 当前数据中未发现缺件记录")
        
        st.markdown("---")
        
        st.subheader("🟠 返工异常分析")
        rework_analysis = analyze_rework_anomalies(filtered_df)
        if rework_analysis is not None and len(rework_analysis) > 0:
            high_rework = rework_analysis[rework_analysis['返工率'] > 15]
            if len(high_rework) > 0:
                st.warning(f"⚠️ 发现 {len(high_rework)} 种样式返工率超过15%")
                for style, row in high_rework.iterrows():
                    st.error(f"🟠 **{style}**: 返工率{row['返工率']}%，共返工{row['返工次数']}件")
            st.dataframe(rework_analysis, use_container_width=True)
        else:
            st.success("✅ 当前数据中未发现返工记录")
        
        st.markdown("---")
        
        st.subheader("🟡 分组缺失分析")
        group_missing = analyze_group_missing(filtered_df)
        if group_missing is not None and len(group_missing) > 0:
            high_missing_groups = group_missing[group_missing['缺件记录数'] >= 2]
            if len(high_missing_groups) > 0:
                st.warning(f"⚠️ 发现 {len(high_missing_groups)} 个分组多次出现缺件")
                for group, row in high_missing_groups.iterrows():
                    st.error(f"🟡 **{group}**: 缺件{row['缺件记录数']}次，涉及{row['涉及样式']}种样式")
            st.dataframe(group_missing, use_container_width=True)
        else:
            st.success("✅ 当前数据中未发现分组缺件")
    
    with tab3:
        st.header("👥 助理负载分析")
        
        helper_stats = analyze_helper_workload(filtered_df)
        
        if len(helper_stats) > 0:
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("📊 助理工作量分布")
                fig = px.bar(
                    helper_stats.reset_index(),
                    x='helper_name',
                    y=['完成总数', '返工总数'],
                    title='各助理完成与返工数量对比',
                    barmode='stack',
                    color_discrete_map={'完成总数': '#4caf50', '返工总数': '#ff9800'}
                )
                fig.update_layout(xaxis_title='助理姓名', yaxis_title='数量')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.subheader("📈 助理返工率对比")
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
                st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            st.subheader("📋 详细负载数据")
            st.dataframe(helper_stats, use_container_width=True)
        else:
            st.info("暂无助理数据")
    
    with tab4:
        st.header("📋 待补件组列表")
        
        pending_list = get_pending_materials(filtered_df)
        
        if pending_list is not None and len(pending_list) > 0:
            st.warning(f"⚠️ 当前有 {len(pending_list)} 个待补件记录")
            
            for idx, row in pending_list.iterrows():
                with st.expander(f"📦 {row['group_no']} - {row['style_name']}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("缺件材料", row['missing_parts'])
                    with col2:
                        st.metric("负责助理", row['助理'])
                    with col3:
                        st.metric("记录日期", row['记录日期'].strftime('%Y-%m-%d') if pd.notna(row['记录日期']) else '未知')
                    
                    col4, col5 = st.columns(2)
                    with col4:
                        st.metric("已完成数量", row['完成数量'])
                    with col5:
                        if row['备注'] and row['备注'] not in ['', 'nan']:
                            st.info(f"备注: {row['备注']}")
            
            st.markdown("---")
            st.subheader("📊 待补件汇总表")
            st.dataframe(pending_list, use_container_width=True)
        else:
            st.success("✅ 当前没有待补件记录")
    
    with tab5:
        st.header("💡 备料建议")
        
        recent_days = st.slider("分析最近多少天的数据", 7, 90, 30, key="suggestion_days")
        
        suggestions = generate_material_suggestions(filtered_df, recent_days)
        
        if suggestions is not None and len(suggestions) > 0:
            st.info(f"基于近 {recent_days} 天的数据分析，为下一场工作坊提供以下备料建议：")
            
            high_priority = suggestions[suggestions['优先级'] == '高']
            medium_priority = suggestions[suggestions['优先级'] == '中']
            
            if len(high_priority) > 0:
                st.subheader("🔴 高优先级建议")
                for _, row in high_priority.iterrows():
                    with st.container():
                        col1, col2, col3 = st.columns([1, 2, 2])
                        with col1:
                            st.error(f"**{row['类型']}**")
                        with col2:
                            st.write(f"**{row['材料/样式']}**: {row['问题描述']}")
                        with col3:
                            st.success(f"💡 {row['建议措施']}")
            
            if len(medium_priority) > 0:
                st.subheader("🟡 中优先级建议")
                for _, row in medium_priority.iterrows():
                    with st.container():
                        col1, col2, col3 = st.columns([1, 2, 2])
                        with col1:
                            st.warning(f"**{row['类型']}**")
                        with col2:
                            st.write(f"**{row['材料/样式']}**: {row['问题描述']}")
                        with col3:
                            st.info(f"💡 {row['建议措施']}")
            
            st.markdown("---")
            st.subheader("📊 建议汇总表")
            st.dataframe(suggestions, use_container_width=True)
            
            csv = suggestions.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                "📥 下载备料建议报告",
                csv,
                "备料建议报告.csv",
                "text/csv",
                key='download-suggestions'
            )
        else:
            st.info("暂无足够数据生成备料建议")
    
    st.markdown("---")
    with st.expander("📋 查看完整数据"):
        display_cols = [c for c in filtered_df.columns if c not in ['source_type', 'has_missing', 'has_rework']]
        st.dataframe(
            style_dataframe(filtered_df[display_cols], numeric_cols=['completed_count', 'rework_count']),
            use_container_width=True
        )
        
        csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "📥 下载处理后数据",
            csv,
            "工作坊分析数据.csv",
            "text/csv",
            key='download-full-data'
        )

if __name__ == "__main__":
    main()
