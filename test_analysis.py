import pytest
import pandas as pd
import numpy as np
from datetime import date, datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.constants import STANDARD_FIELDS, MISSING_PART_EMPTY_VALUES
from core.data_processor import (
    detect_data_type,
    auto_map_columns,
    check_has_missing,
    determine_status,
    process_data,
    filter_data,
)
from core.analytics import (
    analyze_missing_concentration,
    analyze_rework_anomalies,
    analyze_group_missing,
    analyze_helper_workload,
    generate_material_suggestions,
    get_pending_materials,
    calculate_style_stats,
    calculate_daily_stats,
    calculate_summary_metrics,
)


@pytest.fixture
def sample_df():
    return pd.read_csv('sample_data.csv')


@pytest.fixture
def sample_no_date_df():
    return pd.read_csv('sample_data_no_date.csv')


@pytest.fixture
def processed_sample(sample_df):
    mapping = auto_map_columns(sample_df)
    return process_data(sample_df, mapping)


@pytest.fixture
def processed_no_date(sample_no_date_df):
    mapping = auto_map_columns(sample_no_date_df)
    return process_data(sample_no_date_df, mapping)


class TestDetectDataType:
    def test_detect_completion_type(self):
        df = pd.DataFrame({'完成数量': [10, 20], '样式名称': ['A', 'B']})
        assert detect_data_type(df) == 'completion'

    def test_detect_rework_type(self):
        df = pd.DataFrame({'返工数量': [1, 2], '样式名称': ['A', 'B']})
        assert detect_data_type(df) == 'rework'

    def test_detect_material_type(self):
        df = pd.DataFrame({'缺件名称': ['竹骨', '丝线'], '样式名称': ['A', 'B']})
        assert detect_data_type(df) == 'material'

    def test_detect_general_type(self):
        df = pd.DataFrame({'名称': ['A', 'B'], '备注': ['', '']})
        assert detect_data_type(df) == 'general'

    def test_detect_mixed_completion_with_rework(self):
        df = pd.DataFrame({
            '完成数量': [10, 20],
            '返工数量': [1, 2],
            '样式名称': ['A', 'B']
        })
        assert detect_data_type(df) == 'completion'


class TestAutoMapColumns:
    def test_auto_map_chinese_columns(self, sample_df):
        mapping = auto_map_columns(sample_df)
        assert '记录日期' in mapping
        assert mapping['记录日期'] == 'record_date'
        assert '样式名称' in mapping
        assert mapping['样式名称'] == 'style_name'
        assert '分组编号' in mapping
        assert mapping['分组编号'] == 'group_no'
        assert '缺件名称' in mapping
        assert mapping['缺件名称'] == 'missing_parts'
        assert '完成数量' in mapping
        assert mapping['完成数量'] == 'completed_count'
        assert '返工数量' in mapping
        assert mapping['返工数量'] == 'rework_count'
        assert '助理姓名' in mapping
        assert mapping['助理姓名'] == 'helper_name'
        assert '备注' in mapping
        assert mapping['备注'] == 'note'

    def test_auto_map_english_columns(self):
        df = pd.DataFrame({
            'record_date': ['2026-01-01'],
            'style_name': ['test'],
            'group_no': ['A'],
            'missing_parts': [''],
            'completed_count': [10],
            'rework_count': [0],
            'helper_name': ['李老师'],
            'note': ['']
        })
        mapping = auto_map_columns(df)
        assert len(mapping) == 8
        assert mapping['record_date'] == 'record_date'

    def test_auto_map_partial_columns(self):
        df = pd.DataFrame({
            '样式': ['牡丹团扇'],
            '完成数': [10],
            '返工数': [2]
        })
        mapping = auto_map_columns(df)
        assert mapping['样式'] == 'style_name'
        assert mapping['完成数'] == 'completed_count'
        assert mapping['返工数'] == 'rework_count'

    def test_auto_map_empty_dataframe(self):
        df = pd.DataFrame()
        mapping = auto_map_columns(df)
        assert mapping == {}


