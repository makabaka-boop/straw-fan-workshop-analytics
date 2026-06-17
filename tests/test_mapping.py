import pytest
import pandas as pd

from src.core.mapping import auto_map_columns, detect_data_type, reverse_mapping


class TestAutoMapColumns:
    def test_exact_match_chinese(self):
        df = pd.DataFrame({
            '记录日期': ['2026-01-01'],
            '样式名称': ['牡丹'],
            '分组编号': ['A组'],
            '缺件名称': ['竹骨'],
            '完成数量': [10],
            '返工数量': [2],
            '助理姓名': ['李老师'],
            '备注': ['test']
        })
        mapping = auto_map_columns(df)
        assert mapping['记录日期'] == 'record_date'
        assert mapping['样式名称'] == 'style_name'
        assert mapping['分组编号'] == 'group_no'
        assert mapping['缺件名称'] == 'missing_parts'
        assert mapping['完成数量'] == 'completed_count'
        assert mapping['返工数量'] == 'rework_count'
        assert mapping['助理姓名'] == 'helper_name'
        assert mapping['备注'] == 'note'

    def test_exact_match_english(self):
        df = pd.DataFrame({
            'record_date': ['2026-01-01'],
            'style_name': ['牡丹'],
            'group_no': ['A组'],
            'missing_parts': ['竹骨'],
            'completed_count': [10],
            'rework_count': [2],
            'helper_name': ['李老师'],
            'note': ['test']
        })
        mapping = auto_map_columns(df)
        assert mapping['record_date'] == 'record_date'
        assert mapping['style_name'] == 'style_name'
        assert mapping['group_no'] == 'group_no'
        assert mapping['missing_parts'] == 'missing_parts'
        assert mapping['completed_count'] == 'completed_count'
        assert mapping['rework_count'] == 'rework_count'
        assert mapping['helper_name'] == 'helper_name'
        assert mapping['note'] == 'note'

    def test_keyword_match(self):
        df = pd.DataFrame({
            '日期': ['2026-01-01'],
            '款式': ['牡丹'],
            '组别': ['A组'],
            '缺料': ['竹骨'],
            '已完成': [10],
            '返工品': [2],
            '负责老师': ['李老师'],
            '说明': ['test']
        })
        mapping = auto_map_columns(df)
        assert mapping['日期'] == 'record_date'
        assert mapping['款式'] == 'style_name'
        assert mapping['组别'] == 'group_no'
        assert mapping['缺料'] == 'missing_parts'
        assert mapping['已完成'] == 'completed_count'
        assert mapping['返工品'] == 'rework_count'
        assert mapping['负责老师'] == 'helper_name'
        assert mapping['说明'] == 'note'

    def test_partial_columns(self):
        df = pd.DataFrame({
            '样式名称': ['牡丹'],
            '完成数量': [10],
        })
        mapping = auto_map_columns(df)
        assert len(mapping) == 2
        assert mapping['样式名称'] == 'style_name'
        assert mapping['完成数量'] == 'completed_count'

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        mapping = auto_map_columns(df)
        assert mapping == {}

    def test_case_insensitive(self):
        df = pd.DataFrame({
            'DATE': ['2026-01-01'],
            'Style': ['牡丹'],
        })
        mapping = auto_map_columns(df)
        assert 'DATE' in mapping
        assert mapping['DATE'] == 'record_date'
        assert mapping['Style'] == 'style_name'


class TestDetectDataType:
    def test_completion_type(self):
        df = pd.DataFrame({'完成数量': [10, 20]})
        assert detect_data_type(df) == 'completion'

    def test_rework_only_type(self):
        df = pd.DataFrame({'返工数量': [2, 3]})
        assert detect_data_type(df) == 'rework'

    def test_material_only_type(self):
        df = pd.DataFrame({'缺件名称': ['竹骨', '丝线']})
        assert detect_data_type(df) == 'material'

    def test_general_type(self):
        df = pd.DataFrame({'名称': ['test']})
        assert detect_data_type(df) == 'general'

    def test_mixed_completion_rework(self):
        df = pd.DataFrame({'完成数量': [10], '返工数量': [2]})
        assert detect_data_type(df) == 'completion'


class TestReverseMapping:
    def test_reverse_mapping(self):
        mapping = {'记录日期': 'record_date', '样式名称': 'style_name'}
        reverse = reverse_mapping(mapping)
        assert reverse['record_date'] == '记录日期'
        assert reverse['style_name'] == '样式名称'

    def test_empty_mapping(self):
        assert reverse_mapping({}) == {}
