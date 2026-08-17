# stock-analysis V5.2

A股股票深度分析系统 — 脚本强制采集 + agent纯分析 + 校验闭环

## 架构

```
用户: "深度分析XX"
    ↓
阶段1: deep_analysis.py (15步数据采集, 脚本强制执行)
    ↓
阶段2: agent 纯分析 (读JSON → 解读 → 评分 → 写报告)
    ↓
阶段3: validate_report.py (11项完整性校验)
```

## 文件结构

```
├── SKILL.md                    # V5.0 分析方法论(336行, 精简版)
├── README.md                   # 本文档
├── scripts/
│   ├── deep_analysis.py        # V5核心: 15步数据采集(978行)
│   ├── validate_report.py      # V5校验: 11项检查(161行)
│   ├── sector_analysis.py      # 板块分析(本地副本, 221行)
│   └── news_analysis.py        # 消息面分析(本地副本, 470行)
├── references/                 # 13个参考文档
├── strategies/                 # 16个选股策略YAML
└── templates/                  # 3个报告模板
```

## deep_analysis.py 15步

| Step | 名称 | 数据源 | 说明 |
|------|------|--------|------|
| 0 | 前复权检查 | K线跳空检测 | 检测近30日是否有除权 |
| 1 | 核心数据速览 | 腾讯行情(内联) | 现价/PE/PB/市值 |
| 2 | 历史复盘 | stock-reports目录 | 对比上次报告结论 |
| 3 | 市场环境 | 腾讯指数+东财板块 | 大盘+板块+概念TOP |
| 1E | 板块分析 | sector_analysis.py | 个股vs板块强弱 |
| 3B | 北向资金 | 同花顺hsgtApi | 沪股通/深股通 |
| 4 | 量价关系 | 腾讯K线(前复权) | 30日K线+形态+均线 |
| 5 | 资金流向 | mx-data API | 近6日主力资金+DDX/DDY |
| 6 | 均线技术 | 计算得出 | MA/MACD/RSI/ATR |
| 7 | 估值基本面 | 腾讯行情 | PE/PB/市值 |
| 8 | 综合评分 | 5维度加权 | 量价+技术+资金+估值+消息 |
| 10 | 情绪周期 | 换手率5档 | 冷淡/正常/活跃/过热/极热 |
| 11 | 概念映射 | 东财datacenter | 全部概念标签+纯度 |
| 12 | 消息面 | news_analysis.py | 新闻情绪+利好/利空 |
| 14 | 风险筛查 | 7项清单 | 减持/业绩/监管/估值/技术 |
| 15 | 附录 | — | 完整K线数据 |

## 依赖

- Python 3.11+
- MX_APIKEY环境变量 (mx-data资金流API认证)
- requests库 (news_analysis.py使用)
- 无外部skill依赖 (所有脚本已内置到scripts/)

## 用法

```bash
# 数据采集 (15步, 输出JSON)
python3 scripts/deep_analysis.py <股票代码> [股票名称]

# 报告校验 (11项检查)
python3 scripts/validate_report.py <报告.md> <JSON路径>
```

## 版本历史

- **V5.2** (2026-08-17): SKILL.md精简(3487→336行)
- **V5.1** (2026-08-17): 资金流切换mx-data, 内联quote_utils, 脚本自包含
- **V5.0** (2026-08-17): 脚本强制采集+agent纯分析+校验闭环
- **V4.0** (2026-08-13, 已废弃): 4文件拆分, 因agent漏加载失败
- **V3.1.0** (2026-07-27): 单体架构, agent可跳过步骤

## License

Internal use only.