class TestCheckHasMissing:
    @pytest.mark.parametrize("input_val,expected", [
        ('', False),
        ('nan', False),
        ('NaN', False),
        ('None', False),
        ('none', False),
        ('无', False),
        ('没有', False),
        ('无缺件', False),
        ('0', False),
        ('-', False),
        ('/', False),
        ('n/a', False),
        ('N/A', False),
        ('null', False),
        ('NULL', False),
        ('  ', False),
    ])
    def test_empty_values(self, input_val, expected):
        assert check_has_missing(input_val) == expected

    def test_nan_value(self):
        assert check_has_missing(np.nan) is False

    def test_none_value(self):
        assert check_has_missing(None) is False

    @pytest.mark.parametrize("input_val", [
        '竹骨',
        '丝线',
        '竹骨,丝线',
        '装饰纸',
        '胶水瓶',
    ])
    def test_valid_missing_parts(self, input_val):
        assert check_has_missing(input_val) is True

    def test_missing_part_with_spaces(self):
        assert check_has_missing(' 竹骨 ') is True


class TestDetermineStatus:
    def test_status_missing_and_rework(self):
        row = pd.Series({
            'has_missing': True,
            'has_rework': True,
            'completed_count': 10
        })
        assert determine_status(row) == '缺件+返工'

    def test_status_missing_only(self):
        row = pd.Series({
            'has_missing': True,
            'has_rework': False,
            'completed_count': 10
        })
        assert determine_status(row) == '缺件待补'

    def test_status_rework_only(self):
        row = pd.Series({
            'has_missing': False,
            'has_rework': True,
            'completed_count': 10
        })
        assert determine_status(row) == '返工中'

    def test_status_completed(self):
        row = pd.Series({
            'has_missing': False,
            'has_rework': False,
            'completed_count': 10
        })
        assert determine_status(row) == '已完成'

    def test_status_in_progress(self):
        row = pd.Series({
            'has_missing': False,
            'has_rework': False,
            'completed_count': 0
        })
        assert determine_status(row) == '进行中'


class TestProcessData:
    def test_process_data_normal(self, sample_df):
        mapping = auto_map_columns(sample_df)
        result = process_data(sample_df, mapping)
        assert result is not None
        assert len(result) > 0
        assert all(col in result.columns for col in STANDARD_FIELDS.keys())
        assert 'has_missing' in result.columns
        assert 'has_rework' in result.columns
        assert 'status' in result.columns
        assert 'source_type' in result.columns

    def test_process_data_empty_mapping(self, sample_df):
        result = process_data(sample_df, {})
        assert result is None

    def test_process_data_numeric_conversion(self, sample_df):
        mapping = auto_map_columns(sample_df)
        result = process_data(sample_df, mapping)
        assert result['completed_count'].dtype == int
        assert result['rework_count'].dtype == int

    def test_process_data_date_conversion(self, sample_df):
        mapping = auto_map_columns(sample_df)
        result = process_data(sample_df, mapping)
        assert pd.api.types.is_datetime64_any_dtype(result['record_date'])

    def test_process_data_string_strip(self):
        df = pd.DataFrame({
            '样式名称': [' 牡丹团扇 ', ' 梅花团扇'],
            '完成数量': ['10', '20'],
        })
        mapping = {'样式名称': 'style_name', '完成数量': 'completed_count'}
        result = process_data(df, mapping)
        assert result['style_name'].iloc[0] == '牡丹团扇'
        assert result['style_name'].iloc[1] == '梅花团扇'

    def test_process_data_empty_style_filtered(self):
        df = pd.DataFrame({
            '样式名称': ['牡丹团扇', '', '兰花团扇'],
            '完成数量': [10, 20, 30],
        })
        mapping = {'样式名称': 'style_name', '完成数量': 'completed_count'}
        result = process_data(df, mapping)
        assert len(result) == 2
        assert '' not in result['style_name'].values

    def test_process_data_default_values_for_missing_fields(self):
        df = pd.DataFrame({
            '样式名称': ['牡丹团扇'],
        })
        mapping = {'样式名称': 'style_name'}
        result = process_data(df, mapping)
        assert result['completed_count'].iloc[0] == 0
        assert result['rework_count'].iloc[0] == 0
        assert pd.isna(result['record_date'].iloc[0])
        assert result['group_no'].iloc[0] == ''
        assert result['missing_parts'].iloc[0] == ''
        assert result['helper_name'].iloc[0] == ''
        assert result['note'].iloc[0] == ''

    def test_process_data_source_type(self):
        df = pd.DataFrame({'样式名称': ['牡丹团扇']})
        mapping = {'样式名称': 'style_name'}
        result = process_data(df, mapping, source_type='material')
        assert result['source_type'].iloc[0] == 'material'

    def test_process_data_invalid_numeric_values(self):
        df = pd.DataFrame({
            '样式名称': ['牡丹团扇', '梅花团扇'],
            '完成数量': ['abc', '20'],
            '返工数量': ['x', '3'],
        })
        mapping = {
            '样式名称': 'style_name',
            '完成数量': 'completed_count',
            '返工数量': 'rework_count',
        }
        result = process_data(df, mapping)
        assert result['completed_count'].iloc[0] == 0
        assert result['completed_count'].iloc[1] == 20
        assert result['rework_count'].iloc[0] == 0
        assert result['rework_count'].iloc[1] == 3

    def test_process_data_has_missing_calculated(self, sample_df):
        mapping = auto_map_columns(sample_df)
        result = process_data(sample_df, mapping)
        assert 'has_missing' in result.columns
        assert result['has_missing'].dtype == bool

    def test_process_data_has_rework_calculated(self, sample_df):
        mapping = auto_map_columns(sample_df)
        result = process_data(sample_df, mapping)
        assert 'has_rework' in result.columns
        assert result['has_rework'].dtype == bool


