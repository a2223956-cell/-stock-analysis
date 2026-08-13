# execute_code 技术指标批量计算模板

> 创建日期: 2026-07-29
> 用途: 深度分析时用 execute_code 一次性计算所有技术指标,避免逐个 terminal 调用
> 验证: 2026-07-29 许继电气/雷赛智能/双环传动/泛微网络/百利天恒 五票分析均使用此模板

## 为什么用 execute_code

- **速度快**: 一次调用完成 MA/Fibonacci/R:R/箱体/量能/资金流汇总,省去6+次 terminal 调用
- **数据联动**: 所有计算在同一 Python 上下文中,变量可互相引用(如用 MA10 做 R:R 支撑位)
- **可视化输出**: 量能柱状图(█字符)、三重底检测等,直接打印到 stdout
- **无 rate limit**: execute_code 不走 HTTP 代理,不受东财 API 限频影响

## 标准模板(可直接复制修改)

```python
# ===== 输入区(每次分析修改这里) =====
stock_name = "股票名"
stock_code = "000400"
prefix = "sz"  # sh/sz
current = 22.09  # 实时价格(从腾讯行情API获取)
prev_close = 21.78

# K-line 数据(em_api.py kline 输出,每行: date,open,close,high,low,vol)
klines_raw = """2026-06-17,22.68,22.82,22.96,22.51,151423
2026-06-18,22.83,22.66,22.9,22.21,222823
..."""

# 资金流数据(em_api.py fund_flow 输出,每行: date: 主力+X.XX亿)
fund_flow_raw = """2026-07-01: 主力-0.32亿
2026-07-02: 主力-0.29亿
..."""

# ===== 计算区(通常不需要修改) =====
import json

rows = []
for line in klines_raw.strip().split('\n'):
    parts = line.split(',')
    rows.append({
        'date': parts[0],
        'open': float(parts[1]),
        'close': float(parts[2]),
        'high': float(parts[3]),
        'low': float(parts[4]),
        'vol': int(parts[5])
    })

closes = [r['close'] for r in rows]
vols = [r['vol'] for r in rows]

# 均线计算
ma5 = sum(closes[-5:]) / 5
ma10 = sum(closes[-10:]) / 10
ma20 = sum(closes[-20:]) / 20

print(f"=== MA计算 (当前价: {current}) ===")
for name, ma in [('MA5', ma5), ('MA10', ma10), ('MA20', ma20)]:
    print(f"{name}: {ma:.2f}  偏离: {(current/ma-1)*100:.1f}%")

# 均线排列
ma_list = sorted([('MA5',ma5),('MA10',ma10),('MA20',ma20)], key=lambda x:x[1], reverse=True)
print(f"排列: {' > '.join([f'{n}({v:.1f})' for n,v in ma_list])}")

# 量能分析
vol_5d = sum(vols[-5:])/5
vol_prev5 = sum(vols[-10:-5])/5
print(f"\n=== 量能 ===")
print(f"5日均量: {vol_5d:.0f}手, 前5日: {vol_prev5:.0f}手, 比值: {vol_5d/vol_prev5:.2f}")

# 量能柱状图(近10日)
print(f"\n近10日成交量:")
for r in rows[-10:]:
    bar = '█' * int(r['vol'] / 50000)  # 调整除数适配不同量级
    print(f"  {r['date']}: {r['vol']:>8}手 {bar}")

# Fibonacci(需手动设定高低点)
swing_high = max(r['high'] for r in rows)
swing_low = min(r['low'] for r in rows)
range_hl = swing_high - swing_low
print(f"\n=== Fibonacci(从{swing_low}到{swing_high}) ===")
for pct, name in [(0.382,'38.2%'),(0.500,'50.0%'),(0.618,'61.8%')]:
    level = swing_low + range_hl * pct
    pos = "在上方 ✅" if current > level else "在下方"
    print(f"{name}: {level:.2f} ← 当前{current} {pos}")

# R:R(需手动设定阻力/支撑)
resistance = swing_high  # 或用箱顶/前高
support = swing_low      # 或用MA10/箱底
if current > support:
    rr = (resistance - current) / (current - support)
    print(f"\n=== R:R ===")
    print(f"阻力: {resistance}, 支撑: {support}")
    print(f"上涨: +{(resistance/current-1)*100:.1f}%, 下跌: -{(current-support)/current*100:.1f}%")
    print(f"R:R = {rr:.2f} {'✅' if rr>1.0 else '❌'}")

# 箱体分析
recent_closes = closes[-15:]
box_high = max(recent_closes)
box_low = min(recent_closes)
box_pos = (current - box_low) / (box_high - box_low) if box_high != box_low else 0.5
print(f"\n=== 箱体(近15日) ===")
print(f"箱顶: {box_high:.2f}, 箱底: {box_low:.2f}, 位置: {box_pos:.0%}")

# 资金流汇总
fund_flows = []  # 从 fund_flow_raw 解析
# ... 解析逻辑 ...
total_20d = sum(fund_flows) if fund_flows else 0
recent_5d = sum(fund_flows[-5:]) if len(fund_flows) >= 5 else 0
print(f"\n=== 资金流 ===")
print(f"20日累计: {total_20d:+.2f}亿, 近5日: {recent_5d:+.2f}亿")
```

## 使用步骤

1. **获取数据**: 先用 terminal 调 em_api.py 获取 K线和资金流
2. **复制模板**: 将上面的模板粘贴到 execute_code
3. **填入数据**: 粘贴 K线和资金流数据,设置 current/prev_close
4. **调整参数**: 修改 swing_high/swing_low/resistance/support
5. **运行**: execute_code 一次性输出所有指标

## 常见调整点

| 场景 | 调整内容 |
|------|---------|
| 三重底/双底检测 | 添加 low_points 列表,计算极差 |
| 涨停出货分析 | 添加涨停期/出货期资金流对比 |
| 箱体策略 | 添加箱体位置判断(0-20%低吸/80-100%减仓) |
| 大盘指数 | 改用 sh000001 等指数代码 |

## 注意事项

- K线数据中最后一行可能是除权信息(dict),需要 `isinstance(k, list)` 过滤
- 量能柱状图的除数(50000)需根据个股量级调整(小盘股用10000,大盘股用100000)
- 资金流数据需要从 `fund_flow_raw` 文本解析为 float 列表
- execute_code 的5分钟超时对30日K线计算绰绰有余
