import pytest
import pandas as pd
import numpy as np
from datetime import date

from config import STANDARD_FIELDS, MISSING_NEGATIVE_VALUES, COLUMN_KEYWORDS
from column_mapping import auto_map_columns, _match_column_by_keywords
from data_processor import check_has_missing, determine_status, process_data
from data_loader import load_csv, detect_data_type
from filters import filter_data, has_valid_dates


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
        (np.nan, False),
        (None, False),
        ('竹骨', True),
        ('丝线', True),
        ('竹骨,丝线', True),
        ('装饰纸', True),
    ])
    def test_missing_detection(self, input_val, expected):
        assert check_has_missing(input_val) == expected


class TestDetermineStatus:
    def test_missing_and_rework(self):
        assert determine_status(True, True, 5) == '缺件+返工'

    def test_missing_only(self):
        assert determine_status(True, False, 5) == '缺件待补'

    def test_rework_only(self):
        assert determine_status(False, True, 5) == '返工中'

    def test_completed(self):
        assert determine_status(False, False, 5) == '已完成'

    def test_in_progress(self):
        assert determine_status(False, False, 0) == '进行中'

    def test_missing_takes_priority_over_completed(self):
        assert determine_status(True, False, 100) == '缺件待补'


class TestAutoMapColumns:
    def test_exact_chinese_match(self):
        df = pd.DataFrame(columns=['记录日期', '样式名称', '分组编号', '缺件名称', '完成数量', '返工数量', '助理姓名', '备注'])
        mapping = auto_map_columns(df)
        assert mapping == {
            '记录日期': 'record_date', '样式名称': 'style_name', '分组编号': 'group_no',
            '缺件名称': 'missing_parts', '完成数量': 'completed_count', '返工数量': 'rework_count',
            '助理姓名': 'helper_name', '备注': 'note',
        }

    def test_english_field_match(self):
        df = pd.DataFrame(columns=['record_date', 'style_name', 'group_no', 'missing_parts',
                                    'completed_count', 'rework_count', 'helper_name', 'note'])
        mapping = auto_map_columns(df)
        assert len(mapping) == 8

    def test_partial_keyword_match(self):
        df = pd.DataFrame(columns=['日期', '样式', '组别', '缺件', '完成数', '返工数', '助理', '备注说明'])
        mapping = auto_map_columns(df)
        assert '日期' in mapping and mapping['日期'] == 'record_date'
        assert '样式' in mapping and mapping['样式'] == 'style_name'
        assert '组别' in mapping and mapping['组别'] == 'group_no'
        assert '缺件' in mapping and mapping['缺件'] == 'missing_parts'
        assert '完成数' in mapping and mapping['完成数'] == 'completed_count'
        assert '返工数' in mapping and mapping['返工数'] == 'rework_count'
        assert '助理' in mapping and mapping['助理'] == 'helper_name'
        assert '备注说明' in mapping and mapping['备注说明'] == 'note'

    def test_no_match(self):
        df = pd.DataFrame(columns=['foo', 'bar', 'baz'])
        mapping = auto_map_columns(df)
        assert len(mapping) == 0

    def test_mixed_columns(self):
        df = pd.DataFrame(columns=['记录日期', 'style', '分组', '缺件名称', '完成数量', '返工数量', '老师', '备注'])
        mapping = auto_map_columns(df)
        assert '老师' in mapping and mapping['老师'] == 'helper_name'


class TestMatchColumnByKeywords:
    def test_exact_chinese_name(self):
        assert _match_column_by_keywords('记录日期', 'record_date') is True

    def test_exact_english_name(self):
        assert _match_column_by_keywords('record_date', 'record_date') is True

    def test_keyword_match(self):
        assert _match_column_by_keywords('日期', 'record_date') is True

    def test_no_match(self):
        assert _match_column_by_keywords('随机列', 'record_date') is False


