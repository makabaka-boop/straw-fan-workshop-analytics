import pytest
import pandas as pd
import numpy as np
from src.processing import (
    check_has_missing,
    determine_status,
    process_data,
    filter_data,
    has_valid_dates,
    _compute_status_vectorized,
)


class TestCheckHasMissing:
    @pytest.mark.parametrize("value,expected", [
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
        (np.nan, False),
        (None, False),
        ('竹骨', True),
        ('丝线', True),
        ('竹骨,丝线', True),
        (' 竹骨 ', True),
    ])
    def test_check_has_missing_various_inputs(self, value, expected):
        assert check_has_missing(value) == expected

    def test_check_has_missing_with_series(self):
        s = pd.Series(['竹骨', '', '无', np.nan, '丝线'])
        result = s.apply(check_has_missing)
        assert result.tolist() == [True, False, False, False, True]


class TestDetermineStatus:
    def test_missing_and_rework(self):
        row = pd.Series({
            'has_missing': True,
            'has_rework': True,
            'completed_count': 5
        })
        assert determine_status(row) == '缺件+返工'

    def test_missing_only(self):
        row = pd.Series({
            'has_missing': True,
            'has_rework': False,
            'completed_count': 5
        })
        assert determine_status(row) == '缺件待补'

    def test_rework_only(self):
        row = pd.Series({
            'has_missing': False,
            'has_rework': True,
            'completed_count': 5
        })
        assert determine_status(row) == '返工中'

    def test_completed(self):
        row = pd.Series({
            'has_missing': False,
            'has_rework': False,
            'completed_count': 5
        })
        assert determine_status(row) == '已完成'

    def test_in_progress(self):
        row = pd.Series({
            'has_missing': False,
            'has_rework': False,
            'completed_count': 0
        })
        assert determine_status(row) == '进行中'

    def test_vectorized_status_matches_apply(self):
        df = pd.DataFrame({
            'has_missing': [True, True, False, False, False],
            'has_rework': [True, False, True, False, False],
            'completed_count': [5, 3, 2, 1, 0],
        })
        vectorized = _compute_status_vectorized(df)
        applied = df.apply(determine_status, axis=1)
        assert vectorized.tolist() == applied.tolist()


class TestProcessData:
    def test_process_data_returns_dataframe(self, sample_raw_df, sample_mapping):
        result = process_data(sample_raw_df, sample_mapping)
        assert isinstance(result, pd.DataFrame)
        assert len(result) > 0

    def test_process_data_empty_mapping_returns_none(self, sample_raw_df):
        result = process_data(sample_raw_df, {})
        assert result is None

    def test_process_data_standard_columns_present(self, processed_df):
        expected_cols = [
            'record_date', 'style_name', 'group_no', 'missing_parts',
            'completed_count', 'rework_count', 'helper_name', 'note',
            'source_type', 'has_missing', 'has_rework', 'status'
        ]
        for col in expected_cols:
            assert col in processed_df.columns

    def test_process_data_correct_types(self, processed_df):
        assert pd.api.types.is_datetime64_any_dtype(processed_df['record_date'])
        assert pd.api.types.is_integer_dtype(processed_df['completed_count'])
        assert pd.api.types.is_integer_dtype(processed_df['rework_count'])
        assert pd.api.types.is_bool_dtype(processed_df['has_missing'])
        assert pd.api.types.is_bool_dtype(processed_df['has_rework'])

    def test_process_data_empty_style_filtered_out(self, sample_mapping):
        df = pd.DataFrame({
            '样式名称': ['牡丹', '', '梅花'],
            '完成数量': [10, 5, 20],
        })
        result = process_data(df, {'样式名称': 'style_name', '完成数量': 'completed_count'})
        assert len(result) == 2
        assert '' not in result['style_name'].tolist()

    def test_process_data_source_type(self, sample_raw_df, sample_mapping):
        result = process_data(sample_raw_df, sample_mapping, source_type='material')
        assert result['source_type'].unique()[0] == 'material'

    def test_process_data_default_source_type(self, sample_raw_df, sample_mapping):
        result = process_data(sample_raw_df, sample_mapping)
        assert result['source_type'].unique()[0] == 'general'

    def test_process_data_numeric_fill_na(self, sample_mapping):
        df = pd.DataFrame({
            '样式名称': ['牡丹', '梅花'],
            '完成数量': [10, np.nan],
            '返工数量': [np.nan, 2],
        })
        result = process_data(df, {
            '样式名称': 'style_name',
            '完成数量': 'completed_count',
            '返工数量': 'rework_count',
        })
        assert result['completed_count'].tolist() == [10, 0]
        assert result['rework_count'].tolist() == [0, 2]

    def test_process_data_string_strip(self, sample_mapping):
        df = pd.DataFrame({
            '样式名称': [' 牡丹团扇 ', ' 梅花团扇'],
            '完成数量': [10, 20],
        })
        result = process_data(df, {
            '样式名称': 'style_name',
            '完成数量': 'completed_count',
        })
        assert result['style_name'].tolist() == ['牡丹团扇', '梅花团扇']

    def test_process_data_no_date_column(self, sample_no_date_df):
        from src.mapping import auto_map_columns
        mapping = auto_map_columns(sample_no_date_df)
        result = process_data(sample_no_date_df, mapping)
        assert result is not None
        assert result['record_date'].isna().all()

    def test_process_data_missing_columns_filled_default(self):
        df = pd.DataFrame({
            '样式名称': ['牡丹'],
        })
        mapping = {'样式名称': 'style_name'}
        result = process_data(df, mapping)
        assert result['completed_count'].iloc[0] == 0
        assert result['rework_count'].iloc[0] == 0
        assert pd.isna(result['record_date'].iloc[0])
        assert result['helper_name'].iloc[0] == ''


