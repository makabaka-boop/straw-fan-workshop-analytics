import pytest
import pandas as pd
import numpy as np
from src.processing import process_data, filter_data, check_has_missing
from src.analysis import (
    analyze_missing_concentration,
    analyze_rework_anomalies,
    analyze_helper_workload,
    generate_material_suggestions,
    compute_daily_rework_stats,
    compute_overview_metrics,
)
from src.mapping import auto_map_columns


class TestEdgeCaseNoDate:
    def test_process_data_all_dates_na(self):
        df = pd.DataFrame({
            '样式名称': ['牡丹团扇', '梅花团扇'],
            '分组编号': ['A组', 'B组'],
            '完成数量': [10, 20],
        })
        mapping = {
            '样式名称': 'style_name',
            '分组编号': 'group_no',
            '完成数量': 'completed_count',
        }
        result = process_data(df, mapping)
        assert result is not None
        assert len(result) == 2
        assert result['record_date'].isna().all()

    def test_daily_rework_stats_returns_none_no_dates(self, processed_no_date_df):
        result = compute_daily_rework_stats(processed_no_date_df)
        assert result is None

    def test_material_suggestions_no_dates(self, processed_no_date_df):
        result = generate_material_suggestions(processed_no_date_df, recent_days=30)
        assert result is not None
        assert len(result) > 0

    def test_overview_metrics_no_dates(self, processed_no_date_df):
        result = compute_overview_metrics(processed_no_date_df)
        assert result['total_completed'] > 0
        assert result['active_groups'] > 0

    def test_filter_without_date_range_no_effect(self, processed_no_date_df):
        result = filter_data(processed_no_date_df)
        assert len(result) == len(processed_no_date_df)


class TestEdgeCaseEmptyFilter:
    def test_empty_style_filter_returns_empty(self, processed_df):
        result = filter_data(processed_df, selected_styles=[])
        assert len(result) == 0

    def test_empty_group_filter_returns_empty(self, processed_df):
        result = filter_data(processed_df, selected_groups=[])
        assert len(result) == 0

    def test_empty_helper_filter_returns_empty(self, processed_df):
        result = filter_data(processed_df, selected_helpers=[])
        assert len(result) == 0

    def test_empty_status_filter_returns_empty(self, processed_df):
        result = filter_data(processed_df, selected_statuses=[])
        assert len(result) == 0

    def test_multiple_empty_filters_empty(self, processed_df):
        result = filter_data(
            processed_df,
            selected_styles=[],
            selected_groups=['A组'],
        )
        assert len(result) == 0


class TestEdgeCaseAbnormalFields:
    def test_mixed_type_numeric_columns(self):
        df = pd.DataFrame({
            '样式名称': ['牡丹', '梅花', '兰花'],
            '完成数量': ['abc', '10', 20],
            '返工数量': [None, 'xyz', 2],
        })
        mapping = {
            '样式名称': 'style_name',
            '完成数量': 'completed_count',
            '返工数量': 'rework_count',
        }
        result = process_data(df, mapping)
        assert result['completed_count'].dtype == int
        assert result['rework_count'].dtype == int
        assert result['completed_count'].iloc[0] == 0
        assert result['completed_count'].iloc[1] == 10

    def test_all_nan_numeric_columns(self):
        df = pd.DataFrame({
            '样式名称': ['牡丹', '梅花'],
            '完成数量': [np.nan, np.nan],
            '返工数量': [np.nan, np.nan],
        })
        mapping = {
            '样式名称': 'style_name',
            '完成数量': 'completed_count',
            '返工数量': 'rework_count',
        }
        result = process_data(df, mapping)
        assert (result['completed_count'] == 0).all()
        assert (result['rework_count'] == 0).all()

    def test_whitespace_string_fields(self):
        df = pd.DataFrame({
            '样式名称': ['  ', '\t', '\n'],
            '完成数量': [10, 20, 30],
        })
        mapping = {
            '样式名称': 'style_name',
            '完成数量': 'completed_count',
        }
        result = process_data(df, mapping)
        assert len(result) == 0

    def test_mixed_case_missing_values(self):
        test_cases = [
            'NaN', 'Nan', 'NONE', 'Null', 'N/A',
            '无', '没有', '无缺件'
        ]
        for val in test_cases:
            assert check_has_missing(val) is False, f"Failed for: {val}"

    def test_unusual_date_formats(self):
        df = pd.DataFrame({
            '样式名称': ['牡丹', '梅花'],
            '记录日期': ['2026/01/01', 'invalid-date'],
            '完成数量': [10, 20],
        })
        mapping = {
            '样式名称': 'style_name',
            '记录日期': 'record_date',
            '完成数量': 'completed_count',
        }
        result = process_data(df, mapping)
        assert pd.notna(result['record_date'].iloc[0])
        assert pd.isna(result['record_date'].iloc[1])