class TestProcessData:
    @pytest.fixture
    def sample_df(self):
        return pd.DataFrame({
            '记录日期': ['2026-05-01', '2026-05-02', '2026-05-03'],
            '样式名称': ['牡丹团扇', '梅花团扇', '兰花团扇'],
            '分组编号': ['A组', 'B组', 'C组'],
            '缺件名称': ['竹骨', '', '丝线'],
            '完成数量': [18, 25, 12],
            '返工数量': [2, 0, 1],
            '助理姓名': ['李老师', '王老师', '张老师'],
            '备注': ['', '', '缺件'],
        })

    @pytest.fixture
    def full_mapping(self):
        return {
            '记录日期': 'record_date', '样式名称': 'style_name', '分组编号': 'group_no',
            '缺件名称': 'missing_parts', '完成数量': 'completed_count', '返工数量': 'rework_count',
            '助理姓名': 'helper_name', '备注': 'note',
        }

    def test_basic_processing(self, sample_df, full_mapping):
        result = process_data(sample_df, full_mapping)
        assert result is not None
        assert len(result) == 3
        assert 'status' in result.columns
        assert 'has_missing' in result.columns
        assert 'has_rework' in result.columns

    def test_status_values(self, sample_df, full_mapping):
        result = process_data(sample_df, full_mapping)
        statuses = result['status'].tolist()
        assert '缺件+返工' in statuses
        assert '已完成' in statuses

    def test_empty_mapping_returns_none(self, sample_df):
        result = process_data(sample_df, {})
        assert result is None

    def test_partial_mapping(self, sample_df):
        mapping = {'样式名称': 'style_name', '完成数量': 'completed_count'}
        result = process_data(sample_df, mapping)
        assert result is not None
        assert result['completed_count'].sum() > 0
        assert result['rework_count'].sum() == 0

    def test_no_date_data(self):
        df = pd.DataFrame({
            '样式名称': ['牡丹团扇', '梅花团扇'],
            '分组编号': ['A组', 'B组'],
            '缺件名称': ['', '丝线'],
            '完成数量': [20, 15],
            '返工数量': [1, 2],
            '助理姓名': ['李老师', '王老师'],
            '备注': ['', ''],
        })
        mapping = {
            '样式名称': 'style_name', '分组编号': 'group_no', '缺件名称': 'missing_parts',
            '完成数量': 'completed_count', '返工数量': 'rework_count',
            '助理姓名': 'helper_name', '备注': 'note',
        }
        result = process_data(df, mapping)
        assert result is not None
        assert result['record_date'].isna().all()

    def test_non_numeric_completed_count(self):
        df = pd.DataFrame({
            '样式名称': ['牡丹团扇'],
            '完成数量': ['abc'],
            '返工数量': ['xyz'],
        })
        mapping = {'样式名称': 'style_name', '完成数量': 'completed_count', '返工数量': 'rework_count'}
        result = process_data(df, mapping)
        assert result is not None
        assert result['completed_count'].iloc[0] == 0
        assert result['rework_count'].iloc[0] == 0

    def test_empty_style_name_filtered(self):
        df = pd.DataFrame({
            '样式名称': ['牡丹团扇', '', '   '],
            '完成数量': [10, 20, 30],
            '返工数量': [0, 0, 0],
        })
        mapping = {'样式名称': 'style_name', '完成数量': 'completed_count', '返工数量': 'rework_count'}
        result = process_data(df, mapping)
        assert len(result) == 1

    def test_source_type_preserved(self, sample_df, full_mapping):
        result = process_data(sample_df, full_mapping, source_type='rework')
        assert result['source_type'].iloc[0] == 'rework'

    def test_string_fields_stripped(self):
        df = pd.DataFrame({
            '样式名称': ['  牡丹团扇  '],
            '完成数量': [10],
            '返工数量': [0],
        })
        mapping = {'样式名称': 'style_name', '完成数量': 'completed_count', '返工数量': 'rework_count'}
        result = process_data(df, mapping)
        assert result['style_name'].iloc[0] == '牡丹团扇'