class TestFilterData:
    def test_filter_by_style(self, processed_df):
        styles = ['牡丹团扇']
        result = filter_data(processed_df, selected_styles=styles)
        assert all(result['style_name'].isin(styles))
        assert len(result) > 0

    def test_filter_by_group(self, processed_df):
        groups = ['A组']
        result = filter_data(processed_df, selected_groups=groups)
        assert all(result['group_no'].isin(groups))

    def test_filter_by_helper(self, processed_df):
        helpers = ['李老师']
        result = filter_data(processed_df, selected_helpers=helpers)
        assert all(result['helper_name'].isin(helpers))

    def test_filter_by_status(self, processed_df):
        statuses = ['已完成']
        result = filter_data(processed_df, selected_statuses=statuses)
        assert all(result['status'].isin(statuses))

    def test_filter_empty_selection_returns_empty(self, processed_df):
        result = filter_data(processed_df, selected_styles=[])
        assert len(result) == 0

    def test_filter_by_date_range(self, processed_df):
        min_date = processed_df['record_date'].min().date()
        max_date = processed_df['record_date'].max().date()
        mid_date = min_date + (max_date - min_date) / 2
        result = filter_data(processed_df, date_range=(min_date, mid_date))
        assert all(result['record_date'].dt.date >= min_date)
        assert all(result['record_date'].dt.date <= mid_date)

    def test_filter_multiple_conditions(self, processed_df):
        result = filter_data(
            processed_df,
            selected_styles=['牡丹团扇'],
            selected_groups=['A组'],
        )
        assert all(result['style_name'] == '牡丹团扇')
        assert all(result['group_no'] == 'A组')

    def test_filter_no_conditions_returns_all(self, processed_df):
        result = filter_data(processed_df)
        assert len(result) == len(processed_df)

    def test_filter_none_condition_ignored(self, processed_df):
        result = filter_data(processed_df, selected_styles=None)
        assert len(result) == len(processed_df)


class TestHasValidDates:
    def test_has_valid_dates_true(self, processed_df):
        assert has_valid_dates(processed_df) is True

    def test_has_valid_dates_false(self, processed_no_date_df):
        assert has_valid_dates(processed_no_date_df) is False

    def test_has_valid_dates_partial(self):
        df = pd.DataFrame({
            'record_date': pd.to_datetime(['2026-01-01', pd.NaT]),
            'style_name': ['A', 'B'],
        })
        assert has_valid_dates(df) is True