class TestEdgeCaseEmptyData:
    def test_empty_dataframe_mapping(self):
        df = pd.DataFrame()
        mapping = auto_map_columns(df)
        assert isinstance(mapping, dict)
        assert len(mapping) == 0

    def test_empty_dataframe_process(self):
        df = pd.DataFrame()
        result = process_data(df, {})
        assert result is None

    def test_empty_processed_data_analysis(self):
        df = pd.DataFrame({
            'record_date': pd.to_datetime([]),
            'style_name': [],
            'group_no': [],
            'missing_parts': [],
            'completed_count': [],
            'rework_count': [],
            'helper_name': [],
            'has_missing': [],
            'has_rework': [],
            'status': [],
        })
        assert analyze_missing_concentration(df) is None
        assert analyze_rework_anomalies(df) is None

    def test_empty_data_suggestions(self):
        df = pd.DataFrame()
        result = generate_material_suggestions(df)
        assert result is None


class TestEdgeCaseSingleRow:
    def test_single_row_process(self):
        df = pd.DataFrame({
            '样式名称': ['牡丹团扇'],
            '完成数量': [10],
            '返工数量': [0],
        })
        mapping = {
            '样式名称': 'style_name',
            '完成数量': 'completed_count',
            '返工数量': 'rework_count',
        }
        result = process_data(df, mapping)
        assert len(result) == 1
        assert result['status'].iloc[0] == '已完成'

    def test_single_row_all_statuses(self):
        test_cases = [
            ({'has_missing': True, 'has_rework': True, 'completed_count': 5}, '缺件+返工'),
            ({'has_missing': True, 'has_rework': False, 'completed_count': 5}, '缺件待补'),
            ({'has_missing': False, 'has_rework': True, 'completed_count': 5}, '返工中'),
            ({'has_missing': False, 'has_rework': False, 'completed_count': 5}, '已完成'),
            ({'has_missing': False, 'has_rework': False, 'completed_count': 0}, '进行中'),
        ]
        from src.processing import _compute_status_vectorized
        for row_dict, expected in test_cases:
            df = pd.DataFrame([row_dict])
            result = _compute_status_vectorized(df)
            assert result[0] == expected


class TestEdgeCaseAllSameValue:
    def test_all_same_style(self, processed_df):
        filtered = filter_data(processed_df, selected_styles=['牡丹团扇'])
        stats = compute_overview_metrics(filtered)
        assert stats['active_groups'] >= 1
        assert stats['total_completed'] > 0

    def test_all_have_missing(self):
        df = pd.DataFrame({
            'style_name': ['A', 'B', 'C'],
            'group_no': ['G1', 'G2', 'G3'],
            'missing_parts': ['竹骨', '丝线', '胶水瓶'],
            'has_missing': [True, True, True],
            'completed_count': [10, 20, 30],
            'rework_count': [0, 0, 0],
            'helper_name': ['李', '王', '张'],
        })
        result = analyze_missing_concentration(df)
        assert result is not None
        assert len(result) == 3


class TestEdgeCaseZeroValues:
    def test_zero_completed_and_rework(self):
        df = pd.DataFrame({
            'style_name': ['A', 'B'],
            'completed_count': [0, 0],
            'rework_count': [0, 0],
            'has_missing': [False, False],
            'group_no': ['G1', 'G2'],
            'helper_name': ['李', '王'],
        })
        result = compute_overview_metrics(df)
        assert result['total_completed'] == 0
        assert result['total_rework'] == 0
        assert result['rework_rate'] == 0

    def test_zero_rework_rate_stable(self):
        df = pd.DataFrame({
            'helper_name': ['李老师'],
            'completed_count': [0],
            'rework_count': [0],
            'group_no': ['A组'],
            'style_name': ['样式A'],
            'has_missing': [False],
        })
        result = analyze_helper_workload(df)
        assert '返工率' in result.columns
        assert result.iloc[0]['返工率'] == 0
