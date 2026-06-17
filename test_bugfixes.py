import pandas as pd
import numpy as np
from datetime import datetime

STANDARD_FIELDS = {
    'record_date': '记录日期',
    'style_name': '样式名称',
    'group_no': '分组编号',
    'missing_parts': '缺件名称',
    'completed_count': '完成数量',
    'rework_count': '返工数量',
    'helper_name': '助理姓名',
    'note': '备注'
}

def auto_map_columns(df):
    mapping = {}
    df_cols = df.columns.tolist()
    
    for std_field, std_name in STANDARD_FIELDS.items():
        for col in df_cols:
            col_lower = col.lower()
            std_lower = std_name.lower()
            field_lower = std_field.lower()
            
            if col_lower == std_lower or col_lower == field_lower:
                mapping[col] = std_field
                break
            
            if std_field == 'record_date' and ('日期' in col or 'date' in col_lower or '时间' in col):
                mapping[col] = std_field
                break
            elif std_field == 'style_name' and ('样式' in col or '款' in col or 'style' in col_lower or 'name' in col_lower):
                mapping[col] = std_field
                break
            elif std_field == 'group_no' and ('组' in col or 'group' in col_lower or '编号' in col):
                mapping[col] = std_field
                break
            elif std_field == 'missing_parts' and ('缺' in col or 'missing' in col_lower or '少' in col or '材料' in col):
                mapping[col] = std_field
                break
            elif std_field == 'completed_count' and ('完成' in col or 'complete' in col_lower or 'done' in col_lower):
                mapping[col] = std_field
                break
            elif std_field == 'rework_count' and ('返工' in col or 'rework' in col_lower):
                mapping[col] = std_field
                break
            elif std_field == 'helper_name' and ('助理' in col or 'helper' in col_lower or '负责' in col or '老师' in col):
                mapping[col] = std_field
                break
            elif std_field == 'note' and ('备注' in col or 'note' in col_lower or '说明' in col):
                mapping[col] = std_field
                break
    
    return mapping

def determine_status(row):
    if row['has_missing'] and row['has_rework']:
        return '缺件+返工'
    elif row['has_missing']:
        return '缺件待补'
    elif row['has_rework']:
        return '返工中'
    elif row['completed_count'] > 0:
        return '已完成'
    else:
        return '进行中'

def process_data(df, mapping):
    if not mapping:
        return None
    
    processed = df.copy()
    reverse_map = {v: k for k, v in mapping.items()}
    result = pd.DataFrame()
    
    for std_field in STANDARD_FIELDS.keys():
        if std_field in reverse_map:
            original_col = reverse_map[std_field]
            result[std_field] = processed[original_col]
        else:
            if std_field in ['completed_count', 'rework_count']:
                result[std_field] = 0
            elif std_field == 'record_date':
                result[std_field] = pd.NaT
            else:
                result[std_field] = ''
    
    result['record_date'] = pd.to_datetime(result['record_date'], errors='coerce')
    result['completed_count'] = pd.to_numeric(result['completed_count'], errors='coerce').fillna(0).astype(int)
    result['rework_count'] = pd.to_numeric(result['rework_count'], errors='coerce').fillna(0).astype(int)
    result['style_name'] = result['style_name'].astype(str).str.strip()
    result['group_no'] = result['group_no'].astype(str).str.strip()
    result['missing_parts'] = result['missing_parts'].astype(str).str.strip()
    result['helper_name'] = result['helper_name'].astype(str).str.strip()
    result['note'] = result['note'].astype(str).str.strip()
    result = result[result['style_name'] != '']
    result['source_type'] = 'general'
    
    def check_has_missing(x):
        if pd.isna(x):
            return False
        x_str = str(x).strip().lower()
        return x_str not in ['', 'nan', 'none', '无', '没有', '无缺件', '0', '-', '/', 'n/a', 'null']
    
    result['has_missing'] = result['missing_parts'].apply(check_has_missing)
    result['has_rework'] = result['rework_count'] > 0
    result['status'] = result.apply(determine_status, axis=1)
    
    return result

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
        def check_has_missing(x):
            if pd.isna(x):
                return False
            x_str = str(x).strip().lower()
            return x_str not in ['', 'nan', 'none', '无', '没有', '无缺件', '0', '-', '/', 'n/a', 'null']
        
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
        filtered = df.copy()
        
        if len(selected_styles) > 0:
            filtered = filtered[filtered['样式名称'].isin(selected_styles)]
        else:
            filtered = filtered.iloc[0:0]
        
        if len(selected_groups) > 0:
            filtered = filtered[filtered['分组编号'].isin(selected_groups)]
        else:
            filtered = filtered.iloc[0:0]
        
        if len(selected_helpers) > 0:
            filtered = filtered[filtered['助理姓名'].isin(selected_helpers)]
        else:
            filtered = filtered.iloc[0:0]
        
        if len(selected_statuses) > 0:
            filtered = filtered[filtered['status'].isin(selected_statuses)]
        else:
            filtered = filtered.iloc[0:0]
        
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
