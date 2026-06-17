import streamlit as st
import pandas as pd
import numpy as np
import warnings
warnings.filterwarnings('ignore')

from src.config import STANDARD_FIELDS, FIELD_TYPES, DATA_TYPE_MAP
from src.core import (
    auto_map_columns,
    detect_data_type,
    process_data,
    has_valid_dates,
    analyze_missing_concentration,
    analyze_rework_anomalies,
    analyze_group_missing,
    analyze_helper_workload,
    generate_material_suggestions,
    get_pending_materials,
    compute_style_stats,
    compute_daily_rework_stats,
    compute_summary_metrics,
    apply_filters,
    get_unique_values,
    get_date_range,
)
from src.ui import (
    style_dataframe,
    create_completion_rate_chart,
    create_rework_trend_chart,
    create_missing_parts_chart,
    create_helper_workload_chart,
    create_helper_rework_rate_chart,
)

st.set_page_config(
    page_title="草编团扇工作坊分析工作台",
    page_icon="🎭",
    layout="wide",
    initial_sidebar_state="expanded"
)


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


def render_sidebar():
    with st.sidebar:
        st.header("📁 数据上传")

        data_type = st.selectbox(
            "数据类型",
            ['材料发放记录', '完成清单', '返工台账', '综合数据'],
            index=3
        )
        st.session_state.data_type = DATA_TYPE_MAP[data_type]

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
                    processed = process_data(
                        df, mapping,
                        source_type=st.session_state.get('data_type', 'general')
                    )
                    if processed is not None:
                        st.session_state.processed_data = processed
                        st.success(f"数据处理完成，共 {len(processed)} 条有效记录")

        st.markdown("---")
        st.header("🔍 数据筛选")

        df = st.session_state.processed_data
        filtered_df = df.copy() if df is not None else None

        if filtered_df is not None and not filtered_df.empty:
            date_min, date_max = get_date_range(filtered_df)
            if date_min is not None and date_max is not None:
                date_range = st.date_input(
                    "日期范围",
                    value=(date_min, date_max),
                    min_value=date_min,
                    max_value=date_max
                )
                use_date_filter = True
            else:
                st.info("ℹ️ 数据中未检测到有效日期，已跳过日期筛选")
                use_date_filter = False

            styles = get_unique_values(filtered_df, 'style_name')
            selected_styles = st.multiselect("样式名称", styles, default=styles)

            groups = get_unique_values(filtered_df, 'group_no')
            selected_groups = st.multiselect("分组编号", groups, default=groups)

            helpers = get_unique_values(filtered_df, 'helper_name')
            selected_helpers = st.multiselect("助理姓名", helpers, default=helpers)

            statuses = get_unique_values(filtered_df, 'status')
            selected_statuses = st.multiselect("状态", statuses, default=statuses)

            date_range_val = date_range if use_date_filter else None
            filtered_df = apply_filters(
                filtered_df,
                date_range=date_range_val,
                styles=selected_styles,
                groups=selected_groups,
                helpers=selected_helpers,
                statuses=selected_statuses,
            )

            st.session_state.filtered_data = filtered_df

            st.info(f"筛选后共 {len(filtered_df)} 条记录")

        if st.button("🔄 重置数据"):
            st.session_state.raw_data = None
            st.session_state.processed_data = None
            st.session_state.column_mapping = {}
            st.rerun()

    return filtered_df


def render_overview_tab(df):
    st.header("📊 总览看板")

    metrics = compute_summary_metrics(df)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("总完成数", f"{metrics['总完成数']:,}")
    with col2:
        st.metric("总返工数", f"{metrics['总返工数']:,}")
    with col3:
        st.metric("返工率", f"{metrics['返工率']:.1f}%")
    with col4:
        st.metric("缺件记录", f"{metrics['缺件记录']}")
    with col5:
        st.metric("活跃分组", f"{metrics['活跃分组']}")

    st.markdown("---")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("📈 不同样式完成率")
        style_stats = compute_style_stats(df)
        fig = create_completion_rate_chart(style_stats)
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("📉 返工趋势")
        daily_stats = compute_daily_rework_stats(df)
        if daily_stats is not None and len(daily_stats) > 0:
            fig = create_rework_trend_chart(daily_stats)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("ℹ️ 数据中未检测到有效日期，无法展示返工趋势图")

    st.markdown("---")
    st.subheader("🔻 材料缺口分析")

    missing_analysis = analyze_missing_concentration(df)
    if missing_analysis is not None and len(missing_analysis) > 0:
        col_m1, col_m2 = st.columns([1.5, 1])

        with col_m1:
            fig = create_missing_parts_chart(missing_analysis)
            st.plotly_chart(fig, use_container_width=True)

        with col_m2:
            st.dataframe(
                missing_analysis,
                use_container_width=True,
                height=400
            )
    else:
        st.success("✅ 当前数据中未发现缺件记录")


