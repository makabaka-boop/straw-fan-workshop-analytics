import pandas as pd
import numpy as np
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.data_processor import (
    auto_map_columns,
    process_data,
    check_has_missing,
    filter_data,
)


def test_bug_3_missing_detection():
    print("=" * 60)
    print("🧪 Bug 3 测试: 无缺件被误判成有缺件")
    print("=" * 60)

    test_cases = [
        ('', False, '空字符串'),
        ('nan', False, '小写nan'),
        ('NaN', False, '大写NaN'),
        ('None', False, 'None'),
        ('none', False, '小写none'),
        ('无', False, '中文无'),
        ('没有', False, '中文没有'),
        ('无缺件', False, '中文无缺件'),
        ('0', False, '数字0'),
        ('-', False, '横杠'),
        ('/', False, '斜杠'),
        ('n/a', False, 'n/a'),
        ('N/A', False, '大写N/A'),
        ('null', False, 'null'),
        ('NULL', False, '大写NULL'),
        ('  ', False, '空格'),
        (np.nan, False, 'np.nan'),
        (None, False, 'Python None'),
        ('竹骨', True, '正常缺件:竹骨'),
        ('丝线', True, '正常缺件:丝线'),
        ('竹骨,丝线', True, '多个缺件'),
    ]

    all_passed = True
    for input_val, expected, desc in test_cases:
        result = check_has_missing(input_val)
        status = "✅" if result == expected else "❌"
        if result != expected:
            all_passed = False
        print(f"  {status} {desc}: 输入={repr(input_val)}, 预期={expected}, 实际={result}")

    if all_passed:
        print("\n✅ Bug 3 修复验证通过！")
    else:
        print("\n❌ Bug 3 修复验证失败！")

    return all_passed


def test_bug_2_no_date_data():
    print("\n" + "=" * 60)
    print("🧪 Bug 2 测试: 上传的数据没有日期，页面会报错")
    print("=" * 60)

    data_no_date = {
        '样式名称': ['牡丹团扇', '梅花团扇', '兰花团扇'],
        '分组编号': ['A组', 'B组', 'C组'],
        '缺件名称': ['', '丝线', ''],
        '完成数量': [20, 15, 25],
        '返工数量': [1, 2, 0],
        '助理姓名': ['李老师', '王老师', '张老师'],
        '备注': ['', '', '']
    }

    df = pd.DataFrame(data_no_date)
    print(f"  测试数据: {len(df)} 条记录，无日期列")

    mapping = auto_map_columns(df)
    print(f"  自动映射: {mapping}")

    try:
        processed = process_data(df, mapping)
        print(f"  数据处理成功: {len(processed)} 条记录")

        has_valid_dates = processed['record_date'].notna().any()
        print(f"  有效日期检测: has_valid_dates = {has_valid_dates}")

        all_dates_na = processed['record_date'].isna().all()
        print(f"  所有日期为空: {all_dates_na}")

        max_date = processed['record_date'].max()
        print(f"  max_date = {repr(max_date)}, pd.isna(max_date) = {pd.isna(max_date)}")

        if has_valid_dates:
            min_date = processed['record_date'].dropna().min().date()
            max_date = processed['record_date'].dropna().max().date()
            print(f"  日期范围计算: {min_date} ~ {max_date}")
        else:
            print("  ✅ 正确跳过日期筛选，不会报错")

        daily_rework = processed.copy()
        daily_rework = daily_rework.dropna(subset=['record_date'])
        print(f"  去除空日期后记录数: {len(daily_rework)}")

        if len(daily_rework) > 0:
            print("  执行趋势图绘制")
        else:
            print("  ✅ 正确跳过趋势图，显示提示信息")

        print("\n✅ Bug 2 修复验证通过！")
        return True

    except Exception as e:
        print(f"\n❌ Bug 2 修复验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bug_1_empty_filter():
    print("\n" + "=" * 60)
    print("🧪 Bug 1 测试: 清空筛选项后，页面还是显示全部数据")
    print("=" * 60)

    data = {
        '样式名称': ['牡丹团扇', '梅花团扇', '兰花团扇', '菊花团扇'],
        '分组编号': ['A组', 'B组', 'A组', 'C组'],
        '完成数量': [20, 15, 25, 18],
        '返工数量': [1, 2, 0, 3],
        '助理姓名': ['李老师', '王老师', '李老师', '张老师'],
        'status': ['已完成', '返工中', '已完成', '缺件待补']
    }

    df = pd.DataFrame(data)
    print(f"  原始数据: {len(df)} 条记录")

    styles = sorted(df['样式名称'].unique().tolist())
    groups = sorted(df['分组编号'].unique().tolist())
    helpers = sorted(df['助理姓名'].unique().tolist())
    statuses = sorted(df['status'].unique().tolist())

    print(f"  所有样式: {styles}")
    print(f"  所有分组: {groups}")
    print(f"  所有助理: {helpers}")
    print(f"  所有状态: {statuses}")

    test_cases = [
        ([], [], [], [], "全部清空"),
        ([], groups, helpers, statuses, "清空样式"),
        (styles, [], helpers, statuses, "清空分组"),
        (styles, groups, [], statuses, "清空助理"),
        (styles, groups, helpers, [], "清空状态"),
    ]

    all_passed = True
    for selected_styles, selected_groups, selected_helpers, selected_statuses, desc in test_cases:
        filtered = filter_data(
            df.rename(columns={
                '样式名称': 'style_name',
                '分组编号': 'group_no',
                '助理姓名': 'helper_name',
            }),
            selected_styles=selected_styles,
            selected_groups=selected_groups,
            selected_helpers=selected_helpers,
            selected_statuses=selected_statuses,
        )

        expected_count = 0
        actual_count = len(filtered)
        status = "✅" if actual_count == expected_count else "❌"
        if actual_count != expected_count:
            all_passed = False
        print(f"  {status} {desc}: 预期={expected_count}条, 实际={actual_count}条")

    if all_passed:
        print("\n✅ Bug 1 修复验证通过！")
    else:
        print("\n❌ Bug 1 修复验证失败！")

    return all_passed


def run_all_tests():
    print("\n" + "=" * 60)
    print("🔍 开始三个Bug修复验证测试")
    print("=" * 60)

    results = []
    results.append(('Bug 3: 无缺件误判', test_bug_3_missing_detection()))
    results.append(('Bug 2: 无日期数据报错', test_bug_2_no_date_data()))
    results.append(('Bug 1: 清空筛选仍显示全部', test_bug_1_empty_filter()))

    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    all_passed = True
    for name, passed in results:
        status = "✅ 通过" if passed else "❌ 失败"
        if not passed:
            all_passed = False
        print(f"  {status} - {name}")

    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有Bug修复验证通过！")
    else:
        print("⚠️  部分Bug修复需要进一步检查")
    print("=" * 60)

    return all_passed


if __name__ == "__main__":
    run_all_tests()
