# Stock Analysis Framework

融合两套A股分析系统精华的统一股票分析方法论。

## 版本: V2.2 (2026-07-21)

## 分析流程: 8步法

| 步骤 | 内容 | 数据源 |
|------|------|--------|
| 1 前复权 | 除权记录+手动复权计算 | mootdx xdxr |
| **2 市场环境** | **大盘+北向+板块TOP+个股所属板块(sector_analysis.py)** | **腾讯+东财+脚本** |
| 3 量价关系 | 逐日K线+成交量→判断主力阶段+组合形态 | 东财K线 |
| 4 资金流向 | 主力/散户/超大单20日逐日 | 东财push2his |
| 5 均线技术 | MA5/10/20/30+偏离度+排列 | K线计算 |
| 6 估值基本面 | PE/PB/PEG+财务数据+机构预期 | 腾讯+akshare |
| 7 概念板块 | 完整概念映射+核心vs蹭概念 | 同花顺+东财 |
| 8 消息面 | 5源新闻+情绪打分+风险筛查 | news_analysis.py |

## V2.2更新日志 (2026-07-21)

### 策略改进(7项,来源: 深科技/凯盛/通富微电三票复盘)

1. **超跌反弹修正** — 跌幅>30%时评分自动+10-15分缓冲,防止极度看空
2. **板块联动修正** — 多只同板块票同时异动时,先排查板块催化再下结论
3. **评分震荡修正** — 评分震荡>30分(1周内)禁止极端方向判断(80+或<20)
4. **利好兑现出货硬规则** — 利好当天收盘=最高+次日天量→自动触发见顶标记
5. **盘中数据局限性** — 盘中报告必须标注"收盘后可能有重大变化"
6. **出货完成度修正** — 出货完成度>80%时从"看空"调为"中性"
7. **暴跌后止损动态调整** — 暴跌40%+后切换为"观察反转信号"模式

### 新增Reference文件

| 文件 | 内容 |
|------|------|
| strategy-improvements-20260721.md | 7项策略改进详细记录 |
| benefit-cashing-out-pattern.md | 利好兑现出货案例(通富微电) |
| kline-data-fabrication-case-study.md | K线数据编造案例(通富微电79.39) |
| tongfu-v2-report-failure-case-study.md | 通富微电V2报告80.5分失败案例 |

### Pitfall新增

- 超跌反弹权重被系统性低估
- 板块联动效应必须纳入分析
- 评分震荡模式的正确处理
- 利好兑现出货硬规则
- 盘中数据局限性
- 出货完成度>80%应中性偏多
- 暴跌后止损策略需动态调整

## V2.1更新日志 (2026-07-03)

新增 sector_analysis.py 脚本，分析个股所属板块:
- 全部概念板块今日涨跌幅
- 个股vs板块相对强弱
- 板块近5日趋势
- 同板块标的横向对比

## 文件结构

```
SKILL.md                    # 主分析框架(V2.2, 8步法)
references/                 # API文档+产业链图谱+策略改进记录
  strategy-improvements-20260721.md  # V2.2策略改进
  benefit-cashing-out-pattern.md     # 利好兑现出货案例
  kline-data-fabrication-case-study.md  # K线数据编造案例
  tongfu-v2-report-failure-case-study.md # 通富V2失败案例
  tencent-api-fields.md      # 腾讯API字段映射
  eastmoney-api.md           # 东财API文档
  market-data-api.md         # 市场数据API速查
  stock-code-lookup.md       # 股票代码查询
  daily_stock_analysis_framework.md  # 16个策略YAML
  ...
strategies/                 # 14个策略YAML
templates/                  # 输出模板
```

## 免责声明

本框架仅供学习和研究使用，不构成投资建议。