def render_anomaly_tab(df):
    st.header("⚠️ 异常分析")

    st.subheader("🔴 缺件集中分析")
    missing_analysis = analyze_missing_concentration(df)
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
    rework_analysis = analyze_rework_anomalies(df)
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
    group_missing = analyze_group_missing(df)
    if group_missing is not None and len(group_missing) > 0:
        high_missing_groups = group_missing[group_missing['缺件记录数'] >= 2]
        if len(high_missing_groups) > 0:
            st.warning(f"⚠️ 发现 {len(high_missing_groups)} 个分组多次出现缺件")
            for group, row in high_missing_groups.iterrows():
                st.error(f"🟡 **{group}**: 缺件{row['缺件记录数']}次，涉及{row['涉及样式']}种样式")
        st.dataframe(group_missing, use_container_width=True)
    else:
        st.success("✅ 当前数据中未发现分组缺件")


def render_helper_tab(df):
    st.header("👥 助理负载分析")

    helper_stats = analyze_helper_workload(df)

    if len(helper_stats) > 0:
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("📊 助理工作量分布")
            fig = create_helper_workload_chart(helper_stats)
            st.plotly_chart(fig, use_container_width=True)

        with col2:
            st.subheader("📈 助理返工率对比")
            fig = create_helper_rework_rate_chart(helper_stats)
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("📋 详细负载数据")
        st.dataframe(helper_stats, use_container_width=True)
    else:
        st.info("暂无助理数据")


def render_pending_tab(df):
    st.header("📋 待补件组列表")

    pending_list = get_pending_materials(df)

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
                    record_date = row['记录日期']
                    date_str = record_date.strftime('%Y-%m-%d') if pd.notna(record_date) else '未知'
                    st.metric("记录日期", date_str)

                col4, col5 = st.columns(2)
                with col4:
                    st.metric("已完成数量", row['完成数量'])
                with col5:
                    note = row['备注']
                    if note and note not in ['', 'nan']:
                        st.info(f"备注: {note}")

        st.markdown("---")
        st.subheader("📊 待补件汇总表")
        st.dataframe(pending_list, use_container_width=True)
    else:
        st.success("✅ 当前没有待补件记录")


def render_suggestion_tab(df):
    st.header("💡 备料建议")

    recent_days = st.slider("分析最近多少天的数据", 7, 90, 30, key="suggestion_days")

    suggestions = generate_material_suggestions(df, recent_days)

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


def render_full_data_section(df):
    st.markdown("---")
    with st.expander("📋 查看完整数据"):
        display_cols = [c for c in df.columns if c not in ['source_type', 'has_missing', 'has_rework']]
        st.dataframe(
            style_dataframe(df[display_cols], numeric_cols=['completed_count', 'rework_count']),
            use_container_width=True
        )

        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            "📥 下载处理后数据",
            csv,
            "工作坊分析数据.csv",
            "text/csv",
            key='download-full-data'
        )


def render_empty_state():
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


def main():
    init_session_state()

    st.title("🎭 草编团扇工作坊分析工作台")
    st.markdown("---")

    filtered_df = render_sidebar()

    if filtered_df is None or filtered_df.empty:
        render_empty_state()
        return

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 总览看板",
        "⚠️ 异常分析",
        "👥 助理负载",
        "📋 待补件列表",
        "💡 备料建议"
    ])

    with tab1:
        render_overview_tab(filtered_df)
    with tab2:
        render_anomaly_tab(filtered_df)
    with tab3:
        render_helper_tab(filtered_df)
    with tab4:
        render_pending_tab(filtered_df)
    with tab5:
        render_suggestion_tab(filtered_df)

    render_full_data_section(filtered_df)


if __name__ == "__main__":
    main()
