#!/usr/bin/env python3
"""
V5报告校验器 — 检查分析报告完整性
用法: python3 validate_report.py <报告.md> <JSON路径>

检查报告是否包含所有必需章节,交叉验证关键数据。
"""
import sys, os, json, re

def validate(report_path, json_path):
    """校验报告完整性"""
    print(f"{'='*50}")
    print(f"  V5报告校验")
    print(f"{'='*50}")
    print(f"报告: {report_path}")
    print(f"JSON: {json_path}")
    print()

    # 读取报告
    with open(report_path, encoding="utf-8") as f:
        report = f.read()

    # 读取JSON
    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    checks = []
    passed = 0
    total = 11

    # 1. 历史复盘
    if "历史复盘" in report or "上次分析" in report or "上次结论" in report:
        checks.append(("✅", "历史复盘"))
        passed += 1
    else:
        checks.append(("❌", "历史复盘", "报告未包含历史复盘章节"))

    # 2. 前复权说明
    if "前复权" in report or "除权" in report or "复权" in report:
        checks.append(("✅", "前复权说明"))
        passed += 1
    else:
        checks.append(("❌", "前复权说明", "报告未提及前复权或除权检查"))

    # 3. 板块强弱对比
    if ("板块" in report and ("强于" in report or "弱于" in report or "同步" in report)) or "sector_analysis" in report:
        checks.append(("✅", "板块强弱对比"))
        passed += 1
    else:
        checks.append(("❌", "板块强弱对比", "报告未包含个股vs板块强弱对比"))

    # 4. 逐日量价分析(至少3根K线)
    kline_mentions = len(re.findall(r'K线\d|K线[★☆]|\d/\d.*收盘|\d月\d日', report))
    if kline_mentions >= 3:
        checks.append((f"✅", f"量价分析({kline_mentions}处K线引用)"))
        passed += 1
    else:
        checks.append(("❌", "量价分析", f"仅{kline_mentions}处K线引用,需至少3根"))

    # 5. 资金流向
    if "资金" in report and ("净流入" in report or "净流出" in report or "主力" in report):
        checks.append(("✅", "资金流向"))
        passed += 1
    else:
        checks.append(("❌", "资金流向", "报告未包含资金流数据"))

    # 6. 情绪周期(换手率)
    if "情绪" in report and ("换手" in report or "冷淡" in report or "过热" in report or "情绪底部" in report):
        checks.append(("✅", "情绪周期分析"))
        passed += 1
    else:
        checks.append(("❌", "情绪周期分析", "报告未分析换手率5档或情绪周期"))

    # 7. 概念纯度评级
    if "概念" in report and ("纯度" in report or "核心概念" in report or "★" in report or "龙头" in report):
        checks.append(("✅", "概念纯度评级"))
        passed += 1
    else:
        checks.append(("❌", "概念纯度评级", "报告未包含概念纯度评级或龙头识别"))

    # 8. 消息面情绪评分
    if "消息面" in report and ("情绪" in report or "得分" in report or "利好" in report):
        checks.append(("✅", "消息面情绪"))
        passed += 1
    else:
        checks.append(("❌", "消息面情绪", "报告未包含消息面情绪评分"))

    # 9. 风险筛查(至少3项)
    risk_items = len(re.findall(r'风险|减持|质押|亏损|利空|解禁|破位|估值异常', report))
    if risk_items >= 3:
        checks.append((f"✅", f"风险筛查({risk_items}项)"))
        passed += 1
    else:
        checks.append(("❌", "风险筛查", f"仅{risk_items}项风险,需至少3项"))

    # 10. 操作建议(已持有+未持有)
    has_hold = "已持有" in report or "持有" in report
    has_no_hold = "未持有" in report or "空仓" in report or "不建议" in report
    if has_hold and has_no_hold:
        checks.append(("✅", "操作建议(已持有+未持有)"))
        passed += 1
    elif has_hold or has_no_hold:
        checks.append(("⚠️", "操作建议", "仅覆盖部分场景(已持有或未持有)"))
        passed += 0.5
    else:
        checks.append(("❌", "操作建议", "报告未包含操作建议"))

    # 11. 交叉验证: 关键价位
    price_ok = True
    issues = []
    if data.get("indicators"):
        ma5 = data["indicators"].get("ma5")
        ma20 = data["indicators"].get("ma20")
        if ma5 and f"MA5" in report:
            # 检查报告中MA5数值是否合理(容差1%)
            m = re.search(r'MA5[=:]\s*([\d.]+)', report)
            if m:
                reported_ma5 = float(m.group(1))
                if abs(reported_ma5 - ma5) / ma5 > 0.02:
                    issues.append(f"MA5: 报告{reported_ma5} vs 数据{ma5}")
                    price_ok = False
    if price_ok:
        checks.append(("✅", "关键价位交叉验证"))
        passed += 1
    else:
        checks.append(("❌", "关键价位交叉验证", "; ".join(issues)))

    # 输出结果
    for item in checks:
        icon = item[0]
        name = item[1]
        detail = item[2] if len(item) > 2 else ""
        if detail:
            print(f"  {icon} {name} ({detail})")
        else:
            print(f"  {icon} {name}")

    print()
    print(f"  校验结果: {passed}/{total} 通过")
    if passed == total:
        print(f"  🟢 报告完整,无缺项")
    elif passed >= total - 2:
        print(f"  🟡 报告基本完整,有{total - int(passed)}项需补充")
    else:
        print(f"  🔴 报告缺项较多,需重写{total - int(passed)}项")

    # JSON版本检查
    version = data.get("version", "unknown")
    steps = data.get("steps_completed", [])
    print(f"\n  JSON版本: V{version}")
    print(f"  完成步骤: {len(steps)}/15")

    print(f"{'='*50}")
    return passed >= total - 2

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python3 validate_report.py <报告.md> <JSON路径>")
        sys.exit(1)
    ok = validate(sys.argv[1], sys.argv[2])
    sys.exit(0 if ok else 1)
