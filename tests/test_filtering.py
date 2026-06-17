import pytest
import pandas as pd
from datetime import datetime, date

from src.core.filtering import (
    filter_by_date,
    filter_by_styles,
    filter_by_groups,
    filter_by_helpers,
    filter_by_statuses,
    apply_filters,
    get_unique_values,
    get_date_range,
)


@pytest.fixture
def sample_df():
    data = {
        'record_date': pd.to_datetime([
            '2026-05-01', '2026-05-02', '2026-05-03', '2026-05-04', '2026-05-05'
        ]),
        'style_name': ['牡丹团扇', '梅花团扇', '兰花团扇', '菊花团扇', '牡丹团扇'],
        'group_no': ['A组', 'B组', 'A组', 'C组', 'B组'],
        'helper_name': ['李老师', '王老师', '李老师', '张老师', '王老师'],
        'status': ['已完成', '返工中', '已完成', '缺件待补', '已完成'],
        'completed_count': [20, 15, 25, 18, 22],
        'rework_count': [0, 2, 0, 1, 0],
        'has_missing': [False, False, False, True, False],
    }
    return pd.DataFrame(data)


class TestFilterByDate:
    def test_start_date_only(self, sample_df):
        start = date(2026, 5, 3)
        result = filter_by_date(sample_df, start_date=start)
        assert len(result) == 3
        assert result['record_date'].min().date() >= start

    def test_end_date_only(self, sample_df):
        end = date(2026, 5, 3)
        result = filter_by_date(sample_df, end_date=end)
        assert len(result) == 3
        assert result['record_date'].max().date() <= end

    def test_date_range(self, sample_df):
        start = date(2026, 5, 2)
        end = date(2026, 5, 4)
        result = filter_by_date(sample_df, start_date=start, end_date=end)
        assert len(result) == 3

    def test_no_date_column(self, sample_df):
        df = sample_df.drop(columns=['record_date'])
        result = filter_by_date(df, start_date=date(2026, 5, 1))
        assert len(result) == len(df)

    def test_no_dates_provided(self, sample_df):
        result = filter_by_date(sample_df)
        assert len(result) == len(sample_df)


class TestFilterByStyles:
    def test_selected_styles(self, sample_df):
        result = filter_by_styles(sample_df, ['牡丹团扇', '梅花团扇'])
        assert len(result) == 3
        assert set(result['style_name'].unique()) == {'牡丹团扇', '梅花团扇'}

    def test_empty_styles_returns_empty(self, sample_df):
        result = filter_by_styles(sample_df, [])
        assert len(result) == 0

    def test_nonexistent_style(self, sample_df):
        result = filter_by_styles(sample_df, ['不存在的样式'])
        assert len(result) == 0


class TestFilterByGroups:
    def test_selected_groups(self, sample_df):
        result = filter_by_groups(sample_df, ['A组'])
        assert len(result) == 2

    def test_empty_groups_returns_empty(self, sample_df):
        result = filter_by_groups(sample_df, [])
        assert len(result) == 0


class TestFilterByHelpers:
    def test_selected_helpers(self, sample_df):
        result = filter_by_helpers(sample_df, ['李老师'])
        assert len(result) == 2

    def test_empty_helpers_returns_empty(self, sample_df):
        result = filter_by_helpers(sample_df, [])
        assert len(result) == 0


class TestFilterByStatuses:
    def test_selected_statuses(self, sample_df):
        result = filter_by_statuses(sample_df, ['已完成'])
        assert len(result) == 3

    def test_empty_statuses_returns_empty(self, sample_df):
        result = filter_by_statuses(sample_df, [])
        assert len(result) == 0


class TestApplyFilters:
    def test_multiple_filters(self, sample_df):
        result = apply_filters(
            sample_df,
            styles=['牡丹团扇'],
            groups=['A组', 'B组'],
        )
        assert len(result) == 2

    def test_date_filter_only(self, sample_df):
        result = apply_filters(
            sample_df,
            date_range=(date(2026, 5, 2), date(2026, 5, 4)),
        )
        assert len(result) == 3

    def test_all_filters_empty(self, sample_df):
        result = apply_filters(
            sample_df,
            styles=[],
            groups=[],
            helpers=[],
            statuses=[],
        )
        assert len(result) == 0

    def test_no_filters_returns_all(self, sample_df):
        result = apply_filters(sample_df)
        assert len(result) == len(sample_df)


class TestGetUniqueValues:
    def test_existing_column(self, sample_df):
        result = get_unique_values(sample_df, 'style_name')
        assert isinstance(result, list)
        assert len(result) == 4
        assert result == sorted(result)

    def test_nonexistent_column(self, sample_df):
        result = get_unique_values(sample_df, '不存在的列')
        assert result == []


class TestGetDateRange:
    def test_valid_dates(self, sample_df):
        min_d, max_d = get_date_range(sample_df)
        assert min_d == date(2026, 5, 1)
        assert max_d == date(2026, 5, 5)

    def test_no_date_column(self, sample_df):
        df = sample_df.drop(columns=['record_date'])
        min_d, max_d = get_date_range(df)
        assert min_d is None
        assert max_d is None

    def test_all_nat_dates(self):
        df = pd.DataFrame({
            'record_date': pd.to_datetime([pd.NaT, pd.NaT]),
        })
        min_d, max_d = get_date_range(df)
        assert min_d is None
        assert max_d is None
