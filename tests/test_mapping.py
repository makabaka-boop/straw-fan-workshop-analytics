import pytest
import pandas as pd
from src.mapping import auto_map_columns, detect_data_type


class TestDetectDataType:
    def test_detect_completion_type(self):
        df = pd.DataFrame({
            '完成数量': [10, 20],
            '样式名称': ['A', 'B']
        })
        assert detect_data_type(df) == 'completion'

    def test_detect_rework_type(self):
        df = pd.DataFrame({
            '返工数量': [2, 3],
            '样式名称': ['A', 'B']
        })
        assert detect_data_type(df) == 'rework'

    def test_detect_material_type(self):
        df = pd.DataFrame({
            '缺件名称': ['竹骨', '丝线'],
            '样式名称': ['A', 'B']
        })
        assert detect_data_type(df) == 'material'

    def test_detect_general_type(self):
        df = pd.DataFrame({
            '样式名称': ['A', 'B'],
            '备注': ['test', 'test2']
        })
        assert detect_data_type(df) == 'general'

    def test_detect_english_columns(self):
        df = pd.DataFrame({
            'completed_count': [10, 20],
            'style_name': ['A', 'B']
        })
        assert detect_data_type(df) == 'completion'

    def test_mixed_columns(self):
        df = pd.DataFrame({
            '完成数量': [10, 20],
            'rework_count': [2, 3],
            'style_name': ['A', 'B']
        })
        assert detect_data_type(df) == 'completion'

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        assert detect_data_type(df) == 'general'


class TestAutoMapColumns:
    def test_map_chinese_column_names(self):
        df = pd.DataFrame({
            '记录日期': ['2026-01-01'],
            '样式名称': ['牡丹团扇'],
            '分组编号': ['A组'],
            '缺件名称': ['竹骨'],
            '完成数量': [10],
            '返工数量': [1],
            '助理姓名': ['李老师'],
            '备注': ['test'],
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

    def test_map_english_column_names(self):
        df = pd.DataFrame({
            'record_date': ['2026-01-01'],
            'style_name': ['Peony'],
            'group_no': ['A'],
            'missing_parts': ['bamboo'],
            'completed_count': [10],
            'rework_count': [1],
            'helper_name': ['Li'],
            'note': ['test'],
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

    def test_map_fuzzy_keywords(self):
        df = pd.DataFrame({
            '日期': ['2026-01-01'],
            '款式': ['牡丹'],
            '组别': ['A组'],
            '缺料': ['竹骨'],
            'done': [10],
            'rework': [1],
            '负责老师': ['王老师'],
            '说明': ['备注内容'],
        })
        mapping = auto_map_columns(df)
        assert mapping['日期'] == 'record_date'
        assert mapping['款式'] == 'style_name'
        assert mapping['组别'] == 'group_no'
        assert mapping['缺料'] == 'missing_parts'
        assert mapping['done'] == 'completed_count'
        assert mapping['rework'] == 'rework_count'
        assert mapping['负责老师'] == 'helper_name'
        assert mapping['说明'] == 'note'

    def test_mapping_returns_dict(self):
        df = pd.DataFrame({'样式名称': ['A']})
        mapping = auto_map_columns(df)
        assert isinstance(mapping, dict)

    def test_no_duplicate_mappings(self):
        df = pd.DataFrame({
            '样式名称': ['A'],
            '款式': ['B'],
        })
        mapping = auto_map_columns(df)
        mapped_fields = list(mapping.values())
        assert len(mapped_fields) == len(set(mapped_fields))

    def test_partial_columns(self):
        df = pd.DataFrame({
            '样式名称': ['牡丹团扇'],
            '完成数量': [10],
        })
        mapping = auto_map_columns(df)
        assert mapping['样式名称'] == 'style_name'
        assert mapping['完成数量'] == 'completed_count'
        assert 'record_date' not in mapping.values()
