import pytest
import pandas as pd
import numpy as np

from analysis import (
    analyze_missing_concentration,
    analyze_rework_anomalies,
    analyze_group_missing,
    analyze_helper_workload,
    generate_material_suggestions,
    get_pending_materials,
)


def _make_processed_df():
    return pd.DataFrame({
        'record_date': pd.to_datetime([
            '2026-05-01', '2026-05-01', '2026-05-02', '2026-05-02',
            '2026-05-03', '2026-05-03', '2026-05-04', '2026-05-04',
        ]),
        'style_name': ['牡丹团扇', '梅花团扇', '兰花团扇', '菊花团扇',
                        '牡丹团扇', '梅花团扇', '兰花团扇', '菊花团扇'],
        'group_no': ['A组', 'B组', 'A组', 'C组', 'B组', 'A组', 'C组', 'B组'],
        'missing_parts': ['竹骨', '', '丝线', '', '竹骨', '', '丝线,装饰纸', ''],
        'completed_count': [18, 22, 25, 15, 20, 28, 12, 24],
        'rework_count': [2, 1, 0, 3, 1, 0, 2, 1],
        'helper_name': ['李老师', '王老师', '李老师', '张老师',
                         '王老师', '李老师', '张老师', '王老师'],
        'note': ['首次缺件', '', '', '返工较多', '', '', '多种材料缺失', ''],
        'source_type': ['general'] * 8,
        'has_missing': [True, False, True, False, True, False, True, False],
        'has_rework': [True, True, False, True, True, False, True, True],
        'status': ['缺件+返工', '返工中', '缺件待补', '返工中',
                    '缺件+返工', '已完成', '缺件+返工', '返工中'],
    })


class TestAnalyzeMissingConcentration:
    def test_basic_analysis(self):
        df = _make_processed_df()
        result = analyze_missing_concentration(df)
        assert result is not None
        assert '出现次数' in result.columns
        assert '涉及分组' in result.columns
        assert '涉及样式' in result.columns

    def test_top_missing_is_silk_thread(self):
        df = _make_processed_df()
        result = analyze_missing_concentration(df)
        top_part = result.index[0]
        assert top_part == '丝线'

    def test_no_missing_returns_none(self):
        df = _make_processed_df()
        df['has_missing'] = False
        result = analyze_missing_concentration(df)
        assert result is None

    def test_multi_part_split(self):
        df = _make_processed_df()
        result = analyze_missing_concentration(df)
        part_names = result.index.tolist()
        assert '装饰纸' in part_names
        assert '丝线' in part_names

    def test_empty_df(self):
        df = pd.DataFrame(columns=['missing_parts', 'has_missing', 'group_no', 'style_name'])
        result = analyze_missing_concentration(df)
        assert result is None


class TestAnalyzeReworkAnomalies:
    def test_basic_analysis(self):
        df = _make_processed_df()
        result = analyze_rework_anomalies(df)
        assert result is not None
        assert '返工次数' in result.columns
        assert '返工率' in result.columns

    def test_no_rework_returns_none(self):
        df = _make_processed_df()
        df['rework_count'] = 0
        result = analyze_rework_anomalies(df)
        assert result is None

    def test_rework_rate_calculation(self):
        df = _make_processed_df()
        result = analyze_rework_anomalies(df)
        for style, row in result.iterrows():
            assert row['返工率'] >= 0


class TestAnalyzeGroupMissing:
    def test_basic_analysis(self):
        df = _make_processed_df()
        result = analyze_group_missing(df)
        assert result is not None
        assert '缺件记录数' in result.columns

    def test_no_missing_returns_empty(self):
        df = _make_processed_df()
        df['has_missing'] = False
        result = analyze_group_missing(df)
        assert len(result) == 0


class TestAnalyzeHelperWorkload:
    def test_basic_analysis(self):
        df = _make_processed_df()
        result = analyze_helper_workload(df)
        assert result is not None
        assert '完成总数' in result.columns
        assert '返工总数' in result.columns
        assert '返工率' in result.columns

    def test_helper_count(self):
        df = _make_processed_df()
        result = analyze_helper_workload(df)
        assert len(result) == 3

    def test_rework_rate_no_nan(self):
        df = _make_processed_df()
        result = analyze_helper_workload(df)
        assert not result['返工率'].isna().any()


class TestGenerateMaterialSuggestions:
    def test_basic_suggestions(self):
        df = _make_processed_df()
        result = generate_material_suggestions(df, recent_days=30)
        assert result is not None
        assert len(result) > 0
        assert '类型' in result.columns
        assert '优先级' in result.columns

    def test_empty_df_returns_none(self):
        df = pd.DataFrame(columns=['record_date', 'style_name', 'completed_count',
                                    'rework_count', 'has_missing', 'missing_parts', 'group_no'])
        result = generate_material_suggestions(df)
        assert result is None

    def test_no_date_data(self):
        df = _make_processed_df()
        df['record_date'] = pd.NaT
        result = generate_material_suggestions(df, recent_days=30)
        assert result is not None

    def test_suggestion_types(self):
        df = _make_processed_df()
        result = generate_material_suggestions(df, recent_days=30)
        types = result['类型'].unique().tolist()
        assert '高频缺件' in types or '高返工样式' in types or '热门样式' in types


class TestGetPendingMaterials:
    def test_basic_pending(self):
        df = _make_processed_df()
        result = get_pending_materials(df)
        assert result is not None
        assert len(result) > 0
        assert 'group_no' in result.columns
        assert 'style_name' in result.columns

    def test_no_missing_returns_none(self):
        df = _make_processed_df()
        df['has_missing'] = False
        result = get_pending_materials(df)
        assert result is None

    def test_sorted_by_date_desc(self):
        df = _make_processed_df()
        result = get_pending_materials(df)
        if result is not None and len(result) > 1:
            dates = result['记录日期'].dropna()
            if len(dates) > 1:
                assert list(dates) == sorted(dates, reverse=True)
