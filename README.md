# stock-analysis V5.0

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
├── deep_analysis.py          # V5核心: 15步数据采集器 (971行)
├── validate_report.py        # V5报告校验器 (155行)
├── SKILL.md                  # 分析方法论 (V3单体架构)
├── V5_UPGRADE_PLAN.md        # V5升级方案文档
├── references/               # 技术形态+数据源+历史教训
├── templates/                # 各类分析报告模板
├── strategies/               # 16个选股策略YAML
└── deep_analysis_v4_backup.py # V4版本备份(679行)
```

## deep_analysis.py 15步

| Step | 名称 | 数据源 | 说明 |
|------|------|--------|------|
| 0 | 前复权检查 | K线跳空检测 | 检测近30日是否有除权 |
| 1 | 核心数据速览 | 腾讯行情 | 现价/PE/PB/市值 |
| 2 | 历史复盘 | stock-reports目录 | 对比上次报告结论 |
| 3 | 市场环境 | 腾讯指数+东财板块 | 大盘+板块+概念TOP |
| 1E | 板块分析 | sector_analysis.py | 个股vs板块强弱 |
| 3B | 北向资金 | 同花顺hsgtApi | 沪股通/深股通 |
| 4 | 量价关系 | 腾讯K线(前复权) | 30日K线+形态+均线 |
| 5 | 资金流向 | 东财push2his | 20日逐日主力资金 |
| 6 | 均线技术 | 计算得出 | MA/MACD/RSI/ATR |
| 7 | 估值基本面 | 腾讯行情 | PE/PB/市值 |
| 8 | 综合评分 | 5维度加权 | 量价+技术+资金+估值+消息 |
| 10 | 情绪周期 | 换手率5档 | 冷淡/正常/活跃/过热/极热 |
| 11 | 概念映射 | 东财datacenter | 全部概念标签+纯度 |
| 12 | 消息面 | news_analysis.py | 新闻情绪+利好/利空 |
| 14 | 风险筛查 | 7项清单 | 减持/业绩/监管/估值/技术 |
| 15 | 附录 | — | 完整K线数据 |

## 用法

```bash
# 数据采集 (15步, 输出JSON)
python3 deep_analysis.py <股票代码> [股票名称]

# 报告校验 (11项检查)
python3 validate_report.py <报告.md> <JSON路径>
```

## JSON输出示例

```json
{
  "code": "000400",
  "name": "许继电气",
  "version": "5.0",
  "steps_completed": ["step0","step1","step2",...,"step15"],
  "quote": {"price": 22.14, "pe_ttm": 21.06, ...},
  "ex_right_check": {"ex_right": false, "checked": true},
  "indices": {"上证指数": {"price": 3949, "change_pct": 0.56}},
  "northbound": {"hgt": -9.28, "sgt": 379.75, "total": 370.47},
  "sector_analysis": {...},
  "klines_30d": [...],
  "indicators": {"ma5": 22.29, "rsi6": 37.21, ...},
  "fund_flow": [...],
  "sentiment": {"turnover_level": "正常平稳", "volume_trend": "缩量"},
  "concept_blocks": {"blocks": [...], "count": 27},
  "news_analysis": {"sentiment": "偏多", "score": 1.0},
  "risks": [...],
  "scores": {"score_100": 55.5, ...}
}
```

## 版本历史

- **V5.0** (2026-08-17): 脚本强制采集+agent纯分析+校验闭环
- **V4.0** (2026-08-13, 已废弃): 4文件拆分, 因agent漏加载失败
- **V3.1.0** (2026-07-27): 单体架构, agent可跳过步骤

## 依赖

- Python 3.11+
- quote_utils.py (腾讯行情工具)
- sector_analysis.py (板块分析, 可选)
- news_analysis.py (新闻分析, 可选)

## License

Internal use only.
