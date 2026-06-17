import pytest
import pandas as pd
import numpy as np
from datetime import date

from src.core import (
    auto_map_columns,
    process_data,
    check_has_missing,
    determine_status,
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
    filter_by_styles,
    filter_by_groups,
    filter_by_helpers,
    filter_by_statuses,
    get_date_range,
    get_unique_values,
)


class TestEdgeCaseNoDateData:
    def setup_method(self):
        self.df_no_date = pd.DataFrame({
            '样式名称': ['牡丹团扇', '梅花团扇', '兰花团扇'],
            '分组编号': ['A组', 'B组', 'C组'],
            '缺件名称': ['', '丝线', ''],
            '完成数量': [20, 15, 25],
            '返工数量': [1, 2, 0],
            '助理姓名': ['李老师', '王老师', '张老师'],
            '备注': ['', '', '']
        })
        self.mapping = {
            '样式名称': 'style_name',
            '分组编号': 'group_no',
            '缺件名称': 'missing_parts',
            '完成数量': 'completed_count',
            '返工数量': 'rework_count',
            '助理姓名': 'helper_name',
            '备注': 'note',
        }

    def test_process_data_without_date_column(self):
        result = process_data(self.df_no_date, self.mapping)
        assert result is not None
        assert len(result) == 3
        assert 'record_date' in result.columns
        assert result['record_date'].isna().all()

    def test_has_valid_dates_returns_false(self):
        result = process_data(self.df_no_date, self.mapping)
        assert has_valid_dates(result) == False

    def test_get_date_range_returns_none(self):
        result = process_data(self.df_no_date, self.mapping)
        min_d, max_d = get_date_range(result)
        assert min_d is None
        assert max_d is None

    def test_daily_rework_stats_returns_none(self):
        result = process_data(self.df_no_date, self.mapping)
        daily_stats = compute_daily_rework_stats(result)
        assert daily_stats is None

    def test_generate_suggestions_without_dates(self):
        result = process_data(self.df_no_date, self.mapping)
        suggestions = generate_material_suggestions(result, recent_days=30)
        assert suggestions is not None
        assert len(suggestions) > 0

    def test_analysis_works_without_dates(self):
        result = process_data(self.df_no_date, self.mapping)
        missing = analyze_missing_concentration(result)
        rework = analyze_rework_anomalies(result)
        helper = analyze_helper_workload(result)
        assert missing is not None
        assert rework is not None
        assert helper is not None


class TestEdgeCaseEmptyFilter:
    def setup_method(self):
        self.df = pd.DataFrame({
            'record_date': pd.to_datetime(['2026-05-01', '2026-05-02', '2026-05-03']),
            'style_name': ['牡丹团扇', '梅花团扇', '兰花团扇'],
            'group_no': ['A组', 'B组', 'A组'],
            'helper_name': ['李老师', '王老师', '李老师'],
            'status': ['已完成', '返工中', '已完成'],
            'completed_count': [20, 15, 25],
            'rework_count': [0, 2, 0],
            'has_missing': [False, False, False],
        })

    def test_empty_styles_filter_returns_empty(self):
        result = filter_by_styles(self.df, [])
        assert len(result) == 0

    def test_empty_groups_filter_returns_empty(self):
        result = filter_by_groups(self.df, [])
        assert len(result) == 0

    def test_empty_helpers_filter_returns_empty(self):
        result = filter_by_helpers(self.df, [])
        assert len(result) == 0

    def test_empty_statuses_filter_returns_empty(self):
        result = filter_by_statuses(self.df, [])
        assert len(result) == 0

    def test_all_empty_filters_returns_empty(self):
        result = apply_filters(
            self.df,
            styles=[],
            groups=[],
            helpers=[],
            statuses=[],
        )
        assert len(result) == 0

    def test_partial_empty_filters(self):
        result = apply_filters(
            self.df,
            styles=['牡丹团扇'],
            groups=[],
        )
        assert len(result) == 0

    def test_summary_metrics_on_empty_df(self):
        empty_df = self.df.iloc[0:0]
        metrics = compute_summary_metrics(empty_df)
        assert metrics['总完成数'] == 0
        assert metrics['总返工数'] == 0
        assert metrics['返工率'] == 0
        assert metrics['缺件记录'] == 0
        assert metrics['活跃分组'] == 0