class TestFilterData:
    @pytest.fixture
    def filter_test_df(self):
        data = {
            'record_date': pd.to_datetime([
                '2026-05-01', '2026-05-02', '2026-05-03', '2026-05-04'
            ]),
            'style_name': ['牡丹', '梅花', '兰花', '菊花'],
            'group_no': ['A组', 'B组', 'A组', 'C组'],
            'helper_name': ['李老师', '王老师', '李老师', '张老师'],
            'status': ['已完成', '返工中', '已完成', '缺件待补'],
            'completed_count': [20, 15, 25, 18],
            'rework_count': [1, 2, 0, 3],
            'has_missing': [False, False, False, True],
        }
        return pd.DataFrame(data)

    def test_filter_by_style(self, filter_test_df):
        result = filter_data(filter_test_df, selected_styles=['牡丹', '梅花'])
        assert len(result) == 2
        assert set(result['style_name']) == {'牡丹', '梅花'}

    def test_filter_by_group(self, filter_test_df):
        result = filter_data(filter_test_df, selected_groups=['A组'])
        assert len(result) == 2
        assert set(result['group_no']) == {'A组'}

    def test_filter_by_helper(self, filter_test_df):
        result = filter_data(filter_test_df, selected_helpers=['李老师'])
        assert len(result) == 2
        assert set(result['helper_name']) == {'李老师'}

    def test_filter_by_status(self, filter_test_df):
        result = filter_data(filter_test_df, selected_statuses=['已完成'])
        assert len(result) == 2
        assert set(result['status']) == {'已完成'}

    def test_filter_by_date_range(self, filter_test_df):
        result = filter_data(
            filter_test_df,
            date_range=(date(2026, 5, 2), date(2026, 5, 3))
        )
        assert len(result) == 2

    def test_filter_empty_styles_returns_empty(self, filter_test_df):
        result = filter_data(filter_test_df, selected_styles=[])
        assert len(result) == 0

    def test_filter_empty_groups_returns_empty(self, filter_test_df):
        result = filter_data(filter_test_df, selected_groups=[])
        assert len(result) == 0

    def test_filter_empty_helpers_returns_empty(self, filter_test_df):
        result = filter_data(filter_test_df, selected_helpers=[])
        assert len(result) == 0

    def test_filter_empty_statuses_returns_empty(self, filter_test_df):
        result = filter_data(filter_test_df, selected_statuses=[])
        assert len(result) == 0

    def test_filter_combined_conditions(self, filter_test_df):
        result = filter_data(
            filter_test_df,
            selected_styles=['牡丹', '兰花'],
            selected_groups=['A组']
        )
        assert len(result) == 2
        assert set(result['style_name']) == {'牡丹', '兰花'}
        assert set(result['group_no']) == {'A组'}

    def test_filter_no_filters_returns_all(self, filter_test_df):
        result = filter_data(filter_test_df)
        assert len(result) == len(filter_test_df)

    def test_filter_none_filters_returns_all(self, filter_test_df):
        result = filter_data(
            filter_test_df,
            date_range=None,
            selected_styles=None,
            selected_groups=None,
            selected_helpers=None,
            selected_statuses=None,
        )
        assert len(result) == len(filter_test_df)


