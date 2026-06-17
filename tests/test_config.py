import pytest
from src.config import (
    STANDARD_FIELDS,
    FIELD_TYPES,
    MISSING_PART_EMPTY_VALUES,
    MISSING_PART_SPLIT_PATTERN,
    STATUS_LABELS,
    DATA_TYPE_LABELS,
    NUMERIC_FIELDS,
    STRING_FIELDS,
    DEFAULT_SOURCE_TYPE,
)


class TestStandardFields:
    def test_standard_fields_has_expected_keys(self):
        expected_keys = [
            'record_date', 'style_name', 'group_no', 'missing_parts',
            'completed_count', 'rework_count', 'helper_name', 'note'
        ]
        assert list(STANDARD_FIELDS.keys()) == expected_keys

    def test_standard_fields_chinese_names(self):
        assert STANDARD_FIELDS['record_date'] == '记录日期'
        assert STANDARD_FIELDS['style_name'] == '样式名称'
        assert STANDARD_FIELDS['completed_count'] == '完成数量'

    def test_field_types_match_standard_fields(self):
        assert set(FIELD_TYPES.keys()) == set(STANDARD_FIELDS.keys())

    def test_numeric_fields_in_standard(self):
        for field in NUMERIC_FIELDS:
            assert field in STANDARD_FIELDS
            assert FIELD_TYPES[field] == 'numeric'

    def test_string_fields_in_standard(self):
        for field in STRING_FIELDS:
            assert field in STANDARD_FIELDS
            assert FIELD_TYPES[field] == 'string'


class TestMissingPartValues:
    def test_empty_values_is_set(self):
        assert isinstance(MISSING_PART_EMPTY_VALUES, set)

    def test_common_empty_values_present(self):
        assert '' in MISSING_PART_EMPTY_VALUES
        assert 'nan' in MISSING_PART_EMPTY_VALUES
        assert 'none' in MISSING_PART_EMPTY_VALUES
        assert '无' in MISSING_PART_EMPTY_VALUES
        assert '0' in MISSING_PART_EMPTY_VALUES
        assert '-' in MISSING_PART_EMPTY_VALUES
        assert '/' in MISSING_PART_EMPTY_VALUES
        assert 'n/a' in MISSING_PART_EMPTY_VALUES
        assert 'null' in MISSING_PART_EMPTY_VALUES

    def test_split_pattern_is_regex(self):
        import re
        assert isinstance(MISSING_PART_SPLIT_PATTERN, str)
        re.compile(MISSING_PART_SPLIT_PATTERN)


class TestStatusLabels:
    def test_all_status_keys_present(self):
        expected = ['missing_and_rework', 'missing_only', 'rework_only', 'completed', 'in_progress']
        assert set(STATUS_LABELS.keys()) == set(expected)

    def test_status_labels_chinese(self):
        assert STATUS_LABELS['missing_and_rework'] == '缺件+返工'
        assert STATUS_LABELS['missing_only'] == '缺件待补'
        assert STATUS_LABELS['rework_only'] == '返工中'
        assert STATUS_LABELS['completed'] == '已完成'
        assert STATUS_LABELS['in_progress'] == '进行中'


class TestDataTypeLabels:
    def test_all_data_types_present(self):
        expected = ['material', 'completion', 'rework', 'general']
        assert set(DATA_TYPE_LABELS.keys()) == set(expected)

    def test_default_source_type(self):
        assert DEFAULT_SOURCE_TYPE == 'general'
        assert DEFAULT_SOURCE_TYPE in DATA_TYPE_LABELS
