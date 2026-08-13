# 腾讯K线API 'day' vs 'qfqday' key差异

## 问题描述

腾讯历史K线API (`web.ifzq.gtimg.cn/appstock/app/fqkline/get`) 返回的JSON中,
**指数**和**个股**使用不同的key存储K线数据:

| 类型 | key | 示例 |
|------|-----|------|
| 指数(上证/深证/创业板) | `day` | `data.sh000001.day` |
| 个股(股票) | `qfqday` | `data.sz000400.qfqday` |

## 影响

如果代码只查找 `qfqday` key,获取指数K线数据会失败,
导致MA20计算返回当前价格而非真正的20日均线。

## 修复方案

```python
# ✅ 正确: 兼容两种key
stock_data = data['data'][full_code]
klines = stock_data.get('qfqday') or stock_data.get('day', [])

# ❌ 错误: 只查找qfqday
klines = data['data'][full_code]['qfqday']  # 指数会KeyError
```

## 触发场景

- `market_environment.py` 计算上证MA20时
- `scan_candidate.py` 的市场状态检测
- 任何需要获取指数K线数据的场景

## 实测案例

2026-07-31: market_environment.py 计算上证MA20时,
因只查找 `qfqday` key 导致返回空列表,
MA20回退为当前价格(3838.24=3838.24),
偏离度显示0.0%(实际应为-1.41%)。

修复后正确计算: MA20=3894.03, 偏离=-1.41%。