class TestDetectDataType:
    def test_completion_type(self):
        df = pd.DataFrame(columns=['完成数量', '样式名称'])
        assert detect_data_type(df) == 'completion'

    def test_rework_type(self):
        df = pd.DataFrame(columns=['返工数量', '样式名称'])
        assert detect_data_type(df) == 'rework'

    def test_material_type(self):
        df = pd.DataFrame(columns=['缺件名称', '样式名称'])
        assert detect_data_type(df) == 'material'

    def test_general_type(self):
        df = pd.DataFrame(columns=['样式名称', '分组编号'])
        assert detect_data_type(df) == 'general'

    def test_completion_with_rework(self):
        df = pd.DataFrame(columns=['完成数量', '返工数量'])
        assert detect_data_type(df) == 'completion'


class TestFilterData:
    @pytest.fixture
    def processed_df(self):
        return pd.DataFrame({
            'record_date': pd.to_datetime(['2026-05-01', '2026-05-02', '2026-05-03', '2026-05-04']),
            'style_name': ['牡丹团扇', '梅花团扇', '兰花团扇', '牡丹团扇'],
            'group_no': ['A组', 'B组', 'A组', 'C组'],
            'helper_name': ['李老师', '王老师', '李老师', '张老师'],
            'status': ['已完成', '返工中', '已完成', '缺件待补'],
            'completed_count': [20, 15, 25, 18],
            'rework_count': [0, 2, 0, 0],
            'has_missing': [False, False, False, True],
            'has_rework': [False, True, False, False],
        })

    def test_filter_by_style(self, processed_df):
        result = filter_data(processed_df, selected_styles=['牡丹团扇'])
        assert len(result) == 2

    def test_filter_empty_style_returns_empty(self, processed_df):
        result = filter_data(processed_df, selected_styles=[])
        assert len(result) == 0

    def test_filter_by_date_range(self, processed_df):
        result = filter_data(processed_df, date_range=(date(2026, 5, 2), date(2026, 5, 3)))
        assert len(result) == 2

    def test_filter_by_status(self, processed_df):
        result = filter_data(processed_df, selected_statuses=['已完成'])
        assert len(result) == 2

    def test_filter_none_input(self):
        assert filter_data(None) is None

    def test_filter_empty_df(self):
        df = pd.DataFrame()
        result = filter_data(df)
        assert result.empty

    def test_filter_all_empty_selections(self, processed_df):
        result = filter_data(processed_df, selected_styles=[], selected_groups=[], selected_helpers=[], selected_statuses=[])
        assert len(result) == 0

    def test_no_filters_returns_all(self, processed_df):
        result = filter_data(processed_df)
        assert len(result) == 4


class TestHasValidDates:
    def test_with_valid_dates(self):
        df = pd.DataFrame({'record_date': pd.to_datetime(['2026-05-01', '2026-05-02'])})
        assert has_valid_dates(df) == True

    def test_with_no_dates(self):
        df = pd.DataFrame({'record_date': [pd.NaT, pd.NaT]})
        assert has_valid_dates(df) == False

    def test_with_none(self):
        assert has_valid_dates(None) is False

    def test_with_empty_df(self):
        df = pd.DataFrame()
        assert has_valid_dates(df) is False


class TestLoadCSV:
    def test_load_valid_csv(self, tmp_path):
        csv_file = tmp_path / "test.csv"
        csv_file.write_text("样式名称,完成数量\n牡丹团扇,10\n", encoding='utf-8')
        df = load_csv(str(csv_file))
        assert len(df) == 1
        assert '样式名称' in df.columns

    def test_load_invalid_file(self):
        with pytest.raises(ValueError):
            load_csv('/nonexistent/path/file.csv')


class TestConfigConstants:
    def test_standard_fields_complete(self):
        expected_fields = {'record_date', 'style_name', 'group_no', 'missing_parts',
                           'completed_count', 'rework_count', 'helper_name', 'note'}
        assert set(STANDARD_FIELDS.keys()) == expected_fields

    def test_missing_negative_values_is_frozenset(self):
        assert isinstance(MISSING_NEGATIVE_VALUES, frozenset)

    def test_column_keywords_has_all_fields(self):
        for field in STANDARD_FIELDS:
            assert field in COLUMN_KEYWORDS