class TestAnalyzeMissingConcentration:
    def test_missing_concentration_normal(self, processed_sample):
        result = analyze_missing_concentration(processed_sample)
        assert result is not None
        assert len(result) > 0
        assert '出现次数' in result.columns
        assert '涉及分组' in result.columns
        assert '涉及样式' in result.columns

    def test_missing_concentration_no_missing(self):
        df = pd.DataFrame({
            'has_missing': [False, False],
            'missing_parts': ['', ''],
            'group_no': ['A', 'B'],
            'style_name': ['X', 'Y'],
        })
        result = analyze_missing_concentration(df)
        assert result is None

    def test_missing_concentration_empty_df(self):
        df = pd.DataFrame(columns=['has_missing', 'missing_parts', 'group_no', 'style_name'])
        result = analyze_missing_concentration(df)
        assert result is None

    def test_missing_concentration_multiple_parts(self):
        df = pd.DataFrame({
            'has_missing': [True, True],
            'missing_parts': ['竹骨,丝线', '竹骨,装饰纸'],
            'group_no': ['A组', 'B组'],
            'style_name': ['牡丹', '梅花'],
        })
        result = analyze_missing_concentration(df)
        assert result is not None
        assert len(result) == 3
        assert result.loc['竹骨', '出现次数'] == 2


class TestAnalyzeReworkAnomalies:
    def test_rework_anomalies_normal(self, processed_sample):
        result = analyze_rework_anomalies(processed_sample)
        assert result is not None
        assert len(result) > 0
        assert '返工次数' in result.columns
        assert '涉及记录数' in result.columns
        assert '平均返工量' in result.columns
        assert '总完成量' in result.columns
        assert '返工率' in result.columns

    def test_rework_anomalies_no_rework(self):
        df = pd.DataFrame({
            'style_name': ['A', 'B'],
            'rework_count': [0, 0],
            'completed_count': [10, 20],
        })
        result = analyze_rework_anomalies(df)
        assert result is None

    def test_rework_anomalies_empty_df(self):
        df = pd.DataFrame(columns=['style_name', 'rework_count', 'completed_count'])
        result = analyze_rework_anomalies(df)
        assert result is None

    def test_rework_rate_calculation(self):
        df = pd.DataFrame({
            'style_name': ['A', 'A', 'B'],
            'rework_count': [5, 5, 0],
            'completed_count': [90, 90, 100],
        })
        result = analyze_rework_anomalies(df)
        assert result is not None
        assert result.loc['A', '返工次数'] == 10
        assert result.loc['A', '总完成量'] == 180
        assert abs(result.loc['A', '返工率'] - 5.26) < 0.01


class TestAnalyzeGroupMissing:
    def test_group_missing_normal(self, processed_sample):
        result = analyze_group_missing(processed_sample)
        assert result is not None
        assert len(result) > 0
        assert '缺件记录数' in result.columns
        assert '涉及样式' in result.columns
        assert '缺件详情' in result.columns

    def test_group_missing_no_missing(self):
        df = pd.DataFrame({
            'has_missing': [False, False],
            'group_no': ['A', 'B'],
            'style_name': ['X', 'Y'],
            'missing_parts': ['', ''],
        })
        result = analyze_group_missing(df)
        assert len(result) == 0


class TestAnalyzeHelperWorkload:
    def test_helper_workload_normal(self, processed_sample):
        result = analyze_helper_workload(processed_sample)
        assert result is not None
        assert len(result) > 0
        assert '负责记录数' in result.columns
        assert '完成总数' in result.columns
        assert '返工总数' in result.columns
        assert '涉及分组' in result.columns
        assert '涉及样式' in result.columns
        assert '缺件记录' in result.columns
        assert '返工率' in result.columns

    def test_helper_workload_empty_df(self):
        df = pd.DataFrame(columns=[
            'helper_name', 'completed_count', 'rework_count',
            'group_no', 'style_name', 'has_missing'
        ])
        result = analyze_helper_workload(df)
        assert len(result) == 0


class TestGenerateMaterialSuggestions:
    def test_suggestions_normal(self, processed_sample):
        result = generate_material_suggestions(processed_sample, recent_days=30)
        assert result is not None
        assert len(result) > 0
        assert '类型' in result.columns
        assert '材料/样式' in result.columns
        assert '问题描述' in result.columns
        assert '建议措施' in result.columns
        assert '优先级' in result.columns

    def test_suggestions_empty_df(self):
        df = pd.DataFrame(columns=['record_date', 'style_name', 'completed_count', 'rework_count'])
        result = generate_material_suggestions(df)
        assert result is None

    def test_suggestions_no_date_data(self, processed_no_date):
        result = generate_material_suggestions(processed_no_date, recent_days=30)
        assert result is not None

    def test_suggestions_includes_high_freq_missing(self, processed_sample):
        result = generate_material_suggestions(processed_sample)
        assert '高频缺件' in result['类型'].values

    def test_suggestions_includes_popular_styles(self, processed_sample):
        result = generate_material_suggestions(processed_sample)
        assert '热门样式' in result['类型'].values


