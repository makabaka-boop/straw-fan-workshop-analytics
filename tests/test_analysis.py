import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from src.core.analysis import (
    analyze_missing_concentration,
    analyze_rework_anomalies,
    analyze_group_missing,
    analyze_helper_workload,
    generate_material_suggestions,
    get_pending_materials,
    compute_style_stats,
    compute_daily_rework_stats,
    compute_summary_metrics,
)


@pytest.fixture
def sample_processed_df():
    dates = pd.date_range('2026-05-01', periods=10, freq='D')
    data = {
        'record_date': list(dates) + list(dates[:5]),
        'style_name': ['牡丹团扇', '梅花团扇', '兰花团扇', '菊花团扇', '牡丹团扇',
                      '梅花团扇', '兰花团扇', '菊花团扇', '牡丹团扇', '梅花团扇',
                      '兰花团扇', '菊花团扇', '牡丹团扇', '梅花团扇', '兰花团扇'],
        'group_no': ['A组', 'B组', 'A组', 'C组', 'B组',
                    'A组', 'C组', 'B组', 'A组', 'C组',
                    'B组', 'A组', 'C组', 'B组', 'A组'],
        'missing_parts': ['竹骨', '丝线', '', '竹骨', '胶水瓶',
                         '', '丝线,装饰纸', '', '竹骨', '',
                         '竹骨,丝线', '', '装饰纸', '丝线', ''],
        'completed_count': [18, 22, 25, 15, 20, 28, 12, 24, 16, 30,
                           18, 22, 20, 26, 30],
        'rework_count': [2, 1, 0, 3, 1, 0, 2, 1, 4, 0,
                        2, 0, 1, 1, 0],
        'helper_name': ['李老师', '王老师', '李老师', '张老师', '王老师',
                       '李老师', '张老师', '王老师', '李老师', '张老师',
                       '王老师', '李老师', '张老师', '王老师', '李老师'],
        'note': ['', '', '', '返工较多', '', '', '多种材料缺失', '',
                '质量问题', '', '', '', '', '', ''],
        'has_missing': [True, True, False, True, True,
                       False, True, False, True, False,
                       True, False, True, True, False],
        'has_rework': [True, True, False, True, True,
                      False, True, True, True, False,
                      True, False, True, True, False],
        'status': ['缺件+返工', '缺件+返工', '已完成', '缺件+返工', '缺件+返工',
                  '已完成', '缺件+返工', '返工中', '缺件+返工', '已完成',
                  '缺件+返工', '已完成', '缺件+返工', '缺件+返工', '已完成'],
    }
    return pd.DataFrame(data)


class TestAnalyzeMissingConcentration:
    def test_basic_function(self, sample_processed_df):
        result = analyze_missing_concentration(sample_processed_df)
        assert result is not None
        assert '出现次数' in result.columns
        assert '涉及分组' in result.columns
        assert '涉及样式' in result.columns

    def test_no_missing_returns_none(self, sample_processed_df):
        df = sample_processed_df.copy()
        df['has_missing'] = False
        result = analyze_missing_concentration(df)
        assert result is None

    def test_multi_part_split(self, sample_processed_df):
        result = analyze_missing_concentration(sample_processed_df)
        assert '竹骨' in result.index
        assert '丝线' in result.index


class TestAnalyzeReworkAnomalies:
    def test_basic_function(self, sample_processed_df):
        result = analyze_rework_anomalies(sample_processed_df)
        assert result is not None
        assert '返工次数' in result.columns
        assert '返工率' in result.columns

    def test_no_rework_returns_none(self, sample_processed_df):
        df = sample_processed_df.copy()
        df['rework_count'] = 0
        result = analyze_rework_anomalies(df)
        assert result is None

    def test_rework_rate_calculation(self, sample_processed_df):
        result = analyze_rework_anomalies(sample_processed_df)
        for style, row in result.iterrows():
            expected_rate = (row['返工次数'] / (row['总完成量'] + row['返工次数'])) * 100
            assert abs(row['返工率'] - round(expected_rate, 2)) < 0.01


class TestAnalyzeGroupMissing:
    def test_basic_function(self, sample_processed_df):
        result = analyze_group_missing(sample_processed_df)
        assert result is not None
        assert '缺件记录数' in result.columns
        assert '涉及样式' in result.columns

    def test_all_groups_present(self, sample_processed_df):
        result = analyze_group_missing(sample_processed_df)
        assert len(result) == 3


class TestAnalyzeHelperWorkload:
    def test_basic_function(self, sample_processed_df):
        result = analyze_helper_workload(sample_processed_df)
        assert result is not None
        assert '完成总数' in result.columns
        assert '返工率' in result.columns

    def test_fillna_zero(self, sample_processed_df):
        result = analyze_helper_workload(sample_processed_df)
        assert result.isnull().sum().sum() == 0


class TestGetPendingMaterials:
    def test_basic_function(self, sample_processed_df):
        result = get_pending_materials(sample_processed_df)
        assert result is not None
        assert '缺件材料' not in result.columns
        assert 'missing_parts' in result.columns

    def test_no_pending_returns_none(self, sample_processed_df):
        df = sample_processed_df.copy()
        df['has_missing'] = False
        result = get_pending_materials(df)
        assert result is None


class TestGenerateMaterialSuggestions:
    def test_basic_function(self, sample_processed_df):
        result = generate_material_suggestions(sample_processed_df, recent_days=30)
        assert result is not None
        assert len(result) > 0
        assert '类型' in result.columns
        assert '优先级' in result.columns

    def test_empty_df_returns_none(self):
        df = pd.DataFrame(columns=['record_date', 'style_name', 'completed_count', 'rework_count'])
        result = generate_material_suggestions(df)
        assert result is None

    def test_recent_days_filter(self, sample_processed_df):
        result_7 = generate_material_suggestions(sample_processed_df, recent_days=7)
        result_30 = generate_material_suggestions(sample_processed_df, recent_days=30)
        assert len(result_7) <= len(result_30)


class TestComputeStyleStats:
    def test_basic_function(self, sample_processed_df):
        result = compute_style_stats(sample_processed_df)
        assert result is not None
        assert '完成率' in result.columns
        assert '总数' in result.columns

    def test_completion_rate_between_0_and_100(self, sample_processed_df):
        result = compute_style_stats(sample_processed_df)
        assert result['完成率'].min() >= 0
        assert result['完成率'].max() <= 100


class TestComputeDailyReworkStats:
    def test_basic_function(self, sample_processed_df):
        result = compute_daily_rework_stats(sample_processed_df)
        assert result is not None
        assert '返工率' in result.columns

    def test_no_dates_returns_none(self):
        df = pd.DataFrame({
            'record_date': pd.to_datetime([pd.NaT, pd.NaT]),
            'completed_count': [10, 5],
            'rework_count': [2, 1],
        })
        result = compute_daily_rework_stats(df)
        assert result is None


class TestComputeSummaryMetrics:
    def test_basic_function(self, sample_processed_df):
        result = compute_summary_metrics(sample_processed_df)
        assert '总完成数' in result
        assert '返工率' in result
        assert result['总完成数'] > 0

    def test_zero_total_no_error(self):
        df = pd.DataFrame({
            'completed_count': [0, 0],
            'rework_count': [0, 0],
            'has_missing': [False, False],
            'group_no': ['A', 'B'],
        })
        result = compute_summary_metrics(df)
        assert result['返工率'] == 0
