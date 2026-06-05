# 魔改 Stock Analysis Framework

融合两套A股分析系统精华的统一股票分析方法论。

## 来源

- **Hermes Agent 量价分析体系**: 深度K线量价关系解读、5源新闻情绪打分、主力行为逐K线追踪
- **daily_stock_analysis 多Agent策略框架**: 可插拔策略YAML、7条核心理念、评分体系、大盘复盘、风控机制

## 核心特点

1. **量价关系为王** — 通过逐日K线+成交量判断主力建仓/洗盘/拉升/出货
2. **每个判断必须有K线实例** — 不能空口说结论
3. **资金流只是验证** — 量价才是主力真实意图
4. **综合评分体系** — 量价30%+技术25%+资金20%+消息15%+估值10%
5. **风险一票否决** — high级风险直接降为卖出

## 文件结构

```
├── README.md                    # 本文件
├── SKILL.md                     # 完整分析方法论(Hermes skill格式)
├── strategies/                  # daily_stock_analysis 16个可插拔策略
│   ├── bull_trend.yaml          # 默认多头趋势
│   ├── shrink_pullback.yaml     # 缩量回踩
│   ├── ma_golden_cross.yaml     # 均线金叉
│   ├── volume_breakout.yaml     # 放量突破
│   ├── dragon_head.yaml         # 龙头策略
│   ├── bottom_volume.yaml       # 底部放量
│   ├── box_oscillation.yaml     # 箱体震荡
│   ├── chan_theory.yaml          # 缠论
│   ├── wave_theory.yaml          # 波浪理论
│   ├── emotion_cycle.yaml        # 情绪周期
│   ├── event_driven.yaml         # 事件驱动
│   ├── hot_theme.yaml            # 热点题材
│   ├── growth_quality.yaml       # 成长质量
│   ├── expectation_repricing.yaml # 预期重估
│   ├── one_yang_three_yin.yaml   # 一阳夹三阴
│   └── README.md                 # 策略编写指南
└── templates/                   # 输出模板
    ├── stock_report.md           # 个股分析报告模板
    ├── market_review.md          # 大盘复盘模板
    └── comparison.md             # 多票横向对比模板
```

## 快速开始

### 个股分析

按SKILL.md中的5步法执行：
1. 量价关系分析 → 判断主力阶段
2. 资金流向验证 → 数字印证量价
3. 技术面+均线 → 趋势配合
4. 估值+基本面 → 安全边际
5. 消息面+风险 → 催化/风控

### 加仓决策

检查5项信号：
- [ ] 量价关系确认主力未出货
- [ ] 均线多头排列
- [ ] 价格站稳MA10上方
- [ ] 主力资金连续流入
- [ ] 估值合理

### 大盘复盘

检查趋势结构+资金情绪+主线板块，判断进攻/均衡/防守。

## 7条核心交易理念

1. 严进策略 — 乖离率<5%才考虑入场
2. 趋势交易 — 多头排列顺势而为
3. 效率优先 — 关注筹码结构好的票
4. 买点偏好 — MA5/MA10回踩买入
5. 风险排查 — 高风险一票否决
6. 量价配合 — 成交量验证价格运动
7. 龙头放宽 — 龙头股可适当放宽标准

## License

MIT
