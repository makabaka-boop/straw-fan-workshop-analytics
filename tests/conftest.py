import os
import sys

import pytest
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def sample_raw_df():
    return pd.read_csv(os.path.join(PROJECT_ROOT, 'sample_data.csv'))


@pytest.fixture
def sample_no_date_df():
    return pd.read_csv(os.path.join(PROJECT_ROOT, 'sample_data_no_date.csv'))


@pytest.fixture
def sample_mapping(sample_raw_df):
    from src.mapping import auto_map_columns
    return auto_map_columns(sample_raw_df)


@pytest.fixture
def processed_df(sample_raw_df, sample_mapping):
    from src.processing import process_data
    return process_data(sample_raw_df, sample_mapping, source_type='general')


@pytest.fixture
def processed_no_date_df(sample_no_date_df):
    from src.mapping import auto_map_columns
    from src.processing import process_data
    mapping = auto_map_columns(sample_no_date_df)
    return process_data(sample_no_date_df, mapping, source_type='general')


@pytest.fixture
def empty_mapping():
    return {}


@pytest.fixture
def minimal_valid_df():
    return pd.DataFrame({
        'record_date': pd.to_datetime(['2026-01-01', '2026-01-02']),
        'style_name': ['样式A', '样式B'],
        'group_no': ['A组', 'B组'],
        'missing_parts': ['竹骨', ''],
        'completed_count': [10, 20],
        'rework_count': [1, 0],
        'helper_name': ['李老师', '王老师'],
        'note': ['', ''],
        'source_type': 'general',
        'has_missing': [True, False],
        'has_rework': [True, False],
        'status': ['缺件+返工', '已完成'],
    })
