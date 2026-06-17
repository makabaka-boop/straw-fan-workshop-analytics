import pytest
import pandas as pd
import numpy as np
from src.analysis import (
    analyze_missing_concentration,
    analyze_rework_anomalies,
    analyze_group_missing,
    analyze_helper_workload,
    compute_style_stats,
    compute_daily_rework_stats,
    compute_overview_metrics,
    generate_material_suggestions,
    get_pending_materials,
)


class TestAnalyzeMissingConcentration:
    def test_returns_dataframe_with_missing(self, processed_df):
        result = analyze_missing_concentration(processed_df)
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert '出现次数' in result.columns
        assert '涉及分组' in result.columns
        assert '涉及样式' in result.columns

    def test_returns_none_when_no_missing(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        df['has_missing'] = False
        result = analyze_missing_concentration(df)
        assert result is None

    def test_explodes_multiple_parts(self, processed_df):
        result = analyze_missing_concentration(processed_df)
        assert '竹骨' in result.index
        assert '丝线' in result.index

    def test_sorted_by_count_desc(self, processed_df):
        result = analyze_missing_concentration(processed_df)
        counts = result['出现次数'].tolist()
        assert counts == sorted(counts, reverse=True)


class TestAnalyzeReworkAnomalies:
    def test_returns_dataframe_with_rework(self, processed_df):
        result = analyze_rework_anomalies(processed_df)
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert '返工次数' in result.columns
        assert '返工率' in result.columns
        assert '总完成量' in result.columns

    def test_returns_none_when_no_rework(self):
        df = pd.DataFrame({
            'style_name': ['A', 'B'],
            'rework_count': [0, 0],
            'completed_count': [10, 20],
            'has_missing': [False, False],
        })
        result = analyze_rework_anomalies(df)
        assert result is None

    def test_rework_rate_calculation(self):
        df = pd.DataFrame({
            'style_name': ['样式A', '样式A', '样式B'],
            'rework_count': [5, 5, 0],
            'completed_count': [90, 90, 100],
            'has_missing': [False, False, False],
        })
        result = analyze_rework_anomalies(df)
        assert '样式A' in result.index
        assert result.loc['样式A', '返工次数'] == 10
        expected_rate = (10 / (180 + 10)) * 100
        assert abs(result.loc['样式A', '返工率'] - round(expected_rate, 2)) < 0.01


class TestAnalyzeGroupMissing:
    def test_returns_dataframe(self, processed_df):
        result = analyze_group_missing(processed_df)
        assert isinstance(result, pd.DataFrame)
        assert '缺件记录数' in result.columns
        assert '涉及样式' in result.columns
        assert '缺件详情' in result.columns

    def test_grouped_by_group_no(self, processed_df):
        result = analyze_group_missing(processed_df)
        assert result.index.name == 'group_no'

    def test_empty_when_no_missing(self, minimal_valid_df):
        df = minimal_valid_df.copy()
        df['has_missing'] = False
        result = analyze_group_missing(df)
        assert len(result) == 0


class TestAnalyzeHelperWorkload:
    def test_returns_dataframe(self, processed_df):
        result = analyze_helper_workload(processed_df)
        assert isinstance(result, pd.DataFrame)
        assert '完成总数' in result.columns
        assert '返工总数' in result.columns
        assert '返工率' in result.columns

    def test_sorted_by_completed_desc(self, processed_df):
        result = analyze_helper_workload(processed_df)
        totals = result['完成总数'].tolist()
        assert totals == sorted(totals, reverse=True)

    def test_rework_rate_between_0_and_100(self, processed_df):
        result = analyze_helper_workload(processed_df)
        assert all(0 <= rate <= 100 for rate in result['返工率'])

    def test_fillna_applied(self):
        df = pd.DataFrame({
            'helper_name': ['李老师', '王老师'],
            'completed_count': [0, 10],
            'rework_count': [0, 2],
            'group_no': ['A组', 'B组'],
            'style_name': ['样式A', '样式B'],
            'has_missing': [False, False],
        })
        result = analyze_helper_workload(df)
        assert not result.isna().any().any()


class TestComputeStyleStats:
    def test_returns_dataframe(self, processed_df):
        result = compute_style_stats(processed_df)
        assert isinstance(result, pd.DataFrame)
        assert '完成率' in result.columns
        assert '总数' in result.columns

    def test_completion_rate_calculation(self):
        df = pd.DataFrame({
            'style_name': ['样式A', '样式A', '样式B'],
            'completed_count': [80, 10, 100],
            'rework_count': [10, 0, 0],
            'has_missing': [False, False, False],
        })
        result = compute_style_stats(df)
        style_a = result[result['style_name'] == '样式A'].iloc[0]
        assert style_a['完成数'] == 90
        assert style_a['返工数'] == 10
        assert style_a['总数'] == 100
        assert style_a['完成率'] == 90.0


class TestComputeDailyReworkStats:
    def test_returns_dataframe_with_dates(self, processed_df):
        result = compute_daily_rework_stats(processed_df)
        assert result is not None
        assert '日期' in result.columns
        assert '返工率' in result.columns

    def test_returns_none_when_no_dates(self, processed_no_date_df):
        result = compute_daily_rework_stats(processed_no_date_df)
        assert result is None


class TestComputeOverviewMetrics:
    def test_returns_dict(self, processed_df):
        result = compute_overview_metrics(processed_df)
        assert isinstance(result, dict)
        expected_keys = ['total_completed', 'total_rework', 'rework_rate', 'missing_count', 'active_groups']
        assert all(k in result for k in expected_keys)

    def test_metrics_positive(self, processed_df):
        result = compute_overview_metrics(processed_df)
        assert result['total_completed'] > 0
        assert result['total_rework'] >= 0
        assert 0 <= result['rework_rate'] <= 100
        assert result['missing_count'] >= 0
        assert result['active_groups'] > 0


class TestGenerateMaterialSuggestions:
    def test_returns_dataframe(self, processed_df):
        result = generate_material_suggestions(processed_df, recent_days=30)
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert '类型' in result.columns
        assert '优先级' in result.columns

    def test_returns_none_for_empty_df(self):
        df = pd.DataFrame()
        result = generate_material_suggestions(df)
        assert result is None

    def test_suggestion_types(self, processed_df):
        result = generate_material_suggestions(processed_df, recent_days=30)
        types = set(result['类型'].unique())
        assert '高频缺件' in types or '高返工样式' in types or '热门样式' in types

    def test_priority_levels(self, processed_df):
        result = generate_material_suggestions(processed_df, recent_days=30)
        priorities = set(result['优先级'].unique())
        assert priorities.issubset({'高', '中'})

    def test_no_date_data_works(self, processed_no_date_df):
        result = generate_material_suggestions(processed_no_date_df, recent_days=30)
        assert result is not None
        assert len(result) > 0


class TestGetPendingMaterials:
    def test_returns_dataframe_with_missing(self, processed_df):
        result = get_pending_materials(processed_df)
        assert result is not None
        assert isinstance(result, pd.DataFrame)
        assert '记录日期' in result.columns
        assert '助理' in result.columns

    def test_returns_none_when_no_missing(self):
        df = pd.DataFrame({
            'has_missing': [False, False],
            'group_no': ['A', 'B'],
            'style_name': ['S1', 'S2'],
            'missing_parts': ['', ''],
            'record_date': pd.to_datetime(['2026-01-01', '2026-01-02']),
            'completed_count': [10, 20],
            'helper_name': ['李', '王'],
            'note': ['', ''],
        })
        result = get_pending_materials(df)
        assert result is None

    def test_sorted_by_date_desc(self, processed_df):
        result = get_pending_materials(processed_df)
        dates = result['记录日期'].tolist()
        valid_dates = [d for d in dates if pd.notna(d)]
        assert valid_dates == sorted(valid_dates, reverse=True)

    def test_grouped_correctly(self, processed_df):
        result = get_pending_materials(processed_df)
        assert 'group_no' in result.columns
        assert 'style_name' in result.columns