class TestEdgeCaseAbnormalFields:
    def test_completed_count_with_strings(self):
        df = pd.DataFrame({
            '样式名称': ['test1', 'test2', 'test3'],
            '完成数量': ['abc', '123', None],
        })
        mapping = {
            '样式名称': 'style_name',
            '完成数量': 'completed_count',
        }
        result = process_data(df, mapping)
        assert result['completed_count'].iloc[0] == 0
        assert result['completed_count'].iloc[1] == 123
        assert result['completed_count'].iloc[2] == 0

    def test_rework_count_with_strings(self):
        df = pd.DataFrame({
            '样式名称': ['test1', 'test2'],
            '返工数量': ['not_a_number', '5'],
        })
        mapping = {
            '样式名称': 'style_name',
            '返工数量': 'rework_count',
        }
        result = process_data(df, mapping)
        assert result['rework_count'].dtype == int
        assert result['rework_count'].iloc[0] == 0
        assert result['rework_count'].iloc[1] == 5

    def test_invalid_date_format(self):
        df = pd.DataFrame({
            '样式名称': ['test'],
            '记录日期': ['invalid_date'],
        })
        mapping = {
            '样式名称': 'style_name',
            '记录日期': 'record_date',
        }
        result = process_data(df, mapping)
        assert pd.isna(result['record_date'].iloc[0])

    def test_missing_parts_with_various_formats(self):
        test_cases = [
            ('竹骨,丝线', True),
            ('竹骨，丝线', True),
            ('竹骨、丝线', True),
            ('竹骨;丝线', True),
            ('竹骨；丝线', True),
            ('无', False),
            ('', False),
            (' ', False),
        ]
        for value, has_missing in test_cases:
            assert check_has_missing(value) == has_missing

    def test_auto_map_with_unknown_columns(self):
        df = pd.DataFrame({
            '随机列1': [1, 2, 3],
            '另一列': ['a', 'b', 'c'],
        })
        mapping = auto_map_columns(df)
        assert len(mapping) == 0

    def test_style_name_with_nan(self):
        df = pd.DataFrame({
            '样式名称': [np.nan, '牡丹', ''],
            '完成数量': [10, 20, 30],
        })
        mapping = {
            '样式名称': 'style_name',
            '完成数量': 'completed_count',
        }
        result = process_data(df, mapping)
        assert 'nan' not in result['style_name'].values


class TestEdgeCaseEmptyData:
    def test_empty_dataframe_processing(self):
        df = pd.DataFrame()
        mapping = {}
        result = process_data(df, mapping)
        assert result is None

    def test_empty_dataframe_with_mapping(self):
        df = pd.DataFrame(columns=['样式名称', '完成数量'])
        mapping = {
            '样式名称': 'style_name',
            '完成数量': 'completed_count',
        }
        result = process_data(df, mapping)
        assert result is not None
        assert len(result) == 0

    def test_analysis_on_empty_df(self):
        df = pd.DataFrame(columns=[
            'style_name', 'group_no', 'helper_name', 'status',
            'completed_count', 'rework_count', 'has_missing',
            'record_date', 'missing_parts'
        ])
        assert analyze_missing_concentration(df) is None
        assert analyze_rework_anomalies(df) is None
        assert get_pending_materials(df) is None

    def test_generate_suggestions_empty_df(self):
        df = pd.DataFrame(columns=[
            'record_date', 'style_name', 'completed_count',
            'rework_count', 'has_missing', 'missing_parts',
            'group_no', 'helper_name'
        ])
        result = generate_material_suggestions(df)
        assert result is None

    def test_style_stats_empty_df(self):
        df = pd.DataFrame(columns=[
            'style_name', 'completed_count', 'rework_count', 'has_missing'
        ])
        result = compute_style_stats(df)
        assert len(result) == 0


class TestEdgeCaseSingleRecord:
    def test_single_record_analysis(self):
        df = pd.DataFrame({
            'record_date': pd.to_datetime(['2026-05-01']),
            'style_name': ['牡丹团扇'],
            'group_no': ['A组'],
            'helper_name': ['李老师'],
            'status': ['已完成'],
            'completed_count': [10],
            'rework_count': [0],
            'has_missing': [False],
            'missing_parts': [''],
        })
        metrics = compute_summary_metrics(df)
        assert metrics['总完成数'] == 10
        assert metrics['活跃分组'] == 1

        style_stats = compute_style_stats(df)
        assert len(style_stats) == 1
        assert style_stats.iloc[0]['完成率'] == 100.0


class TestEdgeCaseAllMissingAllRework:
    def test_all_missing(self):
        df = pd.DataFrame({
            'style_name': ['款式A', '款式B'],
            'group_no': ['A组', 'B组'],
            'missing_parts': ['竹骨', '丝线'],
            'completed_count': [5, 3],
            'rework_count': [0, 0],
            'has_missing': [True, True],
            'record_date': pd.to_datetime(['2026-05-01', '2026-05-01']),
            'helper_name': ['李老师', '王老师'],
        })
        result = analyze_missing_concentration(df)
        assert result is not None
        assert len(result) == 2

    def test_all_rework(self):
        df = pd.DataFrame({
            'style_name': ['款式A', '款式B'],
            'group_no': ['A组', 'B组'],
            'missing_parts': ['', ''],
            'completed_count': [5, 3],
            'rework_count': [2, 1],
            'has_missing': [False, False],
            'has_rework': [True, True],
            'record_date': pd.to_datetime(['2026-05-01', '2026-05-01']),
            'helper_name': ['李老师', '王老师'],
        })
        result = analyze_rework_anomalies(df)
        assert result is not None
        assert len(result) == 2
