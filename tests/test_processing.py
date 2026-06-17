import pytest
import pandas as pd
import numpy as np
from datetime import datetime

from src.core.processing import (
    check_has_missing,
    determine_status,
    process_data,
    has_valid_dates,
)


class TestCheckHasMissing:
    @pytest.mark.parametrize("value, expected", [
        ('', False),
        ('nan', False),
        ('NaN', False),
        ('none', False),
        ('None', False),
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
    ])
    def test_various_inputs(self, value, expected):
        assert check_has_missing(value) == expected


class TestDetermineStatus:
    def test_missing_and_rework(self):
        assert determine_status(True, True, 10) == '缺件+返工'

    def test_only_missing(self):
        assert determine_status(True, False, 5) == '缺件待补'

    def test_only_rework(self):
        assert determine_status(False, True, 0) == '返工中'

    def test_completed(self):
        assert determine_status(False, False, 10) == '已完成'

    def test_in_progress(self):
        assert determine_status(False, False, 0) == '进行中'


class TestProcessData:
    def setup_method(self):
        self.sample_df = pd.DataFrame({
            '记录日期': ['2026-05-01', '2026-05-02', '2026-05-03'],
            '样式名称': ['牡丹团扇', '梅花团扇', '兰花团扇'],
            '分组编号': ['A组', 'B组', 'A组'],
            '缺件名称': ['竹骨', '', '丝线'],
            '完成数量': [18, 25, 12],
            '返工数量': [2, 0, 3],
            '助理姓名': ['李老师', '王老师', '李老师'],
            '备注': ['首次缺件', '', '多种问题']
        })
        self.mapping = {
            '记录日期': 'record_date',
            '样式名称': 'style_name',
            '分组编号': 'group_no',
            '缺件名称': 'missing_parts',
            '完成数量': 'completed_count',
            '返工数量': 'rework_count',
            '助理姓名': 'helper_name',
            '备注': 'note',
        }

    def test_process_data_basic(self):
        result = process_data(self.sample_df, self.mapping)
        assert result is not None
        assert len(result) == 3
        assert 'record_date' in result.columns
        assert 'style_name' in result.columns
        assert 'has_missing' in result.columns
        assert 'has_rework' in result.columns
        assert 'status' in result.columns

    def test_data_types(self):
        result = process_data(self.sample_df, self.mapping)
        assert pd.api.types.is_datetime64_any_dtype(result['record_date'])
        assert pd.api.types.is_integer_dtype(result['completed_count'])
        assert pd.api.types.is_integer_dtype(result['rework_count'])

    def test_numeric_conversion_and_fillna(self):
        df = pd.DataFrame({
            '样式名称': ['test'],
            '完成数量': ['abc'],
            '返工数量': [None],
        })
        mapping = {
            '样式名称': 'style_name',
            '完成数量': 'completed_count',
            '返工数量': 'rework_count',
        }
        result = process_data(df, mapping)
        assert result['completed_count'].iloc[0] == 0
        assert result['rework_count'].iloc[0] == 0

    def test_empty_mapping_returns_none(self):
        result = process_data(self.sample_df, {})
        assert result is None

    def test_filter_empty_style_name(self):
        df = pd.DataFrame({
            '样式名称': ['牡丹', '', '梅花', '  '],
            '完成数量': [10, 5, 8, 3],
        })
        mapping = {
            '样式名称': 'style_name',
            '完成数量': 'completed_count',
        }
        result = process_data(df, mapping)
        assert len(result) == 2

    def test_missing_columns_filled(self):
        df = pd.DataFrame({
            '样式名称': ['test'],
        })
        mapping = {'样式名称': 'style_name'}
        result = process_data(df, mapping)
        assert result['completed_count'].iloc[0] == 0
        assert result['rework_count'].iloc[0] == 0
        assert pd.isna(result['record_date'].iloc[0])
        assert result['group_no'].iloc[0] == ''

    def test_source_type_set(self):
        result = process_data(self.sample_df, self.mapping, source_type='completion')
        assert result['source_type'].iloc[0] == 'completion'

    def test_has_missing_calculated(self):
        result = process_data(self.sample_df, self.mapping)
        assert result.iloc[0]['has_missing'] == True
        assert result.iloc[1]['has_missing'] == False
        assert result.iloc[2]['has_missing'] == True

    def test_has_rework_calculated(self):
        result = process_data(self.sample_df, self.mapping)
        assert result.iloc[0]['has_rework'] == True
        assert result.iloc[1]['has_rework'] == False
        assert result.iloc[2]['has_rework'] == True

    def test_status_calculated(self):
        result = process_data(self.sample_df, self.mapping)
        assert result.iloc[0]['status'] == '缺件+返工'
        assert result.iloc[1]['status'] == '已完成'
        assert result.iloc[2]['status'] == '缺件+返工'

    def test_whitespace_stripped(self):
        df = pd.DataFrame({
            '样式名称': [' 牡丹团扇 ', ' 梅花团扇'],
            '分组编号': [' A组 ', 'B组 '],
            '完成数量': [10, 5],
        })
        mapping = {
            '样式名称': 'style_name',
            '分组编号': 'group_no',
            '完成数量': 'completed_count',
        }
        result = process_data(df, mapping)
        assert result.iloc[0]['style_name'] == '牡丹团扇'
        assert result.iloc[0]['group_no'] == 'A组'


class TestHasValidDates:
    def test_with_valid_dates(self):
        df = pd.DataFrame({
            'record_date': pd.to_datetime(['2026-01-01', '2026-01-02']),
        })
        assert has_valid_dates(df) == True

    def test_all_nat(self):
        df = pd.DataFrame({
            'record_date': pd.to_datetime([pd.NaT, pd.NaT]),
        })
        assert has_valid_dates(df) == False

    def test_no_date_column(self):
        df = pd.DataFrame({'other': [1, 2, 3]})
        assert has_valid_dates(df) == False

    def test_mixed_valid_and_nat(self):
        df = pd.DataFrame({
            'record_date': pd.to_datetime(['2026-01-01', pd.NaT]),
        })
        assert has_valid_dates(df) == True
