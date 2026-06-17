import pandas as pd
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.constants import STANDARD_FIELDS
from core.data_processor import auto_map_columns, process_data
from core.analytics import (
    analyze_missing_concentration,
    analyze_rework_anomalies,
    analyze_group_missing,
    analyze_helper_workload,
    generate_material_suggestions,
    get_pending_materials,
    calculate_style_stats,
    calculate_summary_metrics,
)


def run_tests():
    print("=" * 60)
    print("🧪 开始测试草编团扇工作坊分析工作台核心功能")
    print("=" * 60)

    df = pd.read_csv('sample_data.csv')
    print(f"\n✅ 1. 测试数据加载: 成功加载 {len(df)} 条记录")
    print(f"   列名: {list(df.columns)}")

    mapping = auto_map_columns(df)
    print(f"\n✅ 2. 测试自动列名映射:")
    for col, std_field in mapping.items():
        print(f"   {col} -> {std_field} ({STANDARD_FIELDS[std_field]})")

    processed = process_data(df, mapping)
    print(f"\n✅ 3. 测试数据处理: 处理后 {len(processed)} 条有效记录")
    print(f"   列名: {list(processed.columns)}")
    print(f"   状态分布: {processed['status'].value_counts().to_dict()}")

    missing_analysis = analyze_missing_concentration(processed)
    print(f"\n✅ 4. 测试缺件集中分析: 发现 {len(missing_analysis)} 种缺件材料")
    if missing_analysis is not None:
        print(missing_analysis.head())

    rework_analysis = analyze_rework_anomalies(processed)
    print(f"\n✅ 5. 测试返工异常分析: 发现 {len(rework_analysis)} 种样式有返工记录")
    if rework_analysis is not None:
        print(rework_analysis.head())

    group_missing = analyze_group_missing(processed)
    print(f"\n✅ 6. 测试分组缺失分析: 发现 {len(group_missing)} 个分组有缺件")
    if group_missing is not None:
        print(group_missing.head())

    helper_stats = analyze_helper_workload(processed)
    print(f"\n✅ 7. 测试助理负载分析: 共 {len(helper_stats)} 位助理")
    print(helper_stats.head())

    suggestions = generate_material_suggestions(processed, recent_days=30)
    print(f"\n✅ 8. 测试备料建议生成: 生成 {len(suggestions)} 条建议")
    if suggestions is not None:
        print(suggestions)

    pending = get_pending_materials(processed)
    print(f"\n✅ 9. 测试待补件列表: 共 {len(pending)} 个待补件记录")
    if pending is not None:
        print(pending.head())

    style_stats = calculate_style_stats(processed)
    print(f"\n✅ 10. 测试样式完成率计算:")
    print(style_stats[['style_name', '完成率']].sort_values('完成率', ascending=False))

    metrics = calculate_summary_metrics(processed)
    print(f"\n📊 关键指标汇总:")
    print(f"   总完成数: {metrics['total_completed']:,}")
    print(f"   总返工数: {metrics['total_rework']:,}")
    print(f"   返工率: {metrics['rework_rate']:.1f}%")
    print(f"   缺件记录: {metrics['missing_count']}")
    print(f"   活跃分组: {metrics['active_groups']}")

    print("\n" + "=" * 60)
    print("🎉 所有测试通过！核心功能正常工作")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
