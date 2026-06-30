# Stock Analysis Framework

融合两套A股分析系统精华的统一股票分析方法论。

## 来源

- **Hermes Agent 量价分析体系**: 深度K线量价关系解读、5源新闻情绪打分、主力行为逐K线追踪
- **daily_stock_analysis 多Agent策略框架**: 可插拔策略YAML、7条核心理念、评分体系、大盘复盘、风控机制

## 核心特点

1. **市场环境先行** — 每次分析必先扫描大盘+板块+北向资金，为个股提供参照系
2. **量价关系为王** — 通过逐日K线+成交量判断主力建仓/洗盘/拉升/出货
3. **每个判断必须有K线实例** — 不能空口说结论
4. **资金流只是验证** — 量价才是主力真实意图
5. **综合评分体系** — 量价30%+技术25%+资金20%+消息15%+估值10%
6. **风险一票否决** — high级风险直接降为卖出

## 分析流程

### V2.0 六步法(含市场环境)

| 步骤 | 内容 | 数据源 |
|------|------|--------|
| ⓪ 前复权 | 除权记录+手动复权计算 | mootdx xdxr |
| **0.5 市场环境** | **大盘指数+北向资金+板块涨跌+个股vs板块强弱** | **腾讯API+东财+同花顺** |
| ① 量价关系 | 逐日K线+成交量→判断主力阶段 | 东财K线/mootdx |
| ② 资金流向 | 主力/散户/超大单20日逐日 | 东财push2his |
| ③ 均线技术 | MA5/10/20/30+偏离度+排列 | K线计算 |
| ④ 估值基本面 | PE/PB/PEG+财务数据+机构预期 | 腾讯+akshare+东财研报 |
| ⑤ 消息风险 | 5源新闻情绪+风险筛查 | news_analysis.py |

### 市场环境模块(V2.0新增)

分析个股前必先获取：
- **大盘指数**: 上证/深证/创业板/科创50 (腾讯API批量)
- **北向资金**: 沪股通/深股通当日净流入 (同花顺hsgtApi)
- **概念板块**: 涨幅TOP15+跌幅TOP5 (东财API)
- **行业板块**: 涨幅TOP10 (东财API)
- **个股vs板块**: 所属板块今日涨跌 vs 个股涨跌 → 判断强弱

影响规则:
- 大盘强+板块强+个股强 → 🟢 独立强势
- 大盘弱+板块弱+个股弱 → 🔴 系统性风险
- 大盘弱+板块强 → 独立行情，警惕补跌

## 文件结构

```
├── README.md                    # 本文件
├── .gitignore                   # 防止敏感文件提交
├── SKILL.md                     # 完整分析方法论(Hermes skill格式, ~1600行)
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
├── references/                  # 参考文档(V2.0新增)
│   ├── tencent-api-fields.md    # 腾讯行情API字段映射
│   ├── eastmoney-api.md         # 东财K线/资金流API参考
│   ├── daily_stock_analysis_framework.md # 16策略YAML详情
│   ├── serenity-bottleneck-framework.md  # Serenity瓶颈投资法
│   ├── stock-code-lookup.md     # 股票代码查询+易混淆表
│   ├── mlcc-sector-mapping.md   # MLCC产业链图谱
│   ├── glass-substrate-tgv-industry.md # TGV玻璃基板产业链
│   └── tgv-glass-substrate-map.md      # 半导体TGV图谱
└── templates/                   # 输出模板
    ├── stock_report.md           # 个股分析报告模板
    ├── market_review.md          # 大盘复盘模板
    └── comparison.md             # 多票横向对比模板
```

## 7条核心交易理念

1. 严进策略 — 乖离率<5%才考虑入场
2. 趋势交易 — 多头排列顺势而为
3. 效率优先 — 关注筹码结构好的票
4. 买点偏好 — MA5/MA10回踩买入
5. 风险排查 — 高风险一票否决
6. 量价配合 — 成交量验证价格运动
7. 龙头放宽 — 龙头股可适当放宽标准

## 版本历史

### V2.0 (2026-06-30)
- 新增步骤0.5: 市场环境扫描(大盘+板块+北向+个股vs板块强弱)
  - 6个数据获取模块(A-F)
  - 市场环境对个股分析的影响规则矩阵
- 标准输出模板新增"0、市场环境"板块
- 子agent委托模板新增市场环境扫描为第0步
- 同步references/目录(8个参考文档)
- 添加.gitignore防止敏感文件提交

### V1.0 (初始版本)
- 5步分析法: 量价→资金→均线→估值→消息
- 7条核心交易理念
- 综合评分体系(量价30%+技术25%+资金20%+消息15%+估值10%)
- 16个可插拔策略YAML
- 3个输出模板

## 回滚方法

```bash
# 查看所有版本
git tag -l

# 回滚到指定版本
git checkout v1.0

# 基于某个版本建新分支
git checkout -b hotfix v1.0
```

## License

MIT