class TestGetPendingMaterials:
    def test_pending_materials_normal(self, processed_sample):
        result = get_pending_materials(processed_sample)
        assert result is not None
        assert len(result) > 0
        assert '记录日期' in result.columns
        assert '完成数量' in result.columns
        assert '助理' in result.columns
        assert '备注' in result.columns

    def test_pending_materials_no_missing(self):
        df = pd.DataFrame({
            'has_missing': [False, False],
            'group_no': ['A', 'B'],
            'style_name': ['X', 'Y'],
            'missing_parts': ['', ''],
            'record_date': pd.to_datetime(['2026-01-01', '2026-01-02']),
            'completed_count': [10, 20],
            'helper_name': ['李老师', '王老师'],
            'note': ['', ''],
        })
        result = get_pending_materials(df)
        assert result is None

    def test_pending_materials_empty_df(self):
        df = pd.DataFrame(columns=[
            'has_missing', 'group_no', 'style_name', 'missing_parts',
            'record_date', 'completed_count', 'helper_name', 'note'
        ])
        result = get_pending_materials(df)
        assert result is None


class TestCalculateStyleStats:
    def test_style_stats_normal(self, processed_sample):
        result = calculate_style_stats(processed_sample)
        assert result is not None
        assert len(result) > 0
        assert '完成数' in result.columns
        assert '返工数' in result.columns
        assert '缺件数' in result.columns
        assert '总数' in result.columns
        assert '完成率' in result.columns

    def test_style_stats_completion_rate(self):
        df = pd.DataFrame({
            'style_name': ['A', 'A', 'B'],
            'completed_count': [80, 20, 100],
            'rework_count': [10, 10, 0],
            'has_missing': [False, True, False],
        })
        result = calculate_style_stats(df)
        a_row = result[result['style_name'] == 'A'].iloc[0]
        assert a_row['完成数'] == 100
        assert a_row['返工数'] == 20
        assert a_row['总数'] == 120
        assert abs(a_row['完成率'] - 83.33) < 0.01


class TestCalculateDailyStats:
    def test_daily_stats_normal(self, processed_sample):
        result = calculate_daily_stats(processed_sample)
        assert result is not None
        assert len(result) > 0
        assert '日期' in result.columns
        assert '完成数' in result.columns
        assert '返工数' in result.columns
        assert '返工率' in result.columns

    def test_daily_stats_no_dates(self, processed_no_date):
        result = calculate_daily_stats(processed_no_date)
        assert result is None

    def test_daily_stats_empty_df(self):
        df = pd.DataFrame(columns=['record_date', 'completed_count', 'rework_count'])
        result = calculate_daily_stats(df)
        assert result is None


class TestCalculateSummaryMetrics:
    def test_summary_metrics_normal(self, processed_sample):
        result = calculate_summary_metrics(processed_sample)
        assert 'total_completed' in result
        assert 'total_rework' in result
        assert 'rework_rate' in result
        assert 'missing_count' in result
        assert 'active_groups' in result
        assert result['total_completed'] > 0
        assert result['total_rework'] >= 0
        assert 0 <= result['rework_rate'] <= 100
        assert result['missing_count'] >= 0
        assert result['active_groups'] > 0

    def test_summary_metrics_zero_total(self):
        df = pd.DataFrame({
            'completed_count': [0, 0],
            'rework_count': [0, 0],
            'has_missing': [False, False],
            'group_no': ['A', 'B'],
        })
        result = calculate_summary_metrics(df)
        assert result['rework_rate'] == 0

    def test_summary_metrics_empty_df(self):
        df = pd.DataFrame(columns=[
            'completed_count', 'rework_count', 'has_missing', 'group_no'
        ])
        result = calculate_summary_metrics(df)
        assert result['total_completed'] == 0
        assert result['total_rework'] == 0
        assert result['rework_rate'] == 0
        assert result['missing_count'] == 0
        assert result['active_groups'] == 0


