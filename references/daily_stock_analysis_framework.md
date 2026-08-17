# daily_stock_analysis 策略框架参考

> 来源: https://github.com/ZhuLinsen/daily_stock_analysis
> 本地路径: /home/harry/daily_stock_analysis
> 提取日期: 2026-06-05

## 架构概览

多Agent协作分析系统，4种模式(quick/standard/full/specialist)：
- TechnicalAgent: K线/均线/MACD/RSI/量价/筹码
- IntelAgent: 新闻/公告/资金流向/风险信号
- RiskAgent: 减持/业绩雷/监管/解禁/估值异常
- SkillAgent: 可插拔策略评估
- DecisionAgent: 加权汇总(技术40%+情报30%+风险30%+策略20%)

## 16个策略YAML

已提取到 /home/harry/stock-analysis-framework/strategies/

| 策略 | 分类 | 适配市场状态 | 优先级 |
|------|------|-------------|--------|
| bull_trend(默认多头趋势) | trend | trending_up | 10(最高) |
| shrink_pullback(缩量回踩) | trend | trending_down,sideways | 40 |
| ma_golden_cross(均线金叉) | trend | trending_up | 20 |
| volume_breakout(放量突破) | trend | trending_up | 30 |
| hot_theme(热点题材) | framework | sector_hot | 35 |
| event_driven(事件驱动) | framework | sector_hot,volatile | 45 |
| box_oscillation(箱体震荡) | framework | sideways | 50 |
| growth_quality(成长质量) | framework | trending_up | 55 |
| bottom_volume(底部放量) | reversal | trending_down | 60 |
| expectation_repricing(预期重估) | framework | volatile,sector_hot | 65 |
| chan_theory(缠论) | framework | volatile | 70 |
| wave_theory(波浪理论) | framework | volatile | 80 |
| dragon_head(龙头策略) | trend | sector_hot | 90 |
| emotion_cycle(情绪周期) | framework | sector_hot | 100 |
| one_yang_three_yin(一阳夹三阴) | pattern | — | 110 |

## 核心评分体系

```
80-100分: 买入(条件全满足,高确信)
60-79分:  买入(多数积极,小瑕疵)
40-59分:  持有(信号混合或有风险)
20-39分:  卖出(趋势偏空+风险)
0-19分:   卖出(高风险+看空)
```

## 大盘复盘三段式(A股)

1. 趋势结构: 上证/深证/创业板同向性+量能+关键位
2. 资金情绪: 涨跌家数+成交额扩张+高位股分歧
3. 主线板块: 领涨催化+龙头带动+领跌扩散
→ 输出: 进攻(共振上行) / 均衡(分化震荡) / 防守(转弱减仓)

## 可借鉴但未合并到stock-analysis的

- 策略YAML可插拔框架(用户写YAML即可定义新策略，无需代码)
- SkillAgent独立评估每个策略的满足条件
- 市场状态自动路由(market_regimes标签匹配当前行情)
- 情绪周期逆向布局思路
- 缠论/波浪理论高级形态分析