class TestEdgeCases:
    def test_all_empty_dataframe(self):
        df = pd.DataFrame()
        mapping = auto_map_columns(df)
        assert mapping == {}
        result = process_data(df, mapping)
        assert result is None

    def test_single_row_data(self):
        df = pd.DataFrame({
            '样式名称': ['牡丹团扇'],
            '分组编号': ['A组'],
            '完成数量': [10],
            '返工数量': [1],
        })
        mapping = auto_map_columns(df)
        result = process_data(df, mapping)
        assert len(result) == 1
        assert result['status'].iloc[0] == '返工中'

    def test_all_missing_parts_various_separators(self):
        df = pd.DataFrame({
            '样式名称': ['A', 'B', 'C', 'D'],
            '缺件名称': ['竹骨,丝线', '竹骨;丝线', '竹骨、丝线', '竹骨，丝线'],
            '完成数量': [10, 10, 10, 10],
        })
        mapping = {'样式名称': 'style_name', '缺件名称': 'missing_parts', '完成数量': 'completed_count'}
        result = process_data(df, mapping)
        missing_analysis = analyze_missing_concentration(result)
        assert missing_analysis is not None
        assert missing_analysis.loc['竹骨', '出现次数'] == 4
        assert missing_analysis.loc['丝线', '出现次数'] == 4

    def test_whitespace_in_data(self):
        df = pd.DataFrame({
            '样式名称': [' 牡丹团扇 ', '梅花团扇', ' 兰花团扇'],
            '分组编号': [' A组 ', 'B组', ' C组'],
            '完成数量': [' 10 ', '20', ' 30 '],
        })
        mapping = {'样式名称': 'style_name', '分组编号': 'group_no', '完成数量': 'completed_count'}
        result = process_data(df, mapping)
        assert result['style_name'].iloc[0] == '牡丹团扇'
        assert result['group_no'].iloc[0] == 'A组'
        assert result['completed_count'].iloc[0] == 10

    def test_nan_in_string_fields(self):
        df = pd.DataFrame({
            '样式名称': ['牡丹团扇', np.nan, '兰花团扇'],
            '完成数量': [10, 20, 30],
        })
        mapping = {'样式名称': 'style_name', '完成数量': 'completed_count'}
        result = process_data(df, mapping)
        assert len(result) == 3
        assert result['style_name'].iloc[1] == 'nan'

    def test_date_filter_with_invalid_dates(self):
        df = pd.DataFrame({
            '样式名称': ['A', 'B', 'C'],
            '记录日期': ['2026-05-01', 'invalid-date', '2026-05-03'],
            '完成数量': [10, 20, 30],
        })
        mapping = {'样式名称': 'style_name', '记录日期': 'record_date', '完成数量': 'completed_count'}
        result = process_data(df, mapping)
        assert result['record_date'].isna().sum() == 1
        assert result['record_date'].notna().sum() == 2

    def test_filter_with_empty_date_range_no_valid_dates(self, processed_no_date):
        result = filter_data(
            processed_no_date,
            date_range=(date(2026, 1, 1), date(2026, 12, 31))
        )
        assert len(result) == len(processed_no_date)

    def test_generate_suggestions_with_future_dates(self):
        df = pd.DataFrame({
            'record_date': pd.to_datetime(['2099-01-01', '2099-01-02']),
            'style_name': ['A', 'B'],
            'completed_count': [100, 200],
            'rework_count': [5, 10],
            'has_missing': [False, True],
            'missing_parts': ['', '竹骨'],
            'group_no': ['X', 'Y'],
            'helper_name': ['李老师', '王老师'],
        })
        result = generate_material_suggestions(df, recent_days=30)
        assert result is not None
        assert len(result) > 0

    def test_pending_materials_sorted_by_date(self):
        df = pd.DataFrame({
            'has_missing': [True, True, True],
            'group_no': ['A', 'B', 'C'],
            'style_name': ['X', 'Y', 'Z'],
            'missing_parts': ['竹骨', '丝线', '装饰纸'],
            'record_date': pd.to_datetime(['2026-05-03', '2026-05-01', '2026-05-02']),
            'completed_count': [10, 20, 30],
            'helper_name': ['李老师', '王老师', '张老师'],
            'note': ['', '', ''],
        })
        result = get_pending_materials(df)
        assert result is not None
        dates = result['记录日期'].tolist()
        assert dates[0] >= dates[1] >= dates[2]

    def test_helper_rework_rate_with_zero_completed(self):
        df = pd.DataFrame({
            'helper_name': ['A', 'A'],
            'completed_count': [0, 0],
            'rework_count': [0, 0],
            'group_no': ['X', 'Y'],
            'style_name': ['P', 'Q'],
            'has_missing': [False, False],
        })
        result = analyze_helper_workload(df)
        assert len(result) == 1
        assert result['返工率'].iloc[0] == 0
